#!/usr/bin/env python3
"""Executable check for one platform-diff capture directory.

Completeness always: capture.log ends CAPTURE_COMPLETE for the expected
version, all four JSON artifacts parse, turn2 carries a non-empty
data.assistant_responses list.

--reference additionally asserts the working-baseline behavior (v96): the
turn-2 envelope must contain a concrete MM/DD/2026 date and no unrendered
{{...}} template. A red here means the baseline itself is invalid and the
diff would be meaningless.
"""

import json
import os
import re
import sys


def main():
    args = [a for a in sys.argv[1:] if a != "--reference"]
    reference = "--reference" in sys.argv
    if len(args) != 2:
        print("usage: check_capture.py <capture_dir> <version> [--reference]")
        return 1
    cap_dir, version = args

    failures = []
    log_path = os.path.join(cap_dir, "capture.log")
    try:
        log = open(log_path, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"FAIL: no capture.log: {exc}")
        return 1
    if f"CAPTURE_COMPLETE version={version}" not in log:
        print(f"FAIL: capture did not complete for version {version}; log tail:")
        print("\n".join(log.splitlines()[-8:]))
        return 1

    loaded = {}
    for name in ("graph.json", "create.json", "turn1.json", "turn2.json"):
        path = os.path.join(cap_dir, name)
        try:
            loaded[name] = json.load(open(path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{name} unreadable/invalid JSON: {exc}")

    turn2 = loaded.get("turn2.json")
    said = ""
    if turn2 is not None:
        data = turn2.get("data") or {}
        responses = data.get("assistant_responses")
        if not isinstance(responses, list) or not responses:
            failures.append("turn2 data.assistant_responses missing or empty")
        else:
            said = " | ".join(str(r) for r in responses)
        serialized = json.dumps(turn2)
        templated = "{{" in serialized
        if reference:
            if templated:
                failures.append(f"reference envelope contains unrendered template: {said[:200]}")
            if not re.search(r"\d{2}/\d{2}/2026", serialized):
                failures.append(f"reference turn2 has no concrete 2026 date; said: {said[:200]}")
        else:
            print(f"INFO: unrendered_templates={'yes' if templated else 'no'}")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print(f"PASS: capture v{version} complete; turn2 said: {said[:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
