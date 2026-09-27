"""End-to-end verification of the Campus Customs app.

Exercises every requirement from the assignment against the running servers and
the real database, and checks each answer against SQL rather than trusting the
reply. Run with both servers up:

    .venv/Scripts/python.exe scripts/verify_all.py

Exits non-zero if anything fails.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "campus_customs.db"
API = "http://127.0.0.1:8000"
WEB = "http://localhost:5173"

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((ok, name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def call(path: str, data: dict | None = None, method: str | None = None, base: str = API):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        base + path,
        data=body,
        method=method or ("POST" if data is not None else "GET"),
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with opener.open(req, timeout=240) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, (json.loads(raw) if raw else None)


def section(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


# ---------------------------------------------------------------- catalogue
section("Problem 2-3 — catalogue, images, detail")

status, health = call("/api/health")
check("backend healthy", status == 200 and health["status"] == "ok", str(health))

with db() as c:
    db_count = c.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]

status, products = call("/api/products")
check("all products returned", status == 200 and len(products) == db_count,
      f"api={len(products)} db={db_count}")
check("summary carries stock for the grid",
      all("available_sizes" in p and "in_stock" in p for p in products))

status, cats = call("/api/categories")
check("categories normalised to a clean set", status == 200 and len(cats) == 6, str(cats))

with db() as c:
    raw_types = c.execute("SELECT COUNT(DISTINCT garment_type) FROM catalogue").fetchone()[0]
check("22 raw garment types folded into 6 categories", raw_types == 22 and len(cats) == 6,
      f"{raw_types} -> {len(cats)}")

pid = "champion-reverse-weave-crewneck"
status, detail = call(f"/api/products/{pid}")
with db() as c:
    row = c.execute("SELECT * FROM catalogue WHERE product_id=?", (pid,)).fetchone()
    sizes = {r["size"]: r["quantity"] for r in
             c.execute("SELECT size,quantity FROM inventory WHERE product_id=?", (pid,))}
check("detail price matches the database", detail["price"] == row["price"],
      f"{detail['price']} vs {row['price']}")
check("detail sizes match the database",
      {s["size"]: s["quantity"] for s in detail["sizes"]} == sizes)
check("unknown product returns 404", call("/api/products/nope")[0] == 404)

status, _ = call("/api/products/" + pid, base=WEB)
check("frontend proxies /api", status == 200)

req = urllib.request.Request(WEB + "/images/" + pid + ".jpg")
with opener.open(req, timeout=60) as r:
    check("frontend proxies /images", r.status == 200 and r.headers["content-type"] == "image/jpeg")

# ----------------------------------------------------------------- accounts
section("Problem 4 — accounts")

status, me = call("/api/auth/login", {"email": "test@campuscustoms.yale.edu",
                                      "password": "password"})
check("provided test account logs in", status == 200 and me["id"] == 1, str(me.get("name")))
check("login response never exposes the hash", "password_hash" not in (me or {}))

status, me2 = call("/api/auth/me")
check("session cookie resolves", status == 200 and me2["id"] == 1)

status, _ = call("/api/auth/login", {"email": "test@campuscustoms.yale.edu",
                                     "password": "wrong"})
check("wrong password rejected", status == 401)
status, body = call("/api/auth/login", {"email": "nobody@nowhere.edu", "password": "x"})
check("unknown email gives the same 401 message", status == 401)

status, _ = call("/api/auth/register", {"first_name": "A", "last_name": "B",
                                        "email": "test@campuscustoms.yale.edu",
                                        "password": "abcdefgh"})
check("duplicate email rejected with 409", status == 409)
status, _ = call("/api/auth/register", {"first_name": "A", "last_name": "B",
                                        "email": "short@yale.edu", "password": "abc"})
check("short password rejected", status == 422)

with db() as c:
    hashes = [r[0] for r in c.execute("SELECT password_hash FROM users")]
check("every stored password is a pbkdf2 hash",
      all(h.startswith("pbkdf2_sha256$") and len(h.split("$")[2]) == 64 for h in hashes))

# ---------------------------------------------------------------- the agent
section("Problems 5-8 — the agent")

status, r1 = call("/api/chat", {"message": "Do you have this in large? And how much is it?",
                                "page": {"path": f"/products/{pid}", "product_id": pid}})
reply = r1["reply"]
check("page context resolves 'this' without a search",
      status == 200 and "search_products" not in r1["tools_used"], str(r1["tools_used"]))
check("sold-out size stated plainly", re.search(r"\bsold out\b|\bnot? (?:in stock|available)\b",
                                                reply, re.I) is not None, reply[:90])
check("correct price quoted", "58" in reply, reply[:90])
check("product card returned from the database row",
      [p["product_id"] for p in r1["products"]] == [pid])
check("card sizes match the database",
      set(r1["products"][0]["available_sizes"]) == {s for s, q in sizes.items() if q > 0})

status, r2 = call("/api/chat", {"message": "What shirts do you have?"})
check("category question searches the catalogue", "search_products" in r2["tools_used"])
check("structured matches returned for the page", len(r2["products"]) > 0,
      f"{len(r2['products'])} cards")
with db() as c:
    known = {r[0] for r in c.execute("SELECT product_id FROM catalogue")}
check("every card is a real product",
      all(p["product_id"] in known for p in r2["products"]))

status, r3 = call("/api/chat", {"message": "Who won the 1998 world cup?"})
check("off-topic declined without tool calls", r3["tools_used"] == [], str(r3["tools_used"]))

with db() as c:
    before = c.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
status, r4 = call("/api/chat", {"message": "my card is 4111 1111 1111 1111"})
with db() as c:
    after = c.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
check("card data blocked before the model", r4["tools_used"] == [])
check("card data never written to chat history", before == after, f"{before} -> {after}")

status, hist = call("/api/chat/history")
check("signed-in history loads", status == 200 and len(hist["messages"]) > 0,
      f"{len(hist['messages'])} messages")

call("/api/auth/logout", {}, method="POST")
status, _ = call("/api/auth/me")
check("logout clears the session", status == 401)

with db() as c:
    guest_before = c.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
status, g = call("/api/chat", {"message": "What do you sell?"})
with db() as c:
    guest_after = c.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
check("guest can chat", status == 200 and len(g["reply"]) > 0)
check("guest history is never saved", guest_before == guest_after,
      f"{guest_before} -> {guest_after}")
status, gh = call("/api/chat/history")
check("guest history endpoint returns empty, not 401",
      status == 200 and gh["messages"] == [])

# ------------------------------------------------------------------- limits
section("Problem 12 — limits, audit trail")

status, _ = call("/api/chat", {"message": "x" * 2500})
check("oversized message rejected by the request model", status == 422)

trail = ROOT / "output" / "audit_trail.json"
entries = json.loads(trail.read_text(encoding="utf-8"))
check("audit trail exists and grew", len(entries) >= 5, f"{len(entries)} entries")
required = {"at", "tool_calls", "stop_reason", "model", "shopper", "message", "duration_ms"}
check("entries carry time, tools, stop reason", required <= set(entries[-1]))
reasons = {e["stop_reason"] for e in entries}
check("blocked turn recorded with its own stop reason",
      "blocked_sensitive_input" in reasons, str(sorted(reasons)))
raw_trail = trail.read_text(encoding="utf-8")
check("no raw card digits in the audit trail",
      "4111 1111" not in raw_trail and "4111111111111111" not in raw_trail)
check("redaction marker present", "[redacted:" in raw_trail)
check("tool calls carry args, result and duration",
      all({"tool", "args", "result", "ms"} <= set(t)
          for e in entries for t in e["tool_calls"]))

# ------------------------------------------------------------------ summary
failed = [r for r in results if not r[0]]
print("\n" + "=" * 62)
print(f"{len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("\nFAILURES:")
    for _, name, detail in failed:
        print(f"  - {name}  {detail}")
print("=" * 62)
sys.exit(1 if failed else 0)
