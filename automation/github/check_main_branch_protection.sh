#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-fourmajor}"
REPO="${2:-hoopsmania}"
BRANCH="${3:-main}"

json="$(gh api "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection")"

python3 - <<'PY' "$json"
import json
import sys


def is_enabled(value):
    """Accept GitHub API variants for feature toggles.

    Some protection fields come back as an object, e.g.
    {"enabled": true}. Older/alternate shapes may be a bare boolean.
    """
    if isinstance(value, dict):
        return value.get("enabled") is True
    return value is True


if __name__ == "__main__":
    # Lightweight self-test for parsing robustness.
    assert is_enabled({"enabled": True}) is True
    assert is_enabled({"enabled": False}) is False
    assert is_enabled(True) is True
    assert is_enabled(False) is False

    obj = json.loads(sys.argv[1])

    checks = []

    reviews = obj.get("required_pull_request_reviews") or {}
    status_checks = obj.get("required_status_checks") or {}

    checks.append((reviews.get("required_approving_review_count", -1) == 0, "required_approving_review_count == 0"))
    checks.append((reviews.get("dismiss_stale_reviews") is True, "dismiss_stale_reviews"))
    checks.append((status_checks.get("strict") is True, "required_status_checks.strict"))
    checks.append((len(status_checks.get("contexts") or []) > 0, "required_status_checks contexts set"))

    conv = obj.get("required_conversation_resolution")
    checks.append((is_enabled(conv), "required_conversation_resolution.enabled"))

    failed = False
    for ok, label in checks:
        print(f"{label}: {'OK' if ok else 'FAIL'}")
        if not ok:
            failed = True

    if failed:
        if not is_enabled(conv):
            print(f"debug: required_conversation_resolution payload={conv!r}")
        sys.exit(1)
PY
