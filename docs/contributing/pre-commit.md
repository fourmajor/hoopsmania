# Pre-commit hooks

This repo uses [pre-commit](https://pre-commit.com/) for lightweight formatting and validation before code reaches CI.

## One-time setup

```bash
python3 -m pip install pre-commit
pre-commit install
```

After setup, hooks run automatically on each `git commit`.

## Run manually

```bash
pre-commit run
pre-commit run --all-files
```

## Update hook versions

```bash
pre-commit autoupdate
```

Then commit the updated `.pre-commit-config.yaml`.
