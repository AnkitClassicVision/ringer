#!/usr/bin/env python3
"""Validate a target-runtime skill invocation receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_QUOTES = {
    "Never treat a path that merely exists as indexed, loaded, or invoked.",
    "Do not invent native Claude Code, Codex, Gemini, or Hermes commands.",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid discovery receipt: {type(exc).__name__}")
    expected_keys = {"runtime", "skill_name", "invoked", "quotes", "tools_used", "error"}
    if set(data) != expected_keys:
        raise SystemExit(f"receipt keys differ: {sorted(data)}")
    if data["runtime"] != args.runtime:
        raise SystemExit("runtime mismatch")
    if data["skill_name"] != "clean-my-ai-harness-mission-fit":
        raise SystemExit("skill name mismatch")
    if data["invoked"] is not True or data["error"] is not None:
        raise SystemExit("runtime did not report successful invocation")
    if data["tools_used"] not in ([], None):
        raise SystemExit("discovery worker used tools beyond artifact creation")
    if set(data["quotes"]) != EXPECTED_QUOTES:
        raise SystemExit("verbatim guardrails do not match the loaded skill")
    print(f"PASS: {args.runtime} invoked clean-my-ai-harness-mission-fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
