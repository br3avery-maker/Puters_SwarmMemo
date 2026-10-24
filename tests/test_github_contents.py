"""Offline contract tests for external GitHub file writes."""
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from pocket.github_contents import (GitHubContentsClient, RemoteError, RemoteFile,
                                    _blob_sha, sync_file)
from pocket.receipts import ReceiptStore
from pocket.github_file_cli import main


class FakeGitHub:
    owner, repo, branch = "puter", "fixtures", "main"
    _token = "mock-available-not-real"

    def __init__(self, content=None):
        self.content = content
        self.calls = 0
        self.after_put_error = False
        self.read_error = False

    def read(self, path):
        if self.read_error:
            raise RemoteError("simulated intermittent read failure")
        if self.content is None:
            return None
        return RemoteFile(_blob_sha(self.content), self.content)

    def put(self, path, data, *, message, expected_sha):
        current = _blob_sha(self.content) if self.content is not None else None
        if expected_sha != current:
            raise RemoteError("concurrent remote change")
        self.calls += 1
        self.content = data
        if self.after_put_error:
            raise RemoteError("transport timed out after service committed")


class RemoteContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = Path(tmp.name) / "receipts.sqlite"
        self.client = FakeGitHub(b"before")
        self.expected = _blob_sha(b"before")

    def sync(self, operation_id="op1", **kwargs):
        return sync_file(self.client, self.ledger, operation_id, "state.json", b"after",
                         expected_sha=self.expected, message="fixture update", **kwargs)

    def test_default_dry_run_never_writes_or_begins(self):
        result = self.sync()
        self.assertEqual(result["outcome"], "would_write")
        self.assertEqual(self.client.calls, 0)
        with ReceiptStore(self.ledger) as store:
            self.assertIsNone(store.get("op1"))

    def test_write_then_remote_readback_verified(self):
        result = self.sync(allow_write=True)
        self.assertEqual(result["outcome"], "verified_write")
        self.assertEqual(result["receipt"]["status"], "verified")
        self.assertEqual(self.client.calls, 1)
        self.assertEqual(self.sync()["outcome"], "still_verified")
        self.assertEqual(self.client.calls, 1)

    def test_crash_after_remote_write_reconciles_without_duplicate(self):
        class Crash(BaseException):
            pass
        def checkpoint(stage):
            if stage == "after_put":
                raise Crash()
        with self.assertRaises(Crash):
            self.sync(allow_write=True, checkpoint=checkpoint)
        with ReceiptStore(self.ledger) as store:
            self.assertEqual(store.get("op1")["status"], "attempted")
        r = self.sync()
        self.assertEqual(r["outcome"], "reconciled")
        self.assertEqual(r["receipt"]["status"], "verified")
        self.assertEqual(self.client.calls, 1)

    def test_timeout_after_server_write_reconciles(self):
        self.client.after_put_error = True
        with self.assertRaises(RemoteError):
            self.sync(allow_write=True)
        self.assertEqual(self.client.calls, 1)
        self.assertEqual(self.sync()["outcome"], "reconciled")
        self.assertEqual(self.client.calls, 1)

    def test_crash_before_write_requires_explicit_retry(self):
        class Crash(BaseException):
            pass
        def checkpoint(stage):
            if stage == "after_begin":
                raise Crash()
        with self.assertRaises(Crash):
            self.sync(allow_write=True, checkpoint=checkpoint)
        self.assertEqual(self.sync(allow_write=True)["outcome"], "unresolved_requires_review")
        self.assertEqual(self.client.calls, 0)
        self.assertEqual(self.sync(retry_unresolved=True)["outcome"], "would_write")
        self.assertEqual(self.sync(retry_unresolved=True, allow_write=True)["outcome"], "verified_write")
        self.assertEqual(self.client.calls, 1)

    def test_concurrent_remote_change_blocks_retry(self):
        def checkpoint(stage):
            if stage == "after_begin":
                raise RuntimeError("test abort")
        with self.assertRaises(RuntimeError):
            self.sync(allow_write=True, checkpoint=checkpoint)
        self.client.content = b"someone else wrote here"
        with self.assertRaisesRegex(ValueError, "preimage changed"):
            self.sync(allow_write=True, retry_unresolved=True)
        self.assertEqual(self.client.calls, 0)

    def test_readback_mismatch_fails_terminally(self):
        def checkpoint(stage):
            if stage == "after_accept":
                self.client.content = b"other value"
        r = self.sync(allow_write=True, checkpoint=checkpoint)
        self.assertEqual(r["outcome"], "readback_mismatch")
        self.assertEqual(r["receipt"]["status"], "failed")
        self.assertNotEqual(r["receipt"]["payload_sha256"], r["receipt"]["readback_sha256"])
        with self.assertRaisesRegex(ValueError, "terminal"):
            self.sync(allow_write=True, retry_unresolved=True)

    def test_new_file_requires_expected_absent(self):
        self.client.content = None
        self.expected = None
        result = self.sync(allow_write=True)
        self.assertEqual(result["outcome"], "verified_write")
        self.assertEqual(self.client.calls, 1)

    def test_reuse_id_different_target_is_rejected(self):
        self.sync(allow_write=True)
        with self.assertRaisesRegex(ValueError, "different remote intent"):
            sync_file(self.client, self.ledger, "op1", "other.json", b"after",
                      expected_sha=self.expected, message="fixture update")
        self.assertEqual(self.client.calls, 1)

    def test_preexisting_target_is_not_attributed_to_operation(self):
        self.client.content = b"after"
        result = self.sync(allow_write=True)
        self.assertEqual(result["outcome"], "already_present_no_write")
        self.assertIsNone(result["receipt"])
        self.assertEqual(self.client.calls, 0)

    def test_verified_receipt_detects_drift_without_replay(self):
        self.sync(allow_write=True)
        self.client.content = b"someone modified"
        result = self.sync(allow_write=True, retry_unresolved=True)
        self.assertEqual(result["outcome"], "remote_drift")
        self.assertEqual(self.client.calls, 1)

    def test_validation_precedes_network_or_ledger(self):
        with self.assertRaisesRegex(ValueError, "unsafe"):
            sync_file(self.client, self.ledger, "x", "../evil", b"stuff",
                      expected_sha=self.expected, message="change", allow_write=True)
        with self.assertRaisesRegex(ValueError, "expected blob SHA"):
            sync_file(self.client, self.ledger, "x", "state.json", b"stuff",
                      expected_sha="invalid", message="change", allow_write=True)


