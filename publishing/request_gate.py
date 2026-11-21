"""Offline policy for the single authorized Loopy Library publication request."""
import json
import os
from pathlib import Path

REPO = "br3avery-maker/Puters_SwarmMemo"
ISSUE = 11
DIGEST = "9fbc1c368f9b5147efbd8634e278f0ce60df9c78b963d1057a7bffcf8d707564"
REQUEST = f"/publish loopy-library sha256:{DIGEST}"


def authorized(event_name, event, ref, actor_id, triggering_actor):
    repository = event.get("repository", {})
    owner = repository.get("owner", {})
    owner_id = owner.get("id")
    sender = event.get("sender", {})
    if (repository.get("full_name") != REPO or ref != "refs/heads/main"
            or type(owner_id) is not int or owner_id <= 0
            or str(owner_id) != str(actor_id)
            or sender.get("id") != owner_id or sender.get("type") != "User"
            or not owner.get("login") or triggering_actor != owner["login"]):
        return False
    if event_name == "workflow_dispatch":
        return True
    if event_name != "issue_comment" or event.get("action") != "created":
        return False
    issue, comment = event.get("issue", {}), event.get("comment", {})
    return (issue.get("number") == ISSUE and "pull_request" not in issue
            and comment.get("author_association") == "OWNER"
            and comment.get("user", {}).get("id") == owner_id
            and comment.get("user", {}).get("type") == "User"
            and comment.get("body") == REQUEST)


def main():
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        ok = authorized(os.environ["GITHUB_EVENT_NAME"], event, os.environ["GITHUB_REF"],
                        os.environ["GITHUB_ACTOR_ID"], os.environ["GITHUB_TRIGGERING_ACTOR"])
    except (KeyError, OSError, TypeError, ValueError, AttributeError):
        ok = False
    if not ok:
        raise SystemExit("Publication request rejected; no signer invoked.")
    print("Authorized fixed Loopy Library publication request.")


if __name__ == "__main__":
    main()
