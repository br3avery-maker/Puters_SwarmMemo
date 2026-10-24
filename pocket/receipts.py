"""Durable, offline verification receipts. Requires Python 3.11+; no network or side effects.

A receipt records a caller's intent and subsequent evidence, not the external write
itself. In particular, attempted after a crash means outcome unknown, not safe
to retry. The caller must reconcile with the external target before resubmitting.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = "puter.pocket.receipt.v1"
_STATUSES = ("attempted", "accepted", "verified", "failed")
_SOURCES = ("observed", "reproduced", "inferred", "inherited")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _hash(payload: bytes) -> str:
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    return hashlib.sha256(payload).hexdigest()


class ReceiptStore:
    """Per-operation SQLite receipts; transitions commit before returning.

    Not a publisher, distributed lock, secret vault, or authorization to retry
    external actions. Use one stable operation ID per intended side effect.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("database symlinks are not supported")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=15)
        try:
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA busy_timeout=15000")
            self.db.execute("""CREATE TABLE IF NOT EXISTS receipts (
                operation_id TEXT PRIMARY KEY,
                payload_sha256 TEXT NOT NULL,
                specification TEXT NOT NULL,
                evidence_source TEXT NOT NULL CHECK (evidence_source IN
                    ('observed','reproduced','inferred','inherited')),
                status TEXT NOT NULL CHECK (status IN
                    ('attempted','accepted','verified','failed')),
                readback_sha256 TEXT,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )""")
            self.db.commit()
        except BaseException:
            self.db.close()
            raise

    def __enter__(self) -> "ReceiptStore":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        self.db.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        return {"schema": SCHEMA, **dict(row)}

    def get(self, operation_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM receipts WHERE operation_id=?", (operation_id,)).fetchone()
        return self._record(row) if row else None

    def begin(self, operation_id: str, payload: bytes, *, specification: str = "unspecified",
              evidence_source: str = "observed") -> dict[str, Any]:
        if not isinstance(operation_id, str) or not _ID.fullmatch(operation_id):
            raise ValueError("operation_id must be 1-128 safe characters")
        if evidence_source not in _SOURCES:
            raise ValueError("unknown evidence source")
        if not isinstance(specification, str) or not specification or len(specification) > 256:
            raise ValueError("invalid specification revision")
        h = _hash(payload)
        with self.db:
            self.db.execute("""INSERT OR IGNORE INTO receipts
                (operation_id, payload_sha256, specification, evidence_source, status)
                VALUES (?, ?, ?, ?, 'attempted')""",
                (operation_id, h, specification, evidence_source))
            item = self.get(operation_id)
            if (item["payload_sha256"], item["specification"], item["evidence_source"]) != (h, specification, evidence_source):
                raise ValueError("operation ID already belongs to different intent")
        return item

    def _advance(self, operation_id: str, allowed: tuple[str, ...], status: str,
                 *, readback_sha256: str | None = None, reason: str = "") -> dict[str, Any]:
        if status not in _STATUSES:
            raise ValueError("invalid receipt status")
        placeholders = ",".join("?" for _ in allowed)
        with self.db:
            result = self.db.execute(f"""UPDATE receipts
                SET status=?, readback_sha256=?, reason=?,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE operation_id=? AND status IN ({placeholders})""",
                (status, readback_sha256, reason, operation_id, *allowed))
            if result.rowcount != 1:
                existing = self.get(operation_id)
                raise ValueError("unknown operation" if existing is None else
                                 f"invalid transition from {existing['status']}")
        return self.get(operation_id)

    def accept(self, operation_id: str) -> dict[str, Any]:
        """Record that the external tool reported acceptance, not verification."""
        return self._advance(operation_id, ("attempted",), "accepted")

    def verify(self, operation_id: str, readback: bytes) -> dict[str, Any]:
        """Require an actual independently obtained readback after acceptance."""
        h = _hash(readback)
        original = self.get(operation_id)
        if original is None:
            raise ValueError("unknown operation")
        if original["status"] != "accepted":
            raise ValueError("verification requires accepted state")
        if h != original["payload_sha256"]:
            return self._advance(operation_id, ("accepted",), "failed",
                                 readback_sha256=h, reason="readback mismatch")
        return self._advance(operation_id, ("accepted",), "verified", readback_sha256=h)

    def fail(self, operation_id: str, reason: str) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason or len(reason) > 2000:
            raise ValueError("a bounded, nonempty failure reason is required")
        return self._advance(operation_id, ("attempted", "accepted"), "failed", reason=reason)

    def unresolved(self) -> list[dict[str, Any]]:
        """Items requiring reconciliation; do not automatically replay them."""
        rows = self.db.execute("""SELECT * FROM receipts WHERE status IN ('attempted','accepted')
            ORDER BY created_at, operation_id""").fetchall()
        return [self._record(row) for row in rows]
