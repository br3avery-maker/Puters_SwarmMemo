import tempfile
import unittest
from pathlib import Path
from pocket.receipt_cli import main
from unittest.mock import patch
from io import StringIO


class CliTests(unittest.TestCase):
    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "ledger.db")
            src, out = Path(tmp) / "src", Path(tmp) / "out"
            src.write_bytes(b"data")
            out.write_bytes(b"data")
            with patch("sys.stdout", new_callable=StringIO):
                self.assertEqual(main([db, "begin", "cli-1", str(src), "--spec", "test@1"]), 0)
                self.assertEqual(main([db, "accept", "cli-1"]), 0)
                self.assertEqual(main([db, "verify", "cli-1", str(out)]), 0)
                self.assertEqual(main([db, "unresolved"]), 0)

    def test_cli_mismatch_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "ledger.db")
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            a.write_bytes(b"expected")
            b.write_bytes(b"changed")
            with patch("sys.stdout", new_callable=StringIO):
                self.assertEqual(main([db, "begin", "mismatch", str(a)]), 0)
                self.assertEqual(main([db, "accept", "mismatch"]), 0)
                self.assertEqual(main([db, "verify", "mismatch", str(b)]), 1)


if __name__ == "__main__":
    unittest.main()
