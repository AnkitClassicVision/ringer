#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

BASELINE = Path("/mnt/d_drive/ringer-work/ob-company-hook-health-fix/source-baseline")
WORK = Path("/mnt/d_drive/ringer-work/ob-company-hook-health-fix/source-work")
ALLOWED = {
    "config/ob_company_daily_watchdog_policy.json",
    "scripts/ob_company_daily_watchdog.py",
    "scripts/verify_ob_company_daily_watchdog.py",
    "tests/test_ob_company_daily_watchdog.py",
    "staff/ob_company_agent_event.py",
    "staff/ob_company_agent_event.sha256",
    "tests/test_ob_company_agent_event.py",
    "staff/ob_company_hook_health.py",
    "tests/test_ob_company_hook_health.py",
    "supabase/functions/ob-company-ingest/index.ts",
    "tests/test_ob_company_ingest_contract.py",
    "staff/README.md",
}
REQUIRED = {
    "config/ob_company_daily_watchdog_policy.json": ("HookHeartbeat", "hook_health"),
    "scripts/ob_company_daily_watchdog.py": ("HookHeartbeat", "hook_health"),
    "staff/ob_company_agent_event.py": ("HookHeartbeat",),
    "staff/ob_company_agent_event.sha256": (),
    "staff/ob_company_hook_health.py": ("HookHeartbeat",),
    "supabase/functions/ob-company-ingest/index.ts": ("HookHeartbeat",),
    "tests/test_ob_company_daily_watchdog.py": ("HookHeartbeat",),
    "tests/test_ob_company_hook_health.py": ("HookHeartbeat",),
    "tests/test_ob_company_ingest_contract.py": ("HookHeartbeat",),
}


def fail(message: str) -> int:
    print(f"WHY: {message}")
    return 1


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path) -> dict[str, tuple[str, int]]:
    found: dict[str, tuple[str, int]] = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if any(part == "__pycache__" for part in path.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            found[rel] = (f"symlink:{os.readlink(path)}", 0)
        elif path.is_file():
            found[rel] = (digest(path), path.stat().st_mode & 0o777)
    return found


def main() -> int:
    notes = Path("notes.md")
    if not notes.is_file() or notes.stat().st_size < 100:
        return fail("notes.md is missing or too short")
    notes_text = notes.read_text(encoding="utf-8", errors="replace")
    for heading in ("# Implementation Notes", "## Files Changed", "## Verification", "## Assumptions"):
        if heading not in notes_text:
            return fail(f"notes.md missing {heading}")

    if not BASELINE.is_dir() or not WORK.is_dir():
        return fail("baseline or work snapshot is missing")
    before = inventory(BASELINE)
    after = inventory(WORK)
    changed = sorted(rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel))
    unexpected = [rel for rel in changed if rel not in ALLOWED]
    if unexpected:
        return fail(f"snapshot changes escaped ownership boundary: {unexpected}")
    if not changed:
        return fail("worker made no implementation changes")

    for rel, needles in REQUIRED.items():
        path = WORK / rel
        if not path.is_file() or path.stat().st_size == 0:
            return fail(f"required implementation file missing or empty: {rel}")
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in needles:
            if needle not in text:
                return fail(f"required marker {needle!r} missing from {rel}")

    helper_digest = digest(WORK / "staff/ob_company_agent_event.py")
    manifest_text = (WORK / "staff/ob_company_agent_event.sha256").read_text(encoding="utf-8").strip()
    manifest_digest = manifest_text.split()[0] if manifest_text else ""
    if manifest_digest != helper_digest:
        return fail("approved helper manifest does not match ob_company_agent_event.py")
    if helper_digest not in (WORK / "supabase/functions/ob-company-ingest/index.ts").read_text(encoding="utf-8"):
        return fail("server heartbeat contract is not bound to the approved helper digest")

    commands = [
        ["python3", "scripts/verify_ob_company_daily_watchdog.py"],
        ["python3", "tests/test_ob_company_daily_watchdog.py"],
        ["python3", "tests/test_ob_company_agent_event.py"],
        ["python3", "tests/test_ob_company_hook_health.py"],
        ["python3", "tests/test_ob_company_ingest_contract.py"],
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for command in commands:
        print(f"RUN: {' '.join(command)}")
        proc = subprocess.run(command, cwd=WORK, env=env, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            print(proc.stdout[-4000:])
            print(proc.stderr[-3000:])
            return fail(f"verification command failed with {proc.returncode}: {' '.join(command)}")
        if proc.stdout.strip():
            print(proc.stdout[-1200:])
        if proc.stderr.strip():
            print(proc.stderr[-800:])

    print(f"PASS: {len(changed)} owned snapshot paths changed; all offline heartbeat/watchdog checks passed")
    print("CHANGED:")
    for rel in changed:
        print(f" - {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
