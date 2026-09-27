"""Authentication for Campus Customs.

Passwords are never stored in plain text. Each one is put through
PBKDF2-HMAC-SHA256 with a per-user random salt, and only the salt and the
resulting digest are written to the database.

The stored format matches the rows the database already shipped with, so the
seeded test account verifies with exactly the same code path as a brand new
signup:

    pbkdf2_sha256$<salt>$<64-hex-digest>

The iteration count is not part of that string, so it is pinned here as a
constant. It was recovered from the seeded test account and must not be changed
without re-hashing every existing row, or those users could no longer log in.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8  # 8 random bytes -> 16 hex characters, matching the seeded rows

SESSION_COOKIE = "campus_customs_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # one week

# Signing key for session cookies. A random key is generated when none is
# configured, which is fine for local development — it just means sessions do
# not survive a server restart.
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------


def hash_password(password: str, salt: str | None = None) -> str:
    """Return a storable `pbkdf2_sha256$salt$digest` string."""
    if salt is None:
        salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()
    return f"{ALGORITHM}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, in constant time."""
    try:
        algorithm, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()
    # compare_digest avoids leaking how much of the digest matched
    return hmac.compare_digest(candidate, digest)


# --------------------------------------------------------------------------
# Session tokens
# --------------------------------------------------------------------------
#
# A session is a signed string, not a database row: "<user_id>.<expiry>.<sig>".
# The signature is an HMAC over the first two parts, so the cookie cannot be
# edited to impersonate another user without knowing SECRET_KEY.


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_MAX_AGE}"
    return f"{payload}.{_sign(payload)}"


def read_session_token(token: str | None) -> int | None:
    """Return the user id in a valid, unexpired token, else None."""
    if not token:
        return None
    try:
        user_id, expiry, signature = token.rsplit(".", 2)
        payload = f"{user_id}.{expiry}"
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    if int(expiry) < time.time():
        return None
    return int(user_id)
