#!/usr/bin/env bash
set -euo pipefail

# Idempotently create/update canonical labels.
# Usage: automation/github/sync_labels.sh [owner/repo]

REPO="${1:-}"
if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

upsert_label() {
  local name="$1"
  local color="$2"
  local desc="$3"

  if gh label list --repo "$REPO" --search "$name" --json name --jq ".[] | select(.name==\"$name\") | .name" | grep -qx "$name"; then
    gh label edit "$name" --repo "$REPO" --color "$color" --description "$desc" >/dev/null
    echo "updated: $name"
  else
    gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" >/dev/null
    echo "created: $name"
  fi
}

# Type labels
upsert_label "type:frontend" "1f6feb" "Changes primarily in frontend/UI"
upsert_label "type:backend" "0e8a16" "Changes primarily in backend/service logic"
upsert_label "type:documentation" "5319e7" "Documentation-focused changes"
upsert_label "type:ci-cd" "c5def5" "CI/CD and workflow changes"

# Area labels
upsert_label "area:frontend" "0052cc" "Touches web frontend area"
upsert_label "area:backend" "006b75" "Touches backend area"
upsert_label "area:automation" "1d76db" "Touches automation/tooling area"
upsert_label "area:docs" "fbca04" "Touches docs area"

# Priority/status labels
upsert_label "priority:p0" "b60205" "Urgent/highest priority"
upsert_label "priority:p1" "d93f0b" "High priority"
upsert_label "priority:p2" "fbca04" "Normal priority"
upsert_label "status:needs-triage" "ededed" "Needs initial triage"
upsert_label "status:blocked" "000000" "Blocked pending dependency/decision"
upsert_label "status:ready-for-review" "0e8a16" "Ready for maintainer review"

echo "Label sync complete for $REPO"
