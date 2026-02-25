#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${DISPATCHER_ENV_FILE:-$SCRIPT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${GITHUB_WEBHOOK_SECRET:?GITHUB_WEBHOOK_SECRET must be set (or present in .env)}"

HOST="${DISPATCHER_HOST:-127.0.0.1}"
PORT="${DISPATCHER_PORT:-8787}"

sign_file() {
  local file="$1"
  python3 - <<PY
import hmac, hashlib
secret = ${GITHUB_WEBHOOK_SECRET@Q}.encode('utf-8')
body = open(${file@Q}, 'rb').read()
print('sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest())
PY
}

post() {
  local event="$1"
  local delivery="$2"
  local file="$3"
  local sig
  sig="$(sign_file "$file")"
  curl -sS -X POST "http://$HOST:$PORT/github/webhook" \
    -H "Content-Type: application/json" \
    -H "X-GitHub-Event: $event" \
    -H "X-GitHub-Delivery: $delivery" \
    -H "X-Hub-Signature-256: $sig" \
    --data-binary "@$file"
  echo
}

issue_payload="$(mktemp)"
pr_comment_payload="$(mktemp)"

cat >"$issue_payload" <<'JSON'
{
  "action": "opened",
  "issue": {
    "number": 16,
    "title": "DevOps: verify issue dispatcher automation",
    "body": "Synthetic local webhook test",
    "html_url": "https://github.com/fourmajor/hoopsmania/issues/16",
    "updated_at": "2026-02-25T05:10:00Z",
    "labels": [{"name": "devops"}]
  },
  "repository": {"full_name": "fourmajor/hoopsmania"}
}
JSON

cat >"$pr_comment_payload" <<'JSON'
{
  "action": "created",
  "issue": {
    "number": 42,
    "title": "feat: sample pull request",
    "body": "Sample PR body",
    "html_url": "https://github.com/fourmajor/hoopsmania/pull/42",
    "pull_request": {"url": "https://api.github.com/repos/fourmajor/hoopsmania/pulls/42"},
    "labels": [{"name": "backend"}]
  },
  "comment": {
    "body": "Please address nits before merge.",
    "html_url": "https://github.com/fourmajor/hoopsmania/pull/42#issuecomment-1000000000",
    "created_at": "2026-02-25T05:12:00Z"
  },
  "repository": {"full_name": "fourmajor/hoopsmania"},
  "sender": {"login": "reviewer-bot"}
}
JSON

echo "-- issues event --"
post "issues" "test-issue-$(date +%s)" "$issue_payload"

echo "-- pr issue_comment event --"
post "issue_comment" "test-pr-comment-$(date +%s)" "$pr_comment_payload"

echo "-- duplicate delivery check --"
post "issue_comment" "duplicate-delivery-1" "$pr_comment_payload"
post "issue_comment" "duplicate-delivery-1" "$pr_comment_payload"

rm -f "$issue_payload" "$pr_comment_payload"
