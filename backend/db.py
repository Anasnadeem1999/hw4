"""Shared database access for the Campus Customs backend."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# backend/db.py -> HW4/ -> HW4/data
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
# catalogue.image_file_path is stored as "products/<id>.jpg", relative to data/
IMAGES_DIR = DATA_DIR / "products"


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. "
            "The data/ folder is intentionally not committed — unpack the "
            "provided data archive into HW4/data/ before running the backend."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
