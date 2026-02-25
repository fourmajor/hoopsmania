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
DELIVERY_ID="test-$(date +%s)"
PAYLOAD_FILE="$(mktemp)"

cat >"$PAYLOAD_FILE" <<'JSON'
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
  "repository": {
    "full_name": "fourmajor/hoopsmania"
  }
}
JSON

SIGNATURE=$(
  python3 - <<PY
import hmac, hashlib
secret = ${GITHUB_WEBHOOK_SECRET@Q}.encode('utf-8')
body = open(${PAYLOAD_FILE@Q}, 'rb').read()
print('sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest())
PY
)

set -x
curl -sS -X POST "http://$HOST:$PORT/github/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -H "X-GitHub-Delivery: $DELIVERY_ID" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  --data-binary "@$PAYLOAD_FILE"

echo

echo "-- duplicate delivery check --"
curl -sS -X POST "http://$HOST:$PORT/github/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -H "X-GitHub-Delivery: $DELIVERY_ID" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  --data-binary "@$PAYLOAD_FILE"
set +x

echo
rm -f "$PAYLOAD_FILE"
