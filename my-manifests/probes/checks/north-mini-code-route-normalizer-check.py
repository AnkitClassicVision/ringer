#!/usr/bin/env python3
"""Executable acceptance check for the North Mini Code rookie audition."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def run_case(script: Path, payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        input=payload,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def expect_success(script: Path, payload: object, expected: dict[str, str], label: str) -> None:
    result = run_case(script, json.dumps(payload))
    if result.returncode != 0:
        fail(f"{label} exited {result.returncode}; stderr={result.stderr.strip()!r}")
    try:
        actual = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"{label} did not emit valid JSON: {exc}; stdout={result.stdout!r}")
    if actual != expected:
        fail(f"{label} mismatch; expected={expected!r} actual={actual!r}")
    if result.stdout.count("\n") != 1 or not result.stdout.endswith("\n"):
        fail(f"{label} must emit exactly one JSON line")


def expect_failure(script: Path, payload: str, label: str) -> None:
    result = run_case(script, payload)
    if result.returncode == 0:
        fail(f"{label} unexpectedly succeeded; stdout={result.stdout!r}")
    if not result.stderr.startswith("ERROR:"):
        fail(f"{label} stderr must begin with ERROR:; stderr={result.stderr!r}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: north-mini-code-route-normalizer-check.py PATH_TO_NORMALIZE_ROUTE.py")
    script = Path(sys.argv[1])
    if not script.is_file() or script.stat().st_size == 0:
        fail(f"worker script missing or empty: {script}")

    expect_success(
        script,
        {"task_type": " Docs ", "engine": " OpenCode ", "model": " openrouter/z-ai/glm-5.2 "},
        {"task_type": "docs", "engine": "opencode", "model": "openrouter/z-ai/glm-5.2"},
        "trim-and-normalize",
    )
    expect_success(
        script,
        {"task_type": "PROBE", "engine": "CLAUDE-LEAN"},
        {"task_type": "probe", "engine": "claude-lean", "model": ""},
        "missing-model-default",
    )
    expect_failure(script, json.dumps({"task_type": "docs", "engine": "   "}), "blank-engine")
    expect_failure(script, "not-json", "invalid-json")
    expect_failure(script, json.dumps(["docs", "opencode"]), "non-object")
    expect_failure(script, json.dumps({"task_type": 7, "engine": "opencode"}), "non-string-task-type")
    expect_failure(script, json.dumps({"task_type": "docs", "engine": 7}), "non-string-engine")
    expect_failure(
        script,
        json.dumps({"task_type": "docs", "engine": "opencode", "model": 7}),
        "non-string-model",
    )
    print("PASS: rookie route normalizer satisfied all eight executable cases")


if __name__ == "__main__":
    main()
