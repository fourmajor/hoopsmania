#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  automation/github/create_issue_with_body_file.sh \
    --title "<issue title>" \
    --employee "<employee alias>" \
    [--repo <owner/repo>] \
    [--labels "bug,devops"] \
    [--assignee <login>] \
    [--milestone <name-or-number>] \
    [--extra-file <markdown file>] \
    [--dry-run]

What it does:
- Generates an issue body markdown file with real newlines.
- Enforces required policy fields:
  - submitting AI employee attribution (`AI Employee: <name>`)
- Creates the issue with: gh issue create --body-file <generated-file>

Examples:
  automation/github/create_issue_with_body_file.sh \
    --title "devops: harden webhook retries" \
    --employee "pipewire" \
    --repo "fourmajor/hoopsmania"

  automation/github/create_issue_with_body_file.sh \
    --title "docs: add onboarding troubleshooting" \
    --employee "docdrip" \
    --labels "documentation" \
    --extra-file /tmp/issue-extra.md
USAGE
}

TITLE=""
EMPLOYEE=""
REPO=""
LABELS=""
ASSIGNEE=""
MILESTONE=""
EXTRA_FILE=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)
      TITLE="${2:-}"; shift 2 ;;
    --employee)
      EMPLOYEE="${2:-}"; shift 2 ;;
    --repo)
      REPO="${2:-}"; shift 2 ;;
    --labels)
      LABELS="${2:-}"; shift 2 ;;
    --assignee)
      ASSIGNEE="${2:-}"; shift 2 ;;
    --milestone)
      MILESTONE="${2:-}"; shift 2 ;;
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

if [[ -z "$TITLE" || -z "$EMPLOYEE" ]]; then
  echo "Missing required args: --title, --employee" >&2
  usage
  exit 2
fi

if [[ -n "$EXTRA_FILE" && ! -f "$EXTRA_FILE" ]]; then
  echo "--extra-file not found: $EXTRA_FILE" >&2
  exit 2
fi

body_file="$(mktemp -t hoopsmania-issue-body-XXXXXX.md)"

cat > "$body_file" <<EOF_BODY
## Summary
- Describe the problem and expected outcome.

## Why this matters
- Explain impact and urgency.

## Acceptance Criteria
- [ ] Add concrete, testable criteria.

## Attribution
AI Employee: $EMPLOYEE
EOF_BODY

if [[ -n "$EXTRA_FILE" ]]; then
  {
    printf '\n## Additional Context\n'
    cat "$EXTRA_FILE"
    printf '\n'
  } >> "$body_file"
fi

cmd=(gh issue create --title "$TITLE" --body-file "$body_file")

if [[ -n "$REPO" ]]; then
  cmd+=(--repo "$REPO")
fi
if [[ -n "$LABELS" ]]; then
  cmd+=(--label "$LABELS")
fi
if [[ -n "$ASSIGNEE" ]]; then
  cmd+=(--assignee "$ASSIGNEE")
fi
if [[ -n "$MILESTONE" ]]; then
  cmd+=(--milestone "$MILESTONE")
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

echo "Issue body file used: $body_file"
