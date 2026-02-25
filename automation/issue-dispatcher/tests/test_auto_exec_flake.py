from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_dispatcher_module():
    root = Path(__file__).resolve().parents[1]
    mod_path = root / "dispatcher.py"
    spec = importlib.util.spec_from_file_location("issue_dispatcher", mod_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _routing_config(default_role: str = "ctrl^core") -> dict:
    return {
        "default_role": default_role,
        "rules": [
            {"name": "devops-title", "title_contains": ["ci", "infra", "deploy"], "role": "pipewire"},
            {"name": "frontend-title", "title_contains": ["ui", "frontend"], "role": "neonflux"},
            {"name": "docs-title", "title_contains": ["docs", "readme"], "role": "docdrip"},
        ],
    }


def _issue(title: str, labels: list[str] | None = None, body: str = "") -> dict:
    return {
        "number": 74,
        "title": title,
        "body": body,
        "html_url": "https://github.com/fourmajor/hoopsmania/issues/74",
        "labels": [{"name": x} for x in (labels or [])],
    }


def test_route_issue_confident_match_is_stable_across_many_runs():
    dispatcher = _load_dispatcher_module()
    routing = _routing_config()
    issue = _issue("Test: CI pipeline flake validation for dispatcher auto-exec")

    results = [dispatcher._route_issue(issue, routing) for _ in range(200)]

    assert len(set(results)) == 1
    role, confident, reason = results[0]
    assert role == "pipewire"
    assert confident is True
    assert reason == "single confident role match"


def test_route_issue_ambiguous_match_falls_back_to_triage_stably():
    dispatcher = _load_dispatcher_module()
    routing = _routing_config(default_role="ctrl^core")
    issue = _issue("CI + frontend orchestration")

    results = [dispatcher._route_issue(issue, routing) for _ in range(200)]

    assert len(set(results)) == 1
    role, confident, reason = results[0]
    assert role == "ctrl^core"
    assert confident is False
    assert reason.startswith("ambiguous role matches:")


def test_render_hook_supports_legacy_issue_placeholders_for_bridge_compat():
    dispatcher = _load_dispatcher_module()
    original = dispatcher.HOOK_CMD
    dispatcher.HOOK_CMD = "echo role={role_q} issue={issue_number_q} title={issue_title_q}"
    try:
        cmd = dispatcher._render_hook(
            {
                "role": "pipewire",
                "repo": "fourmajor/hoopsmania",
                "task_kind": "issue",
                "task_number": "74",
                "task_title": "CI flake validation",
                "task_url": "https://github.com/fourmajor/hoopsmania/issues/74",
                "context_json": "{}",
            }
        )
    finally:
        dispatcher.HOOK_CMD = original

    assert "issue=74" in cmd
    assert "role=pipewire" in cmd
