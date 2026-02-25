from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


DISPATCHER_PATH = Path(__file__).resolve().parents[1] / "dispatcher.py"
spec = importlib.util.spec_from_file_location("issue_dispatcher", DISPATCHER_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DispatcherRoutingRetryTests(unittest.TestCase):
    def test_locktrace_changes_requested_routes_back_to_owner(self) -> None:
        original_gh_api_json = module._gh_api_json
        try:
            module._gh_api_json = lambda _path: []
            routing = {
                "default_pr_role": "ctrl^core",
                "pr_rules": [{"any_labels": ["backend"], "role": "Ghost|line"}],
            }
            payload = {
                "action": "submitted",
                "repository": {"full_name": "fourmajor/hoopsmania"},
                "pull_request": {
                    "number": 90999,
                    "title": "feat: backend update",
                    "body": "",
                    "html_url": "https://github.com/fourmajor/hoopsmania/pull/90999",
                    "labels": [{"name": "backend"}],
                },
                "review": {"state": "changes_requested", "html_url": "https://github.com/x"},
                "sender": {"login": "locktrace"},
            }
            task, _ = module._create_or_update_followup(payload, "pull_request_review", routing)
            self.assertEqual(task["owner_role"], "Ghost|line")
            self.assertEqual(task["role"], "Ghost|line")
            self.assertTrue(task["security_review_required"])
        finally:
            module._gh_api_json = original_gh_api_json

    def test_attempt_close_followup_requires_locktrace_approval_for_non_security_pr(self) -> None:
        original_threads = module._all_threads_resolved
        original_checks = module._checks_green
        original_reviews = module._latest_locktrace_review_state
        try:
            module._all_threads_resolved = lambda _repo, _pr: True
            module._checks_green = lambda _repo, _pr: True
            module._latest_locktrace_review_state = lambda _repo, _pr: "CHANGES_REQUESTED"
            closed, reason = module._attempt_close_followup(
                {
                    "id": "fourmajor/hoopsmania#100",
                    "repo": "fourmajor/hoopsmania",
                    "pr_number": 100,
                    "security_review_required": True,
                    "labels": [],
                }
            )
            self.assertFalse(closed)
            self.assertIn("locktrace approval required", reason)
        finally:
            module._all_threads_resolved = original_threads
            module._checks_green = original_checks
            module._latest_locktrace_review_state = original_reviews

    def test_override_label_allows_close_without_locktrace_approval(self) -> None:
        original_threads = module._all_threads_resolved
        original_checks = module._checks_green
        original_reviews = module._latest_locktrace_review_state
        try:
            module._all_threads_resolved = lambda _repo, _pr: True
            module._checks_green = lambda _repo, _pr: True
            module._latest_locktrace_review_state = lambda _repo, _pr: "CHANGES_REQUESTED"
            closed, _reason = module._attempt_close_followup(
                {
                    "id": "fourmajor/hoopsmania#101",
                    "repo": "fourmajor/hoopsmania",
                    "pr_number": 101,
                    "security_review_required": True,
                    "labels": [{"name": module.LOCKTRACE_OVERRIDE_LABEL}],
                }
            )
            self.assertTrue(closed)
        finally:
            module._all_threads_resolved = original_threads
            module._checks_green = original_checks
            module._latest_locktrace_review_state = original_reviews

    def test_normalize_role_falls_back_to_ctrl_core_when_unset_or_unknown(self) -> None:
        routing = {
            "default_role": "",
            "default_pr_role": "",
            "rules": [{"role": "pipewire"}],
            "pr_rules": [{"role": "neonflux"}],
        }
        self.assertEqual(module._normalize_role("", routing, pr=True), "ctrl^core")
        self.assertEqual(module._normalize_role("unknown-role", routing, pr=True), "ctrl^core")

    def test_route_pr_feedback_uses_default_when_no_rule_matches(self) -> None:
        original = module._gh_api_json
        module._gh_api_json = lambda _path: []
        try:
            routing = {
                "default_pr_role": "ctrl^core",
                "pr_rules": [{"any_paths": ["backend/"], "role": "Ghost|line"}],
            }
            role = module._route_pr_feedback(
                "fourmajor/hoopsmania",
                {"number": 123, "title": "chore", "body": "", "labels": []},
                routing,
            )
            self.assertEqual(role, "ctrl^core")
        finally:
            module._gh_api_json = original

    def test_dispatch_ok_requires_success_exit_and_ok_marker(self) -> None:
        self.assertTrue(module._dispatch_ok(0, {"status": "ok"}))
        self.assertFalse(module._dispatch_ok(1, {"status": "ok"}))
        self.assertFalse(module._dispatch_ok(0, {"status": "error"}))
        self.assertFalse(module._dispatch_ok(0, None))


if __name__ == "__main__":
    unittest.main()
