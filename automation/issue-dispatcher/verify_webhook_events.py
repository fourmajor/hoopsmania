#!/usr/bin/env python3
"""Verify (and optionally repair) GitHub webhook event subscriptions.

AI Employee: pipewire
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib import error, request

REQUIRED_EVENTS = {
    "issues",
    "issue_comment",
    "pull_request_review",
    "pull_request_review_comment",
}


def _api(path: str, token: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    url = f"https://api.github.com{path}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--hook-id", type=int, help="Webhook ID to check/update")
    parser.add_argument("--url-contains", help="Find hook by URL substring")
    parser.add_argument("--apply", action="store_true", help="Patch webhook to include required events")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    owner, repo = args.repo.split("/", 1)
    hooks = _api(f"/repos/{owner}/{repo}/hooks", token)
    if not isinstance(hooks, list):
        print("error: unexpected API response", file=sys.stderr)
        return 2

    selected = None
    if args.hook_id:
        for hook in hooks:
            if int(hook.get("id", 0)) == args.hook_id:
                selected = hook
                break
    elif args.url_contains:
        for hook in hooks:
            if args.url_contains in (hook.get("config", {}) or {}).get("url", ""):
                selected = hook
                break
    elif len(hooks) == 1:
        selected = hooks[0]

    if not selected:
        print("error: could not uniquely select webhook; pass --hook-id or --url-contains", file=sys.stderr)
        return 2

    hook_id = int(selected["id"])
    current_events = set(selected.get("events", []))
    missing = sorted(REQUIRED_EVENTS - current_events)

    print(f"hook_id={hook_id}")
    print(f"url={(selected.get('config', {}) or {}).get('url', '')}")
    print(f"current_events={sorted(current_events)}")

    if not missing:
        print("status=ok all required events present")
        return 0

    print(f"status=missing required_events={missing}")
    if not args.apply:
        return 1

    patched_events = sorted(current_events | REQUIRED_EVENTS)
    try:
        _api(
            f"/repos/{owner}/{repo}/hooks/{hook_id}",
            token,
            method="PATCH",
            payload={"events": patched_events, "active": True},
        )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        print(f"error: patch failed status={exc.code} body={body}", file=sys.stderr)
        return 2

    print(f"status=patched events={patched_events}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
