"""Synthetic offline crash-boundary and recovery tests for real disk writes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pocket.receipts import ReceiptStore
from pocket.thread_apply import apply_thread_page


class SimulatedProcessDeath(BaseException):
    pass


class ApplyThreadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.state, self.page, self.ledger = (root / x for x in
                                               ("state.json", "page.json", "ledger.db"))
        self.initial = {"root_id": "root", "cursor": "older", "seen": []}
        self.state.write_text(json.dumps(self.initial))
        self.page.write_text(json.dumps({"ok": True, "data": {
            "root_id": "root", "messages": [{"id": "msg1", "text": "public fixture"}],
            "next_cursor": "newer"}}))

    def apply(self, op="one", **kwargs):
        return apply_thread_page(self.state, self.page, self.ledger, op, **kwargs)

    def test_real_write_is_independently_verified(self):
        response = self.apply()
        self.assertEqual(response["outcome"], "written")
        self.assertEqual(response["new_ids"], ["msg1"])
        self.assertEqual(response["receipt"]["status"], "verified")
        self.assertEqual(json.loads(self.state.read_text())["cursor"], "newer")
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.unresolved(), [])

    def test_invalid_input_does_not_mutate_state_or_ledger(self):
        original = self.state.read_bytes()
        self.page.write_text(json.dumps({"ok": True, "data": {"root_id": "wrong",
                                                             "messages": []}}))
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(self.state.read_bytes(), original)
        with ReceiptStore(self.ledger) as store:
            self.assertIsNone(store.get("one"))

    def test_crash_after_begin_requires_explicit_retry(self):
        original = self.state.read_bytes()
        def crash(stage):
            if stage == "after_begin":
                raise SimulatedProcessDeath()
        with self.assertRaises(SimulatedProcessDeath):
            self.apply(checkpoint=crash)
        self.assertEqual(self.state.read_bytes(), original)
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("one")["status"], "attempted")
        with self.assertRaisesRegex(ValueError, "explicitly --retry"):
            self.apply()
        self.assertEqual(self.apply(retry_unresolved=True)["outcome"], "explicit_retry")
        self.assertEqual(self.apply()["outcome"], "previously_verified")

    def test_crash_after_atomic_rename_reconciles_without_second_write(self):
        def crash(stage):
            if stage == "after_replace":
                raise SimulatedProcessDeath()
        with self.assertRaises(SimulatedProcessDeath):
            self.apply(checkpoint=crash)
        self.assertEqual(json.loads(self.state.read_text())["cursor"], "newer")
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("one")["status"], "attempted")
        with patch("pocket.thread_apply._replace_durably",
                   side_effect=AssertionError("must not rewrite")):
            result = self.apply()
        self.assertEqual(result["outcome"], "reconciled")
        self.assertEqual(result["receipt"]["status"], "verified")

    def test_crash_after_accept_reconciles(self):
        def crash(stage):
            if stage == "after_accept":
                raise SimulatedProcessDeath()
        with self.assertRaises(SimulatedProcessDeath):
            self.apply(checkpoint=crash)
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("one")["status"], "accepted")
        self.assertEqual(self.apply()["outcome"], "reconciled")

    def test_mismatched_readback_records_failure(self):
        def corrupt(stage):
            if stage == "after_accept":
                self.state.write_bytes(b'{"unexpected":"mutation"}')
        result = self.apply(checkpoint=corrupt)
        self.assertEqual(result["receipt"]["status"], "failed")
        self.assertNotEqual(result["receipt"]["payload_sha256"],
                            result["receipt"]["readback_sha256"])
        with self.assertRaises(ValueError):
            self.apply()

    def test_verified_id_not_replayed_and_cannot_bind_other_page(self):
        self.apply()
        with patch("pocket.thread_apply._replace_durably",
                   side_effect=AssertionError("must not rewrite")):
            self.assertEqual(self.apply()["outcome"], "previously_verified")
        self.page.write_text(json.dumps({"ok": True, "data": {"root_id": "root",
                                    "messages": [], "next_cursor": "different"}}))
        with self.assertRaisesRegex(ValueError, "different page"):
            self.apply()

    def test_separate_files_and_no_symlink(self):
        with self.assertRaises(ValueError):
            apply_thread_page(self.state, self.page, self.state, "same")
        link = self.state.with_name("alias.json")
        link.symlink_to(self.state)
        with self.assertRaises(ValueError):
            apply_thread_page(link, self.page, self.ledger, "aliased")


if __name__ == "__main__":
    unittest.main()
