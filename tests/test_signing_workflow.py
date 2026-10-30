"""Static safety assertions for the optional GitHub NIP-46 connection probe."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/puter-nip46-check.yml"
GUIDE = ROOT / "NOSTR-SIGNING-TEST.md"


class GitHubSignerSmokeTests(unittest.TestCase):
    def test_workflow_is_manual_only_and_read_only(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", content)
        self.assertNotIn("pull_request:", content)
        self.assertNotIn("push:", content)
        self.assertIn("contents: read", content)
        self.assertIn("cancel-in-progress: false", content)

    def test_no_publication_or_weak_dry_run_substitution(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        commands = [
            line.strip() for line in content.splitlines()
            if re.match(r"^(?:nsyte |deno |curl |gh )", line.strip())
        ]
        self.assertTrue(any("nsyte list --sec" in c for c in commands))
        self.assertFalse(any(c.startswith(("nsyte deploy", "nsyte upload", "nsyte put", "nsyte announce", "nsyte delete", "nsyte undeploy")) for c in commands))
        self.assertFalse(any("--dry-run" in c for c in commands))
        self.assertIn("${{ secrets.NBUNK_SECRET }}", content)
        self.assertIn("nbunksec1*", content)

    def test_explicit_scope_and_first_pairing_documentation(self):
        guide = GUIDE.read_text(encoding="utf-8")
        for required in ("nsyte ci", "NBUNK_SECRET", "not tested", "Puter", "no nsite manifest"):
            self.assertIn(required.lower(), guide.lower())
        self.assertNotIn("nsec1", WORKFLOW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
