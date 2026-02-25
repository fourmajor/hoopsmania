#!/usr/bin/env python3
"""Validate generated PR body markdown content.

Fails if literal escaped newline sequences (\\n) are present in content,
because these render incorrectly on GitHub when passed as plain text.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN = "\\n"


def validate_content(content: str) -> tuple[bool, str]:
    if FORBIDDEN in content:
        return (
            False,
            "PR body contains literal escaped newline sequence '\\n'. "
            "Use real newlines and pass content via --body-file.",
        )
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PR body markdown file")
    parser.add_argument("--file", required=True, help="Path to PR body markdown file")
    args = parser.parse_args()

    path = Path(args.file)
    content = path.read_text(encoding="utf-8")
    ok, msg = validate_content(content)
    if not ok:
        print(f"ERROR: {msg}\nFile: {path}")
        return 1
    print(f"PR body validation passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
