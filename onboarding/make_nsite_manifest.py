#!/usr/bin/env python3
"""Compute unsigned NIP-5A path tags + aggregate hash for static site; no keys or network."""
import argparse
import hashlib
import json
from pathlib import Path

def manifest(site: Path) -> dict:
    site = site.resolve(strict=True)
    if not site.is_dir():
        raise ValueError("Site must be a directory")
    tags = []
    for p in sorted(site.rglob("*")):
        if p.is_symlink():
            raise ValueError(f"Symlink rejected: {p}")
        if not p.is_file():
            continue
        relative = "/" + p.relative_to(site).as_posix()
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        tags.append(["path",relative,digest])
    if not tags:
        raise ValueError("Site has no files")
    lines = sorted(f"{digest} {path}\n" for _,path,digest in tags)
    aggregate = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    return {"status":"unsigned; not a Nostr event or publication",
            "file_count":len(tags),"tags":tags+[["x",aggregate,"aggregate"]]}

if __name__=="__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("site",type=Path)
    args = p.parse_args()
    print(json.dumps(manifest(args.site),sort_keys=True,indent=2))
