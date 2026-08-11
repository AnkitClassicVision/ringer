#!/usr/bin/env python3
"""Verify and export the Mott v21 build from inside a disposable git worktree.

On PASS the worktree is deleted, so everything worth keeping is exported first.
Runs the orchestrator-owned graph gate rather than trusting the worker's own
validator, proves the generator is deterministic, runs the test suite, and
confirms the worker stayed inside its declared ownership.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

OWNED = [
    "scripts/build_v21_recall_lanes.py",
    "scripts/validate_v21.py",
    "tests/test_v21_scenarios.py",
]

# Harness- and tooling-owned paths the worker is not responsible for. Ringer
# creates worker.log in every task directory before the worker runs, so failing
# on it would fail every honest task.
ALLOWED_PREFIXES = ("build/", "worker.log", "__pycache__/", ".pytest_cache/", "sources/")
ALLOWED_SUFFIXES = (".pyc",)

FAILURES: list[str] = []


def run(cmd: list[str] | str, cwd: Path, label: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    shell = isinstance(cmd, str)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=shell,
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip()
    print(f"--- {label} (exit {proc.returncode}) ---")
    print(output[:4000] or "(no output)")
    return proc.returncode, output


def changed_paths(worktree: Path) -> list[str]:
    """Union of staged and unstaged changes, so the check is retry-idempotent."""
    proc = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    paths = []
    for line in proc.stdout.splitlines():
        if len(line) > 3:
            paths.append(line[3:].strip().strip('"'))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True, type=Path)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--gate", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    args = parser.parse_args()

    worktree = args.worktree.resolve()

    # 1. every owned file must exist
    for rel in OWNED:
        if not (worktree / rel).is_file():
            FAILURES.append(f"owned file was never created: {rel}")
    if FAILURES:
        print("V21 BUILD CHECK FAILED")
        for reason in FAILURES:
            print(f"  - {reason}")
        return 1

    # 2. ownership boundary
    stray = []
    for path in changed_paths(worktree):
        if path in OWNED:
            continue
        if path.startswith(ALLOWED_PREFIXES) or path.endswith(ALLOWED_SUFFIXES):
            continue
        stray.append(path)
    if stray:
        FAILURES.append(
            "worker modified paths outside its declared ownership: "
            + ", ".join(sorted(stray))
        )

    # 3. deterministic regeneration
    code, _ = run(
        "python3 scripts/build_v21_recall_lanes.py --out build/v21_a.json "
        "&& python3 scripts/build_v21_recall_lanes.py --out build/v21_b.json "
        "&& diff build/v21_a.json build/v21_b.json",
        worktree,
        "deterministic regeneration",
    )
    if code != 0:
        FAILURES.append("generator is not deterministic, or it failed to run (see diff above)")

    graph = worktree / "build" / "v21_a.json"
    if not graph.is_file():
        FAILURES.append("generator produced no build/v21_a.json")
    else:
        # 4. the orchestrator-owned gate, not the worker's own validator
        code, _ = run(
            ["python3", str(args.gate), "--graph", str(graph), "--packet", str(args.packet.resolve())],
            worktree,
            "orchestrator graph gate",
        )
        if code != 0:
            FAILURES.append("generated graph failed the orchestrator-owned gate")

    # 5. the worker's own validator must at least run clean on its own output
    code, _ = run(["python3", "scripts/validate_v21.py"], worktree, "worker validator")
    if code != 0:
        FAILURES.append("the worker's own validate_v21.py does not pass on its own graph")

    # 6. scenario suite
    code, _ = run(
        ["python3", "-m", "pytest", "tests/test_v21_scenarios.py", "-q", "-p", "no:cacheprovider"],
        worktree,
        "scenario suite",
    )
    if code != 0:
        FAILURES.append("tests/test_v21_scenarios.py did not pass")

    # 7. export everything worth keeping BEFORE the worktree is removed
    args.export.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(worktree), "add", "--"] + OWNED, check=False, timeout=120)
    patch = subprocess.run(
        ["git", "-C", str(worktree), "diff", "--cached"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    (args.export / "v21_build.patch").write_text(patch.stdout, encoding="utf-8")
    for rel in OWNED:
        source = worktree / rel
        if source.is_file():
            target = args.export / Path(rel).name
            shutil.copy2(source, target)
    if graph.is_file():
        shutil.copy2(graph, args.export / "v21_graph.json")
    exported = sorted(p.name for p in args.export.iterdir())
    print(f"--- exported to {args.export} ---")
    print(", ".join(exported))
    if not patch.stdout.strip():
        FAILURES.append("exported patch is empty; the worker's changes would die with the worktree")

    if FAILURES:
        print("V21 BUILD CHECK FAILED")
        for reason in FAILURES:
            print(f"  - {reason}")
        return 1

    print("V21 BUILD CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
