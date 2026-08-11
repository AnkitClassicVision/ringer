#!/usr/bin/env python3
"""Executable check for the lane-39 port onto deployed lane-38 truth.

1. Lane-38 preservation: every line present in the DEPLOYED file but absent
   from the repo-clone base must still be present in the ported file (the
   uncommitted lane-38 work must survive the port byte-for-line).
2. Lane-39 presence: the ported file carries the time-suffix strip and the
   relative-offset block.
3. Executed proof: install the ported file into a fresh copy of the lane-39b
   test tree, run the full pytest suite (clean summary), and run proof_parse
   against it (all phrases including the datetime case).
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

M = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback")
TEST_TREE = M / "workGW39b/gw-datetime-tolerance/gw"
PROOF = M / "workGW39b/gw-datetime-tolerance/proof_parse.py"


def lines(path):
    return set(Path(path).read_text(encoding="utf-8", errors="replace").splitlines())


def main():
    if len(sys.argv) not in (4, 5):
        print("usage: check_port39.py <ported.py> <deployed.py> <clone_base.py> [updated_tests_dir]")
        return 1
    ported_p, deployed_p, base_p = map(Path, sys.argv[1:4])
    updated_tests = Path(sys.argv[4]) if len(sys.argv) == 5 else None
    ported_text = ported_p.read_text(encoding="utf-8", errors="replace")
    failures = []

    lane38_only = lines(deployed_p) - lines(base_p)
    missing = {l for l in lane38_only if l not in lines(ported_p)}
    if missing:
        failures.append(
            f"{len(missing)} lane-38-only lines missing from port (silent rollback); "
            f"sample: {sorted(missing)[:3]}"
        )

    if not re.search(r"re\.sub\(r\"\\s\+\(\?:0\?\[1-9\]", ported_text):
        failures.append("time-suffix strip (lane-39b) absent from ported file")
    if "from (?:today|now)" not in ported_text:
        failures.append("relative-offset block (lane-39) absent from ported file")

    tmp = Path(tempfile.mkdtemp(prefix="port39-"))
    try:
        tree = tmp / "gw"
        shutil.copytree(TEST_TREE, tree)
        if updated_tests is not None and updated_tests.is_dir():
            shutil.copytree(updated_tests, tree, dirs_exist_ok=True)
        shutil.copy(ported_p, tree / "container/bland_gateway.py")
        shutil.copy(PROOF, tmp / "proof_parse.py")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"], cwd=tree,
            capture_output=True, text=True, timeout=600,
            env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        summary = (proc.stdout + proc.stderr).strip().splitlines()[-1] if (proc.stdout + proc.stderr).strip() else ""
        if proc.returncode != 0 or not re.match(r"^\d+ passed", summary):
            failures.append(f"suite not green with ported file (rc={proc.returncode}): {summary[:160]}")
        proof = subprocess.run(
            [sys.executable, "proof_parse.py"], cwd=tmp,
            capture_output=True, text=True, timeout=300,
            env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        out = proof.stdout
        if "PHRASE=08/06/2026 10:30 am DATE=2026-08-06" not in out:
            failures.append(f"proof_parse datetime case failed against port: {out[-200:]}")
        if "PHRASE=2 weeks from today DATE=" not in out:
            failures.append(f"proof_parse relative case failed against port: {out[-200:]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("FAIL: " + " | ".join(failures))
        return 1
    print(f"PASS: lane-39 ported onto deployed lane-38 truth ({len(lane38_only)} lane-38 lines preserved; {summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
