# Issue Dispatcher Local Runbook

This runbook covers webhook-driven issue routing and PR feedback followup automation.

## 1) Setup

```bash
cd automation/issue-dispatcher
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- required: `GITHUB_WEBHOOK_SECRET`
- recommended: `GITHUB_TOKEN` (for PR file heuristics + closure gate + comments)
- optional role mappings: `OPENCLAW_SESSION_<ROLE_KEY>` / `OPENCLAW_AGENT_<ROLE_KEY>`

## 2) Run as persistent service

### macOS (launchd)

```bash
cd automation/issue-dispatcher
./dispatcher_service.sh install
./dispatcher_service.sh status
```

## 3) Webhook wiring in GitHub

- Repo Settings -> Webhooks -> Add webhook
- URL: `https://<public-endpoint>/github/webhook`
- Content type: `application/json`
- Secret: same as `GITHUB_WEBHOOK_SECRET`
- Events to enable:
  - Issues
  - Pull request reviews
  - Pull request review comments
  - Issue comments

## 4) Verify

```bash
curl -sS http://127.0.0.1:8787/healthz
cd automation/issue-dispatcher
./test_webhook.sh
```

Expected:
- issue routing response with role + dispatch exit
- PR feedback response with followup task payload
- duplicate delivery returns `ignored: duplicate delivery`

## 5) Check state + logs

```bash
cat .openclaw/state/review_followups.json

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

## 7) Closure gate behavior

Followup record closes only when both are true:

1. all PR review threads resolved/answered
2. latest PR checks are green

If either condition is not satisfied or API data unavailable, followup remains open.
