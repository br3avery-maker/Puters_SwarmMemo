import json
import tempfile
import unittest
from pathlib import Path
from pocket.workbench import (digest, merge_thread_page, scan_tree, verify_tree,
                              pack_tree, verify_archive)


class WorkbenchTest(unittest.TestCase):
    def test_thread_new_changed_and_cursor(self):
        state = {"root_id": "root", "cursor": "old", "seen": []}
        page = {"ok": True, "data": {"root_id": "root", "messages": [{"id": "a", "text": "one"}], "next_cursor": "new"}}
        first = merge_thread_page(state, page)
        self.assertEqual(first["new_ids"], ["a"])
        self.assertEqual(first["state"]["cursor"], "new")
        self.assertEqual(state["cursor"], "old")
        second = merge_thread_page(first["state"], page)
        self.assertEqual(second["new_ids"], [])
        third = merge_thread_page(second["state"], {"ok": True, "data": {"root_id": "root", "messages": [{"id": "a", "text": "two"}]}})
        self.assertEqual(third["changed_ids"], ["a"])

    def test_failed_thread_does_not_advance(self):
        state = {"root_id": "r", "cursor": "safe"}
        with self.assertRaises(ValueError):
            merge_thread_page(state, {"ok": False, "next_cursor": "bad"})
        self.assertEqual(state["cursor"], "safe")
        with self.assertRaises(ValueError):
            merge_thread_page(state, {"ok": True, "data": {"root_id": "wrong"}})

    def test_tree_manifest_and_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            root.mkdir()
            (root / "a.txt").write_text("hello")
            manifest = scan_tree(root)
            self.assertTrue(verify_tree(root, manifest)["ok"])
            (root / "a.txt").write_text("other")
            self.assertEqual(verify_tree(root, manifest)["modified"], ["a.txt"])
            (root / "extra").write_bytes(b"")
            self.assertEqual(verify_tree(root, manifest)["extra"], ["extra"])

    def test_archive_reproducibility_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            root.mkdir()
            (root / "a").write_bytes(b"hello")
            out1, out2 = Path(tmp) / "one.zip", Path(tmp) / "two.zip"
            a, b = pack_tree(root, out1), pack_tree(root, out2)
            self.assertEqual(a["archive_sha256"], b["archive_sha256"])
            self.assertEqual(verify_archive(out1), {"ok": True, "files": 1, "modified": []})

    def test_no_archive_inside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                pack_tree(tmp, Path(tmp) / "inside.zip")

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            root.mkdir()
            (root / "link").symlink_to(Path(tmp))
            with self.assertRaises(ValueError):
                scan_tree(root)

    def test_reject_traversal_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                verify_tree(tmp, {"schema": "puter.pocket.manifest.v1", "files": [{"path": "../secret", "sha256": "x", "size": 1}]})

    def test_reserved_archive_manifest_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            root.mkdir()
            (root / "MANIFEST.json").write_text("not allowed")
            with self.assertRaises(ValueError):
                pack_tree(root, Path(tmp) / "a.zip")

    def test_digests(self):
        self.assertEqual(digest(b""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


if __name__ == "__main__":
    unittest.main()
