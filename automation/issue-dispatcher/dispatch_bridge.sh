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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="${STATE_DIR:-$REPO_ROOT/.openclaw/state}"
mkdir -p "$STATE_DIR"

BRIDGE_LOG_FILE="${BRIDGE_LOG_FILE:-$STATE_DIR/dispatch-bridge.log}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$HOME/.npm-global/bin/openclaw}"
OPENCLAW_FALLBACK_AGENT="${OPENCLAW_FALLBACK_AGENT:-main}"

log() {
  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*" | tee -a "$BRIDGE_LOG_FILE" >&2
}

role_key="$(echo "$ROLE" | tr '[:lower:]-' '[:upper:]_')"
session_var="OPENCLAW_SESSION_${role_key}"
agent_var="OPENCLAW_AGENT_${role_key}"
session_id="${!session_var:-}"
agent_id="${!agent_var:-}"

message=$(cat <<EOF
Hoops Mania issue dispatch handoff.
Role: $ROLE
Repo: $REPO
Issue: #$ISSUE_NUMBER
Title: $ISSUE_TITLE
URL: $ISSUE_URL

Please pick this up according to your role ownership in EMPLOYEES.md.
EOF
)

if [[ ! -x "$OPENCLAW_BIN" ]]; then
  log "[bridge] openclaw binary not found at $OPENCLAW_BIN"
  exit 127
fi

if [[ -n "$session_id" ]]; then
  log "[bridge] steering to persistent session via $session_var=$session_id"
  exec "$OPENCLAW_BIN" agent --session-id "$session_id" --message "$message"
fi

if [[ -n "$agent_id" ]]; then
  log "[bridge] no session mapping; falling back to role agent via $agent_var=$agent_id"
  exec "$OPENCLAW_BIN" agent --agent "$agent_id" --message "$message"
fi

log "[bridge] no role mapping found; falling back to OPENCLAW_FALLBACK_AGENT=$OPENCLAW_FALLBACK_AGENT"
exec "$OPENCLAW_BIN" agent --agent "$OPENCLAW_FALLBACK_AGENT" --message "$message"
