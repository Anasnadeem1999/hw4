"""Catalogue lookups, and the tools the agent can call.

Everything the agent is allowed to know about the shop comes through here, and
every function reads SQLite directly. Nothing is cached, so a price or a stock
count can never be stale, and the model has no way to answer from memory.
"""

from __future__ import annotations

import functools
import json
import sqlite3
import time

from pydantic_ai import RunContext

from db import connect
from models import (
    ChatDeps,
    ChatMessage,
    MAX_HISTORY_TURNS,
    MAX_SEARCH_RESULTS,
    InventoryReport,
    PriceInfo,
    StoredChatMessage,
    ProductCard,
    ProductDetail,
    ProductSearchResult,
    ProductSummary,
    SizeAvailability,
    SizeQuantity,
    SizeStock,
    clip,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
CANONICAL_CATEGORIES = [
    "T-Shirts",
    "Crewnecks",
    "Hoodies",
    "Quarter-Zips",
    "Jackets",
    "Performance",
]


# --------------------------------------------------------------------------
# Row shaping
# --------------------------------------------------------------------------


def normalise_category(garment_type: str) -> str:
    """Fold the 22 raw `garment_type` values into one clean set.

    The column has case-only duplicates ("short-sleeve t-shirt" vs
    "short-sleeve T-shirt") and synonyms ("hoodie", "pullover hoodie",
    "hooded sweatshirt"); see output/harness.md, Problem 2.
    """
    g = garment_type.lower()
    if "quarter-zip" in g or "1/4" in g:
        return "Quarter-Zips"
    if "hood" in g:
        return "Hoodies"
    if "jacket" in g:
        return "Jackets"
    if "t-shirt" in g or "tee" in g:
        return "T-Shirts"
    if "performance" in g or "long-sleeve" in g:
        return "Performance"
    if "crewneck" in g or "sweatshirt" in g or "mockneck" in g:
        return "Crewnecks"
    return "Other"


def image_url_for(image_file_path: str) -> str:
    """Map a stored "products/x.jpg" path onto the /images mount."""
    return "/images/" + image_file_path.removeprefix("products/")


def shorten(text: str, limit: int = 110) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;") + "…"


def availability_map(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """In-stock sizes for every product, in one query.

    Doing this per card would be 102 extra queries on the Products page; this
    is a single grouped read instead.
    """
    rows = conn.execute(
        "SELECT product_id, size FROM inventory WHERE quantity > 0"
    ).fetchall()
    found: dict[str, list[str]] = {}
    for r in rows:
        found.setdefault(r["product_id"], []).append(r["size"])
    order = {s: i for i, s in enumerate(SIZE_ORDER)}
    for sizes in found.values():
        sizes.sort(key=lambda s: order.get(s, len(order)))
    return found


def row_to_summary(
    row: sqlite3.Row, available: list[str] | None = None
) -> ProductSummary:
    return ProductSummary(
        available_sizes=available or [],
        in_stock=bool(available),
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=normalise_category(row["garment_type"]),
        short_description=shorten(row["description"]),
        price=row["price"],
        image_url=image_url_for(row["image_file_path"]),
        colors=json.loads(row["colors"]),
    )


def sizes_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    by_size = {r["size"]: r["quantity"] for r in rows}
    ordered = [s for s in SIZE_ORDER if s in by_size]
    ordered += [s for s in by_size if s not in SIZE_ORDER]
    return [
        SizeStock(size=s, quantity=by_size[s], in_stock=by_size[s] > 0) for s in ordered
    ]


def row_to_detail(conn: sqlite3.Connection, row: sqlite3.Row) -> ProductDetail:
    sizes = sizes_for(conn, row["product_id"])
    in_stock_sizes = [s.size for s in sizes if s.in_stock]
    return ProductDetail(
        **row_to_summary(row, in_stock_sizes).model_dump(),
        description=row["description"],
        search_tags=json.loads(row["search_tags"]),
        sizes=sizes,
        total_stock=sum(s.quantity for s in sizes),
    )


def row_to_card(conn: sqlite3.Connection, row: sqlite3.Row) -> ProductCard:
    summary = row_to_summary(row, [s.size for s in sizes_for(conn, row["product_id"]) if s.in_stock])
    return ProductCard(
        product_id=summary.product_id,
        name=summary.name,
        price=summary.price,
        image_url=summary.image_url,
        category=summary.category,
        short_description=summary.short_description,
        available_sizes=[s.size for s in sizes_for(conn, row["product_id"]) if s.in_stock],
    )


# --------------------------------------------------------------------------
# Catalogue queries used by both the REST routes and the agent
# --------------------------------------------------------------------------


def all_products(category: str | None = None, q: str | None = None) -> list[ProductSummary]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        available = availability_map(conn)
        products = [row_to_summary(r, available.get(r["product_id"], [])) for r in rows]
        if category:
            products = [p for p in products if p.category == category]
        if q:
            needle = q.lower()
            haystack = {
                r["product_id"]: (r["search_tags"] + " " + r["description"]).lower()
                for r in rows
            }
            products = [
                p
                for p in products
                if needle in p.name.lower() or needle in haystack.get(p.product_id, "")
            ]
    return products


def product_detail(product_id: str) -> ProductDetail | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        return row_to_detail(conn, row)


def categories() -> list[str]:
    with connect() as conn:
        rows = conn.execute("SELECT DISTINCT garment_type FROM catalogue").fetchall()
    found = {normalise_category(r["garment_type"]) for r in rows}
    return [c for c in CANONICAL_CATEGORIES if c in found] + sorted(
        found - set(CANONICAL_CATEGORIES)
    )


def _score(row: sqlite3.Row, terms: list[str]) -> int:
    """Rank a catalogue row against the shopper's words.

    Tags and the product name are weighted above the description because
    `search_tags` is the widest retrieval surface in this data — 270 distinct
    tags carrying residential college, school, and sport terms that appear
    nowhere else (see harness.md, Problem 2).
    """
    name = row["name"].lower()
    tags = " ".join(json.loads(row["search_tags"])).lower()
    colors = " ".join(json.loads(row["colors"])).lower()
    description = row["description"].lower()
    category = normalise_category(row["garment_type"]).lower()

    total = 0
    for term in terms:
        if term in name:
            total += 5
        if term in tags:
            total += 4
        if term in category:
            total += 3
        if term in colors:
            total += 2
        if term in description:
            total += 1
    return total


STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "can", "do", "does", "for",
    "from", "got", "has", "have", "how", "i", "in", "is", "it", "me", "my", "of",
    "on", "or", "s", "show", "some", "something", "that", "the", "them", "there",
    "they", "this", "to", "want", "was", "we", "what", "with", "would", "you",
    "your", "looking", "need", "like", "get", "buy",
}




# --------------------------------------------------------------------------
# Tool instrumentation
# --------------------------------------------------------------------------

BUDGET_MESSAGE = (
    "Tool budget for this turn is spent. Answer the shopper with what you "
    "already found, and do not call further tools."
)


def audited(fn):
    """Enforce the per-turn tool budget and record the call for the audit trail.

    Wrapping rather than repeating this in every tool keeps the tools readable,
    and means a new tool cannot be added that quietly skips the budget or the
    log. `functools.wraps` preserves the signature and docstring, which is what
    PydanticAI reads to describe the tool to the model.
    """

    @functools.wraps(fn)
    async def wrapper(ctx, *args, **kwargs):
        if ctx.deps.budget_spent:
            ctx.deps.log_tool(fn.__name__, "refused", "tool budget exhausted", 0)
            return BUDGET_MESSAGE

        started = time.perf_counter()
        result = await fn(ctx, *args, **kwargs)
        elapsed = int((time.perf_counter() - started) * 1000)

        shown = ", ".join(f"{k}={v!r}" for k, v in kwargs.items() if v is not None)
        if args:
            shown = ", ".join([*(repr(a) for a in args), shown]).strip(", ")
        ctx.deps.log_tool(fn.__name__, shown or "-", summarise(result), elapsed)
        return result

    return wrapper


def summarise(result) -> str:
    """One short line describing what a tool returned."""
    if isinstance(result, list):
        if not result:
            return "0 results"
        names = [getattr(r, "name", None) or str(r) for r in result[:3]]
        more = f" +{len(result) - 3} more" if len(result) > 3 else ""
        return f"{len(result)} results: " + ", ".join(names) + more
    if isinstance(result, str):
        return clip(result)
    name = getattr(result, "product_name", None) or getattr(result, "name", "")
    bits = [b for b in [name] if b]
    for attr in ("price", "size", "in_stock", "quantity", "total_quantity"):
        value = getattr(result, attr, None)
        if value is not None:
            bits.append(f"{attr}={value}")
    return clip(", ".join(bits)) if bits else clip(repr(result))


# --------------------------------------------------------------------------
# Agent tools
# --------------------------------------------------------------------------


@audited
async def search_products(
    ctx: RunContext[ChatDeps],
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    limit: int = 4,
) -> list[ProductSearchResult]:
    """Search the Campus Customs catalogue.

    Use this whenever a shopper describes what they are after — a residential
    college, a school, a sport, a colour, a garment type, or a mix. Returns the
    closest matches with their real prices and the sizes currently in stock.

    Args:
        query: What the shopper is looking for, in their own words.
        category: Optional filter: T-Shirts, Crewnecks, Hoodies, Quarter-Zips,
            Jackets, or Performance.
        max_price: Optional maximum price in dollars.
        limit: How many products to return, at most 8.
    """
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    terms = [t for t in query.lower().replace(",", " ").split() if t not in STOPWORDS]

    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()

        candidates = rows
        if category:
            wanted = category.strip().lower()
            candidates = [
                r for r in candidates if normalise_category(r["garment_type"]).lower() == wanted
            ]
        if max_price is not None:
            candidates = [r for r in candidates if r["price"] <= max_price]

        scored = [(_score(r, terms), r) for r in candidates]
        scored = [(s, r) for s, r in scored if s > 0]
        scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))

        # Nothing matched the words, but the filters still narrowed it down —
        # show the cheapest of what is left rather than returning nothing.
        chosen = [r for _, r in scored[:limit]]
        if not chosen and candidates:
            chosen = sorted(candidates, key=lambda r: r["price"])[:limit]

        results: list[ProductSearchResult] = []
        for row in chosen:
            sizes = sizes_for(conn, row["product_id"])
            ctx.deps.record(row_to_card(conn, row), "search_products")
            results.append(
                ProductSearchResult(
                    product_id=row["product_id"],
                    name=row["name"],
                    category=normalise_category(row["garment_type"]),
                    price=row["price"],
                    colors=json.loads(row["colors"]),
                    description=row["description"],
                    sizes_in_stock=[s.size for s in sizes if s.in_stock],
                )
            )
    return results


