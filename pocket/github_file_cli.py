"""Explicit opt-in GitHub file sync. Never sends a write without --write.

Usage: python -m pocket.github_file_cli [plan|sync] ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from .github_contents import GitHubContentsClient, RemoteError, sync_file


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verified GitHub file sync; dry run by default")
    subs = p.add_subparsers(dest="command", required=True)
    for command in ("plan", "sync"):
        s = subs.add_parser(command)
        if command == "sync":
            s.add_argument("ledger", help="local SQLite receipt ledger; never commit it")
            s.add_argument("operation_id", help="stable unique operation ID")
        for name in ("owner", "repo", "branch", "path", "source_file"):
            s.add_argument(name)
        if command == "sync":
            expect = s.add_mutually_exclusive_group(required=True)
            expect.add_argument("--expect-sha", help="current GitHub file blob SHA")
            expect.add_argument("--expect-absent", action="store_true",
                                help="create only if file is absent")
            s.add_argument("--message", default="Verified workbench file update")
            s.add_argument("--write", action="store_true", help="allow one remote PUT")
            s.add_argument("--retry", action="store_true",
                           help="explicitly permit retry of an unresolved operation")
    args = p.parse_args(argv)
    try:
        data = Path(args.source_file).read_bytes()
        # A token is read from the environment only; never print it or store it.
        client = GitHubContentsClient(args.owner, args.repo, args.branch,
                                      token=os.environ.get("GITHUB_TOKEN"))
        if args.command == "plan":
            remote = client.read(args.path)
            result = {"outcome": "inspection_only", "current_sha": remote.sha if remote else None,
                      "desired_sha256": hashlib.sha256(data).hexdigest(),
                      "matches": remote is not None and remote.content == data}
            code = 0
        else:
            result = sync_file(client, args.ledger, args.operation_id, args.path, data,
                               expected_sha=args.expect_sha, message=args.message,
                               allow_write=args.write, retry_unresolved=args.retry)
            code = (0 if result["outcome"] in ("verified_write", "reconciled",
                                               "still_verified", "already_present_no_write")
                    else 1)
        print(json.dumps(result, sort_keys=True, indent=2))
        return code
    except (RemoteError, ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        p.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
