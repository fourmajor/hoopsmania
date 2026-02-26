# CODEOWNERS and Review Ownership

This repository uses `.github/CODEOWNERS` to map major areas to owners.

## Why

- Auto-request the right reviewers when sensitive paths change.
- Keep review accountability clear for frontend/backend/infra/docs/governance paths.

## Current ownership map

- `web/` → `@fourmajor`
- `backend/` → `@fourmajor`
- `automation/` → `@fourmajor`
- `docs/` → `@fourmajor`
- `.github/` → `@fourmajor`
- fallback `*` → `@fourmajor`

## Enforcement

- Workflow: `.github/workflows/codeowner-review-gate.yml`
- Codeowner behavior: fails PR checks when owned paths change but no approval exists from a mapped code owner.
- Documentation behavior: for non-doc PRs, also fails PR checks unless docdrip review is completed with explicit documentation-impact status.

This is a practical repo-level guardrail that works with standard branch protection requiring passing checks and preserves a clear audit trail in PR reviews.

## Ownership update process

1. Edit `.github/CODEOWNERS` with path + owner changes.
2. Open a PR that includes why ownership changed.
3. Ensure at least one current code owner approves.
4. After merge, verify reviewer auto-request behavior on the next PR touching changed paths.

## Notes

- Keep mappings broad and low-friction first; split into finer areas only when needed.
- Prefer stable owner handles (users/teams) to avoid stale ownership.
