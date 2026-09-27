"""Campus Customs — FastAPI app.

Run from the backend folder:

    uvicorn main:app --reload --port 8000

Serves the catalogue, the product images, the account endpoints, and the chat
route that the frontend widget talks to. Price and stock are always read live
from SQLite, so the storefront can never quote a stale number.
"""

from __future__ import annotations

import sqlite3

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import auth
import tools
from agent import answer, looks_sensitive
from db import IMAGES_DIR, connect
from models import (
    ChatDeps,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    ProductDetail,
    ProductSummary,
    RegisterRequest,
    UserOut,
)

app = FastAPI(title="Campus Customs API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def row_to_user(row: sqlite3.Row) -> UserOut:
    return UserOut(
        id=row["id"],
        name=row["name"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        created_at=row["created_at"],
    )


def current_user(token: str | None) -> sqlite3.Row | None:
    """Resolve the session cookie to a user row, or None."""
    user_id = auth.read_session_token(token)
    if user_id is None:
        return None
    with connect() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.get("/api/health")
def health() -> dict:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "products": count, "images": IMAGES_DIR.exists()}


# ------------------------------------------------------------------ catalogue


@app.get("/api/categories", response_model=list[str])
def list_categories() -> list[str]:
    return tools.categories()


@app.get("/api/products", response_model=list[ProductSummary])
def list_products(category: str | None = None, q: str | None = None) -> list[ProductSummary]:
    return tools.all_products(category=category, q=q)


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> ProductDetail:
    detail = tools.product_detail(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return detail


# ----------------------------------------------------------------------- auth


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        auth.SESSION_COOKIE,
        auth.create_session_token(user_id),
        max_age=auth.SESSION_MAX_AGE,
        httponly=True,  # not readable from JavaScript, so XSS cannot steal it
        samesite="lax",
        path="/",
    )


@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, response: Response) -> UserOut:
    first = payload.first_name.strip()
    last = payload.last_name.strip()
    email = payload.email.strip().lower()
    # `users.name` is NOT NULL and overlaps first_name/last_name, so all three
    # are written together to stop the profile and the greeting drifting apart.
    full_name = f"{first} {last}"

    with connect() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (full_name, email, auth.hash_password(payload.password), first, last),
            )
        except sqlite3.IntegrityError:
            # users.email carries a UNIQUE index — let the database be the
            # authority rather than pre-checking and racing.
            raise HTTPException(
                status_code=409, detail="An account with that email already exists."
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    set_session_cookie(response, row["id"])
    return row_to_user(row)


@app.post("/api/auth/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response) -> UserOut:
    email = payload.email.strip().lower()
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    # The same message either way, so the response cannot be used to discover
    # which email addresses have accounts.
    if row is None or not auth.verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    set_session_cookie(response, row["id"])
    return row_to_user(row)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(auth.SESSION_COOKIE, path="/")


@app.get("/api/auth/me", response_model=UserOut | None)
def me(campus_customs_session: str | None = Cookie(default=None)) -> UserOut | None:
    """Who the session cookie belongs to, or null.

    Browsing signed out is a normal state, not an error, so this answers 200
    with `null` rather than 401. Every page load calls it; returning an error
    status would fill a visitor's console with red 401s for simply not having
    an account yet. The same reasoning as `/api/chat/history`.
    """
    row = current_user(campus_customs_session)
    return row_to_user(row) if row is not None else None


# ----------------------------------------------------------------------- chat


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
def chat_history(
    campus_customs_session: str | None = Cookie(default=None),
) -> ChatHistoryResponse:
    """The signed-in shopper's saved conversation, so it reloads when they return.

    Guests get an empty list rather than a 401 — having no saved history is a
    normal state for them, not an error.
    """
    row = current_user(campus_customs_session)
    if row is None:
        return ChatHistoryResponse(messages=[])
    return ChatHistoryResponse(messages=tools.load_chat_history(row["id"]))


@app.delete("/api/chat/history", status_code=204)
def clear_chat_history(
    campus_customs_session: str | None = Cookie(default=None),
) -> None:
    """Let a signed-in shopper delete their own saved conversation."""
    row = current_user(campus_customs_session)
    if row is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (row["id"],))
        conn.commit()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    campus_customs_session: str | None = Cookie(default=None),
) -> ChatResponse:
    """One turn of conversation with the shopping assistant.

    Identity comes from the session cookie and page context from the request
    body; both are assembled into `ChatDeps` here rather than anywhere the
    model can influence.

    Signed-in shoppers have their conversation loaded from and written back to
    `chat_messages`. Guests chat normally but nothing is saved — their history
    rides along in the request instead.
    """
    row = current_user(campus_customs_session)

    deps = ChatDeps()
    if row is not None:
        deps.user_id = row["id"]
        deps.user_name = row["name"]
        deps.user_email = row["email"]
        deps.user_first_name = row["first_name"] or row["name"].split(" ")[0]

    if payload.page:
        deps.page_path = payload.page.path
        if payload.page.product_id:
            # Resolve the id to a real product name. An id the catalogue does
            # not know is dropped rather than passed through, so a crafted
            # request cannot inject a fake product into the agent's context.
            name = tools.product_name_for(payload.page.product_id)
            if name:
                deps.page_product_id = payload.page.product_id
                deps.page_product_name = name

    # Signed-in: the database is the source of truth for history. Guests: the
    # browser's copy, since there is nothing stored for them.
    if deps.is_signed_in:
        history = tools.history_as_messages(tools.load_chat_history(deps.user_id))
    else:
        history = payload.history

    try:
        response = await answer(payload.message, history=history, deps=deps)
    except RuntimeError as exc:
        # Missing API key or missing prompt file — a setup problem, not a bug
        # in the conversation.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="The shopping assistant is unavailable right now. Please try again.",
        )

    # Persist only after a successful reply, so a failed turn does not leave a
    # dangling question in the shopper's saved history.
    #
    # A message carrying card or credential data is never written at all. The
    # agent already refused to send it to the model; storing it would be the
    # same mistake with a longer shelf life.
    if deps.is_signed_in and not looks_sensitive(payload.message):
        tools.save_chat_message(deps.user_id, "user", payload.message)
        tools.save_chat_message(
            deps.user_id, "assistant", response.reply, response.products
        )

    return response
