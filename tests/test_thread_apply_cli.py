import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from pocket.__main__ import main


class ApplyCliTest(unittest.TestCase):
    def test_apply_command_writes_readable_verified_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, page, ledger = (Path(tmp) / p for p in
                                   ("state.json", "page.json", "ledger.sqlite"))
            state.write_text(json.dumps({"root_id": "root", "seen": [], "cursor": "old"}))
            page.write_text(json.dumps({"ok": True, "data": {
                "root_id": "root", "next_cursor": "new",
                "messages": [{"id": "m", "text": "sample"}]}}))
            with patch("sys.argv", ["pocket", "apply-thread", str(state),
                                    str(page), str(ledger), "work-1"]):
                with patch("sys.stdout", new_callable=StringIO) as out:
                    rc = main()
                result = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(result["receipt"]["status"], "verified")
            self.assertEqual(json.loads(state.read_text())["cursor"], "new")


if __name__ == "__main__":
    unittest.main()
