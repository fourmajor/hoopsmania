#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-fourmajor}"
REPO="${2:-hoopsmania}"
BRANCH="${3:-main}"

json="$(gh api "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection")"

python3 - <<'PY' "$json"
import json
import sys

obj = json.loads(sys.argv[1])

checks = []

reviews = obj.get("required_pull_request_reviews") or {}
status_checks = obj.get("required_status_checks") or {}

checks.append((reviews.get("required_approving_review_count", 0) >= 1, "required_approving_review_count >= 1"))
checks.append((reviews.get("dismiss_stale_reviews") is True, "dismiss_stale_reviews"))
checks.append((status_checks.get("strict") is True, "required_status_checks.strict"))
checks.append((len(status_checks.get("contexts") or []) > 0, "required_status_checks contexts set"))

failed = False
for ok, label in checks:
    print(f"{label}: {'OK' if ok else 'FAIL'}")
    if not ok:
        failed = True

if failed:
    sys.exit(1)
PY
