"""Run python -m pocket.receipt_cli for offline durable receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .receipts import ReceiptStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline receipts; never executes or retries writes")
    parser.add_argument("database", help="SQLite ledger filename")
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser("begin", help="record intent BEFORE the external operation")
    begin.add_argument("id")
    begin.add_argument("input_file")
    begin.add_argument("--spec", default="unspecified", help="specification revision")
    begin.add_argument("--source", default="observed", choices=["observed", "reproduced", "inferred", "inherited"])
    accept = commands.add_parser("accept", help="record external acceptance, NOT verification")
    accept.add_argument("id")
    verify = commands.add_parser("verify", help="compare independent readback with intended bytes")
    verify.add_argument("id")
    verify.add_argument("readback_file")
    fail = commands.add_parser("fail", help="record an explicitly known failure")
    fail.add_argument("id")
    fail.add_argument("reason")
    show = commands.add_parser("show", help="inspect one operation")
    show.add_argument("id")
    commands.add_parser("unresolved", help="list work requiring reconciliation; no automatic replay")
    args = parser.parse_args(argv)
    try:
        with ReceiptStore(args.database) as store:
            if args.command == "begin":
                result = store.begin(args.id, Path(args.input_file).read_bytes(),
                                     specification=args.spec, evidence_source=args.source)
            elif args.command == "accept":
                result = store.accept(args.id)
            elif args.command == "verify":
                result = store.verify(args.id, Path(args.readback_file).read_bytes())
            elif args.command == "fail":
                result = store.fail(args.id, args.reason)
            elif args.command == "show":
                result = store.get(args.id)
                if result is None:
                    raise ValueError("unknown operation")
            else:
                result = store.unresolved()
        print(json.dumps(result, indent=2, sort_keys=True))
        if isinstance(result, dict) and result.get("status") == "failed":
            return 1
        return 0
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
