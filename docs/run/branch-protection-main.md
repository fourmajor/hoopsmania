# Branch Protection Runbook (`main`)

Issue link: [#57](https://github.com/fourmajor/hoopsmania/issues/57)

This runbook sets and verifies the required protection policy on `main`:
- Require pull requests before merge (no direct pushes for non-admins)
- Require at least **1 approving review**
- Dismiss stale approvals on new commits
- Require required status checks to pass before merge

## Prerequisites

- GitHub CLI authenticated with admin access to the repo:

```bash
gh auth status
```

- From repository root, set once:

```bash
export OWNER="fourmajor"
export REPO="hoopsmania"
```

## Apply protection (API one-liner)

> This command configures branch protection on `main` in a single call.

```bash
gh api --method PUT "repos/$OWNER/$REPO/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks.strict=true \
  -f required_status_checks.contexts[]='test-and-lint' \
  -f enforce_admins=false \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f required_pull_request_reviews.require_code_owner_reviews=false \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f required_conversation_resolution=true \
  -f restrictions=
```

## Verify protection (script)

Run:

```bash
./automation/github/check_main_branch_protection.sh fourmajor hoopsmania
```

Expected output includes:
- `required_approving_review_count >= 1: OK`
- `dismiss_stale_reviews: OK`
- `required_status_checks.strict: OK`
- `required_status_checks contexts set: OK`

## Manual GitHub UI path (if API access is unavailable)

1. Open: `Settings` → `Branches`.
2. Add/edit branch protection rule for `main`.
3. Enable:
   - Require a pull request before merging
   - Require approvals (**1**)
   - Dismiss stale pull request approvals when new commits are pushed
   - Require status checks to pass before merging
4. Select required check(s): `test-and-lint` (or project’s current CI check name).
5. Save changes.

## Notes

- If CI check names change, re-run the API command with updated `required_status_checks.contexts[]` values.
- If admin enforcement is desired later, set `enforce_admins=true`.
