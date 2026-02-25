# Issue Dispatcher (Webhook-Driven)

This service implements the first pass of **Implementation B**:

`GitHub issue event -> route to role -> handoff hook`

## What it does today

- Receives GitHub webhooks at `POST /github/webhook`
- Verifies webhook signatures with `GITHUB_WEBHOOK_SECRET`
- Routes issue to a role using `.openclaw/issue-routing.yaml`
- Executes a configurable handoff command (`DISPATCH_HOOK_CMD`)
- Optionally posts an assignment comment back to the issue (`GITHUB_TOKEN`)
- Deduplicates webhook deliveries

## What it does not do yet

- Direct OpenClaw sub-agent spawning from inside this process
- Retry queue / dead-letter processing
- Rich confidence scoring

Those are good next steps once initial routing is stable.

---

## Quick start (copy/paste)

From repo root:

```bash
cd automation/issue-dispatcher
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set environment variables:

```bash
export GITHUB_WEBHOOK_SECRET='replace-with-webhook-secret'
export GITHUB_TOKEN='replace-with-fine-grained-token'
export DISPATCHER_HOST='127.0.0.1'
export DISPATCHER_PORT='8787'
```

Set the dispatch hook command:

```bash
export DISPATCH_HOOK_CMD='echo role={role} repo={repo} issue={issue_number} title="{issue_title}" url={issue_url}'
```

Run the dispatcher:

```bash
python dispatcher.py
```

---

## GitHub webhook configuration

In GitHub repo settings:

- **Payload URL:** `https://<your-public-endpoint>/github/webhook`
- **Content type:** `application/json`
- **Secret:** must match `GITHUB_WEBHOOK_SECRET`
- **Events:** `Issues` (opened/edited/labeled/reopened)

For local testing, use a tunnel (Cloudflare Tunnel, ngrok, etc.) from public HTTPS -> `127.0.0.1:8787`.

---

## Routing config

Edit:

- `.openclaw/issue-routing.yaml`

The dispatcher picks the first matching rule and falls back to `default_role`.

---

## Suggested next step (OpenClaw integration)

Point `DISPATCH_HOOK_CMD` at a small bridge script that invokes your preferred OpenClaw handoff method for each role.

This keeps routing logic stable while you iterate on agent orchestration.
