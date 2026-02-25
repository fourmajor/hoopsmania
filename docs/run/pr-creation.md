# PR Creation Standard (Multiline Body Safe)

Use this standard for all agent/employee-created PRs so markdown renders with **real newlines** (never literal `\n`).

## Required policy fields in every PR body

- Issue linkage: `Closes #<issue>` (or `Refs #<issue>` when not closing)
- Submitting AI employee name: `AI Employee: <employee-alias>`

## Preferred method: `--body-file`

```bash
automation/github/create_pr_with_body_file.sh \
  --title "fix(devops): preserve multiline PR body formatting" \
  --issue 50 \
  --employee "pipewire"
```

This helper calls `gh pr create --body-file ...` so newlines are preserved.
It also runs `automation/github/validate_pr_body.py` and fails fast if literal `\\n` appears in generated body content.

## Direct `gh` usage (also valid)

```bash
cat >/tmp/pr-body.md <<'EOF'
## Summary
- Explain what changed.

## Validation
- List checks you ran.

## Policy
Closes #50
AI Employee: pipewire
EOF

gh pr create \
  --title "fix(devops): preserve multiline PR body formatting" \
  --body-file /tmp/pr-body.md
```

## Avoid

- `--body "line1\nline2..."` strings for multiline content.
- Any PR body missing employee name or issue link.
