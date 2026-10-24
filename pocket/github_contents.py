"""GitHub Contents API + crash-reconcilable, verified file writes.

No implicit remote writes. API host is pinned to api.github.com; credentials
are supplied at runtime, never persisted in receipts or surfaced in errors.
The file's preimage SHA is required for compare-and-swap writes.
"""
from __future__ import annotations

import base64
import binascii
from contextlib import contextmanager
from dataclasses import dataclass
import os
import hashlib
import json
import re
from pathlib import Path
from typing import Callable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .receipts import ReceiptStore

_SPEC = "puter.pocket.github-contents.v1"
_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")
_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class RemoteError(Exception):
    """Remote result is unconfirmed. Do not assume failure implies no write."""


@dataclass(frozen=True)
class RemoteFile:
    sha: str
    content: bytes


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RemoteError("GitHub API redirect refused")


def _path(name: str) -> str:
    if (not isinstance(name, str) or not name or name.startswith("/") or
            "\\" in name or "\x00" in name or "//" in name or name.endswith("/") or
            any(p in ("", ".", "..") for p in name.split("/"))):
        raise ValueError("unsafe GitHub file path")
    return "/".join(quote(p, safe="") for p in name.split("/"))


def _blob_sha(data: bytes, algorithm: str = "sha1") -> str:
    content = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.new(algorithm, content).hexdigest()


def _validate_sha(value: str | None) -> str | None:
    if value is not None and (not isinstance(value, str) or not _SHA.fullmatch(value)):
        raise ValueError("expected blob SHA must be 40 or 64 lowercase hex characters")
    return value


class GitHubContentsClient:
    """Pinned GitHub API transport. Does not follow redirects or send auth elsewhere."""

    def __init__(self, owner: str, repo: str, branch: str, *, token: str | None = None):
        if not all(isinstance(n, str) and _COMPONENT.fullmatch(n) and n not in (".", "..")
                   for n in (owner, repo)):
            raise ValueError("invalid GitHub owner or repo")
        if (not isinstance(branch, str) or not branch or len(branch) > 240 or
                branch.startswith("/") or branch.endswith("/") or ".." in branch or
                "\\" in branch or any(ord(c) < 32 for c in branch)):
            raise ValueError("invalid branch name")
        self.owner, self.repo, self.branch = owner, repo, branch
        self._token = token
        self._opener = build_opener(_NoRedirect())

    def _url(self, path: str, *, reading: bool) -> str:
        url = (f"https://api.github.com/repos/{quote(self.owner, safe='')}/"
               f"{quote(self.repo, safe='')}/contents/{_path(path)}")
        return url + ("?ref=" + quote(self.branch, safe="") if reading else "")

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | None:
        url = self._url(path, reading=method == "GET")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "puter-pocket-receipts/1",
                   "Cache-Control": "no-cache"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=15) as response:
                if response.geturl() != url:
                    raise RemoteError("GitHub API redirect refused")
                raw = response.read(6 * 1024 * 1024 + 1)
                if len(raw) > 6 * 1024 * 1024:
                    raise RemoteError("GitHub response too large")
                decoded = json.loads(raw)
                if not isinstance(decoded, dict):
                    raise RemoteError("unexpected GitHub API response")
                return decoded
        except HTTPError as exc:
            if method == "GET" and exc.code == 404:
                return None
            # Never include the response body, headers, or request URL in an error:
            # all may contain private information or attacker-controlled text.
            raise RemoteError(f"GitHub API HTTP {exc.code}; outcome unknown") from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeError):
            raise RemoteError("GitHub transport/response error; outcome unknown") from None

    def read(self, path: str) -> RemoteFile | None:
        item = self._request("GET", path)
        if item is None:
            return None
        if item.get("type") != "file" or item.get("encoding") != "base64":
            raise RemoteError("GitHub did not return an inline file")
        sha = item.get("sha")
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise RemoteError("GitHub returned invalid blob SHA")
        raw = item.get("content")
        if not isinstance(raw, str):
            raise RemoteError("GitHub returned no inline file bytes")
        try:
            data = base64.b64decode(raw.replace("\n", ""), validate=True)
        except (binascii.Error, ValueError):
            raise RemoteError("invalid GitHub base64 data") from None
        algorithm = "sha1" if len(sha) == 40 else "sha256"
        if _blob_sha(data, algorithm) != sha:
            raise RemoteError("GitHub blob SHA/content mismatch")
        return RemoteFile(sha, data)

    def put(self, path: str, data: bytes, *, message: str,
            expected_sha: str | None) -> None:
        if not self._token:
            raise ValueError("GITHUB_TOKEN required for remote write")
        _validate_sha(expected_sha)
        if not isinstance(message, str) or not message or len(message) > 256:
            raise ValueError("invalid commit message")
        payload = {"message": message, "content": base64.b64encode(data).decode("ascii"),
                   "branch": self.branch}
        if expected_sha is not None:
            payload["sha"] = expected_sha
        result = self._request("PUT", path, payload)
        if result is None or "commit" not in result:
            raise RemoteError("GitHub write acknowledgment incomplete; outcome unknown")


