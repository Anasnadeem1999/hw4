# Harness Notes — Campus Customs HW4

## Problem 2 — Database analysis

Everything below was read from `data/campus_customs.db` with live queries
(`PRAGMA table_info`, plus value profiling), not inferred from filenames or
guessed from the brief.

**Database:** SQLite, 172 KB, five tables. The three in scope are `catalogue`,
`inventory`, and `users`. (`chat_messages` and `sqlite_sequence` also exist —
noted at the bottom for completeness.)

---

## `catalogue` — 102 rows, one per product

The product master. Every shopper-facing price, image, and description
resolves here.

| Field | Type | Constraints | Why it matters |
|---|---|---|---|
| `product_id` | TEXT | **PRIMARY KEY** | Slug-style id (`2025-yale-vs-harvard-t-shirt`). Stable join key to `inventory`, safe in URLs, and the token the chatbot passes back to the UI to say "show this product". |
| `name` | TEXT | NOT NULL | Human display title on cards and in chat replies. |
| `garment_type` | TEXT | NOT NULL | Category ("crewneck sweatshirt", "pullover hoodie"). Drives browse filters and lets the chatbot narrow "I want a hoodie". **Dirty — see caveat below.** |
| `description` | TEXT | NOT NULL | 93–184 chars of detail: colour, graphic, fit. The richest text the chatbot has for matching a free-text request, and good product-page copy. |
| `colors` | TEXT | NOT NULL | **JSON array** of strings, e.g. `["heather gray","white","red","navy blue"]`. Powers colour filtering and answers "do you have it in navy". Must be parsed as JSON, not string-matched. |
| `search_tags` | TEXT | NOT NULL | **JSON array**, 4–12 tags per product, 270 distinct. The primary retrieval surface for the chatbot — carries residential college, school, sport, and occasion terms that never appear in `garment_type`. |
| `image_file_path` | TEXT | NOT NULL | Relative path, always `products/<product_id>.jpg`. **Relative to `data/`, not the repo root** — the static mount must be rooted at `data/`. |
| `price` | REAL | NOT NULL | Dollars. Only 7 distinct values: 32, 45, 58, 68, 72, 88, 98 (avg 58.48). The chatbot must read this per request and never recall it, so quoted prices stay correct. |

### Caveat: `garment_type` is not clean enough to use as a filter as-is

22 distinct values across 102 products, including case-only duplicates and
synonyms meaning the same thing:

- `short-sleeve t-shirt` (16) vs `short-sleeve T-shirt` (6) vs `t-shirt` (1)
  vs `heavyweight short-sleeve t-shirt` (1) vs `short-sleeve crew-neck t-shirt` (1)
- `pullover hoodie` (18) vs `hoodie` (5) vs `hooded sweatshirt` (1)
  vs `hooded pullover sweatshirt` (1)
- `quarter-zip pullover sweatshirt` (6) vs `quarter-zip pullover` (5)
- `fleece jacket` (1) vs `full-zip fleece jacket` (5)

A browse facet built straight off this column would list the same category
several times and split the counts. It needs normalising to a small canonical
set (t-shirt / crewneck / hoodie / quarter-zip / jacket / performance) before
a shopper sees it.

`colors` has the same problem more mildly: `navy blue` (62) and `navy` (18)
are stored as different strings.

---

## `inventory` — 612 rows, stock by product and size

| Field | Type | Constraints | Why it matters |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Surrogate row id. No shopper meaning; real identity is the pair below. |
| `product_id` | TEXT | NOT NULL, **FK → `catalogue.product_id`** | Links stock to the product. |
| `size` | TEXT | NOT NULL, UNIQUE with `product_id` | One of exactly six: `XS, S, M, L, XL, XXL`. Populates the size selector. |
| `quantity` | INTEGER | NOT NULL | Units on hand, 0–25 (avg 9.7). The only honest source for "in stock" — the chatbot must query it rather than assume availability. |

### Shape of the data (checked, not assumed)

- **Perfectly regular:** every one of the 102 products carries all 6 sizes.
  612 = 102 × 6. No product is missing inventory rows, and there are no orphan
  inventory rows pointing at a product that doesn't exist.
- **Stockouts are per size, never per product.** 145 of 612 rows (24%) are
  `quantity = 0`, but **zero products are fully out of stock**.

That second point has a direct design consequence: a product-level "Sold out"
badge would never fire on this dataset. Availability belongs on the **size
selector** — grey out the sizes sitting at 0 — and the chatbot should answer
"yes, but only in S and XL" rather than a flat yes/no.

The `UNIQUE (product_id, size)` constraint means stock writes can safely be an
upsert keyed on that pair.

---

## `users` — 3 rows, shopper accounts

| Field | Type | Constraints | Why it matters |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Session identity; `chat_messages.user_id` points here, so it's how a conversation is tied to a shopper. |
| `name` | TEXT | NOT NULL | Full display name. Redundant with the two fields below — see caveat. |
| `email` | TEXT | NOT NULL, **UNIQUE** | The login identifier. The unique index means duplicate registration fails at the database level, so signup must handle that error rather than pre-checking and hoping. |
| `password_hash` | TEXT | NOT NULL | Never a plaintext password. Format is `pbkdf2_sha256$<salt>$<64-hex-digest>` — verified on all three rows. |
| `created_at` | TEXT | NOT NULL, DEFAULT `datetime('now')` | Account age. The default means inserts may omit it. |
| `first_name` | TEXT | *nullable* | Added after the fact (the column sits after `created_at`). Lets the chatbot greet a shopper by first name. |
| `last_name` | TEXT | *nullable* | Same. |

