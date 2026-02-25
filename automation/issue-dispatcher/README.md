# Issue Dispatcher (Webhook-Driven)

GitHub issue event -> role routing -> OpenClaw handoff bridge.

This is a bootstrap-quality automation path intended for local persistent runtime.

## What is implemented

- Webhook endpoint: `POST /github/webhook`
- Signature verification: `X-Hub-Signature-256` against `GITHUB_WEBHOOK_SECRET`
- Role routing from `.openclaw/issue-routing.yaml`
- `DISPATCH_HOOK_CMD` support (defaults to `dispatch_bridge.sh`)
- OpenClaw bridge routing:
  - role -> persistent session id (`OPENCLAW_SESSION_<ROLE>`)
  - role -> agent id fallback (`OPENCLAW_AGENT_<ROLE>`)
  - fallback agent (`OPENCLAW_FALLBACK_AGENT`)
- Idempotency protection:
  - delivery-id dedupe (`X-GitHub-Delivery`)
  - payload fingerprint dedupe (`repo+issue+action+updated_at`)
- Logging:
  - dispatcher log: `.openclaw/state/issue-dispatcher.log`
  - bridge log: `.openclaw/state/dispatch-bridge.log`

---

## Setup

From repo root:

```bash
cd automation/issue-dispatcher
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with real values (do not commit `.env`).

### Required env vars

- `GITHUB_WEBHOOK_SECRET`

### Recommended env vars

- `GITHUB_TOKEN` (for assignment comments back to issue)
- `OPENCLAW_SESSION_<ROLE>` mappings for persistent employee sessions

---

## Run options

### A) Foreground dev run

```bash
cd automation/issue-dispatcher
./run_dispatcher.sh
```

### B) Persistent service (macOS launchd)

```bash
cd automation/issue-dispatcher
./dispatcher_service.sh install
./dispatcher_service.sh status
```

Useful lifecycle commands:

```bash
./dispatcher_service.sh start
./dispatcher_service.sh stop
./dispatcher_service.sh restart
./dispatcher_service.sh logs
```

### C) Non-macOS fallback

`dispatcher_service.sh` automatically falls back to a nohup/pidfile runner.

---

## GitHub webhook wiring

In the target repository settings:

- **Settings -> Webhooks -> Add webhook**
- **Payload URL:** `https://<public-endpoint>/github/webhook`
- **Content type:** `application/json`
- **Secret:** same value as `GITHUB_WEBHOOK_SECRET`
- **Events:** choose **Let me select individual events** -> check **Issues**
- **Active:** enabled

### Local tunnel option

For local machine testing, expose local dispatcher:

```bash
# Example with ngrok
ngrok http 8787
```

Then set payload URL to:

`https://<ngrok-id>.ngrok-free.app/github/webhook`

(Cloudflare Tunnel or similar is also fine.)

---

## DISPATCH_HOOK_CMD + bridge behavior

Default command in `.env.example`:

```bash
DISPATCH_HOOK_CMD=./dispatch_bridge.sh {role_q} {repo_q} {issue_number} {issue_title_q} {issue_url_q}
```

Bridge routing order:

1. `OPENCLAW_SESSION_<ROLE_KEY>` (persistent employee session)
2. `OPENCLAW_AGENT_<ROLE_KEY>` (role-specific agent id)
3. `OPENCLAW_FALLBACK_AGENT` (default: `main`)

Role key transform examples:

- `tech-writer` -> `OPENCLAW_SESSION_TECH_WRITER`
- `backend-dev` -> `OPENCLAW_SESSION_BACKEND_DEV`
- `devops` -> `OPENCLAW_SESSION_DEVOPS`

---

## Idempotency + logging notes

- Dispatcher persists dedupe state at `.openclaw/state/processed_deliveries.json`.
- Two checks prevent duplicate handoffs:
  - same `X-GitHub-Delivery`
  - same payload fingerprint (`repo+issue+action+updated_at`)
- If state file is deleted, dedupe history resets.
- Hook execution timeout defaults to 45s (`DISPATCH_HOOK_TIMEOUT_SEC`).

Logs to check first when debugging:

```bash
tail -n 100 .openclaw/state/issue-dispatcher.log
tail -n 100 .openclaw/state/dispatch-bridge.log
```

---

## Verification steps

1. Start dispatcher service/run script.
2. Confirm health endpoint:

```bash
curl -sS http://127.0.0.1:8787/healthz
```

3. Run local synthetic webhook test:

```bash
cd automation/issue-dispatcher
./test_webhook.sh
```

4. In GitHub, use **Webhooks -> Recent Deliveries -> Redeliver** and verify duplicates are ignored.

---

## What is still manual

- Creating/maintaining role->session-id mappings in `.env`
- Ensuring OpenClaw/Gateway auth is already configured on the host
- Creating and running a public tunnel for local webhook delivery
