#!/usr/bin/env python3
"""GitHub webhook -> role router + review followup tracker (bootstrap).

Supported flows:
- issues: route to role and hand off to OpenClaw bridge
- PR feedback events: create/update review-followup task records, route by PR heuristics,
  post followup linkage comments, and enforce closure gate
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import shlex
import string
import subprocess
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml

ROOT = Path(__file__).resolve().parents[2]
ROUTING_FILE = Path(os.getenv("ROUTING_FILE", ROOT / ".openclaw" / "issue-routing.yaml"))
STATE_DIR = Path(os.getenv("STATE_DIR", ROOT / ".openclaw" / "state"))
STATE_FILE = STATE_DIR / "processed_deliveries.json"
FOLLOWUP_FILE = STATE_DIR / "review_followups.json"

LOG_DIR = Path(os.getenv("DISPATCHER_LOG_DIR", STATE_DIR))
LOG_FILE = Path(os.getenv("DISPATCHER_LOG_FILE", LOG_DIR / "issue-dispatcher.log"))

HOST = os.getenv("DISPATCHER_HOST", "127.0.0.1")
PORT = int(os.getenv("DISPATCHER_PORT", "8787"))
HOOK_TIMEOUT_SEC = int(os.getenv("DISPATCH_HOOK_TIMEOUT_SEC", "45"))

AUTO_EXECUTE_NEW_ISSUES = os.getenv("AUTO_EXECUTE_NEW_ISSUES", "1").lower() not in {"0", "false", "no"}
AUTO_EXECUTE_ONLY_ON_OPENED = os.getenv("AUTO_EXECUTE_ONLY_ON_OPENED", "1").lower() not in {"0", "false", "no"}
FORCE_TRIAGE_LABEL = os.getenv("FORCE_TRIAGE_LABEL", "dispatch:triage").strip().lower()

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")
GH_API = os.getenv("GITHUB_API_URL", "https://api.github.com")

# Hook command template placeholders:
# {role} {repo} {task_kind} {task_number} {task_title} {task_url} {context_json}
# plus shell-escaped variants: *_q
SUPPORTED_HOOK_KEYS = {
    "role",
    "repo",
    "task_kind",
    "task_number",
    "task_title",
    "task_url",
    "context_json",
    # legacy aliases still accepted for backward compatibility
    "issue_number",
    "issue_title",
    "issue_url",
    "role_q",
    "repo_q",
    "task_kind_q",
    "task_number_q",
    "task_title_q",
    "task_url_q",
    "context_json_q",
    "issue_number_q",
    "issue_title_q",
    "issue_url_q",
}
HOOK_CMD = os.getenv(
    "DISPATCH_HOOK_CMD",
    str((Path(__file__).resolve().parent / "dispatch_bridge.sh").resolve())
    + " {role_q} {repo_q} {task_kind_q} {task_number_q} {task_title_q} {task_url_q} {context_json_q}",
)

EVENTS_ALLOWED = {"issues", "pull_request_review", "pull_request_review_comment", "issue_comment"}
ISSUE_ACTIONS_ALLOWED = {"opened", "edited", "labeled", "reopened"}
FEEDBACK_ACTIONS_ALLOWED = {"created", "edited", "submitted"}

REQUIRED_ACTION_CHECKLIST = [
    "Post acknowledgement in the PR thread.",
    "Push fix commit(s) that address each feedback item.",
    "Reply in-thread with addressed commit hash(es).",
]

logger = logging.getLogger("issue-dispatcher")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _load_followups() -> dict[str, Any]:
    if not FOLLOWUP_FILE.exists():
        return {"tasks": {}}
    try:
        raw = json.loads(FOLLOWUP_FILE.read_text())
        tasks = raw.get("tasks", {}) if isinstance(raw, dict) else {}
        return {"tasks": tasks}
    except Exception:
        return {"tasks": {}}


def _save_followups(followups: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    FOLLOWUP_FILE.write_text(json.dumps(followups, indent=2, sort_keys=True))


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




def _known_roles(routing: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    for key in ("default_role", "default_pr_role"):
        value = routing.get(key)
        if isinstance(value, str) and value.strip():
            roles.add(value.strip())
    for rule_set in ("rules", "pr_rules"):
        for rule in routing.get(rule_set, []):
            if isinstance(rule, dict):
                role = rule.get("role")
                if isinstance(role, str) and role.strip():
                    roles.add(role.strip())
    return roles


def _normalize_role(role: str | None, routing: dict[str, Any], *, pr: bool) -> str:
    candidate = (role or "").strip()
    known_roles = _known_roles(routing)

    if candidate and (not known_roles or candidate in known_roles):
        return candidate

    default_key = "default_pr_role" if pr else "default_role"
    fallback = (routing.get(default_key) or "").strip()
    if fallback:
        return fallback

    return "ctrl^core"


def _dispatch_ok(rc: int, marker: dict[str, Any] | None) -> bool:
    return rc == 0 and isinstance(marker, dict) and marker.get("status") == "ok"

def _match_issue_roles(issue: dict[str, Any], routing: dict[str, Any]) -> list[str]:
    labels = {x["name"].lower() for x in issue.get("labels", []) if x.get("name")}
    title = issue.get("title", "")
    body = issue.get("body", "")

    matched_roles: list[str] = []
    for rule in routing.get("rules", []):
        role = rule.get("role")
        if not role:
            continue

        any_labels = [x.lower() for x in rule.get("any_labels", [])]
        title_contains = rule.get("title_contains", [])
        body_contains = rule.get("body_contains", [])

        if any_labels and labels.intersection(any_labels):
            matched_roles.append(role)
            continue
        if title_contains and _contains_any(title, title_contains):
            matched_roles.append(role)
            continue
        if body_contains and _contains_any(body, body_contains):
            matched_roles.append(role)
            continue

    return matched_roles


def _route_issue(issue: dict[str, Any], routing: dict[str, Any]) -> tuple[str, bool, str]:
    """Return (role, should_auto_execute, routing_reason)."""
    default_role = _normalize_role(routing.get("default_role"), routing, pr=False)
    matched_roles = _match_issue_roles(issue, routing)
    unique_roles = sorted(set(matched_roles))

    if not unique_roles:
        return _normalize_role(default_role, routing, pr=False), False, "no routing rule matched"

    if len(unique_roles) > 1:
        return default_role, False, f"ambiguous role matches: {', '.join(unique_roles)}"

    chosen_role = _normalize_role(unique_roles[0], routing, pr=False)
    if chosen_role == default_role:
        return default_role, False, "matched default triage role"

    return chosen_role, True, "single confident role match"


def _gh_api_json(path: str) -> dict[str, Any] | list[Any] | None:
    if not GH_TOKEN:
        return None
    req = request.Request(f"{GH_API}{path}", method="GET")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {GH_TOKEN}")
    try:
        with request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _gh_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any] | None:
    if not GH_TOKEN:
        return None
    req = request.Request(f"{GH_API}/graphql", method="POST")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {GH_TOKEN}")
    req.add_header("Content-Type", "application/json")
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    try:
        with request.urlopen(req, data=body, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload.get("data")
    except Exception:
        return None


def _route_pr_feedback(repo: str, pr: dict[str, Any], routing: dict[str, Any]) -> str:
    labels = {x.get("name", "").lower() for x in pr.get("labels", []) if x.get("name")}
    title = pr.get("title", "")
    body = pr.get("body", "") or ""

    file_paths: list[str] = []
    files_json = _gh_api_json(f"/repos/{repo}/pulls/{pr.get('number')}/files")
    if isinstance(files_json, list):
        file_paths = [x.get("filename", "") for x in files_json if x.get("filename")]

    for rule in routing.get("pr_rules", []):
        any_labels = [x.lower() for x in rule.get("any_labels", [])]
        any_paths = [x.lower() for x in rule.get("any_paths", [])]
        title_contains = [x.lower() for x in rule.get("title_contains", [])]
        body_contains = [x.lower() for x in rule.get("body_contains", [])]

        if any_labels and labels.intersection(any_labels):
            return _normalize_role(rule.get("role"), routing, pr=True)
        if any_paths and any(any(p in fp.lower() for p in any_paths) for fp in file_paths):
            return _normalize_role(rule.get("role"), routing, pr=True)
        if title_contains and _contains_any(title, title_contains):
            return _normalize_role(rule.get("role"), routing, pr=True)
        if body_contains and _contains_any(body, body_contains):
            return _normalize_role(rule.get("role"), routing, pr=True)

    return _normalize_role(routing.get("default_pr_role"), routing, pr=True)


def _fingerprint(payload: dict[str, Any], evt: str) -> str:
    repo = payload.get("repository", {}).get("full_name", "")
    action = payload.get("action", "")
    if evt == "issues":
        issue = payload.get("issue", {})
        updated_at = issue.get("updated_at", "")
        raw = f"{evt}:{repo}:{issue.get('number')}:{action}:{updated_at}"
    else:
        pr = payload.get("pull_request", {}) or payload.get("issue", {})
        pr_number = pr.get("number", "")
        updated_at = (
            payload.get("review", {}).get("submitted_at")
            or payload.get("comment", {}).get("updated_at")
            or payload.get("comment", {}).get("created_at")
            or pr.get("updated_at", "")
        )
        permalink = payload.get("review", {}).get("html_url") or payload.get("comment", {}).get("html_url", "")
        raw = f"{evt}:{repo}:{pr_number}:{action}:{updated_at}:{permalink}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _render_hook(task: dict[str, str]) -> str:
    # Backward-compatible aliases for older hook templates.
    aliases = {
        "issue_number": task.get("task_number", ""),
        "issue_title": task.get("task_title", ""),
        "issue_url": task.get("task_url", ""),
    }
    merged = {**task, **aliases}

    quoted = {f"{k}_q": shlex.quote(v) for k, v in merged.items()}
    fields = {fname for _, fname, _, _ in string.Formatter().parse(HOOK_CMD) if fname}
    unknown = sorted(fields.difference(SUPPORTED_HOOK_KEYS))
    if unknown:
        raise ValueError(f"DISPATCH_HOOK_CMD has unsupported placeholders: {', '.join(unknown)}")
    return HOOK_CMD.format(**merged, **quoted)


def _comment_issue(repo: str, issue_number: int, text: str) -> None:
    if not GH_TOKEN:
        return
    url = f"{GH_API}/repos/{repo}/issues/{issue_number}/comments"
    data = json.dumps({"body": text}).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {GH_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=15):
            pass
    except Exception as exc:
        logger.warning("failed to post comment repo=%s issue=%s err=%s", repo, issue_number, exc)


def _extract_dispatch_marker(stdout: str) -> dict[str, Any] | None:
    marker_prefix = "OPENCLAW_DISPATCH_RESULT "
    for line in reversed(stdout.splitlines()):
        if line.startswith(marker_prefix):
            try:
                return json.loads(line[len(marker_prefix) :])
            except json.JSONDecodeError:
                return None
    return None


def _is_pr_issue_comment(payload: dict[str, Any]) -> bool:
    issue = payload.get("issue", {})
    return bool(issue.get("pull_request"))


def _extract_pr_feedback(payload: dict[str, Any], evt: str) -> dict[str, Any] | None:
    repo = payload.get("repository", {}).get("full_name")
    if not repo:
        return None

    if evt == "pull_request_review":
        pr = payload.get("pull_request", {})
        review = payload.get("review", {})
        if not pr.get("number"):
            return None
        permalink = review.get("html_url")
        body = review.get("body", "")
        source = "review"
    elif evt == "pull_request_review_comment":
        pr = payload.get("pull_request", {})
        comment = payload.get("comment", {})
        if not pr.get("number"):
            return None
        permalink = comment.get("html_url")
        body = comment.get("body", "")
        source = "review_comment"
    elif evt == "issue_comment":
        if not _is_pr_issue_comment(payload):
            return None
        pr = payload.get("issue", {})
        comment = payload.get("comment", {})
        permalink = comment.get("html_url")
        body = comment.get("body", "")
        source = "pr_issue_comment"
    else:
        return None

    return {
        "repo": repo,
        "pr_number": int(pr.get("number")),
        "pr_title": pr.get("title", f"PR #{pr.get('number')}") or f"PR #{pr.get('number')}",
        "pr_url": pr.get("html_url", ""),
        "labels": pr.get("labels", []),
        "body": pr.get("body", "") or "",
        "permalink": permalink,
        "feedback_body": body,
        "source": source,
        "sender": payload.get("sender", {}).get("login", "unknown"),
    }


def _create_or_update_followup(payload: dict[str, Any], evt: str, routing: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    feedback = _extract_pr_feedback(payload, evt)
    if not feedback:
        raise ValueError("payload is not PR feedback")

    key = f"{feedback['repo']}#{feedback['pr_number']}"
    followups = _load_followups()
    existing = followups["tasks"].get(key)

    routed_role = _route_pr_feedback(
        feedback["repo"],
        {
            "number": feedback["pr_number"],
            "title": feedback["pr_title"],
            "body": feedback["body"],
            "labels": feedback.get("labels", []),
        },
        routing,
    )

    if existing:
        task = existing
        is_new = False
    else:
        task = {
            "id": key,
            "created_at": _now_iso(),
        }
        is_new = True

    # Backfill/migrate legacy task records so older schema entries don't crash updates.
    task.setdefault("id", key)
    task.setdefault("repo", feedback["repo"])
    task.setdefault("pr_number", feedback["pr_number"])
    task.setdefault("pr_title", feedback["pr_title"])
    task.setdefault("pr_url", feedback["pr_url"])
    task.setdefault("required_action_checklist", REQUIRED_ACTION_CHECKLIST)
    if not isinstance(task.get("comment_permalinks"), list):
        task["comment_permalinks"] = []
    if not isinstance(task.get("events"), list):
        task["events"] = []

    # Always keep routing fresh + reopen on new feedback.
    task["role"] = _normalize_role(routed_role, routing, pr=True)
    task["status"] = "open"
    task["closed_at"] = None

    permalink = feedback.get("permalink")
    if permalink and permalink not in task["comment_permalinks"]:
        task["comment_permalinks"].append(permalink)

    task["events"].append(
        {
            "event": evt,
            "action": payload.get("action", ""),
            "source": feedback.get("source", ""),
            "sender": feedback.get("sender", ""),
            "at": _now_iso(),
        }
    )
    task["updated_at"] = _now_iso()

    followups["tasks"][key] = task
    _save_followups(followups)
    return task, is_new


def _all_threads_resolved(repo: str, pr_number: int) -> bool | None:
    owner, name = repo.split("/", 1)
    data = _gh_graphql(
        """
        query($owner:String!, $name:String!, $number:Int!) {
          repository(owner:$owner, name:$name) {
            pullRequest(number:$number) {
              reviewThreads(first:100) {
                nodes { isResolved }
              }
            }
          }
        }
        """,
        {"owner": owner, "name": name, "number": pr_number},
    )
    try:
        threads = data["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    except Exception:
        return None
    return all(x.get("isResolved", False) for x in threads)


def _checks_green(repo: str, pr_number: int) -> bool | None:
    # REST endpoint aggregates check suites + statuses
    data = _gh_api_json(f"/repos/{repo}/commits/HEAD/status")
    # Above is not PR-specific if branch unknown; prefer GraphQL mergeable checks when token available.
    owner, name = repo.split("/", 1)
    gql = _gh_graphql(
        """
        query($owner:String!, $name:String!, $number:Int!) {
          repository(owner:$owner, name:$name) {
            pullRequest(number:$number) {
              commits(last:1) {
                nodes {
                  commit {
                    statusCheckRollup {
                      state
                    }
                  }
                }
              }
            }
          }
        }
        """,
        {"owner": owner, "name": name, "number": pr_number},
    )
    try:
        state = (
            gql["repository"]["pullRequest"]["commits"]["nodes"][0]["commit"]["statusCheckRollup"]["state"]
        )
        return state == "SUCCESS"
    except Exception:
        if isinstance(data, dict):
            return data.get("state") == "success"
        return None


def _attempt_close_followup(task: dict[str, Any]) -> tuple[bool, str]:
    threads_ok = _all_threads_resolved(task["repo"], int(task["pr_number"]))
    checks_ok = _checks_green(task["repo"], int(task["pr_number"]))

    if threads_ok is True and checks_ok is True:
        followups = _load_followups()
        key = task["id"]
        current = followups["tasks"].get(key, task)
        current["status"] = "closed"
        current["closed_at"] = _now_iso()
        current["updated_at"] = _now_iso()
        followups["tasks"][key] = current
        _save_followups(followups)
        return True, "all review threads resolved and checks green"

    reasons = []
    if threads_ok is not True:
        reasons.append("review threads still unresolved or unavailable")
    if checks_ok is not True:
        reasons.append("checks not green or unavailable")
    return False, "; ".join(reasons)


def _dispatch_task(task: dict[str, Any]) -> tuple[int, str, str, dict[str, Any] | None]:
    context = {
        "task_id": task["id"],
        "repo": task["repo"],
        "pr_number": task["pr_number"],
        "pr_url": task["pr_url"],
        "comment_permalinks": task.get("comment_permalinks", []),
        "required_action_checklist": task.get("required_action_checklist", []),
        "closure_gate": "Close only when all review threads are resolved/answered and checks are green.",
    }
    cmd = _render_hook(
        {
            "role": task["role"],
            "repo": task["repo"],
            "task_kind": "pr-followup",
            "task_number": str(task["pr_number"]),
            "task_title": f"PR followup: {task['pr_title']}",
            "task_url": task.get("pr_url", ""),
            "context_json": json.dumps(context, separators=(",", ":")),
        }
    )
    result = subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True,
        timeout=HOOK_TIMEOUT_SEC,
    )
    marker = _extract_dispatch_marker(result.stdout)
    return result.returncode, result.stdout, result.stderr, marker


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

        if evt == "issues" and action not in ISSUE_ACTIONS_ALLOWED:
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": f"action {action}"})
            return
        if evt != "issues" and action not in FEEDBACK_ACTIONS_ALLOWED:
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": f"action {action}"})
            return

        if evt == "issue_comment" and not _is_pr_issue_comment(payload):
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": "issue_comment on non-PR issue"})
            return

        state = _load_state()
        if delivery and state["deliveries"].get(delivery):
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": "duplicate delivery"})
            return

        fp = _fingerprint(payload, evt)
        if state["fingerprints"].get(fp):
            self._respond(HTTPStatus.OK, {"ok": True, "ignored": "duplicate payload"})
            return

        routing = _load_routing()

        if evt == "issues":
            issue = payload.get("issue")
            repo = payload.get("repository", {}).get("full_name")
            if not issue or not repo:
                self._respond(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing issue/repo"})
                return

            role, confident, route_reason = _route_issue(issue, routing)
            labels = {x.get("name", "").lower() for x in issue.get("labels", []) if x.get("name")}
            if FORCE_TRIAGE_LABEL and FORCE_TRIAGE_LABEL in labels:
                role = routing.get("default_role", "ctrl^core")
                confident = False
                route_reason = f"forced triage via label `{FORCE_TRIAGE_LABEL}`"

            should_auto_execute = confident
            if AUTO_EXECUTE_ONLY_ON_OPENED and action != "opened":
                should_auto_execute = False
                if route_reason == "single confident role match":
                    route_reason = "confident match but auto-exec restricted to action=opened"
            if not AUTO_EXECUTE_NEW_ISSUES:
                should_auto_execute = False
                route_reason = "auto-execution disabled by AUTO_EXECUTE_NEW_ISSUES"

            effective_role = role if should_auto_execute else _normalize_role(routing.get("default_role"), routing, pr=False)
            marker = None
            result = None
            cmd = ""

            if action == "opened" or should_auto_execute:
                task = {
                    "role": effective_role,
                    "repo": repo,
                    "task_kind": "issue",
                    "task_number": str(issue["number"]),
                    "task_title": issue["title"].replace("\n", " "),
                    "task_url": issue["html_url"],
                    "context_json": json.dumps(
                        {
                            "task_id": f"{repo}#{issue['number']}",
                            "route_reason": route_reason,
                            "route_confident": confident,
                            "auto_executed": should_auto_execute,
                        },
                        separators=(",", ":"),
                    ),
                }
                cmd = _render_hook(task)
                result = subprocess.run(
                    cmd,
                    shell=True,
                    text=True,
                    capture_output=True,
                    timeout=HOOK_TIMEOUT_SEC,
                )
                marker = _extract_dispatch_marker(result.stdout)

            marker_line = "- downstream: `not-triggered`"
            if result and marker:
                marker_line = (
                    "- downstream: "
                    f"`{marker.get('status', 'unknown')}` "
                    f"run=`{marker.get('run_id', '')}` "
                    f"target=`{marker.get('target_kind', '')}:{marker.get('target', '')}`"
                )
            elif result:
                marker_line = "- downstream: `missing-marker`"

            status_word = "start" if action == "opened" else ("update" if action in {"edited", "labeled", "reopened"} else "done")
            dispatch_exit = result.returncode if result else "skipped"
            summary = (
                f"🤖 Issue router {status_word}.\n"
                f"- AI Employee: **{effective_role}**\n"
                f"- action: `{action}`\n"
                f"- routing: `{route_reason}`\n"
                f"- auto-executed: `{str(should_auto_execute).lower()}`\n"
                f"- dispatcher exit: `{dispatch_exit}`\n"
                f"{marker_line}\n"
            )
            _comment_issue(repo, issue["number"], summary)

            if delivery:
                state["deliveries"][delivery] = True
            state["fingerprints"][fp] = True
            _save_state(state)

            payload_out = {
                "ok": True,
                "repo": repo,
                "issue": issue["number"],
                "role": effective_role,
                "routing_reason": route_reason,
                "auto_executed": should_auto_execute,
                "command": cmd,
                "exit": result.returncode if result else None,
                "stdout": (result.stdout[-1000:] if result else ""),
                "stderr": (result.stderr[-1000:] if result else ""),
            }
            self._respond(HTTPStatus.OK, payload_out)
            return

        # PR feedback flow
        try:
            task, is_new = _create_or_update_followup(payload, evt, routing)
        except ValueError as exc:
            self._respond(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return

        rc, out, err, marker = _dispatch_task(task)
        if not _dispatch_ok(rc, marker):
            self._respond(
                HTTPStatus.BAD_GATEWAY,
                {
                    "ok": False,
                    "event": evt,
                    "action": action,
                    "followup": task,
                    "error": "dispatch failed; event left unacknowledged for safe retry",
                    "dispatch_exit": rc,
                    "dispatch_marker": marker,
                    "stdout": out[-600:],
                    "stderr": err[-600:],
                },
            )
            return

        closed, close_reason = _attempt_close_followup(task)

        progress = "done" if closed else ("start" if is_new else "update")
        record_message = (
            f"🤖 Review followup {progress}: `{task['id']}`\n"
            f"- AI Employee: **{task['role']}**\n"
            f"- comment permalinks tracked: `{len(task.get('comment_permalinks', []))}`\n"
            "- required action checklist:\n"
            "  - [ ] post acknowledgement in PR thread\n"
            "  - [ ] push fix commit(s)\n"
            "  - [ ] reply with addressed commit hash(es)\n"
            f"- closure gate: {'✅ closed' if closed else f'⏳ open ({close_reason})'}\n"
            f"- dispatcher exit: `{rc}`\n"
        )
        _comment_issue(task["repo"], int(task["pr_number"]), record_message)

        if delivery:
            state["deliveries"][delivery] = True
        state["fingerprints"][fp] = True
        _save_state(state)

        self._respond(
            HTTPStatus.OK,
            {
                "ok": True,
                "event": evt,
                "action": action,
                "followup": task,
                "dispatch_exit": rc,
                "dispatch_marker": marker,
                "closure": {"closed": closed, "reason": close_reason},
                "stdout": out[-600:],
                "stderr": err[-600:],
            },
        )


def main() -> None:
    _setup_logging()
    logger.info("Issue dispatcher listening on http://%s:%s/github/webhook", HOST, PORT)
    logger.info("Health endpoint: http://%s:%s/healthz", HOST, PORT)
    logger.info("Routing file: %s", ROUTING_FILE)
    logger.info("Followup file: %s", FOLLOWUP_FILE)
    logger.info("Log file: %s", LOG_FILE)
    if not WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET is empty; signature checks will fail.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