Existing rows: `Test User`, `Ada Lovelace`, `Tauhid Zaman` — all three have
both name parts filled despite the columns being nullable.

### Caveats for the signup work

1. **`name` overlaps `first_name`/`last_name`.** All three are populated today
   and nothing keeps them in sync. Registration should write all three
   consistently (`name = first + " " + last`), or the greeting and the profile
   will drift apart.
2. **`first_name`/`last_name` are nullable but `name` is NOT NULL** — the
   schema was clearly extended later. Any insert must still supply `name`.
3. **The PBKDF2 iteration count is not stored in the hash string.** Only the
   algorithm, salt, and digest are. Whatever count we choose at registration
   must be reused at login, or verification fails silently. We cannot log in as
   the three seeded users in any case — their plaintext passwords are unknown —
   so testing needs fresh accounts.

---

## Also present, out of scope for Problem 2

- **`chat_messages`** (22 rows) — `user_id` (FK → `users.id`), `role`,
  `content`, `products_json`, `created_at`. Persisted chat history, with
  `products_json` holding the products shown alongside a reply. Directly
  relevant to the chat and "matching products appear on the page" features.
- **`sqlite_sequence`** (3 rows) — SQLite's internal AUTOINCREMENT
  bookkeeping, not application data.

---

## What this means for the build

| Finding | Consequence |
|---|---|
| `colors` / `search_tags` are JSON strings | Parse them; don't `LIKE` against raw text |
| `search_tags` is the widest retrieval surface (270 distinct) | Chatbot matching should lean on tags + description, not `garment_type` |
| `garment_type` has case and synonym duplicates | Normalise before exposing as a browse facet |
| Image paths are `data/`-relative | Static mount rooted at `data/` |
| Stock hits zero per *size*, never per product | Availability UI belongs on the size selector |
| `email` is UNIQUE | Signup must handle the integrity error |
| Iteration count not stored | Fix one constant, reuse it for signup and login |
| Only 7 distinct prices | Price is cheap to filter on, and easy to verify the chatbot quoted correctly |


---

## Problem 3 — Build the Campus Customs website

### What was built

| Piece | Path |
|---|---|
| FastAPI backend | `backend/main.py` |
| React + Vite + TS app | `frontend/src/` |
| Nav bar | `components/NavBar.tsx` — Home, Products, About Us, Log in, Create account |
| Product grid | `pages/Products.tsx` + `components/ProductCard.tsx` |
| Product detail | `pages/ProductDetail.tsx` |
| Chat stub | `components/ChatWidget.tsx` — fixed bottom-right |
| Paraphrased copy | `pages/Home.tsx`, `pages/About.tsx` |

### Backend endpoints

- `GET /api/health` — row count and image-mount check
- `GET /api/products` — grid data, optional `category` and `q` filters
- `GET /api/products/{id}` — full detail including per-size stock
- `GET /api/categories` — normalised category list
- `GET /api/stats` — shop totals for the home page: `styles` (catalogue
  rows, 102) and `units_in_stock` (summed inventory quantities, 5,920).
  Kept as two separate figures because the hero counts garments on the
  shelf, and quoting the style count there would overstate nothing but
  understate the shop by a factor of 58.
- `/images/*` — static mount over `data/products/`

### Decisions

**The image mount is rooted at `data/`, not the repo root.** `catalogue.image_file_path`
stores `products/<id>.jpg`. The backend strips the `products/` prefix and serves the
folder at `/images`, so the stored path maps onto a URL without the frontend needing
to know where the data folder lives.

**Categories are normalised, not taken raw.** Problem 2 found 22 `garment_type`
values with case-only duplicates (`short-sleeve t-shirt` vs `short-sleeve T-shirt`)
and synonyms (`hoodie`, `pullover hoodie`, `hooded sweatshirt`). Shown raw, the filter
bar would list the same category several times and split the counts.
`normalise_category()` folds them into six: T-Shirts, Crewnecks, Hoodies,
Quarter-Zips, Jackets, Performance.

**Stock is shown per size, never per product.** Problem 2 found 145 of 612
inventory rows at zero but no product fully out of stock, so a product-level
"Sold out" badge would never fire. Sizes at zero are struck through and disabled;
each live size shows its remaining count, and five or fewer turns the note red.
"Add to bag" stays disabled until a size is chosen.

**Vite proxies `/api` and `/images` to port 8000.** Same-origin in the browser, so
no CORS handling is needed in the app code. CORS middleware is still configured on
the backend for direct access.

**Price is always read from SQLite per request.** Nothing is cached or hard-coded,
so a quoted price cannot go stale.

### Chat widget

Deliberately a stub. Collapsed it is a fixed bottom-right launcher; opened it is a
360px panel with a greeting, a scrolling log, and a working input that echoes the
shopper's message and replies with a fixed placeholder saying the assistant is not
connected yet. The message-list state and scroll behaviour are real, so wiring the
PydanticAI agent later means replacing one function rather than rebuilding the UI.

### Page copy

Home and About Us were written from research into yalebulldogblue.com and public
sources about the shop, then written in our own words. Facts used: the Broadway
address, that it is the oldest official Yale merchandise retailer in New Haven,
seven-day opening, official licensing, the Yale Bulldog Blue name, and the range
spanning residential colleges, graduate schools, and varsity teams. No sentence is
copied from the source site. Both pages carry a visible note that this is a student
project rather than a working storefront.

### Verified

- Backend: 102 products, all six categories, per-size stock, 404 on unknown id,
  images served at 200 with `image/jpeg`
