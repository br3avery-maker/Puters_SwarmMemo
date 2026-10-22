"""Synthetic tests for receipt_state; no network or private data."""
import unittest
from experiments.receipt_state import start, transition


class ReceiptStateTests(unittest.TestCase):
    def test_verified_only_after_acceptance_and_matching_readback(self):
        data = b"public fixture"
        r = start(data)
        self.assertEqual(r.state, "attempted")
        r = transition(r, accepted=True)
        self.assertEqual(r.state, "accepted")
        self.assertEqual(transition(r, readback=data).state, "verified")

    def test_mismatch_fails(self):
        r = transition(start(b"original"), accepted=True)
        result = transition(r, readback=b"altered")
        self.assertEqual(result.state, "failed")
        self.assertEqual(result.reason, "readback mismatch")

    def test_no_premature_verification(self):
        with self.assertRaises(ValueError):
            transition(start(b"original"), readback=b"original")

    def test_terminal_state_cannot_change(self):
        r = transition(transition(start(b"x"), accepted=True), readback=b"x")
        with self.assertRaises(ValueError):
            transition(r, accepted=True)

    def test_explicit_failure(self):
        r = transition(start(b"x"), error="timeout")
        self.assertEqual((r.state, r.reason), ("failed", "timeout"))


if __name__ == "__main__":
    unittest.main()
