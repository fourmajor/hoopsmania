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
- auto-exec controls:
  - `AUTO_EXECUTE_NEW_ISSUES=1` (default)
  - `AUTO_EXECUTE_ONLY_ON_OPENED=1` (default)
  - `FORCE_TRIAGE_LABEL=dispatch:triage` (default)
  - `HUMAN_OWNED_LABEL=human-owned` (default)
- security-gate controls:
  - `LOCKTRACE_GITHUB_LOGIN=locktrace` (default)
  - `LOCKTRACE_OVERRIDE_LABEL=security-review:override` (default)

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
- if downstream dispatch fails, webhook returns retryable failure and does **not** persist dedupe markers yet

Issue auto-execution criteria (new issues):
- confident route: exactly one non-default role matches routing rules -> auto-exec that employee
- low confidence: no role match OR multi-role ambiguity -> fallback to `default_role` triage (`ctrl^core`)
- override: if issue has label from `FORCE_TRIAGE_LABEL` (default `dispatch:triage`), force triage fallback
- human-owned guardrail: if issue has label from `HUMAN_OWNED_LABEL` (default `human-owned`), dispatcher skips auto-exec/handoff entirely and records `ignored: human-owned ...` in logs/comments

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

Followup record closes only when all required checks pass:

1. all PR review threads resolved/answered
2. latest PR checks are green
3. for PRs that are **not** purely security-focused, latest locktrace review state is `APPROVED`

If any condition is not satisfied or API data is unavailable, followup remains open.

Override/exception path:
- Add label `security-review:override` (or your configured `LOCKTRACE_OVERRIDE_LABEL`) to bypass locktrace gate for urgent exceptions.
- Use this sparingly and include rationale in PR comments.

Routing fallback safety:
- PR feedback routing uses `default_pr_role` when no rule matches.
- If a configured role is blank/unknown, dispatcher normalizes to `ctrl^core`.
- If locktrace requests changes, dispatcher automatically routes follow-up to the owning engineer (`owner_role`).
