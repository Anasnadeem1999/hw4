"""Append-only audit trail for the agent loop.

Every turn of conversation appends one entry to `output/audit_trail.json`
recording when it ran, which tools were called with what arguments and
results, and why the loop stopped.

**The file is never truncated.** Existing entries are read, the new one is
appended, and the whole list is written back through a temporary file and an
atomic replace — so an interrupted write cannot leave a half-written trail and
lose the history. A file that has been corrupted by something else is moved
aside rather than overwritten.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

# Uvicorn serves requests concurrently; without this two turns finishing at the
# same moment could read the same list and one would overwrite the other.
_lock = threading.Lock()


def _read_existing() -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        # Never silently discard a damaged trail — keep it next to the new one.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        AUDIT_PATH.replace(AUDIT_PATH.with_suffix(f".corrupt-{stamp}.json"))
        return []
    return data if isinstance(data, list) else []


def append(entry: dict[str, Any]) -> None:
    """Append one entry. Never raises into the request path."""
    try:
        with _lock:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            entries = _read_existing()
            entries.append(entry)

            tmp = AUDIT_PATH.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(tmp, AUDIT_PATH)  # atomic on Windows and POSIX
    except Exception:
        # An audit failure must not take down a shopper's conversation.
        pass


def entry_count() -> int:
    with _lock:
        return len(_read_existing())
