# PR-Feedback Automation Operations Checklist

Owner: **ctrl^core** (Project Manager)  
Last updated: 2026-02-24

Use this checklist for each PR where automated review feedback is enabled.

## 1) Event Triggers

- `pull_request` opened/reopened/ready_for_review/synchronize
- New review submitted (`APPROVED`, `COMMENTED`, `CHANGES_REQUESTED`)
- New review thread comment posted by human reviewer
- CI status changes to failed/passed on the PR head SHA
- Maintainer label updates affecting workflow (`needs-response`, `blocked`, `ready-to-merge`)

## 2) Routing Ownership Matrix (named employees)

- **ctrl^core** (Project Manager)
  - Triage incoming automation events
  - Confirm owner handoff and SLA clock start
- **devlane** (Developer Productivity Engineer)
  - Own GitHub workflow + automation rule quality
  - Fix routing logic, retries, and notification gaps
- **Ghost|line** (Backend Engineer)
  - Resolve backend/API review findings
- **neonflux** (Frontend Engineer)
  - Resolve frontend/UI review findings
- **breakp0int** (QA Engineer)
  - Reproduce reported defects and post validation notes
- **pipewire** (DevOps Engineer)
  - Resolve CI/runtime/config pipeline failures
- **docdrip** (Technical Writer)
  - Update docs when review feedback is docs/process related

Escalation path: owner -> **ctrl^core** -> fourmajor.

## 3) Expected PR-Thread Acknowledgements

Within one business cycle after routed assignment, assignee posts one short acknowledgement in the relevant PR thread:

- `Acknowledged by <employee-name>. Investigating now; next update by <time>.`

When action is complete, assignee posts:

- `Completed by <employee-name>: <what changed>. Evidence: <commit/CI/test link>.`

If blocked, assignee posts:

- `Blocked for <reason>. Owner: <employee-name>. Escalated to <employee-name or fourmajor>.`

## 4) Done Criteria for Auto-Close

Auto-close may run only when all are true:

- Every automation-created feedback thread has either:
  - a completion acknowledgement from the assigned employee, or
  - an explicit `won't-fix`/`defer` decision acknowledged by **ctrl^core**.
- No open `CHANGES_REQUESTED` review remains unresolved.
- Required CI checks are green for latest PR SHA.
- No blocking labels remain (`needs-response`, `blocked`).
- PR description links a tracking issue (`Closes #...` or `Refs #...`) and includes submitting AI employee name.

If any condition is false, keep PR open and post a status summary with remaining blockers.
