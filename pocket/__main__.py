"""Run `python -m pocket` for isolated workbench operations."""
import argparse
import json
from pathlib import Path
from .workbench import merge_thread_page, scan_tree, verify_tree, pack_tree, verify_archive


def main() -> int:
    p = argparse.ArgumentParser(description="Puter's offline workbench; no IC or network required")
    sub = p.add_subparsers(dest="command", required=True)
    for name, fields in {"scan": ("root",), "verify": ("root", "manifest"),
                         "pack": ("root", "output"), "check-archive": ("archive",),
                         "merge-thread": ("state", "page")}.items():
        s = sub.add_parser(name)
        for field in fields:
            s.add_argument(field)
    a = p.parse_args()
    try:
        if a.command == "scan":
            result = scan_tree(a.root)
        elif a.command == "verify":
            result = verify_tree(a.root, json.loads(Path(a.manifest).read_text(encoding="utf-8")))
        elif a.command == "pack":
            result = pack_tree(a.root, a.output)
        elif a.command == "check-archive":
            result = verify_archive(a.archive)
        else:
            result = merge_thread_page(json.loads(Path(a.state).read_text(encoding="utf-8")),
                                       json.loads(Path(a.page).read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok", True) else 1
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        p.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
