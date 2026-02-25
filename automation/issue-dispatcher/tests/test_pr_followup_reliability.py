from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


DISPATCHER_PATH = Path(__file__).resolve().parents[1] / "dispatcher.py"
spec = importlib.util.spec_from_file_location("issue_dispatcher", DISPATCHER_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PRFollowupReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        state_dir = Path(self.tmp.name)
        self.orig_followup = module.FOLLOWUP_FILE
        self.orig_state = module.STATE_FILE
        module.FOLLOWUP_FILE = state_dir / "review_followups.json"
        module.STATE_FILE = state_dir / "processed_deliveries.json"

    def tearDown(self) -> None:
        module.FOLLOWUP_FILE = self.orig_followup
        module.STATE_FILE = self.orig_state
        self.tmp.cleanup()

    def _payload(self, comment_id: int, body: str = "fix this") -> dict:
        return {
            "action": "created",
            "repository": {"full_name": "fourmajor/hoopsmania"},
            "issue": {
                "number": 102,
                "title": "PR title",
                "html_url": "https://github.com/fourmajor/hoopsmania/pull/102",
                "pull_request": {"url": "https://api.github.com/repos/fourmajor/hoopsmania/pulls/102"},
                "labels": [],
                "body": "",
            },
            "comment": {
                "id": comment_id,
                "html_url": f"https://github.com/fourmajor/hoopsmania/pull/102#issuecomment-{comment_id}",
                "body": body,
                "created_at": "2026-02-25T18:00:00Z",
                "updated_at": "2026-02-25T18:00:00Z",
            },
            "sender": {"login": "fourmajor"},
        }

    def test_multiple_sequential_comments_increment_sequence(self) -> None:
        routing = {"default_pr_role": "ctrl^core", "pr_rules": []}
        task1, _ = module._create_or_update_followup(self._payload(1001), "issue_comment", routing)
        task2, _ = module._create_or_update_followup(self._payload(1002), "issue_comment", routing)

        self.assertEqual(task1["event_sequence"], 1)
        self.assertEqual(task2["event_sequence"], 2)
        self.assertEqual(task2["status"], "open")

    def test_duplicate_delivery_same_comment_id_is_marked_duplicate(self) -> None:
        routing = {"default_pr_role": "ctrl^core", "pr_rules": []}
        task1, _ = module._create_or_update_followup(self._payload(2001), "issue_comment", routing)
        task2, _ = module._create_or_update_followup(self._payload(2001), "issue_comment", routing)

        self.assertFalse(task1["last_event_duplicate"])
        self.assertTrue(task2["last_event_duplicate"])
        self.assertEqual(task2["event_sequence"], 1)

    def test_done_state_then_new_comment_reopens_followup(self) -> None:
        routing = {"default_pr_role": "ctrl^core", "pr_rules": []}
        task1, _ = module._create_or_update_followup(self._payload(3001), "issue_comment", routing)

        followups = module._load_followups()
        key = task1["id"]
        followups["tasks"][key]["status"] = "closed"
        followups["tasks"][key]["closed_at"] = "2026-02-25T18:10:00Z"
        module._save_followups(followups)

        reopened, _ = module._create_or_update_followup(self._payload(3002), "issue_comment", routing)
        self.assertEqual(reopened["status"], "open")
        self.assertIsNone(reopened["closed_at"])
        self.assertEqual(reopened["event_sequence"], 2)


if __name__ == "__main__":
    unittest.main()
