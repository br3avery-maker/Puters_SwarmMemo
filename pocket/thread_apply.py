"""Persist a verified merge of a previously fetched public thread page.

No network, no publication. POSIX advisory locking protects cooperating writers.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterator

from .receipts import ReceiptStore
from .workbench import canonical, merge_thread_page

APPLY_SPEC = "puter.pocket.thread-apply.v1"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextmanager
def _exclusive_file_lock(state_path: Path) -> Iterator[None]:
    try:
        import fcntl
    except ImportError as exc:
        raise OSError("apply-thread currently requires POSIX flock") from exc
    lock_path = state_path.with_name(state_path.name + ".lock")
    if lock_path.is_symlink():
        raise ValueError("lockfile symlink not allowed")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _replace_durably(path: Path, data: bytes) -> None:
    """Write temp+fsync, atomically rename, fsync parent directory."""
    tmp: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".puter-state-",
                                         dir=path.parent, delete=False) as handle:
            tmp = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        tmp = None
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)


def apply_thread_page(state_file: str | Path, page_file: str | Path,
                      ledger_file: str | Path, operation_id: str, *,
                      retry_unresolved: bool = False,
                      checkpoint: Callable[[str], None] | None = None) -> dict:
    """Write and read back a thread-state merge. Never silently replay unknown writes.

    checkpoint is a test-only hook for exercising crash boundaries.
    """
    state_file = Path(state_file).absolute()
    page_file = Path(page_file).absolute()
    ledger_file = Path(ledger_file).absolute()
    if len({state_file, page_file, ledger_file}) != 3:
        raise ValueError("state, input page, and ledger must be separate files")
    if state_file.is_symlink() or page_file.is_symlink():
        raise ValueError("state and page symlinks not supported")
    if not state_file.is_file() or not page_file.is_file():
        raise ValueError("state and page files must already exist")
    page = json.loads(page_file.read_bytes())
    if not isinstance(page, dict):
        raise ValueError("page must be an object")
    spec = f"{APPLY_SPEC}:page:{_sha(canonical(page))}"
    with _exclusive_file_lock(state_file):
        if state_file.is_symlink():
            raise ValueError("state symlink not supported")
        with ReceiptStore(ledger_file) as store:
            previous = store.get(operation_id)
            if previous and previous["status"] == "verified":
                if previous["specification"] != spec:
                    raise ValueError("operation ID reused for different page")
                return {"outcome": "previously_verified", "receipt": previous,
                        "new_ids": [], "changed_ids": []}
            state = json.loads(state_file.read_bytes())
            if not isinstance(state, dict):
                raise ValueError("state must be an object")
            merged = merge_thread_page(state, page)
            output = canonical(merged["state"])
            expected = _sha(output)
            if previous:
                if (previous["payload_sha256"] != expected or
                        previous["specification"] != spec or
                        previous["evidence_source"] != "observed"):
                    raise ValueError("unresolved operation differs from original intent; inspect ledger")
                if previous["status"] == "failed":
                    raise ValueError("failed operation is terminal; use a new ID after investigating")
                actual = state_file.read_bytes()
                if _sha(actual) == expected:
                    if previous["status"] == "attempted":
                        store.accept(operation_id)
                    receipt = store.verify(operation_id, actual)
                    return {"outcome": "reconciled", "receipt": receipt,
                            "new_ids": [], "changed_ids": []}
                if not retry_unresolved:
                    raise ValueError("unresolved outcome: destination differs; inspect, then explicitly --retry")
            else:
                store.begin(operation_id, output, specification=spec,
                            evidence_source="observed")
                if checkpoint:
                    checkpoint("after_begin")
            _replace_durably(state_file, output)
            if checkpoint:
                checkpoint("after_replace")
            if store.get(operation_id)["status"] == "attempted":
                store.accept(operation_id)
            if checkpoint:
                checkpoint("after_accept")
            receipt = store.verify(operation_id, state_file.read_bytes())
            return {"outcome": ("readback_failed" if receipt["status"] != "verified"
                                else "written" if not previous else "explicit_retry"),
                    "receipt": receipt, "new_ids": merged["new_ids"],
                    "changed_ids": merged["changed_ids"],
                    "has_more": merged["has_more"]}
