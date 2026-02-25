#!/usr/bin/env python3
"""GitHub Issue -> role router (webhook-driven bootstrap).

Receives GitHub issue webhooks, classifies each issue using
.openclaw/issue-routing.yaml, and emits a dispatch event to a configurable
command hook.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import shlex
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

LOG_DIR = Path(os.getenv("DISPATCHER_LOG_DIR", STATE_DIR))
LOG_FILE = Path(os.getenv("DISPATCHER_LOG_FILE", LOG_DIR / "issue-dispatcher.log"))

HOST = os.getenv("DISPATCHER_HOST", "127.0.0.1")
PORT = int(os.getenv("DISPATCHER_PORT", "8787"))
HOOK_TIMEOUT_SEC = int(os.getenv("DISPATCH_HOOK_TIMEOUT_SEC", "45"))

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")
GH_API = os.getenv("GITHUB_API_URL", "https://api.github.com")

# Hook command template placeholders:
# {role} {repo} {issue_number} {issue_title} {issue_url}
# plus shell-escaped variants: *_q
HOOK_CMD = os.getenv(
    "DISPATCH_HOOK_CMD",
    str((Path(__file__).resolve().parent / "dispatch_bridge.sh").resolve())
    + " {role_q} {repo_q} {issue_number} {issue_title_q} {issue_url_q}",
)

EVENTS_ALLOWED = {"issues"}
ACTIONS_ALLOWED = {"opened", "edited", "labeled", "reopened"}


logger = logging.getLogger("issue-dispatcher")


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"deliveries": {}, "fingerprints": {}}
    try:
        raw = json.loads(STATE_FILE.read_text())
        # Backward-compat: prior format was {delivery_id: true}
        if "deliveries" in raw or "fingerprints" in raw:
            return {
                "deliveries": raw.get("deliveries", {}),
                "fingerprints": raw.get("fingerprints", {}),
            }
        return {"deliveries": raw, "fingerprints": {}}
    except Exception:
        return {"deliveries": {}, "fingerprints": {}}


def _save_state(state: dict[str, Any]) -> None:
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


def _fingerprint(payload: dict[str, Any]) -> str:
    issue = payload.get("issue", {})
    repo = payload.get("repository", {}).get("full_name", "")
    action = payload.get("action", "")
    updated_at = issue.get("updated_at", "")
    raw = f"{repo}:{issue.get('number')}:{action}:{updated_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _render_hook(role: str, payload: dict[str, Any]) -> str:
    issue = payload["issue"]
    repo = payload["repository"]["full_name"]

    values = {
        "role": role,
        "repo": repo,
        "issue_number": str(issue["number"]),
        "issue_title": issue["title"].replace("\n", " "),
        "issue_url": issue["html_url"],
    }
    quoted = {f"{k}_q": shlex.quote(v) for k, v in values.items() if k != "issue_number"}
    return HOOK_CMD.format(**values, **quoted)


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
    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("http %s - %s", self.address_string(), fmt % args)

    def _respond(self, code: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._respond(HTTPStatus.OK, {"ok": True})
            return
        self._respond(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

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
        if delivery and state["deliveries"].get(delivery):
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": "duplicate delivery"})
            return

        fp = _fingerprint(payload)
        if state["fingerprints"].get(fp):
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": "duplicate payload"})
            return

        issue = payload.get("issue")
        repo = payload.get("repository", {}).get("full_name")
        if not issue or not repo:
            self._respond(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing issue/repo"})
            return

        routing = _load_routing()
        role = _route_issue(issue, routing)
        cmd = _render_hook(role, payload)

        logger.info("dispatch start repo=%s issue=%s role=%s", repo, issue["number"], role)
        result = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=HOOK_TIMEOUT_SEC,
        )

        summary = (
            f"🤖 Issue router assigned this to **{role}**.\n"
            f"- action: `{action}`\n"
            f"- dispatcher exit: `{result.returncode}`\n"
        )
        _comment_issue(repo, issue["number"], summary)

        if delivery:
            state["deliveries"][delivery] = True
        state["fingerprints"][fp] = True
        _save_state(state)

        logger.info(
            "dispatch done repo=%s issue=%s role=%s exit=%s",
            repo,
            issue["number"],
            role,
            result.returncode,
        )

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
    _setup_logging()
    logger.info("Issue dispatcher listening on http://%s:%s/github/webhook", HOST, PORT)
    logger.info("Health endpoint: http://%s:%s/healthz", HOST, PORT)
    logger.info("Routing file: %s", ROUTING_FILE)
    logger.info("Log file: %s", LOG_FILE)
    if not WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET is empty; signature checks will fail.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
