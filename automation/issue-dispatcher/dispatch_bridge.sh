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

# launchd often has a minimal PATH; ensure node/openclaw runtime paths are available.
export PATH="${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}:/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin"

log() {
  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*" | tee -a "$BRIDGE_LOG_FILE" >&2
}

emit_marker() {
  local status="$1"
  local target_kind="$2"
  local target_value="$3"
  local run_id="$4"
  local session_id="$5"

  local marker
  marker=$(python3 - "$status" "$target_kind" "$target_value" "$run_id" "$session_id" "$ROLE" "$REPO" "$ISSUE_NUMBER" <<'PY'
import json, sys

payload = {
    "status": sys.argv[1],
    "target_kind": sys.argv[2],
    "target": sys.argv[3],
    "run_id": sys.argv[4],
    "session_id": sys.argv[5],
    "role": sys.argv[6],
    "repo": sys.argv[7],
    "issue_number": sys.argv[8],
}
print("OPENCLAW_DISPATCH_RESULT " + json.dumps(payload, separators=(",", ":")))
PY
)

  printf '%s\n' "$marker"
  log "[bridge] $marker"
}

if [[ ! -x "$OPENCLAW_BIN" ]]; then
  log "[bridge] openclaw binary not found at $OPENCLAW_BIN"
  emit_marker "error" "binary" "$OPENCLAW_BIN" "" ""
  exit 127
fi

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

run_target_kind="agent"
run_target="$OPENCLAW_FALLBACK_AGENT"
run_args=(--agent "$OPENCLAW_FALLBACK_AGENT")

if [[ -n "$session_id" ]]; then
  run_target_kind="session"
  run_target="$session_id"
  run_args=(--session-id "$session_id")
  log "[bridge] steering to persistent session via $session_var=$session_id"
elif [[ -n "$agent_id" ]]; then
  run_target_kind="agent"
  run_target="$agent_id"
  run_args=(--agent "$agent_id")
  log "[bridge] no session mapping; falling back to role agent via $agent_var=$agent_id"
else
  log "[bridge] no role mapping found; falling back to OPENCLAW_FALLBACK_AGENT=$OPENCLAW_FALLBACK_AGENT"
fi

out_file="$(mktemp)"
err_file="$(mktemp)"
cleanup() {
  rm -f "$out_file" "$err_file"
}
trap cleanup EXIT

set +e
"$OPENCLAW_BIN" agent "${run_args[@]}" --message "$message" --json >"$out_file" 2>"$err_file"
rc=$?
set -e

if [[ -s "$err_file" ]]; then
  while IFS= read -r line; do
    log "[bridge][stderr] $line"
  done <"$err_file"
fi

if [[ $rc -ne 0 ]]; then
  log "[bridge] openclaw handoff failed rc=$rc target_kind=$run_target_kind target=$run_target"
  emit_marker "error" "$run_target_kind" "$run_target" "" "$session_id"
  exit "$rc"
fi

run_id=""
resolved_session_id="$session_id"
parse_output=$(python3 - "$out_file" <<'PY'
import json, pathlib, sys

raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
obj = json.loads(raw)
run_id = obj.get("runId", "")
session_id = (
    obj.get("result", {})
      .get("meta", {})
      .get("agentMeta", {})
      .get("sessionId", "")
)
print(run_id)
print(session_id)
PY
) || {
  log "[bridge] failed to parse openclaw json output"
  emit_marker "error" "$run_target_kind" "$run_target" "" "$session_id"
  exit 1
}

run_id="$(printf '%s\n' "$parse_output" | sed -n '1p')"
parsed_session_id="$(printf '%s\n' "$parse_output" | sed -n '2p')"
if [[ -n "$parsed_session_id" ]]; then
  resolved_session_id="$parsed_session_id"
fi

if [[ -z "$run_id" ]]; then
  log "[bridge] openclaw response missing runId"
  emit_marker "error" "$run_target_kind" "$run_target" "" "$resolved_session_id"
  exit 1
fi

log "[bridge] openclaw handoff ok run_id=$run_id target_kind=$run_target_kind target=$run_target session_id=$resolved_session_id"
emit_marker "ok" "$run_target_kind" "$run_target" "$run_id" "$resolved_session_id"
