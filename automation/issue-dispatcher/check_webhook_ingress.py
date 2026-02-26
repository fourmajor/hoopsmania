#!/usr/bin/env python3
"""Webhook ingress monitor for GitHub deliveries.

Detects recent non-200 webhook deliveries and optionally posts an alert comment.
AI Employee: pipewire
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from typing import Any


def gh_api(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    cmd = ["gh", "api", path]
    if method != "GET":
        cmd.extend(["--method", method])
    if payload is not None:
        cmd.extend(["--input", "-"])
        proc = subprocess.run(cmd, input=json.dumps(payload).encode("utf-8"), capture_output=True)
    else:
        proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore") or proc.stdout.decode("utf-8", errors="ignore"))
    out = proc.stdout.decode("utf-8", errors="ignore").strip()
    if not out:
        return {}
    return json.loads(out)


def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--hook-id", required=True, type=int)
    ap.add_argument("--lookback-minutes", type=int, default=20)
    ap.add_argument("--alert-issue", type=int, help="Post alert comment to this issue number")
    args = ap.parse_args()

    owner, repo = args.repo.split("/", 1)
    deliveries = gh_api(f"repos/{owner}/{repo}/hooks/{args.hook_id}/deliveries?per_page=100")
    if not isinstance(deliveries, list):
        print("unexpected deliveries response", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(minutes=args.lookback_minutes)

    recent = [d for d in deliveries if parse_ts(d.get("delivered_at", "1970-01-01T00:00:00Z")) >= cutoff]
    failed = [
        {
            "id": d.get("id"),
            "event": d.get("event"),
            "action": d.get("action"),
            "status_code": d.get("status_code"),
            "delivered_at": d.get("delivered_at"),
            "redelivery": d.get("redelivery"),
        }
        for d in recent
        if int(d.get("status_code") or 0) >= 500
    ]

    summary = {
        "repo": args.repo,
        "hook_id": args.hook_id,
        "lookback_minutes": args.lookback_minutes,
        "checked_recent": len(recent),
        "failed_5xx": failed,
    }
    print(json.dumps(summary, indent=2))

    if failed and args.alert_issue:
        run_url = os.getenv("GITHUB_SERVER_URL", "https://github.com") + "/" + os.getenv("GITHUB_REPOSITORY", args.repo) + "/actions/runs/" + os.getenv("GITHUB_RUN_ID", "")
        body = (
            "AI Employee: pipewire\n\n"
            "Webhook ingress alert: detected 5xx deliveries in monitoring window.\n\n"
            f"- repo: `{args.repo}`\n"
            f"- hook id: `{args.hook_id}`\n"
            f"- lookback: `{args.lookback_minutes}m`\n"
            f"- failures: `{len(failed)}`\n"
            f"- workflow run: {run_url}\n\n"
            "Recent failed deliveries:\n"
            + "\n".join(
                f"- id `{x['id']}` `{x['event']}/{x['action']}` status `{x['status_code']}` at `{x['delivered_at']}` redelivery=`{x['redelivery']}`"
                for x in failed[:20]
            )
        )
        gh_api(
            f"repos/{owner}/{repo}/issues/{args.alert_issue}/comments",
            method="POST",
            payload={"body": body},
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
