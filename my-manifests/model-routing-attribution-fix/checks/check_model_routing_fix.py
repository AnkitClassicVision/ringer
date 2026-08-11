#!/usr/bin/env python3
"""Verify and export the Ringer model-routing attribution fix from a worktree."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ALLOWED = {
    "ringer.py",
    "registry/model-identity.toml",
    "tests/test_model_field.py",
    "tests/test_model_log.py",
    "tests/test_catalog.py",
    "tests/test_model_db.py",
}
TESTS = (
    "tests/test_model_field.py",
    "tests/test_model_log.py",
    "tests/test_catalog.py",
    "tests/test_model_db.py",
)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout)
        raise SystemExit(f"FAIL: {' '.join(command)} exited {result.returncode}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", required=True, type=Path)
    args = parser.parse_args()

    for test in TESTS:
        run([sys.executable, test])

    run(["git", "diff", "--check"])
    run(["git", "diff", "--cached", "--check"])
    unstaged_result = run(["git", "diff", "--name-only"], capture=True)
    staged_result = run(["git", "diff", "--cached", "--name-only"], capture=True)
    changed = {
        line.strip()
        for line in (unstaged_result.stdout + "\n" + staged_result.stdout).splitlines()
        if line.strip()
    }
    if not changed:
        raise SystemExit("FAIL: worker produced no tracked changes")
    unexpected = changed - ALLOWED
    if unexpected:
        raise SystemExit(f"FAIL: worker changed files outside ownership: {sorted(unexpected)}")
    required = {"ringer.py", "registry/model-identity.toml", "tests/test_model_field.py", "tests/test_model_log.py", "tests/test_catalog.py"}
    missing = required - changed
    if missing:
        raise SystemExit(f"FAIL: expected changed files are missing: {sorted(missing)}")

    run(["git", "add", "--", *sorted(changed)])
    args.patch.parent.mkdir(parents=True, exist_ok=True)
    patch_result = run(["git", "diff", "--cached", "--binary", "--", *sorted(changed)], capture=True)
    args.patch.write_text(patch_result.stdout, encoding="utf-8")
    if not args.patch.is_file() or args.patch.stat().st_size == 0:
        raise SystemExit("FAIL: exported patch is empty")

    patch_text = args.patch.read_text(encoding="utf-8", errors="replace")
    required_markers = (
        "codex-cli-default",
        "openrouter/",
        "model_source",
        "engine-args",
    )
    missing_markers = [marker for marker in required_markers if marker not in patch_text]
    if missing_markers:
        raise SystemExit(f"FAIL: patch lacks required behavioral markers: {missing_markers}")

    print(
        "PASS: focused model-routing suites passed; file ownership held; "
        f"patch exported to {args.patch}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