- Through the Vite proxy: 102 products, images 200
- `tsc --noEmit` clean; `npm run build` succeeds (280 kB JS, 11 kB CSS)

### Not done yet

Log in and Create account are interface only — their submit buttons are disabled
and no request is made. Authentication is a later problem.


---

## Problem 4 — Create account and login

### How authentication works

Three endpoints in `backend/main.py`, with the cryptography in `backend/auth.py`:

| Endpoint | Does |
|---|---|
| `POST /api/auth/register` | Creates a user, hashes the password, signs them straight in |
| `POST /api/auth/login` | Verifies email + password, issues a session |
| `POST /api/auth/logout` | Clears the session cookie |
| `GET /api/auth/me` | Returns the signed-in shopper, or `null` |

**Registration.** First name, last name, email, and password are validated by
Pydantic — email must parse as a real address, password must be at least 8
characters. The email is lowercased so `Test@…` and `test@…` cannot become two
accounts. The password is hashed, never stored, and the row is inserted.

**`users.email` carries a UNIQUE index, so duplicates are caught by the
database** rather than by checking first and inserting after. Checking first
leaves a gap where two simultaneous signups both pass the check; catching
`sqlite3.IntegrityError` closes it. That becomes a 409 with a clear message.

**Login.** The row is looked up by email and the supplied password is verified
against the stored hash. A missing email and a wrong password return the
*same* 401 message — otherwise the response tells an attacker which addresses
have accounts.

**Sessions.** On success the server sets a cookie holding
`<user_id>.<expiry>.<HMAC-SHA256 signature>`. The signature covers the first
two parts, so editing the cookie to claim another user id invalidates it. The
cookie is `HttpOnly` (JavaScript cannot read it, so an XSS bug cannot steal the
session), `SameSite=Lax`, and expires after a week. Nothing sensitive is in the
cookie — just an id the server re-reads from the database on each request.

The signing key comes from `SECRET_KEY`. If unset, a random key is generated at
startup, which is fine locally and simply means sessions end when the server
restarts.

### What user information is stored

Only what the signup form collects, in the existing `users` table:

| Column | Source |
|---|---|
| `first_name`, `last_name` | Typed at signup |
| `name` | Derived — `first + " " + last` |
| `email` | Typed at signup, lowercased |
| `password_hash` | Derived from the password; the password itself is never stored |
| `created_at` | SQLite default, `datetime('now')` |

`name` is written alongside the two name parts because the column is NOT NULL
and overlaps them (noted in Problem 2). Writing all three together stops the
profile and the chat greeting from disagreeing.

**The API never returns `password_hash`.** The `UserOut` model lists the fields
the frontend may see, and FastAPI drops everything else, so the hash cannot
leak through a response by accident.

### How passwords are protected

Passwords go through **PBKDF2-HMAC-SHA256 with 120,000 iterations** and a
per-user random salt. What lands in the database is:

    pbkdf2_sha256$<16-hex-char salt>$<64-hex-char digest>

- **Hashed, not encrypted.** There is no key that turns the stored value back
  into a password. Even with the database file, an attacker has to guess.
- **Salted per user.** Two shoppers who pick the same password get different
  digests, so one cracked password reveals nothing about the other, and
  precomputed rainbow tables are useless.
- **Deliberately slow.** 120,000 iterations makes each guess expensive, which
  is what makes brute force impractical.
- **Compared in constant time.** `hmac.compare_digest` does not stop early at
  the first differing byte, so response timing does not leak how much of a
  guess was right.

**On the iteration count.** The stored format records the algorithm, salt, and
digest but *not* the iteration count, so it has to be pinned in code. 120,000
was recovered by testing candidate counts against the seeded test account until
one reproduced its digest. It is a module constant in `auth.py` with a comment
explaining that changing it would lock out every existing user.

That recovery is what lets the provided test account log in through exactly the
same code path as a new signup — no special case for seeded rows.

### Verified

| Check | Result |
|---|---|
| Log in as `test@campuscustoms.yale.edu` / `password` | 200, session issued |
| Session cookie resolves via `/api/auth/me` | 200 |
| Wrong password | 401 |
| Unknown email | 401, identical message |
| Register a new account | 201, signed in immediately |
| Log out, then `/me` | 401 |
| Log back in with the new account | 200 |
| Duplicate email | 409 |
| Password under 8 characters | 422 |
| Tampered session cookie | 401 |
| New row stored as `pbkdf2_sha256$…`, no plaintext | confirmed |
| Whole flow through the Vite proxy | cookie set `HttpOnly`, `/me` 200 |

### Known limits

Fine for coursework, not for a real shop: no rate limiting on login attempts,
no password reset, no email verification, and the cookie is not marked `Secure`
because local development is over HTTP.


---

## Problem 5 — PydanticAI agent behind FastAPI

### Backend layout

| File | Holds |
|---|---|
| `backend/main.py` | The FastAPI app and every route, including `POST /api/chat` |
| `backend/agent.py` | Agent wiring — model, prompt loading, tool registration, one-turn runner |
| `backend/tools.py` | The tools the agent can call, plus the catalogue queries the REST routes reuse |
| `backend/models.py` | Pydantic types for chat, product cards, accounts, and tool results |
| `backend/prompts/prompt.md` | The system prompt: Campus Customs voice and safety rules |
| `backend/auth.py`, `backend/db.py` | Password hashing / sessions, and the shared SQLite connection |

Imports are flat, so the app starts from inside `backend/`:

    uvicorn main:app --reload --port 8000

### How the frontend talks to FastAPI

`ChatWidget.tsx` POSTs to `/api/chat`:

