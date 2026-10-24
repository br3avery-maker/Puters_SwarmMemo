"""Hard-process-exit tests: no Python finally blocks or SQLite close run."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pocket.receipts import ReceiptStore
from pocket.thread_apply import apply_thread_page


class HardCrashTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.state = root / "state.json"
        self.page = root / "page.json"
        self.ledger = root / "receipts.sqlite"
        self.state.write_text(json.dumps({"root_id": "r", "seen": [], "cursor": "old"}))
        self.page.write_text(json.dumps({"ok": True, "data": {"root_id": "r",
                          "messages": [{"id": "a", "text": "fixture"}], "next_cursor": "new"}}))

    def _crash_at(self, stage):
        script = (
            "import os; from pocket.thread_apply import apply_thread_page; "
            f"apply_thread_page({str(self.state)!r}, {str(self.page)!r}, "
            f"{str(self.ledger)!r}, 'hard-crash', "
            f"checkpoint=lambda s: os._exit(37) if s == {stage!r} else None)"
        )
        proc = subprocess.run([sys.executable, "-c", script],
                              cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 37, proc.stderr)

    def test_abrupt_exit_after_begin(self):
        self._crash_at("after_begin")
        self.assertEqual(json.loads(self.state.read_text())["cursor"], "old")
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("hard-crash")["status"], "attempted")
        with self.assertRaises(ValueError):
            apply_thread_page(self.state, self.page, self.ledger, "hard-crash")
        result = apply_thread_page(self.state, self.page, self.ledger, "hard-crash",
                                   retry_unresolved=True)
        self.assertEqual(result["receipt"]["status"], "verified")

    def test_abrupt_exit_after_replace(self):
        self._crash_at("after_replace")
        self.assertEqual(json.loads(self.state.read_text())["cursor"], "new")
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("hard-crash")["status"], "attempted")
        result = apply_thread_page(self.state, self.page, self.ledger, "hard-crash")
        self.assertEqual(result["outcome"], "reconciled")
        self.assertEqual(result["receipt"]["status"], "verified")

    def test_abrupt_exit_after_accept(self):
        self._crash_at("after_accept")
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("hard-crash")["status"], "accepted")
        result = apply_thread_page(self.state, self.page, self.ledger, "hard-crash")
        self.assertEqual(result["receipt"]["status"], "verified")


if __name__ == "__main__":
    unittest.main()
