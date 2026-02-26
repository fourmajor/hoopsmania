#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import dispatcher


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay failed GitHub webhook deliveries for dispatcher events.")
    parser.add_argument("--repo", required=True, help="owner/repo")
    args = parser.parse_args()

    result = dispatcher.replay_failed_deliveries(args.repo)
    print(json.dumps(result))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