```json
{ "message": "do you have the Saybrook crewneck in medium?",
  "history": [{ "role": "user", "content": "..." }] }
```

and gets back a `ChatResponse`:

```json
{ "reply": "...", "products": [ProductCard], "tools_used": ["search_products"] }
```

- The request goes to a **relative** URL. Vite proxies `/api` and `/images` to
  port 8000, so the browser treats everything as same-origin.
- `credentials: 'include'` sends the session cookie, which is how the agent
  learns who is signed in.
- `history` is the conversation so far, capped at 40 turns by the request model
  and trimmed to the last 10 before being given to the model.
- Product cards render inside the chat panel and link through to the detail
  page.

### How the agent is loaded

`build_agent()` in `agent.py`, memoised with `lru_cache` so the agent is
constructed once per process rather than per request:

1. **Model.** `MODEL_NAME` (default `gpt-5.6-luna`) through
   `OpenAIChatModel`, pointed at `PORTKEY_BASE_URL`
   (default `https://api.portkey.ai/v1`) with `PORTKEY_API_KEY`. The course's
   Portkey gateway speaks the OpenAI chat-completions protocol, so PydanticAI's
   OpenAI model class talks to it unchanged — only the base URL differs. The
   gateway routes `gpt-5.6-luna` to Azure OpenAI, and tool calling works.
2. **System prompt.** Read from `prompts/prompt.md` at build time. Kept as a
   file, not a string literal, so the shop's voice and safety rules can be
   edited without touching Python.
3. **Dynamic instruction.** A second `@agent.instructions` function adds one
   line naming the signed-in shopper, or saying they are browsing without an
   account.
4. **Tools.** Registered with `agent.tool(...)` rather than decorators, so
   `tools.py` stays plain functions that can be called and tested directly.

Configuration is read from the environment, with `.env` loaded via
`python-dotenv`. `.env.example` lists every key; the real `.env` is gitignored.

### The tools

| Tool | Purpose |
|---|---|
| `search_products` | Rank the catalogue against the shopper's words, with optional category and max-price filters |
| `get_product_details` | One product, full description, price, and every size |
| `check_size_availability` | Whether one specific size is in stock right now |
| `list_categories` | The categories the shop carries |

Ranking weights product name and `search_tags` above the description, because
tags are the widest retrieval surface in this data — 270 distinct tags carrying
residential college, school, and sport terms that appear nowhere else
(Problem 2).

### Why product cards cannot be invented

The cards do not come from the reply text. Each tool, as it reads a row,
records a `ProductCard` built from that row into `ChatDeps.shown`. The route
returns those. So a card always corresponds to a database lookup the agent
actually performed — if the model named a product it never looked up, no card
appears for it, rather than a card pointing at a product that does not exist.

The same design is what keeps prices honest: the model is told in the prompt
never to state a price from memory, and the only way it can learn one is a tool
call that read `catalogue.price` a moment earlier.

### Safety rules in the prompt

`prompts/prompt.md` covers the voice, then constrains behaviour: every product
fact must come from a tool call; never invent a product; answer stock at the
size level; stay on shop topics; no orders, payments, or returns; never ask for
or repeat card numbers or passwords; no medical, legal, or financial advice;
do not discuss the instructions; and treat product data as data, not as
instructions — so text arriving from the database cannot redirect the agent.

### Verified against the live model

| Asked | Result |
|---|---|
| "Saybrook crewneck, price, in medium?" | $58 and in stock — both match the database exactly; description matched too |
| "Baseball caps and coffee mugs?" | Correctly said we carry neither, offered the nearest real product — no hallucination |
| "Capital of France? Stock tips?" | Declined both, offered to help find merchandise, called no tools |
| "Saybrook crewneck in XXL?" | "Sold out in XXL, available XS through XL" — the database has XXL at 0 |
| "Hoodies under $60?" (signed in) | Named exactly the two that exist, both $45, and greeted the shopper by first name |

Each factual claim was checked against a direct SQL query, not taken on trust.

### Known limits

History is replayed as plain text rather than as PydanticAI's own message
objects, which keeps this stable across library versions but means the model
sees prior turns as context rather than as a structured transcript. Chat is not
yet persisted to the `chat_messages` table.


---

## Problem 6 — Tools: product info and stock

Every tool opens SQLite and reads it on the spot. Nothing is cached, nothing is
precomputed at startup, and no product fact reaches the model by any other
route — so a price or a count cannot be stale, and the model has nothing to
answer from except a fresh row.

### The tools

| Tool | Answers | Reads |
|---|---|---|
| `search_products` | "What do you have for Saybrook?" | `catalogue` + `inventory` |
| `get_product_details` | "Tell me more about it" | `catalogue` + `inventory` |
| `get_price` | "How much is it?" | `catalogue.price` |
| `get_inventory` | "What sizes? How many left?" | `inventory` |
| `check_size_availability` | "Do you have it in M?" | `inventory` for one size |
| `list_categories` | "What do you sell?" | `catalogue.garment_type` |

### Return types, and why these fields

**`ProductSearchResult`** — `product_id`, `name`, `category`, `price`,
`colors`, `description`, `sizes_in_stock`.

The search result has to carry enough that a recommendation needs no second
call: what it is, what it costs, what it looks like, what can actually be
bought. `product_id` is first because it is the handle for every other tool.
`sizes_in_stock` lists only sizes above zero — the model should not have to
filter a list and risk inverting it. Raw `garment_type` is deliberately *not*
exposed; the model sees the normalised `category` instead, because the raw
column has case duplicates and synonyms (Problem 2) that would make the model
describe the same thing two different ways.

