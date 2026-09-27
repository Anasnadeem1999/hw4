# Campus Customs — Yale Bulldog Blue

A customer-facing storefront for Campus Customs, the officially licensed Yale
merchandise shop at 57 Broadway in New Haven.

Shoppers can browse the catalogue, open a product for full detail with live
size and stock information, create an account, and chat with an AI shopping
assistant that searches the catalogue and puts matching products on the page.
Every price and stock figure the assistant quotes is read from the local
database at the moment it answers.

Built for Yale SOM MGT 409, Homework 4.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | Python + FastAPI |
| Agent | PydanticAI |
| Database | SQLite |
| Model | `gpt-5.6-luna` via the Portkey gateway |

---

## 1. Add the data pack

The database and product images are **not** in this repository. Unpack the
provided data archive into the project root so the folder looks like this:

```
data/
  campus_customs.db
  products/
    2025-yale-vs-harvard-t-shirt.jpg
    ...
```

The backend reads `data/campus_customs.db` and serves `data/products/` as
images. Nothing works until this folder is in place.

## 2. Add your environment file

```bash
cp .env.example .env
```

Then open `.env` and set `PORTKEY_API_KEY` to your key. `SECRET_KEY` is
optional for local use — without it, sessions simply end when the server
restarts.

`.env` is gitignored and must never be committed.

## 3. Run the backend

From the project root, create the virtual environment and install
dependencies:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Then start the API **from the `backend/` folder**:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Check it with <http://127.0.0.1:8000/api/health> — it should report the number
of products loaded.

## 4. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **<http://localhost:5173>**.

> Use `localhost`, not `127.0.0.1` — Vite binds IPv6 by default. The dev server
> proxies `/api` and `/images` through to port 8000, so the browser treats
> everything as one origin and no CORS configuration is needed.

### Signing in

The provided database ships with a test account:

```
test@campuscustoms.yale.edu  /  password
```

Creating a new account from the header also works, and a signed-in shopper's
chat history is saved and reloaded on their next visit. Guests can chat too,
but nothing is stored for them.

---

## Project layout

```
AI_prompts.md          Log of the prompts used to build this, one per problem
requirements.txt       Python dependencies
.env.example           Environment template — placeholders only
README.md              This file

backend/
  main.py              FastAPI app: catalogue, accounts, chat, image serving
  agent.py             PydanticAI agent wiring, guardrails, audit writing
  tools.py             The tools the agent can call, plus catalogue queries
  models.py            Pydantic types, loop limits and result caps
  auth.py              Password hashing and session cookies
  db.py                Shared SQLite connection
  audit.py             Append-only audit trail writer
  prompts/prompt.md    System prompt: shop voice and safety rules

frontend/
  src/pages/           Home, Products, ProductDetail, About, Login, CreateAccount
  src/components/      NavBar, ProductCard, ChatWidget, ChatMatches, Footer
  src/auth.tsx         Session state
  src/chatResults.tsx  Products the assistant has matched, shown on the page
  scripts/             Playwright scripts that capture output/app_check.html

output/
  harness.md           How the system works and why it is built this way
  design.md            The visual design and the reasoning behind it
  usability.md         Four usability improvements
  app_check.html       Three checks against the live site — open in a browser
  app_check_images/    Screenshots used by app_check.html
  audit_trail.json     Append-only record of every agent turn

data/                  The provided data pack — not committed
```

## Notes

This is coursework, not a real storefront. No orders are taken and no payment
is processed. The assistant cannot take payment or look up an order, and will
refuse card or credential details if they are typed into the chat.

The site is modelled on the real Campus Customs / Yale Bulldog Blue shop; all
page copy here is our own paraphrase rather than the shop's published text.
