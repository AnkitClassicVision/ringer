#!/usr/bin/env python3
"""Validate a Cross-Harness Skill Implant v1 manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from implant_skill import WorkflowError, load_and_validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_and_validate_manifest(args.manifest)
    except WorkflowError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"VALID: {manifest['plan_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
