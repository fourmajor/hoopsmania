# Run Locally (Quickstart)

```text
┌───────────────────────────────┐
│  TIP-OFF: LOCAL DEV RUNBOOK   │
└───────────────────────────────┘
```

This is the fastest **copy/paste-friendly** path to get Hoops Mania running locally.

Current priority: **backend development flow**.  
As frontend/services are added, extend this same runbook pattern.

For deeper details, see:
- Backend guide: [`docs/run/backend-local.md`](./backend-local.md)
- Frontend guide (web): [`web/README.md`](../../web/README.md)
- Issue dispatcher guide: [`docs/run/issue-dispatcher-local.md`](./issue-dispatcher-local.md)
- Configuration guide: [`docs/run/configuration.md`](./configuration.md)
- PR creation guide (multiline body standard): [`docs/run/pr-creation.md`](./pr-creation.md)

---

## 0) Get the code

HTTPS clone (recommended default):

```bash
git clone https://github.com/fourmajor/hoopsmania.git
cd hoopsmania
```

SSH clone (if your GitHub SSH keys are configured):

```bash
git clone git@github.com:fourmajor/hoopsmania.git
cd hoopsmania
```

---

## 1) Open terminal at repo root

```bash
cd /path/to/hoopsmania
```

---

## 2) Setup

Create and activate a Python virtual environment, then install dependencies.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> If your shell does not have `python3`, try `python`.

---

## 3) Run

Start the backend API with auto-reload enabled:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected local endpoints:
- API root: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`

---

## 4) Verify

In a second terminal:

```bash
curl -sS http://127.0.0.1:8000/ping
```

Expected response:

```json
{"message":"pong"}
```

Optional quick test pass:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

### Frontend quickstart (web)

From repo root, in a separate terminal:

```bash
cd web
npm install
npm run dev
```

Open: <http://localhost:3000>

See full frontend notes: [`web/README.md`](../../web/README.md)

---

## 5) Stop

In the server terminal where `uvicorn` is running:

```text
Ctrl+C
```

---

## 6) Restart

Use this for day-to-day backend work:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 7) Troubleshooting quick checks

### A) Port 8000 already in use

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

If needed, stop the conflicting process and re-run the server.

### B) `uvicorn: command not found`

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### C) Import/module errors

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
```

### D) Health check fails

```bash
curl -i http://127.0.0.1:8000/ping
curl -i http://127.0.0.1:8000/docs
```

If `/docs` loads but `/ping` fails, route logic likely changed; verify current routes in Swagger.

---

## Extend this runbook as the project grows

Keep this order for each service runbook:

1. setup
2. run
3. verify
4. stop
5. restart
6. troubleshooting quick checks

Suggested future docs:
- `docs/run/frontend-local.md`
- `docs/run/worker-local.md`
- `docs/run/database-local.md`