@audited
async def get_product_details(
    ctx: RunContext[ChatDeps], product_id: str
) -> ProductDetail | str:
    """Look up one product by its id, with full description, price, and every size.

    Use this when the shopper asks about a specific product you have already
    found, or wants more detail than the search returned.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return f"No product with id {product_id!r} exists in the catalogue."
        ctx.deps.record(row_to_card(conn, row), "get_product_details")
        return row_to_detail(conn, row)


@audited
async def get_price(ctx: RunContext[ChatDeps], product_id: str) -> PriceInfo | str:
    """Look up the current price of one product, in dollars.

    Use this for any question about cost. Never state a price from memory —
    the catalogue is the only source, and this reads it live.

    Args:
        product_id: The product's id.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return f"No product with id {product_id!r} exists in the catalogue."
        ctx.deps.record(row_to_card(conn, row), "get_price")
        return PriceInfo(
            product_id=row["product_id"], product_name=row["name"], price=row["price"]
        )


@audited
async def get_inventory(ctx: RunContext[ChatDeps], product_id: str) -> InventoryReport | str:
    """Get the full stock picture for a product: every size and its quantity.

    Use this when a shopper asks what sizes are available, how many are left,
    or whether a product is in stock generally. For one specific size, use
    `check_size_availability` instead.

    Args:
        product_id: The product's id.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return f"No product with id {product_id!r} exists in the catalogue."

        sizes = sizes_for(conn, product_id)
        ctx.deps.record(row_to_card(conn, row), "get_inventory")

    return InventoryReport(
        product_id=product_id,
        product_name=row["name"],
        sizes=[
            SizeQuantity(size=s.size, quantity=s.quantity, in_stock=s.in_stock)
            for s in sizes
        ],
        sizes_in_stock=[s.size for s in sizes if s.in_stock],
        sizes_sold_out=[s.size for s in sizes if not s.in_stock],
        total_quantity=sum(s.quantity for s in sizes),
        any_in_stock=any(s.in_stock for s in sizes),
    )


@audited
async def check_size_availability(
    ctx: RunContext[ChatDeps], product_id: str, size: str
) -> SizeAvailability | str:
    """Check whether one specific size of a product is in stock right now.

    Stock is tracked per size, so always use this rather than assuming a
    product is available because it exists.

    Args:
        product_id: The product's id.
        size: One of XS, S, M, L, XL, XXL.
    """
    wanted = size.strip().upper()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return f"No product with id {product_id!r} exists in the catalogue."

        sizes = sizes_for(conn, product_id)
        match = next((s for s in sizes if s.size == wanted), None)
        if match is None:
            available = ", ".join(s.size for s in sizes)
            return f"{row['name']} is not stocked in size {wanted}. Sizes carried: {available}."

        ctx.deps.record(row_to_card(conn, row), "check_size_availability")
        return SizeAvailability(
            product_id=product_id,
            product_name=row["name"],
            size=wanted,
            in_stock=match.in_stock,
            quantity=match.quantity,
            other_sizes_in_stock=[
                s.size for s in sizes if s.in_stock and s.size != wanted
            ],
        )


@audited
async def list_categories(ctx: RunContext[ChatDeps]) -> list[str]:
    """List the product categories the shop carries."""
    return categories()


# --------------------------------------------------------------------------
# Chat history (signed-in shoppers only)
# --------------------------------------------------------------------------
#
# Stored in the `chat_messages` table that ships with the database:
#   user_id, role, content, products_json, created_at
#
# Guests are never written here. Nothing calls these functions without a
# user_id, so there is no path by which a guest conversation reaches the table.

# Rows loaded when a shopper returns. Matches the per-request turn cap so the
# agent never sees more history than a request is allowed to carry.
HISTORY_LIMIT = MAX_HISTORY_TURNS


def save_chat_message(
    user_id: int,
    role: str,
    content: str,
    products: list[ProductCard] | None = None,
) -> None:
    """Append one turn to a signed-in shopper's history."""
    payload = (
        json.dumps([p.model_dump() for p in products]) if products else None
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, content, payload),
        )
        conn.commit()


