"""Portable deterministic tools for public-agent experiments (no IC dependency).

Inputs are untrusted; these functions do not make network calls or execute code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

SCHEMA = "puter.pocket.manifest.v1"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_path(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("invalid relative path")
    p = PurePosixPath(name)
    if p.is_absolute() or any(part in ("..", ".") for part in name.split("/")) or "//" in name:
        raise ValueError("unsafe relative path")
    if name.endswith("/") or not p.parts:
        raise ValueError("invalid file path")
    return name


def merge_thread_page(state: dict, page: dict) -> dict:
    """Return a new state and differences; never advance a cursor on failed reads."""
    if page.get("ok") is not True:
        raise ValueError("unsuccessful thread read")
    data = page.get("data") or {}
    root = state.get("root_id")
    if not isinstance(root, str) or data.get("root_id") != root:
        raise ValueError("thread root mismatch")
    messages = data.get("messages", page.get("messages", []))
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    seen = {entry["id"]: entry["sha256"] for entry in state.get("seen", [])}
    new, changed = [], []
    for msg in messages:
        mid = msg.get("id")
        if not isinstance(mid, str) or not mid:
            raise ValueError("message missing id")
        text = msg.get("text", "")
        if not isinstance(text, str):
            raise ValueError("invalid message text")
        h = digest(text.encode("utf-8"))
        if mid not in seen:
            new.append(mid)
        elif seen[mid] != h:
            changed.append(mid)
        seen[mid] = h
    updated = dict(state)
    updated["seen"] = [{"id": k, "sha256": seen[k]} for k in sorted(seen)]
    if page.get("next_cursor") is not None:
        updated["cursor"] = page["next_cursor"]
    elif data.get("next_cursor") is not None:
        updated["cursor"] = data["next_cursor"]
    return {"state": updated, "new_ids": sorted(set(new)), "changed_ids": sorted(set(changed)), "has_more": bool(data.get("has_more", False))}


def scan_tree(root: str | Path) -> dict:
    """Inventory files byte-for-byte without following symbolic links."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be a directory")
    rows = []
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            raise ValueError(f"symlink not supported: {file}")
        if not file.is_file():
            continue
        name = _safe_path(file.relative_to(root).as_posix())
        data = file.read_bytes()
        rows.append({"path": name, "size": len(data), "sha256": digest(data)})
    return {"schema": SCHEMA, "files": rows}


def verify_tree(root: str | Path, manifest: dict) -> dict:
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unrecognized manifest schema")
    expected = {item["path"]: item for item in manifest.get("files", [])}
    if len(expected) != len(manifest.get("files", [])) or any(_safe_path(p) != p for p in expected):
        raise ValueError("invalid or duplicate manifest paths")
    actual = {item["path"]: item for item in scan_tree(root)["files"]}
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    modified = sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p])
    return {"ok": not (missing or extra or modified), "missing": missing, "extra": extra, "modified": modified}


def pack_tree(root: str | Path, output: str | Path) -> dict:
    """Write a deterministic ZIP; output must be outside the source tree."""
    root = Path(root).resolve(strict=True)
    output = Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("archive output must be outside the source tree")
    manifest = scan_tree(root)
    if any(item["path"] == "MANIFEST.json" for item in manifest["files"]):
        raise ValueError("source cannot contain reserved MANIFEST.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as z:
        for item in manifest["files"]:
            info = zipfile.ZipInfo(item["path"], ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, (root / item["path"]).read_bytes())
        info = zipfile.ZipInfo("MANIFEST.json", ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, canonical(manifest))
    return {"manifest": manifest, "archive_sha256": digest(output.read_bytes())}


def verify_archive(path: str | Path) -> dict:
    """Validate member names, uniqueness, sizes, and SHA-256 without extraction."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or "MANIFEST.json" not in names:
            raise ValueError("duplicate names or missing manifest")
        for info in z.infolist():
            _safe_path(info.filename)
            mode = info.external_attr >> 16
            if (mode & 0o170000) == 0o120000:
                raise ValueError("symlink entry not supported")
        manifest = json.loads(z.read("MANIFEST.json"))
        if manifest.get("schema") != SCHEMA:
            raise ValueError("unrecognized manifest schema")
        files = manifest.get("files", [])
        listed = [row["path"] for row in files]
        if len(listed) != len(set(listed)) or set(names) != set(listed) | {"MANIFEST.json"}:
            raise ValueError("archive file list mismatch")
        bad = []
        for row in files:
            name = _safe_path(row["path"])
            data = z.read(name)
            if len(data) != row["size"] or digest(data) != row["sha256"]:
                bad.append(name)
        return {"ok": not bad, "files": len(files), "modified": bad}