**`PriceInfo`** — `product_id`, `product_name`, `price`, `currency`.

Deliberately minimal. The prompt forbids stating a price from memory, so this
exists to make the correct move cheap: one call, one number, nothing to
misread. `product_name` is included so the model can confirm out loud *which*
product it priced, which is how a wrong-product answer becomes visible to the
shopper instead of silent. `currency` is fixed at USD but stated rather than
assumed.

**`InventoryReport`** — `product_id`, `product_name`, `sizes`,
`sizes_in_stock`, `sizes_sold_out`, `total_quantity`, `any_in_stock`.

`sizes` is the **complete** run with quantities, not just what is available,
because "what sizes do you have" needs the gone ones named too. The three
derived fields exist so the model never has to do the filtering itself:
`sizes_in_stock` and `sizes_sold_out` are precomputed on the Python side, where
getting them backwards is impossible, and `any_in_stock` gives a single
unambiguous answer to "is this sold out" rather than asking the model to
reduce a list.

**`SizeQuantity`** — `size`, `quantity`, `in_stock`.

`in_stock` is redundant with `quantity > 0` and that is the point: the boolean
is not left to the model to derive.

**`SizeAvailability`** — `product_id`, `product_name`, `size`, `in_stock`,
`quantity`, `other_sizes_in_stock`.

`in_stock` and `quantity` answer exactly what was asked.
`other_sizes_in_stock` is the useful part: it lets a "no" carry an alternative
in the same breath, so a sold-out answer does not cost the shopper another
round trip. `size` is echoed back normalised — a shopper typing "large" or "l"
gets `L`.

### Handling misses