def load_chat_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[StoredChatMessage]:
    """Load a shopper's recent conversation, oldest first.

    The query takes the newest `limit` rows and then flips them, so a long
    history is truncated at the old end rather than the recent end.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    messages: list[StoredChatMessage] = []
    for row in reversed(rows):
        products: list[ProductCard] = []
        if row["products_json"]:
            try:
                raw = json.loads(row["products_json"])
                # Rows seeded before this build used a different product shape,
                # so anything that does not fit the current card is skipped
                # rather than breaking the whole history load.
                for item in raw:
                    try:
                        products.append(ProductCard.model_validate(item))
                    except Exception:
                        continue
            except (ValueError, TypeError):
                products = []
        if row["role"] not in ("user", "assistant"):
            continue
        messages.append(
            StoredChatMessage(
                role=row["role"],
                content=row["content"],
                products=products,
                created_at=row["created_at"],
            )
        )
    return messages


def history_as_messages(stored: list[StoredChatMessage]) -> list[ChatMessage]:
    """Reduce saved turns to the plain role/content pairs the agent replays."""
    return [ChatMessage(role=m.role, content=m.content) for m in stored]


def product_name_for(product_id: str) -> str | None:
    """Resolve a product id to its name, for page context. None if unknown."""
    with connect() as conn:
        row = conn.execute(
            "SELECT name FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
    return row["name"] if row else None
