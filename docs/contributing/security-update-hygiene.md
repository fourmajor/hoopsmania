# Security update hygiene policy

This document defines how Hoops Mania triages, patches, and verifies dependency security updates.

## Ownership

- **Primary owner:** DevOps Engineer (`pipewire` role)
- **Code owner support:** service owner for affected area (`backend`, `web`, or automation)
- **Approver:** repo maintainer (`@fourmajor`)

## Severity + SLA targets

- **Critical:** triage within 4 hours, patch or mitigation within 24 hours
- **High:** triage within 1 business day, patch or mitigation within 3 business days
- **Medium:** triage within 3 business days, patch in next planned dependency update window
- **Low:** batch into normal maintenance updates

## Triage and remediation workflow

1. **Detect**
   - CI vulnerability scan fails or reports findings.
   - Dependabot/security advisory notification arrives.
2. **Assess**
   - Confirm package is reachable in runtime/build path.
   - Determine exploitability and environment impact.
3. **Plan fix**
   - Preferred: upgrade to patched version.
   - Fallback: pin/override vulnerable transitive dependency.
   - If no patch available, document temporary mitigation and monitoring.
4. **Implement + verify**
   - Apply update in scoped PR.
   - Run unit/integration tests and vulnerability scan workflow.
5. **Rollout + rollback**
   - Merge during normal deployment window unless critical emergency.
   - If regression occurs, rollback to last known-good release and open follow-up issue.
6. **Document**
   - Link advisory + remediation PR in issue/incident notes.

## CI automation

The repository runs a security audit workflow that:

- scans Python dependencies (`pip-audit`) from `backend/requirements.txt`
- scans Node dependencies (`npm audit`) in `web/`
- uploads machine-readable reports as workflow artifacts
- fails the workflow when actionable high-risk findings are present
- permits narrowly scoped, time-boxed ignores only when no compatible upstream patch exists

This keeps vulnerability visibility explicit and actionable in every PR and push.

## Temporary vulnerability exceptions

Use exceptions only when all of the following are true:

1. The advisory cannot be remediated without incompatible upstream constraints.
2. A mitigation or reduced exposure is documented.
3. The exception is explicit in CI and reviewed monthly.

Current exception in CI:

- `GHSA-7f5h-v6xp-fcq8` / `CVE-2025-62727` (Starlette range parser DoS), temporarily ignored while FastAPI-compatible Starlette patch is unavailable in this stack.
