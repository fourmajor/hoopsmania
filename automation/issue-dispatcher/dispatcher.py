#!/usr/bin/env python3
"""GitHub Issue -> role router (webhook-driven bootstrap).

This service receives GitHub issue webhooks, classifies each issue using
.openclaw/issue-routing.yaml, and emits a dispatch event to a configurable
command hook.

Why a command hook?
- Keeps this service decoupled from OpenClaw internals.
- Lets you wire in the exact local handoff command you want.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import request

import yaml

ROOT = Path(__file__).resolve().parents[2]
ROUTING_FILE = Path(os.getenv("ROUTING_FILE", ROOT / ".openclaw" / "issue-routing.yaml"))
STATE_DIR = Path(os.getenv("STATE_DIR", ROOT / ".openclaw" / "state"))
STATE_FILE = STATE_DIR / "processed_deliveries.json"

HOST = os.getenv("DISPATCHER_HOST", "127.0.0.1")
PORT = int(os.getenv("DISPATCHER_PORT", "8787"))

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")
GH_API = os.getenv("GITHUB_API_URL", "https://api.github.com")

# Hook command template. Must include placeholders:
#   {role} {repo} {issue_number} {issue_title} {issue_url}
HOOK_CMD = os.getenv(
    "DISPATCH_HOOK_CMD",
    "echo '[dispatch] role={role} repo={repo} issue=#{issue_number} title={issue_title}'",
)

EVENTS_ALLOWED = {"issues"}
ACTIONS_ALLOWED = {"opened", "edited", "labeled", "reopened"}


def _load_state() -> dict[str, bool]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save_state(state: dict[str, bool]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def _verify_signature(body: bytes, signature_header: str) -> bool:
    if not WEBHOOK_SECRET:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _load_routing() -> dict[str, Any]:
    if not ROUTING_FILE.exists():
        raise FileNotFoundError(f"Routing file missing: {ROUTING_FILE}")
    return yaml.safe_load(ROUTING_FILE.read_text()) or {}


def _contains_any(haystack: str, needles: list[str]) -> bool:
    h = haystack.lower()
    return any(n.lower() in h for n in needles)


def _route_issue(issue: dict[str, Any], routing: dict[str, Any]) -> str:
    labels = {x["name"].lower() for x in issue.get("labels", []) if x.get("name")}
    title = issue.get("title", "")
    body = issue.get("body", "")

    for rule in routing.get("rules", []):
        any_labels = [x.lower() for x in rule.get("any_labels", [])]
        title_contains = rule.get("title_contains", [])
        body_contains = rule.get("body_contains", [])

        if any_labels and labels.intersection(any_labels):
            return rule["role"]
        if title_contains and _contains_any(title, title_contains):
            return rule["role"]
        if body_contains and _contains_any(body, body_contains):
            return rule["role"]

    return routing.get("default_role", "cto-triage")


def _render_hook(role: str, payload: dict[str, Any]) -> str:
    issue = payload["issue"]
    repo = payload["repository"]["full_name"]
    return HOOK_CMD.format(
        role=role,
        repo=repo,
        issue_number=issue["number"],
        issue_title=issue["title"].replace("\n", " "),
        issue_url=issue["html_url"],
    )


def _comment_issue(repo: str, issue_number: int, text: str) -> None:
    if not GH_TOKEN:
        return
    url = f"{GH_API}/repos/{repo}/issues/{issue_number}/comments"
    data = json.dumps({"body": text}).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {GH_TOKEN}")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=10):
        pass


class Handler(BaseHTTPRequestHandler):
    def _respond(self, code: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/github/webhook":
            self._respond(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return

        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        sig = self.headers.get("X-Hub-Signature-256", "")
        evt = self.headers.get("X-GitHub-Event", "")
        delivery = self.headers.get("X-GitHub-Delivery", "")

        if evt not in EVENTS_ALLOWED:
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": f"event {evt}"})
            return

        if not _verify_signature(body, sig):
            self._respond(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "bad signature"})
            return

        payload = json.loads(body.decode("utf-8"))
        action = payload.get("action")
        if action not in ACTIONS_ALLOWED:
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": f"action {action}"})
            return

        state = _load_state()
        if delivery and state.get(delivery):
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": "duplicate delivery"})
            return

        issue = payload.get("issue")
        repo = payload.get("repository", {}).get("full_name")
        if not issue or not repo:
            self._respond(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing issue/repo"})
            return

        routing = _load_routing()
        role = _route_issue(issue, routing)
        cmd = _render_hook(role, payload)

        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)

        summary = (
            f"🤖 Issue router assigned this to **{role}**.\n"
            f"- action: `{action}`\n"
            f"- dispatcher exit: `{result.returncode}`\n"
        )
        _comment_issue(repo, issue["number"], summary)

        if delivery:
            state[delivery] = True
            _save_state(state)

        self._respond(
            HTTPStatus.OK,
            {
                "ok": True,
                "repo": repo,
                "issue": issue["number"],
                "role": role,
                "command": cmd,
                "exit": result.returncode,
                "stdout": result.stdout[-1000:],
                "stderr": result.stderr[-1000:],
            },
        )


def main() -> None:
    print(f"Issue dispatcher listening on http://{HOST}:{PORT}/github/webhook")
    print(f"Routing file: {ROUTING_FILE}")
    if not WEBHOOK_SECRET:
        print("WARNING: GITHUB_WEBHOOK_SECRET is empty; signature checks will fail.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
