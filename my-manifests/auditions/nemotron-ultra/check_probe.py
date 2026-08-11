#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


script = Path(sys.argv[1] if len(sys.argv) > 1 else "nemotron_probe.py")
if not script.is_file():
    fail(f"missing required script: {script}")
if script.stat().st_size < 100:
    fail(f"script is implausibly small: {script.stat().st_size} bytes")

allowed = {"nemotron_probe.py", "worker.log"}
extra = sorted(p.name for p in Path.cwd().iterdir() if p.is_file() and p.name not in allowed)
if extra:
    fail(f"unexpected files created: {extra}")

valid_input = json.dumps([" Beta ", "alpha", "ALPHA", "", " gamma ", "beta"])
proc = subprocess.run(
    [sys.executable, str(script)],
    input=valid_input,
    text=True,
    capture_output=True,
    timeout=10,
)
if proc.returncode != 0:
    fail(f"valid input exited {proc.returncode}; stderr={proc.stderr.strip()!r}")
parsed: object | None = None
try:
    parsed = json.loads(proc.stdout)
except json.JSONDecodeError as exc:
    fail(f"valid input did not emit JSON: {exc}; stdout={proc.stdout!r}")
expected = {"count": 3, "items": ["alpha", "beta", "gamma"]}
if parsed != expected:
    fail(f"wrong normalization result: expected {expected!r}, got {parsed!r}")

invalid = subprocess.run(
    [sys.executable, str(script)],
    input='{"not":"a list"}',
    text=True,
    capture_output=True,
    timeout=10,
)
if invalid.returncode != 2:
    fail(f"invalid input must exit 2, got {invalid.returncode}; stdout={invalid.stdout!r}; stderr={invalid.stderr!r}")
if "expected a json array" not in invalid.stderr.lower():
    fail(f"invalid-input stderr must explain expected JSON array; stderr={invalid.stderr!r}")

print("PASS: script normalized, trimmed, lowercased, removed empties, deduplicated, sorted, counted, and rejected non-array input")