class DummyResponse:
    def __init__(self, data, url):
        self.data = data
        self.url = url
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return None
    def geturl(self):
        return self.url
    def read(self, n):
        return self.data


class FakeOpener:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        result = next(self.replies)
        if isinstance(result, Exception):
            raise result
        return DummyResponse(json.dumps(result).encode(), request.full_url)


class GitHubAPIClientTests(unittest.TestCase):
    def test_read_validates_bytes_and_never_leaks_token_in_url(self):
        data = b"hello bytes!"
        opener = FakeOpener([{"type": "file", "encoding": "base64",
                              "sha": _blob_sha(data), "content": base64.b64encode(data).decode()}])
        client = GitHubContentsClient("owner", "repo", "main", token="secret")
        client._opener = opener
        found = client.read("dir/file name.txt")
        self.assertEqual(found.content, data)
        url = opener.requests[0].full_url
        self.assertTrue(url.startswith("https://api.github.com/"))
        self.assertIn("dir/file%20name.txt?ref=main", url)
        self.assertNotIn("secret", url)
        self.assertEqual(opener.requests[0].get_header("Authorization"), "Bearer secret")

    def test_bad_sha_or_encoding_rejected(self):
        client = GitHubContentsClient("owner", "repo", "main")
        client._opener = FakeOpener([{"type": "file", "encoding": "base64",
                                      "sha": "0" * 40, "content": "aGVsbG8="}])
        with self.assertRaisesRegex(RemoteError, "mismatch"):
            client.read("x")
        client._opener = FakeOpener([{"type": "file", "encoding": "none"}])
        with self.assertRaisesRegex(RemoteError, "inline file"):
            client.read("x")

    def test_put_sends_precondition_and_requires_acknowledgment(self):
        client = GitHubContentsClient("owner", "repo", "develop", token="secret")
        opener = FakeOpener([{"commit": {"sha": "fake-commit"}}])
        client._opener = opener
        client.put("file.txt", b"hi", message="safe update", expected_sha="a" * 40)
        req = opener.requests[0]
        self.assertEqual(req.get_method(), "PUT")
        self.assertNotIn("secret", req.full_url)
        payload = json.loads(req.data)
        self.assertEqual(payload["sha"], "a" * 40)
        self.assertEqual(payload["branch"], "develop")
        self.assertEqual(base64.b64decode(payload["content"]), b"hi")

    def test_http_error_is_sanitized_and_not_falsely_confirmed(self):
        client = GitHubContentsClient("owner", "repo", "main", token="secret")
        client._opener = FakeOpener([HTTPError("https://api.github.com/", 503, "private detail", {}, None)])
        with self.assertRaises(RemoteError) as caught:
            client.put("file.txt", b"x", message="m", expected_sha=None)
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn("private detail", str(caught.exception))
        self.assertIn("outcome unknown", str(caught.exception))

    def test_404_read_is_missing_but_404_put_is_unconfirmed(self):
        client = GitHubContentsClient("owner", "repo", "main", token="secret")
        missing = HTTPError("https://api.github.com/", 404, "missing", {}, None)
        client._opener = FakeOpener([missing])
        self.assertIsNone(client.read("x"))
        client._opener = FakeOpener([missing])
        with self.assertRaises(RemoteError):
            client.put("x", b"data", message="create", expected_sha=None)

    def test_cli_plan_no_write(self):
        import io
        fake = FakeGitHub(b"before")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source"
            path.write_bytes(b"after")
            with patch("pocket.github_file_cli.GitHubContentsClient", return_value=fake):
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    self.assertEqual(main(["plan", "owner", "repo", "main", "x", str(path)]), 0)
                result = json.loads(stdout.getvalue())
                self.assertFalse(result["matches"])
                self.assertEqual(fake.calls, 0)


