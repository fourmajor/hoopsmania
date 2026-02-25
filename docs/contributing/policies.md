# Contribution Policies

These rules apply to all contributors and all repos changes.

Canonical employee source of truth: `.openclaw/employees.yaml`.
Human-readable employee guide: `docs/contributing/employees.md`.

## 1) Issue First, Then PR

- Create a GitHub issue **before** opening a pull request.
- Reference the issue in the PR description using `Closes #<issue-number>` (or `Refs #<issue-number>` when not closing).
- If a PR has no linked issue, it is out of policy and should be updated before review.

## 2) PR Descriptions Must Name the Submitting AI Employee

- Every PR description must include a line in this exact format: `AI Employee: <name>`.
- Put the line near the top of the PR description, before implementation details.
- PRs missing this line are out of policy and must be updated before review.

Example PR description snippet:

```md
## Summary
AI Employee: docdrip

Updated contributor policy docs to require AI employee attribution in PR descriptions.

Closes #<issue-number>
```

## 3) GitHub Issue Comments from Agents Must Name the AI Employee

- Every GitHub issue comment posted by an AI agent/employee must include `AI Employee: <name>`.
- Put the attribution at the top of the comment.
- Agent-posted issue comments missing this line are out of policy and must be corrected.

Example issue comment snippet:

```md
AI Employee: docdrip
Status: Drafted policy update; opening PR next.
```

## 4) Document Standing Instructions Promptly

When fourmajor gives a standing instruction (phrases like "in the future", "always", "from now on"):

- Add the rule to project documentation immediately in the same workstream.
- Keep the instruction concise, actionable, and easy to find.
- Add or update links from top-level docs (like `README.md`) when discoverability is needed.

## 5) Close Issues When Work Is Done

- If your PR resolves the issue, include `Closes #<issue-number>` in the PR description.
- After merge, verify the linked issue is closed.
- If work is complete without a PR, close the issue manually with a short resolution note.

## 6) PR Body Formatting Standard (No Literal `\n`)

- For multiline PR descriptions, use `gh pr create --body-file <file>` (preferred) or a heredoc-written file.
- Avoid escaped newline strings like `--body "line1\\nline2"` for multiline content.
- Canonical helper: `automation/github/create_pr_with_body_file.sh`

## 7) Issue Body Formatting Standard (No Literal `\n`)

- For multiline GitHub issue descriptions, use `gh issue create --body-file <file>` (preferred) or a heredoc-written file.
- Avoid escaped newline strings like `--body "line1\\nline2"` for multiline issue content.
- Canonical helper: `automation/github/create_issue_with_body_file.sh`
- Issue body examples should include employee attribution near the top or in an attribution section: `AI Employee: <name>`.

Example issue creation pattern:

```bash
automation/github/create_issue_with_body_file.sh \
  --title "devops: improve dispatcher retries" \
  --employee "pipewire" \
  --repo "fourmajor/hoopsmania"
```

## 8) Delete Branches After PR Merge

- Delete the working branch immediately after the PR is merged.
- Prefer deleting via GitHub's **Delete branch** action on the merged PR.
- If a branch must be kept temporarily, document the reason in the PR conversation.

## 9) CODEOWNERS and Code-Owner Review Gate

- Maintain `.github/CODEOWNERS` for major project paths.
- Keep ownership mappings broad and practical by default.
- PRs touching owned paths must receive an approval from a mapped owner (enforced by CI gate).
- Update `docs/contributing/codeowners.md` when ownership policy/process changes.

## Quick Checklist

Before requesting review:

- [ ] Related issue exists.
- [ ] PR description includes `AI Employee: <name>` near the top.
- [ ] PR links the issue (`Closes #...` / `Refs #...`).
- [ ] Agent-posted issue comments include `AI Employee: <name>`.
- [ ] Multiline PR body was created via `--body-file` (or heredoc file), not escaped `\\n` text.
- [ ] Multiline issue body was created via `--body-file` (or heredoc file), not escaped `\\n` text.
- [ ] Any new standing instruction has been documented.

After merge:

- [ ] Linked issue is closed.
- [ ] Merged branch is deleted (or exception documented).
