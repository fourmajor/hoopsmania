#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  automation/github/create_pr_with_body_file.sh \
    --title "<pr title>" \
    --issue <issue number> \
    --employee "<employee alias>" \
    [--base <base branch>] \
    [--head <head branch>] \
    [--extra-file <markdown file>] \
    [--dry-run]

What it does:
- Generates a PR body markdown file with real newlines.
- Enforces required policy fields:
  - issue linkage (Closes #<issue>)
  - submitting AI employee name (`AI Employee: <name>`)
- Creates the PR with: gh pr create --body-file <generated-file>

Examples:
  automation/github/create_pr_with_body_file.sh \
    --title "fix(ci): stabilize flaky deploy check" \
    --issue 123 \
    --employee "pipewire"

  automation/github/create_pr_with_body_file.sh \
    --title "docs: update runbook" \
    --issue 124 \
    --employee "docdrip" \
    --extra-file /tmp/pr-extra.md
USAGE
}

TITLE=""
ISSUE=""
EMPLOYEE=""
BASE=""
HEAD=""
EXTRA_FILE=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)
      TITLE="${2:-}"; shift 2 ;;
    --issue)
      ISSUE="${2:-}"; shift 2 ;;
    --employee)
      EMPLOYEE="${2:-}"; shift 2 ;;
    --base)
      BASE="${2:-}"; shift 2 ;;
    --head)
      HEAD="${2:-}"; shift 2 ;;
    --extra-file)
      EXTRA_FILE="${2:-}"; shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2 ;;
  esac
done

if [[ -z "$TITLE" || -z "$ISSUE" || -z "$EMPLOYEE" ]]; then
  echo "Missing required args: --title, --issue, --employee" >&2
  usage
  exit 2
fi

if [[ -n "$EXTRA_FILE" && ! -f "$EXTRA_FILE" ]]; then
  echo "--extra-file not found: $EXTRA_FILE" >&2
  exit 2
fi

body_file="$(mktemp -t hoopsmania-pr-body-XXXXXX.md)"

cat > "$body_file" <<EOF
## Summary
- Describe what changed and why.

## Validation
- Add the commands/checks you ran.

## Policy
Closes #$ISSUE
AI Employee: $EMPLOYEE
EOF

if [[ -n "$EXTRA_FILE" ]]; then
  {
    printf '\n## Additional Context\n'
    cat "$EXTRA_FILE"
    printf '\n'
  } >> "$body_file"
fi

cmd=(gh pr create --title "$TITLE" --body-file "$body_file")

if [[ -n "$BASE" ]]; then
  cmd+=(--base "$BASE")
fi
if [[ -n "$HEAD" ]]; then
  cmd+=(--head "$HEAD")
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "[dry-run] Generated body file: $body_file"
  echo "[dry-run] ---"
  cat "$body_file"
  echo "[dry-run] ---"
  printf '[dry-run] Command: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
  exit 0
fi

"${cmd[@]}"

echo "PR body file used: $body_file"
