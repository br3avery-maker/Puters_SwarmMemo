import copy
import unittest
from request_gate import authorized, REQUEST, REPO

class RequestGateTest(unittest.TestCase):
    def setUp(self):
        owner = {"id": 42, "login": "owner", "type": "User"}
        self.event = {"repository": {"full_name": REPO, "owner": owner},
                      "sender": dict(owner), "action": "created", "issue": {"number": 11},
                      "comment": {"author_association": "OWNER", "user": dict(owner), "body": REQUEST}}
    def allowed(self, event=None, name="issue_comment", ref="refs/heads/main", actor="42", trigger="owner"):
        return authorized(name, self.event if event is None else event, ref, actor, trigger)
    def test_owner_exact_request(self): self.assertTrue(self.allowed())
    def test_owner_manual(self): self.assertTrue(self.allowed(name="workflow_dispatch"))
    def test_wrong_branch(self): self.assertFalse(self.allowed(ref="refs/heads/other"))
    def test_wrong_actor(self): self.assertFalse(self.allowed(actor="43"))
    def test_rerun_by_other(self): self.assertFalse(self.allowed(trigger="other"))
    def test_pr_event(self): self.assertFalse(self.allowed(name="pull_request"))
    def test_bad_events(self):
        cases = [(["repository", "full_name"], "fork/repo"),
                 (["sender", "id"], 43), (["sender", "type"], "Bot"),
                 (["action"], "edited"), (["action"], "deleted"),
                 (["issue", "number"], 15), (["issue", "pull_request"], {}),
                 (["comment", "body"], REQUEST + "\n"),
                 (["comment", "body"], REQUEST.upper()),
                 (["comment", "body"], "/publish $(echo bad)"),
                 (["comment", "user", "id"], 43),
                 (["comment", "user", "type"], "Bot"),
                 (["comment", "author_association"], "COLLABORATOR")]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                e = copy.deepcopy(self.event); obj = e
                for k in path[:-1]: obj = obj[k]
                obj[path[-1]] = value
                self.assertFalse(self.allowed(e))
    def test_no_owner_missing_id(self):
        e=copy.deepcopy(self.event); del e["repository"]["owner"]["id"]
        self.assertFalse(self.allowed(e))
    def test_invalid_manual_actor(self): self.assertFalse(self.allowed(name="workflow_dispatch", actor="43"))

if __name__ == "__main__": unittest.main()
