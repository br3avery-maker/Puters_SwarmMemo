"""Synthetic offline crash-boundary and durable receipt tests."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from pocket.receipts import ReceiptStore


class DurableReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "receipts.sqlite"

    def test_acceptance_is_not_verification(self):
        with ReceiptStore(self.path) as s:
            a = s.begin("job1", b"expected", specification="spec@2")
            self.assertEqual(a["status"], "attempted")
            self.assertEqual(s.accept("job1")["status"], "accepted")
            self.assertEqual(len(s.unresolved()), 1)
            v = s.verify("job1", b"expected")
            self.assertEqual(v["status"], "verified")
            self.assertEqual(v["payload_sha256"], v["readback_sha256"])
            self.assertEqual(s.unresolved(), [])

    def test_incorrect_readback_preserves_evidence(self):
        with ReceiptStore(self.path) as s:
            s.begin("job2", b"expected")
            s.accept("job2")
            v = s.verify("job2", b"actual")
            self.assertEqual((v["status"], v["reason"]), ("failed", "readback mismatch"))
            self.assertNotEqual(v["payload_sha256"], v["readback_sha256"])

    def test_no_premature_verification_or_replay(self):
        with ReceiptStore(self.path) as s:
            s.begin("job3", b"x")
            with self.assertRaises(ValueError):
                s.verify("job3", b"x")
            s.accept("job3")
            with self.assertRaises(ValueError):
                s.accept("job3")
            s.fail("job3", "server lost write")
            with self.assertRaises(ValueError):
                s.accept("job3")

    def test_idempotent_begin_but_conflicts_rejected(self):
        with ReceiptStore(self.path) as s:
            a = s.begin("job4", b"x", evidence_source="inherited")
            b = s.begin("job4", b"x", evidence_source="inherited")
            self.assertEqual(a, b)
            with self.assertRaises(ValueError):
                s.begin("job4", b"y", evidence_source="inherited")
            with self.assertRaises(ValueError):
                s.begin("job4", b"x", evidence_source="observed")
            with self.assertRaises(ValueError):
                s.begin("../bad", b"x")

    def test_reopen_after_new_process(self):
        writer = ("from pocket.receipts import ReceiptStore; "
                  f"s=ReceiptStore({str(self.path)!r}); "
                  "s.begin('crashed', b'data', specification='fixture@1'); "
                  "s.accept('crashed'); s.close()")
        subprocess.run([sys.executable, "-c", writer], check=True,
                       cwd=Path(__file__).resolve().parents[1])
        with ReceiptStore(self.path) as s:
            self.assertEqual(s.get("crashed")["status"], "accepted")
            self.assertEqual([r["operation_id"] for r in s.unresolved()], ["crashed"])
            self.assertEqual(s.verify("crashed", b"data")["status"], "verified")

    def test_unknown_and_bad_inputs(self):
        with ReceiptStore(self.path) as s:
            with self.assertRaises(ValueError):
                s.accept("missing")
            with self.assertRaises(ValueError):
                s.begin("x", b"a", evidence_source="imagined")
            with self.assertRaises(ValueError):
                s.begin("x", b"a", specification="")
            s.begin("x", b"a")
            with self.assertRaises(ValueError):
                s.fail("x", "")


if __name__ == "__main__":
    unittest.main()
