# ADR 001: Single Source of Truth for Employee Data

- Status: Proposed
- Date: 2026-02-25
- Related issue: https://github.com/fourmajor/hoopsmania/issues/87

## Context
Employee/team metadata is currently maintained in more than one place (human-facing markdown + automation-facing YAML/routing). This creates drift risk, duplicate edits, and avoidable review noise.

## Decision
Adopt **one canonical source** for employee data:

- **Canonical file:** `.openclaw/employees.yaml`
- Do **not** add a markdown generation step for `EMPLOYEES.md`; automation and policy decisions should rely on YAML only.

## Why YAML (chosen) vs alternatives

### YAML (chosen)
- **Pros:** human-editable, automation-friendly, supports schema validation, aligns with existing `.openclaw` config patterns.
- **Cons:** less narrative readability than markdown unless rendered.

### Markdown as canonical
- **Pros:** best prose readability in PRs.
- **Cons:** weak structure guarantees, fragile parser logic, harder CI validation.

### JSON as canonical
- **Pros:** strict machine structure.
- **Cons:** poorer authoring ergonomics for frequent manual edits.

## Migration plan (practical)
1. Add `.openclaw/employees.yaml` with full employee roster + required fields.
2. Add schema (`automation/schemas/employees.schema.json`) and validator script.
3. Update automation to read only canonical YAML.
4. CI checks:
   - schema validation passes.
5. Document workflow in `docs/contributing` with YAML as the sole source of truth.

## Validation and enforcement
- **Pre-commit / local check:** validate YAML schema.
- **CI required check:**
  - `employees:validate` (schema + semantic rules).
- **CODEOWNERS (optional):** require review from Dev Productivity for canonical schema/file changes.

## Backward compatibility and deprecation
- **Phase 1 (compat):** keep `EMPLOYEES.md` as-is for existing links/readability while transitioning automation to YAML.
- **Phase 2 (deprecate):** add notice in `EMPLOYEES.md` that canonical employee data lives in `.openclaw/employees.yaml`.
- **Phase 3 (enforce):** reject automation changes that bypass canonical YAML.

## Non-goals (this proposal PR)
- Full implementation of schema/CI in this PR.
- Refactoring unrelated automation.

## Rollout notes
Create follow-up implementation issue(s) after ADR approval:
- implement canonical YAML + schema,
- add CI gates and contributor guidance.
