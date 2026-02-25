# PR Label Taxonomy

This repo uses a compact, practical PR labeling model with two dimensions:

- **Type** (`type:*`) → nature of work
- **Area** (`area:*`) → code ownership/domain touched

## Canonical Labels

### Type labels

- `type:frontend`
- `type:backend`
- `type:documentation`
- `type:ci-cd`

### Area labels

- `area:frontend`
- `area:backend`
- `area:automation`
- `area:docs`

### Priority/Status labels

- `priority:p0`
- `priority:p1`
- `priority:p2`
- `status:needs-triage`
- `status:blocked`
- `status:ready-for-review`

## Automation

- Workflow: `.github/workflows/pr-auto-label.yml`
- Rules: `.github/labeler.yml`

When a PR touches matching paths, corresponding labels are added automatically.
Maintainers can still add/remove labels manually at any time.

## Keeping Labels in Sync

Use the helper script to create/update canonical labels in GitHub settings:

```bash
automation/github/sync_labels.sh
```

The script is idempotent and safe to run repeatedly.
