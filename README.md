# hoopsmania

```text
 _   _  ___   ___  ____   ____    __  __    _    _   _ ___    _   
| | | |/ _ \ / _ \|  _ \ / ___|  |  \/  |  / \  | \ | |_ _|  / \  
| |_| | | | | | | | |_) |\___ \  | |\/| | / _ \ |  \| || |  / _ \ 
|  _  | |_| | |_| |  __/  ___) | | |  | |/ ___ \| |\  || | / ___ \
|_| |_|\___/ \___/|_|    |____/  |_|  |_/_/   \_\_| \_|___/_/   \_\

                🏀  Playbooks + runbooks + automation
              for an AI-driven global basketball simulation.
```

HoopsMania: AI-driven global basketball simulation game.

## Run Locally

Start here for local setup and service runbooks:

- `docs/run/README.md`

## Automation

Webhook-driven issue routing + OpenClaw handoff:

- `automation/issue-dispatcher/README.md`
- `docs/run/issue-dispatcher-local.md`

## Contributor Policies

Project contribution rules and standing-instruction policy:

- `docs/contributing/policies.md`
- `docs/contributing/employees.md` (human-readable employee guide)
- `docs/contributing/security-update-hygiene.md` (vulnerability triage and remediation policy)

## Canonical Employee Source

Employee roster and policy metadata are canonical in:

- `.openclaw/employees.yaml`

Validation:

- `python automation/github/validate_employees_yaml.py`
- CI job: `employees-validate`

PR reminder: include `AI Employee: <name>` near the top of every PR description.
Issue-body reminder: for multiline issue descriptions, use `gh issue create --body-file` (or `automation/github/create_issue_with_body_file.sh`) to avoid literal `\\n` rendering.
Issue-comment reminder: every agent-posted GitHub issue comment must include `AI Employee: <name>`. 
