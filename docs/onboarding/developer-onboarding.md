# Developer Onboarding (30-Minute Quickstart)

Goal: get a new contributor from zero to a verified local run in ~30 minutes.

Vibe recommendation: this guide is best read while listening to Tool.

## Prerequisites

Install before cloning:

- Git
- Python 3.11+ (3.10 may work, but 3.11+ is recommended)
- Node.js 20+ and npm (for web frontend)
- A terminal shell (zsh/bash/fish)

Optional but recommended:

- GitHub CLI (`gh`) for issue/PR workflow

## 30-Minute Path to First Success

### 1) Clone the repository (2 minutes)

```bash
git clone https://github.com/fourmajor/hoopsmania.git
cd hoopsmania
```

### 2) Set up backend environment (8 minutes)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3) Start backend API (2 minutes)

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected endpoints:

- API root: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

### 4) Verify backend health (2 minutes)

In a second terminal:

```bash
curl -sS http://127.0.0.1:8000/ping
```

Expected:

```json
{"message":"pong"}
```

### 5) Run backend tests (3 minutes)

```bash
cd backend
source .venv/bin/activate
pytest -q
```

### 6) (Optional) Run web frontend (8 minutes)

```bash
cd web
npm install
npm run dev
```

Open: http://localhost:3000

## Standard Local Commands

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest -q
```

### Web

```bash
cd web
npm install
npm run dev
npm run test --if-present
```

## Troubleshooting

### `python3: command not found`

Try `python` instead of `python3`, or install Python 3.11+.

### `uvicorn: command not found`

You are likely outside the virtual environment:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Port 8000 already in use

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Stop the conflicting process, then restart backend.

### `npm` errors in `web/`

- Ensure Node 20+ is installed.
- Remove stale modules and reinstall:

```bash
cd web
rm -rf node_modules package-lock.json
npm install
```

## Where to Go Next

- Runbook index: `docs/run/README.md`
- Backend local runbook: `docs/run/backend-local.md`
- Config reference: `docs/run/configuration.md`
- Contributor policies: `docs/contributing/policies.md`
- Employee guide: `docs/contributing/employees.md`
- Canonical employee data source: `.openclaw/employees.yaml`
