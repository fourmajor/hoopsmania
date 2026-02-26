# Issue Dispatcher (Webhook-Driven)

GitHub webhook events -> role routing -> OpenClaw handoff bridge.

This is a bootstrap-quality automation path intended for local persistent runtime.

## What is implemented

### Issue routing + auto-execution (enhanced)
- Webhook endpoint: `POST /github/webhook`
- Signature verification: `X-Hub-Signature-256` against `GITHUB_WEBHOOK_SECRET`
- Role routing from `.openclaw/issue-routing.yaml`
- `DISPATCH_HOOK_CMD` support (defaults to `dispatch_bridge.sh`)
- For **new issues** (`action=opened`):
  - if routing has a **single non-default role match**, the owning employee is auto-executed immediately
  - if low confidence (no match / ambiguous multi-role match), dispatcher falls back to `default_role` (recommended `ctrl^core`) for triage
- Dispatcher issue comments include `AI Employee: <name>` and use start/update/done progress wording

### PR feedback auto-addressing (new)
- Trigger events:
  - `pull_request_review`
  - `pull_request_review_comment`
  - `issue_comment` (only when comment is on a PR)
- Auto-create/link a review-followup task record in:
  - `.openclaw/state/review_followups.json`
- Task record includes:
  - PR number + URL
  - tracked comment permalink(s)
  - required action checklist
  - route owner + event history + status
- Auto-route to owning employee via `pr_rules` heuristics in `.openclaw/issue-routing.yaml`
  - label + file-path + title/body matching
  - fallback: `default_pr_role` (recommended `ctrl^core`)
  - if a routed role is blank/unknown, normalize to safe fallback (`ctrl^core`)
- Security review gate:
  - for PRs that are **not** purely security-focused, locktrace approval is required before followup auto-close
  - if locktrace requests changes, dispatcher routes work back to the owning engineer automatically
  - override/exception label: `security-review:override` (configurable with `LOCKTRACE_OVERRIDE_LABEL`)
- Worker handoff message includes explicit required behavior:
  - post acknowledgement in PR thread
  - push fix commit(s)
  - reply with addressed commit hash(es)
- Closure gate:
  - followup closes only when **all review threads are resolved**, **PR checks are green**, and locktrace gate is satisfied for non-security PRs

### Operational behavior
- Idempotency protection:
  - delivery-id dedupe (`X-GitHub-Delivery`)
  - payload fingerprint dedupe
  - deliveries/fingerprints are persisted **only after successful dispatch marker**, so failed handoffs can be safely retried/redelivered
- Logging:
  - dispatcher log: `.openclaw/state/issue-dispatcher.log`
  - bridge log: `.openclaw/state/dispatch-bridge.log`
  - downstream marker: `OPENCLAW_DISPATCH_RESULT { ... }`

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

- `GITHUB_TOKEN` (required for PR file heuristics + closure gate + comments)
- `OPENCLAW_SESSION_<ROLE_KEY>` mappings for persistent employee sessions
- `GITHUB_WEBHOOK_ID` (required for automated replay of failed webhook deliveries)
- `FAILED_DELIVERY_LOOKBACK_HOURS` + `MAX_FAILED_DELIVERY_REPLAYS` for replay safety bounds

### Auto-execution controls

- `AUTO_EXECUTE_NEW_ISSUES=1|0`
  - `1` (default): allow auto-execution path for confident routes
  - `0`: disable auto-execution and always hand off issue-opened events to triage behavior
- `AUTO_EXECUTE_ONLY_ON_OPENED=1|0`
  - `1` (default): only auto-execute when issue action is `opened`
  - `0`: allow confident non-opened issue events to auto-execute too
- `FORCE_TRIAGE_LABEL=<label>` (default `dispatch:triage`)
  - if present on an issue, force fallback to `default_role` triage even when role matching is confident

### Security review gate controls

- `LOCKTRACE_GITHUB_LOGIN=<login>` (default `locktrace`)
- `LOCKTRACE_OVERRIDE_LABEL=<label>` (default `security-review:override`)
  - if override label is applied, locktrace approval gate is bypassed for exception handling

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

---

## GitHub webhook wiring

In repository settings:

- **Settings -> Webhooks -> Add webhook**
- **Payload URL:** `https://<public-endpoint>/github/webhook`
- **Content type:** `application/json`
- **Secret:** same as `GITHUB_WEBHOOK_SECRET`
- **Events:** choose **Let me select individual events** and enable:
  - **Issues**
  - **Pull request reviews**
  - **Pull request review comments**
  - **Issue comments**

---

## Dispatch bridge placeholders

Default command in `.env.example`:

```bash
DISPATCH_HOOK_CMD=./dispatch_bridge.sh {role_q} {repo_q} {task_kind_q} {task_number_q} {task_title_q} {task_url_q} {context_json_q}
```

Supported placeholders:

- `{role}` `{repo}` `{task_kind}` `{task_number}` `{task_title}` `{task_url}` `{context_json}`
- shell-safe variants: `{role_q}` etc.

Unknown placeholders are rejected with HTTP 400.

---

## Review followup record schema (stored)

Each task is keyed by `<repo>#<pr_number>` and includes:

- `status`: `open|closed`
- `role`
- `pr_number`, `pr_title`, `pr_url`
- `comment_permalinks[]`
- `required_action_checklist[]`
- event history timestamps
- `closed_at` when closure gate passes

---

## Verification steps

1. Start dispatcher.
2. Confirm health endpoint:

```bash
curl -sS http://127.0.0.1:8787/healthz
```

3. Send synthetic issue + PR feedback payloads:

```bash
cd automation/issue-dispatcher
./test_webhook.sh
```

4. Confirm:
- issue routing still works
- followup record created/updated in `.openclaw/state/review_followups.json`
- duplicate delivery gets ignored

5. For live tests, use GitHub webhook **Recent Deliveries -> Redeliver**.

## Replay failed webhook deliveries (recovery path)

When webhook ingress is briefly down (e.g., tunnel outage), GitHub may return `503` and feedback events never reach the dispatcher. Recover with replay:

```bash
cd automation/issue-dispatcher
export GITHUB_TOKEN=<repo-admin-token>
export GITHUB_WEBHOOK_ID=<numeric-hook-id>
python replay_failed_deliveries.py --repo fourmajor/hoopsmania
```

Safety filters:
- event must be one of dispatcher-supported events
- non-200 deliveries only
- skips already-redelivered attempts
- lookback window via `FAILED_DELIVERY_LOOKBACK_HOURS`
- cap via `MAX_FAILED_DELIVERY_REPLAYS`

## Verify webhook subscriptions (important)

PR feedback automation requires these webhook events on the repository hook:

- `issues`
- `issue_comment`
- `pull_request_review`
- `pull_request_review_comment`

Use the verifier (AI Employee: pipewire):

```bash
cd automation/issue-dispatcher
export GITHUB_TOKEN=<repo-admin-token>
python verify_webhook_events.py --repo fourmajor/hoopsmania --hook-id <HOOK_ID>
# auto-repair if needed:
python verify_webhook_events.py --repo fourmajor/hoopsmania --hook-id <HOOK_ID> --apply
```

---

## What is still manual

- Maintaining role mapping env vars (`OPENCLAW_SESSION_*` / `OPENCLAW_AGENT_*`)
- Keeping OpenClaw/Gateway auth healthy on host
- Running a public tunnel when testing locally
