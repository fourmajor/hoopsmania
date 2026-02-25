# Backend: Run Locally

This guide explains how to run the HoopsMania backend on a local machine during development.

## Prerequisites

- Python 3.11+
- `pip` available in your shell
- A terminal (macOS, Linux, or WSL)

## 1) Create and activate a virtual environment

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

> On Windows PowerShell, activate with:
> `./.venv/Scripts/Activate.ps1`

## 2) Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 3) Start the backend server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend should now be available at:

- API base: `http://127.0.0.1:8000`
- API docs (FastAPI): `http://127.0.0.1:8000/docs`

## 4) Verify the server is running

Use any endpoint currently available in the app.

Example:

```bash
curl -sS http://127.0.0.1:8000/ping
```

Expected output (today):

```json
{"message":"pong"}
```

As the project grows, this endpoint may change; `/docs` is always the best source of currently available routes.

## 5) Stop the server

In the server terminal, press `Ctrl+C`.

## Common local workflow

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Next docs

- Configuration conventions: `docs/run/configuration.md`
- Run-locally index: `docs/run/README.md`
