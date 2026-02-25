#!/usr/bin/env python3
"""Validate canonical employee roster YAML against schema + semantic checks."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = ROOT / ".openclaw" / "employees.yaml"
SCHEMA_PATH = ROOT / "automation" / "schemas" / "employees.schema.json"

REQUIRED_ALIASES = {
    "ctrl^core",
    "docdrip",
    "Ghost|line",
    "neonflux",
    "pipewire",
    "breakp0int",
    "wireframe",
    "mont3carlo",
    "fun_logic",
    "pplOps^root",
    "cloudwire",
    "costflux",
    "stratforge",
    "hypepulse",
    "devlane",
}


def fail(message: str) -> None:
    print(f"❌ employees validation failed: {message}")
    sys.exit(1)


def main() -> int:
    if not YAML_PATH.exists():
        fail(f"missing canonical roster file: {YAML_PATH}")

    if not SCHEMA_PATH.exists():
        fail(f"missing schema file: {SCHEMA_PATH}")

    with YAML_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        path = "/".join(str(p) for p in first.absolute_path) or "<root>"
        fail(f"schema error at {path}: {first.message}")

    employees = data.get("employees", [])
    aliases = [emp["alias"] for emp in employees]

    if len(aliases) != len(set(a.lower() for a in aliases)):
        fail("aliases must be unique (case-insensitive)")

    missing_aliases = sorted(REQUIRED_ALIASES - set(aliases))
    if missing_aliases:
        fail(f"missing required aliases: {', '.join(missing_aliases)}")

    print("✅ employees.yaml passed schema + semantic validation")
    print(f"   employees: {len(employees)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