class DiskBackedRemote:
    """Fixture service with a filesystem outside the receipt ledger/process."""
    owner, repo, branch = "puter", "crash-test", "main"
    _token = "test-only"

    def __init__(self, remote_file, count_file):
        self.remote_file = Path(remote_file)
        self.count_file = Path(count_file)

    def read(self, path):
        if not self.remote_file.exists():
            return None
        data = self.remote_file.read_bytes()
        return RemoteFile(_blob_sha(data), data)

    def put(self, path, data, *, message, expected_sha):
        prior = self.read(path)
        if (prior.sha if prior else None) != expected_sha:
            raise RemoteError("conflict")
        self.remote_file.write_bytes(data)
        with self.count_file.open("a") as f:
            f.write("one put\n")
            f.flush()
            import os
            os.fsync(f.fileno())


class RemoteHardCrashTests(unittest.TestCase):
    def test_abrupt_process_exit_before_and_after_remote_write(self):
        # External state survives child process death; count proves no duplicate PUT.
        for stage in ("after_begin", "after_put", "after_accept"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                remote = root / "remote.txt"
                count = root / "count.txt"
                ledger = root / "ledger.sqlite"
                remote.write_bytes(b"before")
                script = '''import os, sys
sys.path.insert(0, "tests")
from test_github_contents import DiskBackedRemote
from pocket.github_contents import sync_file, _blob_sha
remote, count, ledger, stage = sys.argv[1:]
sync_file(DiskBackedRemote(remote, count), ledger, "crash", "test.txt", b"after",
          expected_sha=_blob_sha(b"before"), message="synthetic",
          allow_write=True,
          checkpoint=lambda name: os._exit(47) if name == stage else None)
'''
                result = subprocess.run([sys.executable, "-c", script,
                                         str(remote), str(count), str(ledger), stage],
                                        cwd=Path(__file__).resolve().parents[1],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 47, result.stderr)
                client = DiskBackedRemote(remote, count)
                outcome = sync_file(client, ledger, "crash", "test.txt", b"after",
                                    expected_sha=_blob_sha(b"before"), message="synthetic")
                if stage == "after_begin":
                    self.assertEqual(outcome["outcome"], "unresolved_requires_review")
                    outcome = sync_file(client, ledger, "crash", "test.txt", b"after",
                                        expected_sha=_blob_sha(b"before"),
                                        message="synthetic", retry_unresolved=True,
                                        allow_write=True)
                    self.assertEqual(outcome["outcome"], "verified_write")
                else:
                    self.assertEqual(outcome["outcome"], "reconciled")
                self.assertEqual(outcome["receipt"]["status"], "verified")
                self.assertEqual(remote.read_bytes(), b"after")
                self.assertEqual(count.read_text().count("one put"), 1)


class FailureModeTests(unittest.TestCase):
    def test_no_token_means_no_write_or_ledger_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = FakeGitHub(b"old")
            f._token = None
            db = Path(tmp) / "receipts.sqlite"
            with self.assertRaisesRegex(ValueError, "GITHUB_TOKEN"):
                sync_file(f, db, "id", "path", b"new", expected_sha=_blob_sha(b"old"),
                          message="msg", allow_write=True)
            self.assertEqual(f.calls, 0)
            with ReceiptStore(db) as store:
                self.assertIsNone(store.get("id"))

    def test_lockfile_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ledger.sqlite"
            lock = Path(tmp) / "ledger.sqlite.remote.lock"
            lock.symlink_to(Path(tmp) / "somewhere")
            with self.assertRaisesRegex(ValueError, "symlink"):
                sync_file(FakeGitHub(b"old"), db, "id", "path", b"new",
                          expected_sha=_blob_sha(b"old"), message="msg")

    def test_plan_does_not_accept_remote_write_switch(self):
        with self.assertRaises(SystemExit) as caught:
            main(["plan", "x", "y", "main", "path", "/tmp/none", "--write"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