Unknown ids return a plain sentence ("No product with id 'x' exists in the
catalogue"), not an exception and not an empty object. The model can read that
and tell the shopper honestly, rather than receiving a null and filling the gap
itself. `check_size_availability` for a size the product does not carry lists
the sizes it does carry.

### Prompt changes

`prompts/prompt.md` gained a routing table mapping each kind of question to its
tool, an explicit ban on estimating quantities, and a rule against reasoning a
price from a similar product or a category.

The out-of-stock guidance is now specific: say it plainly and immediately, name
the size that is gone, do not soften it into "limited availability", then offer
what is actually there. Mentioning a low count is allowed only when it is the
number a tool returned.

### Verified

Tools called directly:

| Call | Result |
|---|---|
| `get_price` | $58.00 — matches `catalogue.price` |
| `get_inventory` | XS 0, S 0, M 12, L 0, XL 12, XXL 0; in stock M, XL; sold out XS, S, L, XXL; total 24 — matches `inventory` exactly |
| `check_size_availability(..., 'l')` | Normalised to L, `in_stock=False`, `quantity=0`, offered M and XL |
| Unknown id | Clear sentence, no exception |

Through the live agent:

| Asked | Replied | Correct |
|---|---|---|
| "How much is the Champion Reverse Weave Crewneck?" | "$58, in stock in M and XL" | yes |
| "What sizes and how many left?" | "M — 12 left, XL — 12 left. XS, S, L, and XXL are sold out." | yes, exactly |
| "Do you have it in large?" | "Sold out in L, I'm afraid. In stock in M and XL, for $58." | yes |

### A note on which tool the model picks

Given only a product *name*, the model must call `search_products` first —
that is the only tool that turns words into an id. Because the search result
already carries the price and the in-stock sizes, it often answers a price
question straight from there rather than making a second `get_price` call.

That is correct behaviour, not a gap: the number still came from
`catalogue.price` microseconds earlier. The dedicated tools are what it reaches
for on follow-up turns, when an id is already in hand. All six were tested
directly and return correct data.


---

## Problem 7 — Chat search that updates the page

### The flow, end to end

1. Shopper types "what shirts do you have?" into the chat widget.
2. `POST /api/chat` with the message and the recent history.
3. The agent calls `search_products`. As that tool reads each catalogue row it
   builds a `ProductCard` from the row and records it in `ChatDeps.shown`.
4. The route returns `ChatResponse { reply, products, tools_used }`.
5. `ChatWidget` does two things with the response: appends the reply to the
   conversation, and calls `setMatches(products, message)`.
6. `ChatResultsProvider` holds those matches in React context.
7. `ChatMatches` renders them on the page as a "From your chat" section.

The products never travel through the reply text. They are assembled from the
database rows the tools actually read, so a card cannot point at a product that
does not exist — the same guarantee as Problem 5, now surfaced on the page.

### Why the matches live outside the chat widget

`chatResults.tsx` is a small context separate from the widget. The widget owns
the conversation; the context owns "what is on the page because of it".

That split is what lets a shopper **close the chat panel and keep browsing the
results**. If the matches were widget state they would disappear with it, which
is exactly backwards — the point of putting them on the page is that the page
is where shopping happens.

Two behaviours fall out of the same file:

- **A turn that matches nothing leaves the previous results alone.** Asking a
  follow-up like "what time do you close?" does not blank the shirts the
  shopper is still looking at.
- **Results are replaceable and dismissible.** A new search overwrites them; a
  Clear button removes them.

### The cards are the Problem 3 cards

`ChatMatches` renders the same `ProductCard` component the Products grid uses —
not a lookalike. So the chat results get the same image treatment, the same
name/price/description layout, the same hover, and the same `Link` to
`/products/:productId`. Clicking one opens the single-product detail page built
in Problem 3.

The one wrinkle: `ProductCard` takes a `ProductSummary`, and the chat returns a
`ProductCard` model, which carries `available_sizes` but not `colors`. The
shapes are reconciled inside `ChatMatches` rather than by giving `ProductCard`
a second code path, so the grid component stays single-purpose.

On a product page the band is deliberately **not** rendered: the shopper is
already looking at something specific, and a results strip above it would push
that product below the fold. The chat panel still lists the matches inline
there.

The compact cards inside the chat log are kept as well — they tie a specific
answer to the products that answer was about, which the page section cannot do
once a second search replaces it. Both link to the same detail page.

### Prompt changes

`prompts/prompt.md` gained a section on questions about a *type* of product:
always call `search_products` for "what shirts do you have?" style questions,
even when the answer feels obvious, because the question is a request to see
the range. Follow-up narrowing ("something cheaper", "in navy") means searching
again with tighter terms, not filtering from memory.

A second section tells the agent what the shopper actually sees — that every
product it looks up appears as a clickable card — and therefore not to paste
image links or recite descriptions in prose. Its job is the recommendation, not
the catalogue dump.

### Verified

Asked the exact example from the problem, "What shirts do you have?":

| Check | Result |
|---|---|
| Tool called | `search_products` |
| Cards returned | 4, each with `product_id`, `name`, `price`, `short_description`, `image_url` |
| Reply style | Recommended three by name, did not list every match |
| Card detail links | All 4 resolve 200 at `/api/products/{id}` |
| Card images | All 4 resolve 200 at `/images/{id}.jpg` |

Narrowing follow-up, "Do you have any of those in navy?":

| Check | Result |
|---|---|
| Searched again rather than filtering from memory | yes — `search_products` called |
| Accuracy | Correctly said Boola Boola is navy and Big Yale Tri-Blend is not — the catalogue lists it as dusty coral and white |


---

## Problem 8 — Customer memory

### How chat history is stored

In the `chat_messages` table that shipped with the database — no new tables:

| Column | Written as |
|---|---|
| `user_id` | FK to `users.id`, taken from the session cookie |
| `role` | `user` or `assistant` |
| `content` | The message text |
| `products_json` | For assistant turns, the product cards shown with that reply |
| `created_at` | SQLite default, `datetime('now')` |

Two rows per exchange: the shopper's message, then the reply.

**Saving happens after a successful reply, not before.** If the model call
fails, the question is not written, so a shopper never returns to a saved
conversation that ends in an unanswered question.

**Loading** takes the newest 40 rows and reverses them, so a long history is
truncated at the old end rather than the recent end. Rows whose
`products_json` does not fit the current `ProductCard` shape — the database
ships with seeded rows from an earlier build that stored a different product
structure — are skipped individually rather than failing the whole load.

Endpoints:

| Route | Does |
|---|---|
| `GET /api/chat/history` | The signed-in shopper's saved conversation. Guests get an empty list and a 200, because having nothing saved is normal for them, not an error |
| `DELETE /api/chat/history` | Lets a shopper clear their own history ("Start over" in the widget) |

**Signed-in shoppers: the database is the source of truth for history.** The
`history` field in the request body is ignored for them and reloaded server
side, so the conversation the agent sees cannot be rewritten by editing what
the browser sends.

### Guests

Guests chat normally and nothing is written. The only code that touches
`chat_messages` is guarded by `deps.is_signed_in`, and every write takes a
`user_id`, so there is no path by which a guest conversation reaches the table.
Their history instead rides along in the request body, which is why it survives
a page interaction but not a reload.

The widget says so plainly: "Chatting as a guest — this conversation is not
saved", with a link to create an account.

Verified by counting rows before and after a full guest exchange: 24 before,
24 after.

### What customer information the agent sees

Assembled in the chat route from the **session cookie**, never from the request
body and never from anything the model said:

| Field | Used for |
|---|---|
| `user_id` | Loading and saving history. Never shown to the model |
| `user_name` | Naming the shopper |
| `user_first_name` | The greeting |
| `user_email` | Confirming which account they are on |

These reach the model through an `@agent.instructions` function, so a signed-in
shopper produces one line naming them and their account email, and a guest
produces a line saying they are not signed in and their name is unknown.

`password_hash` and `created_at` are never passed. The prompt tells the agent
the email is context only — not to read it back unless asked which account they
are using — and never to repeat the account id. Asked directly, it named the
email; unprompted, it did not.

### How page context is passed

The widget sends a `page` object with every message:

```json
{ "message": "Do you have this in black?",
  "page": { "path": "/products/boola-boola-t-shirt",
            "product_id": "boola-boola-t-shirt" } }
```

`ChatWidget` renders outside `<Routes>`, so `useParams` is empty there.
`useMatch('/products/:productId')` reads the path directly and works anywhere
under the router.

**The id is re-resolved server side.** The route looks the product id up in
`catalogue` and only sets `page_product_id`/`page_product_name` if it exists —
an id the catalogue does not know is dropped, so a crafted request cannot
inject a fake product into the agent's context.

A second `@agent.instructions` function turns that into a sentence naming the
product and stating that "this", "it", and "this one" refer to it, with an
instruction to use that id directly rather than searching again.

`prompts/prompt.md` documents both halves: who the shopper is, and the rule
that on a product page "this" means the product whose page they are on — and
that if they say "this" with nothing to point at, the agent should ask rather
than guess.

### Verified

| Check | Result |
|---|---|
| Page context: on the Boola Boola page, "Do you have this in black?" | Resolved "this" with **no search** — called `get_product_details` on the right id directly |
| Accuracy of that answer | "navy, white, and gray, not black… $32… XS, S, M, XL, XXL; L is sold out" — matches `catalogue` and `inventory` exactly |
| History saved | `chat_messages` for user 1 went 6 → 8, assistant row carries `products_json` |
| History reloads on return | New session, no `history` in the request: recalled hoodies, the pink question, and the black question |
| Account awareness | Named "Test User" and `test@campuscustoms.yale.edu` when asked which account |
| Guest: no name | "You're browsing as a guest, so I don't know your name" |
| Guest: nothing saved | 24 rows before, 24 after |
| Guest history endpoint | `{"messages": []}`, HTTP 200 |

---

# Reference — Problem 12

Everything below describes the finished system in one place: the types, the
tools, the safety rules, the limits, the model, and how to run it.

## How to run it

The database and product images are not committed. Unpack the provided data
archive first so the folder contains `data/campus_customs.db` and
`data/products/*.jpg`.

**Backend** — from the `backend/` folder:

    python -m venv ../.venv
    ../.venv/Scripts/python.exe -m pip install -r ../requirements.txt
    uvicorn main:app --reload --port 8000

**Frontend** — from the `frontend/` folder, in a second terminal:

    npm install
    npm run dev

Open **http://localhost:5173**. Use `localhost`, not `127.0.0.1` — Vite binds
IPv6. The dev server proxies `/api` and `/images` to port 8000, so the browser
sees one origin and no CORS is involved.

Copy `.env.example` to `.env` and set `PORTKEY_API_KEY`. `SECRET_KEY` is
optional locally; without it sessions simply end when the server restarts.

## The model

| Setting | Value |
|---|---|
| Model | `gpt-5.6-luna` (`MODEL_NAME`) |
| Gateway | Portkey, `https://api.portkey.ai/v1` (`PORTKEY_BASE_URL`) |
| Client | PydanticAI `OpenAIChatModel` + `OpenAIProvider` |
| Auth | `PORTKEY_API_KEY` as a bearer token |

Portkey speaks the OpenAI chat-completions protocol, so PydanticAI's OpenAI
model class works unchanged — only the base URL differs. The gateway routes
`gpt-5.6-luna` to Azure OpenAI and supports tool calling, which is what the
agent depends on.

The agent is built once per process (`lru_cache`) and its system prompt is read
from `prompts/prompt.md` at build time, so the shop's voice and rules can be
edited without touching Python.

## Model fields, and why they are shaped this way

The guiding rule: **the model should never have to derive something we can
compute in Python.** Every derived field below exists so a value cannot be
gotten backwards in a reply.

### Catalogue types

**`ProductSummary`** — `product_id`, `name`, `garment_type`, `category`,
`short_description`, `price`, `image_url`, `colors`, `available_sizes`,
`in_stock`.

`category` is the normalised form of `garment_type`; the raw column has 22
values with case duplicates and synonyms, so a browse facet built on it would
list the same category several times. Both are kept: `category` for filtering,
`garment_type` for display. `available_sizes` and `in_stock` ride on the
summary so the grid can show what is buyable without a request per card.

**`ProductDetail`** extends it with `description`, `search_tags`, `sizes`, and
`total_stock` — everything the detail page needs in one response.

**`SizeStock` / `SizeQuantity`** — `size`, `quantity`, `in_stock`. `in_stock`
is deliberately redundant with `quantity > 0`: the boolean is not left to the
model.

### Tool result types

**`ProductSearchResult`** — enough to recommend without a second call: what it
is, what it costs, what it looks like, and `sizes_in_stock` (only sizes above
zero).

**`PriceInfo`** — `product_id`, `product_name`, `price`, `currency`. Minimal on
purpose, so quoting a real price is the cheapest move available.
`product_name` is echoed so the model states *which* product it priced, making
a wrong-product answer visible.

**`InventoryReport`** — `sizes` is the complete run, not just what is left,
because "what sizes do you have" needs the gone ones named. `sizes_in_stock`,
`sizes_sold_out` and `any_in_stock` are precomputed so the filtering cannot be
inverted.

**`SizeAvailability`** — `in_stock` and `quantity` answer the question;
`other_sizes_in_stock` lets a "no" carry an alternative in the same breath.

### Chat types

**`ChatRequest`** — `message`, `history`, `page`. **`PageContext`** carries
`path` and `product_id`, which is what makes "do you have this in black?"
resolvable.

**`ProductCard`** — what the browser renders. Built from database rows by the
tools, never parsed out of the reply, so a card cannot point at a product that
does not exist.

**`ChatResponse`** — `reply`, `products`, `tools_used`, `corrected`.
`corrected` reports whether the price guardrail rewrote the reply.

**`UserOut`** — the only user shape the API can return. `password_hash` is not
a field on it, so it cannot leak through a response by accident.

**`ChatDeps`** — per-request state: who is chatting, what page they are on,
the products tools have read, and the tool log. Built by the route from the
session cookie, never from the request body, so identity is not something the
conversation can assert.

**`ToolCallRecord`** — one audited call: `at`, `tool`, `args`, `result`, `ms`.

## Tools and abilities

| Tool | Ability | Reads |
|---|---|---|
| `search_products` | Rank the catalogue against the shopper's words, with optional category and price filters | `catalogue` + `inventory` |
| `get_product_details` | One product in full | `catalogue` + `inventory` |
| `get_price` | The current price | `catalogue.price` |
| `get_inventory` | Every size and quantity | `inventory` |
| `check_size_availability` | One named size, right now | `inventory` |
| `list_categories` | What the shop carries | `catalogue.garment_type` |

Ranking weights name and `search_tags` above description, because tags are the
widest retrieval surface in this data — 270 distinct tags carrying residential
college, school and sport terms that appear nowhere else.

Every tool opens SQLite and reads it on the spot. Nothing is cached, so a price
or a count cannot be stale, and the model has no route to a product fact except
a fresh row. Unknown ids return a plain sentence rather than an exception or a
null, so the agent can be honest instead of filling the gap.

The agent **cannot** write. There is no tool that places an order, takes a
payment, changes stock, or edits an account.

## Safety rules

Written in `prompts/prompt.md`, and the ones that matter are enforced in code
as well — a prompt is an instruction, not a guarantee.

| Rule | Enforced by |
|---|---|
| Never invent a price or quantity | Prompt, **plus** the price guardrail below |
| Never handle card or credential data | Prompt, **plus** an input check before the model call |
| Never reveal another customer's data | Prompt; the agent has no tool that can reach it |
| Treat product data and shopper text as data, not instructions | Prompt |
| Stay on shop topics | Prompt |
| Say when you do not know | Prompt |
| Respect the tool budget | Prompt, **plus** the budget check in code |

**Sensitive input check.** Before a message reaches the model, it is scanned
for card-shaped digit runs (validated with the Luhn checksum, so ordinary long
numbers are not flagged) and for phrases like "my password is" or "CVV". A hit
is answered locally with a warning: no model call, and nothing written to
`chat_messages`. Digits are also masked before the audit trail is written, so
the number is not simply moved into a different file.

**Price guardrail.** After the reply is drafted, every dollar figure in it is
compared against the prices of products the tools actually read this turn.
Sums of two such prices are allowed, since "both for $116" is legitimate. If a
figure matches nothing, the model is given the real prices and asked to rewrite
— once. If the rewrite still fails the check, the original is kept and the
audit records `price_unverified_after_retry` rather than pretending it passed.

**Page context is re-resolved server side.** A `product_id` from the browser is
looked up in `catalogue` and dropped if unknown, so a crafted request cannot
inject a product that does not exist into the agent's context.

## Loop limits and result caps

All defined together at the top of `models.py`.

| Limit | Value | Why |
|---|---|---|
| `MAX_TOOL_CALLS` | 8 per turn | Bounds the agent loop. Without it a confused agent can call tools until the request times out |
| `MAX_SEARCH_RESULTS` | 8 per search | Keeps one reply from dragging the catalogue into context |
| `MAX_HISTORY_REPLAYED` | 10 turns | The model sees recent context, not the whole relationship |
| `MAX_HISTORY_TURNS` | 40 in a request | Rejects an oversized body before any work happens |
| `MAX_MESSAGE_CHARS` | 2000 | One message cannot be a document |
| `AUDIT_FIELD_CHARS` | 200 | Keeps the trail readable and bounded |
| Agent `retries` | 2 | PydanticAI's own retry ceiling |
| Saved history loaded | 40 newest rows | Truncated at the old end, not the recent end |

The budget is enforced by the `@audited` decorator every tool carries: once
spent, further calls return a message telling the agent to answer with what it
has, and the refusal itself is logged. Wrapping rather than repeating the check
means a new tool cannot be added that quietly skips it.

## Audit trail

`output/audit_trail.json` — a JSON array, appended to once per turn and never
truncated.

Each entry records the time, duration, model, whether the shopper was signed in
or a guest, the page they were on, the (redacted) message, every tool call with
short arguments and results and its duration, the products returned, whether
the price guardrail corrected the reply, the stop reason, and a clipped reply.

| Stop reason | Meaning |
|---|---|
| `completed` | Normal finish |
| `completed_after_price_correction` | A quoted figure failed the check and the rewrite passed |
| `price_unverified_after_retry` | The rewrite also failed; the first reply was kept |
| `blocked_sensitive_input` | Payment or credential data; no model call was made |
| `tool_budget_exhausted` | The turn used all 8 tool calls |

Writes go through a temporary file and an atomic `os.replace`, under a lock, so
two turns finishing together cannot overwrite each other and an interrupted
write cannot truncate the history. A trail that has been corrupted by something
else is moved aside rather than overwritten. An audit failure is swallowed — it
must never take down a shopper's conversation.


---

## Verification

`scripts/verify_all.py` exercises the whole system against the running servers
and checks each answer against SQL rather than trusting the reply. Run it with
both servers up:

    .venv/Scripts/python.exe scripts/verify_all.py

It covers 41 behaviours: catalogue and image serving, category normalisation,
detail accuracy against `catalogue` and `inventory`, the account flow including
duplicate and weak-password rejection and that no response can carry a password
hash, page-context resolution, honest sold-out reporting, product cards matching
real rows, off-topic refusal, the sensitive-input guard and that blocked
messages are never written to `chat_messages`, saved history for signed-in
shoppers, guests never being stored, request size limits, and the shape and
redaction of the audit trail.

It exits non-zero on any failure, so it can be run before a submission rather
than read.

`frontend/scripts/ui_check.mjs` is the browser-level companion. It drives the
real UI in Chromium — every nav link, the grid with its size filter and price
sort, a product page, signup, sign-out, sign-in, a wrong password, a chat turn
with its cards landing on the page, clicking through to a product, history
reloading on return, guest isolation, a phone viewport, and the console — and
fails on any unexpected console error. 40 checks.

    cd frontend && node scripts/ui_check.mjs

Browsing signed out is treated as a normal state throughout, not an error:
`GET /api/auth/me` answers 200 with `null` rather than 401, so a visitor
without an account does not collect console errors simply for being new. The
same reasoning applies to `GET /api/chat/history`.
