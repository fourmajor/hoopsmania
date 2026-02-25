# Issue Dispatcher Local Runbook

This runbook covers the webhook-driven issue dispatcher service.

## 1) Setup

```bash
cd automation/issue-dispatcher
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- set `GITHUB_WEBHOOK_SECRET`
- optional `GITHUB_TOKEN`
- optional role session mappings (`OPENCLAW_SESSION_<ROLE_KEY>`) for persistent employees

## 2) Run as persistent service

### macOS (launchd)

```bash
cd automation/issue-dispatcher
./dispatcher_service.sh install
./dispatcher_service.sh status
```

### fallback runner (non-macOS)

`install` auto-falls back to nohup/pidfile mode.

## 3) Webhook wiring in GitHub

- Repo Settings -> Webhooks -> Add webhook
- URL: `https://<public-endpoint>/github/webhook`
- Content type: `application/json`
- Secret: same as `GITHUB_WEBHOOK_SECRET`
- Events: `Issues`

For local delivery, expose port 8787 via ngrok/cloudflared.

## 4) Verify

```bash
curl -sS http://127.0.0.1:8787/healthz
cd automation/issue-dispatcher
./test_webhook.sh
```

Expected:
- first request: dispatch result JSON with role + exit
- second request (same delivery id): `ignored: duplicate delivery`

## 5) Logs

```bash
tail -f .openclaw/state/issue-dispatcher.log
tail -f .openclaw/state/dispatch-bridge.log
```

## 6) Stop / restart

```bash
cd automation/issue-dispatcher
./dispatcher_service.sh stop
./dispatcher_service.sh start
./dispatcher_service.sh restart
```

## 7) Manual steps that remain

- Create/update role session-id mappings in `.env`
- Keep OpenClaw auth/session environment healthy on host
- Manage tunnel URL lifecycle for local webhook endpoint
