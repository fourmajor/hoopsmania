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
