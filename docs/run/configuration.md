# Development Configuration

This document defines local configuration conventions for HoopsMania services. It is intentionally generic so it remains valid as backend, frontend, workers, and infrastructure are added.

## Configuration principles

- Keep local config in environment variables.
- Commit an `.env.example` template, never real secrets.
- Load config as close to process startup as possible.
- Fail fast with clear errors when required variables are missing.

## File conventions

At repository root (future shared defaults):

- `.env.example` → committed template with placeholder values
- `.env` → local-only values (gitignored)

Service-specific overrides (optional as project grows):

- `backend/.env.example`
- `backend/.env`
- `web/.env.example`
- `web/.env.local`

Use one pattern consistently per service; document deviations in that service's README.

## Suggested starter variables

These are examples of categories, not final product requirements.

```dotenv
# Runtime
APP_ENV=development
LOG_LEVEL=info

# Backend
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Directory layout assumptions (current)

- `backend/` contains backend app code and Python dependencies
- `web/` contains frontend app code
- `docs/` contains architecture and runbooks

As services are added (workers, jobs, db), add a matching section under `docs/run/`.

## Troubleshooting checklist

### Port already in use

- Symptom: server fails to start on configured port.
- Fix: stop the conflicting process or change the port in env/config.

### Missing dependencies

- Symptom: import/module errors at startup.
- Fix: activate virtual environment and reinstall dependencies (`pip install -r requirements.txt`).

### Import path errors

- Symptom: app module cannot be found by runtime/test runner.
- Fix: run commands from expected working directory (`backend/`) and verify package structure.

### Wrong API base URL in frontend

- Symptom: frontend loads but API calls fail.
- Fix: confirm frontend env variable points to the running backend host/port.

## Related

- Backend local run guide: `docs/run/backend-local.md`
- Run-locally index: `docs/run/README.md`
