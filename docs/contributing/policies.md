# Contribution Policies

These rules apply to all contributors and all repos changes.

## 1) Issue First, Then PR

- Create a GitHub issue **before** opening a pull request.
- Reference the issue in the PR description using `Closes #<issue-number>` (or `Refs #<issue-number>` when not closing).
- If a PR has no linked issue, it is out of policy and should be updated before review.

## 2) PR Descriptions Must Name the Submitting AI Employee

- Every PR description must include: `AI Employee: <name>`.
- Put this line near the top of the PR description.

## 3) Document Standing Instructions Promptly

When fourmajor gives a standing instruction (phrases like "in the future", "always", "from now on"):

- Add the rule to project documentation immediately in the same workstream.
- Keep the instruction concise, actionable, and easy to find.
- Add or update links from top-level docs (like `README.md`) when discoverability is needed.

## 4) Close Issues When Work Is Done

- If your PR resolves the issue, include `Closes #<issue-number>` in the PR description.
- After merge, verify the linked issue is closed.
- If work is complete without a PR, close the issue manually with a short resolution note.

## 5) PR Body Formatting Standard (No Literal `\n`)

- For multiline PR descriptions, use `gh pr create --body-file <file>` (preferred) or a heredoc-written file.
- Avoid escaped newline strings like `--body "line1\\nline2"` for multiline content.
- Canonical helper: `automation/github/create_pr_with_body_file.sh`

## 6) Delete Branches After PR Merge

- Delete the working branch immediately after the PR is merged.
- Prefer deleting via GitHub's **Delete branch** action on the merged PR.
- If a branch must be kept temporarily, document the reason in the PR conversation.

## Quick Checklist

Before requesting review:

- [ ] Related issue exists.
- [ ] PR description includes `AI Employee: <name>` near the top.
- [ ] PR links the issue (`Closes #...` / `Refs #...`).
- [ ] Multiline PR body was created via `--body-file` (or heredoc file), not escaped `\\n` text.
- [ ] Any new standing instruction has been documented.

After merge:

- [ ] Linked issue is closed.
- [ ] Merged branch is deleted (or exception documented).
