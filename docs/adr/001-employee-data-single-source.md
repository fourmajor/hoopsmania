# ADR 001: Single Source of Truth for Employee Data

- Status: Proposed
- Date: 2026-02-25
- Related issue: https://github.com/fourmajor/hoopsmania/issues/87

## Context
Employee/team metadata is currently maintained in more than one place (human-facing markdown + automation-facing YAML/routing). This creates drift risk, duplicate edits, and avoidable review noise.

## Decision
Adopt **one canonical source** for employee data:

- **Canonical file:** `.openclaw/employees.yaml`
- **Human-readable roster (`EMPLOYEES.md`)** becomes **derived output** during migration, then optional to keep as generated docs only.

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
3. Add generator script to produce `EMPLOYEES.md` from YAML.
4. Update automation to read only canonical YAML.
5. CI checks:
   - schema validation passes,
   - generated markdown is up to date (fail on drift).
6. Deprecate manual markdown edits; document workflow in `docs/contributing`.

## Validation and enforcement
- **Pre-commit / local check:** validate YAML schema + regenerate markdown.
- **CI required check:**
  - `employees:validate` (schema + semantic rules),
  - `employees:sync-check` (no diff after generation).
- **CODEOWNERS (optional):** require review from Dev Productivity for canonical schema/file changes.

## Backward compatibility and deprecation
- **Phase 1 (compat):** keep `EMPLOYEES.md` in repo as generated artifact for readers and existing links.
- **Phase 2 (deprecate):** add header notice in `EMPLOYEES.md` (“generated; do not edit manually”).
- **Phase 3 (enforce):** reject PRs that manually edit generated sections; only YAML + generator outputs accepted.
- **Phase 4 (optional):** if desired, stop committing generated markdown and publish rendered docs elsewhere.

## Non-goals (this proposal PR)
- Full implementation of schema/generator/CI in this PR.
- Refactoring unrelated automation.

## Rollout notes
Create follow-up implementation issue(s) after ADR approval:
- implement canonical YAML + schema,
- implement markdown generator,
- add CI gates and contributor guidance.