def _same(remote: RemoteFile | None, desired: bytes) -> bool:
    return remote is not None and hashlib.sha256(remote.content).digest() == hashlib.sha256(desired).digest()


def _identity(client: GitHubContentsClient, path: str, expected_sha: str | None,
              message: str) -> str:
    fields = [client.owner, client.repo, client.branch, path, expected_sha, message]
    data = json.dumps(fields, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return _SPEC + ":" + hashlib.sha256(data).hexdigest()


@contextmanager
def _exclusive_ledger_lock(ledger_file: Path) -> Iterator[None]:
    """Serialize cooperating local callers while network effect is in flight."""
    try:
        import fcntl
    except ImportError as exc:
        raise OSError("remote sync currently requires POSIX flock") from exc
    lock = ledger_file.with_name(ledger_file.name + ".remote.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.is_symlink():
        raise ValueError("remote ledger lockfile symlink refused")
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def sync_file(client: GitHubContentsClient, ledger_file: str | Path,
              operation_id: str, path: str, desired: bytes, *,
              expected_sha: str | None, message: str,
              allow_write: bool = False, retry_unresolved: bool = False,
              checkpoint: Callable[[str], None] | None = None) -> dict:
    """One CAS write + independent GET; resume by inspection, never blind retry.

    For a new file expected_sha=None means EXPECT ABSENT, not unknown.

    On re-entry with an unresolved ledger row, a matching remote value
    reconciles without PUT; a differing value requires explicit retry AND
    matching original preimage SHA. Verified rows remain historical evidence,
    while every call checks current state for drift.
    """
    if not isinstance(desired, bytes):
        raise TypeError("desired must be bytes")
    _path(path)
    _validate_sha(expected_sha)
    if not isinstance(message, str) or not message or len(message) > 256:
        raise ValueError("invalid commit message")
    spec = _identity(client, path, expected_sha, message)
    with _exclusive_ledger_lock(Path(ledger_file).absolute()):
        with ReceiptStore(ledger_file) as store:
            old = store.get(operation_id)
            if old and (old["payload_sha256"] != hashlib.sha256(desired).hexdigest() or
                        old["specification"] != spec or old["evidence_source"] != "observed"):
                raise ValueError("operation ID bound to different remote intent")
            # This read is deliberately remote even when the ledger says verified.
            remote = client.read(path)
            matches = _same(remote, desired)
            if old and old["status"] == "verified":
                return {"outcome": "still_verified" if matches else "remote_drift",
                        "receipt": old, "current_sha": remote.sha if remote else None}
            if old and old["status"] == "failed":
                raise ValueError("failed receipt is terminal; inspect and use a new operation ID")
            if old and matches:
                if old["status"] == "attempted":
                    store.accept(operation_id)
                receipt = store.verify(operation_id, remote.content)
                return {"outcome": "reconciled", "receipt": receipt,
                        "current_sha": remote.sha}
            if not old and matches:
                return {"outcome": "already_present_no_write", "receipt": None,
                        "current_sha": remote.sha}
            current_sha = remote.sha if remote else None
            if current_sha != expected_sha:
                raise ValueError("remote preimage changed; refusing overwrite")
            if old and not retry_unresolved:
                return {"outcome": "unresolved_requires_review", "receipt": old,
                        "current_sha": current_sha}
            if not allow_write:
                return {"outcome": "would_write", "receipt": old,
                        "current_sha": current_sha}
            if not client._token:
                raise ValueError("GITHUB_TOKEN required for remote write")
            if not old:
                store.begin(operation_id, desired, specification=spec,
                            evidence_source="observed")
                if checkpoint:
                    checkpoint("after_begin")
            # A transport error, including a timeout, leaves the receipt unresolved.
            client.put(path, desired, message=message, expected_sha=expected_sha)
            if checkpoint:
                checkpoint("after_put")
            if store.get(operation_id)["status"] == "attempted":
                store.accept(operation_id)
            if checkpoint:
                checkpoint("after_accept")
            # Independent second GET: do not trust the PUT response as evidence.
            actual = client.read(path)
            if actual is None:
                # No bytes to compare: leave accepted receipt unresolved for later.
                return {"outcome": "readback_missing", "receipt": store.get(operation_id),
                        "current_sha": None}
            receipt = store.verify(operation_id, actual.content)
            return {"outcome": ("verified_write" if receipt["status"] == "verified"
                                else "readback_mismatch"), "receipt": receipt,
                    "current_sha": actual.sha}
