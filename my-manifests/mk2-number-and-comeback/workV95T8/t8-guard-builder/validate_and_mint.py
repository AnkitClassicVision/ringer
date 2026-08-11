#!/usr/bin/env python3
"""Validate a canonical pathway graph before minting an unattached version."""

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback")
VALIDATOR = ROOT / "checks/check_v91_graph.py"
MINT_SCRIPT = Path("/home/ankit114/repos/mott-v21-snap/scripts/mint_graph_version.py")
DEFAULT_BASE = ROOT / "pathway-v86.json"
DEFAULT_V88_REF = ROOT / "pathway-v90.json"
DEFAULT_CLASSIFICATION = ROOT / "workK/build-v92/v91-classification.json"
REFUSAL = (
    "REFUSED: validation failed - a version that fails the canonical assertions "
    "must not be minted."
)
REMINDER = (
    "REMINDER: the Bland dashboard editor base is UNVERSIONED and may be stale - "
    "never edit there; regenerate from the transform chain."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", help="path to the draft graph JSON")
    parser.add_argument("--base", default=str(DEFAULT_BASE))
    parser.add_argument("--v88-ref", default=str(DEFAULT_V88_REF))
    parser.add_argument("--classification", default=str(DEFAULT_CLASSIFICATION))
    parser.add_argument("--skip-validation-i-understand-the-risk", action="store_true")
    return parser.parse_args()


def run_validator(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(VALIDATOR),
        "--base", args.base,
        "--draft", args.draft,
        "--v88-ref", args.v88_ref,
        "--classification", args.classification,
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    return completed.returncode


def run_mint(draft: str) -> int:
    process = subprocess.Popen(
        [sys.executable, "-u", str(MINT_SCRIPT), draft],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    version = None
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        match = re.fullmatch(r"VERSION=(\d+)\s*", line)
        if match:
            version = match.group(1)
    returncode = process.wait()
    if returncode != 0:
        return returncode
    if version is None:
        print("REFUSED: mint succeeded without reporting a VERSION= line.", file=sys.stderr)
        return 1
    print(f"GUARD_RESULT=MINTED version={version}")
    print(REMINDER)
    return 0


def main() -> int:
    args = parse_args()
    skip = args.skip_validation_i_understand_the_risk
    if skip:
        print("WARNING: validation SKIPPED by explicit operator flag")
        try:
            confirmation = input("Type YES to continue: ")
        except EOFError:
            confirmation = ""
        if confirmation != "YES":
            print("ABORTED: operator did not type YES; no version was minted.")
            return 2

    validation_code = run_validator(args)
    if validation_code != 0 and not skip:
        print(REFUSAL)
        return 2
    if validation_code != 0:
        print("WARNING: validator reported failures; explicit risk override remains active.")

    return run_mint(args.draft)


if __name__ == "__main__":
    sys.exit(main())
