#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-}"
REPO="${2:-}"
ISSUE_NUMBER="${3:-}"
ISSUE_TITLE="${4:-}"
ISSUE_URL="${5:-}"

if [[ -z "$ROLE" || -z "$REPO" || -z "$ISSUE_NUMBER" ]]; then
  echo "usage: dispatch_bridge.sh <role> <repo> <issue_number> <issue_title> <issue_url>" >&2
  exit 2
fi

# Bootstrap behavior: log dispatch event.
# Replace this with your preferred OpenClaw handoff implementation.
echo "[bridge] role=$ROLE repo=$REPO issue=$ISSUE_NUMBER title=$ISSUE_TITLE url=$ISSUE_URL"
