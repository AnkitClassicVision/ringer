#!/usr/bin/env python3
"""Promote reviewed Mission Fit files with an archive and per-file rollback."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
from datetime import datetime, timezone

FILES = (
    "SKILL.md",
    "references/install-upgrade-protocol.md",
    "references/cross-harness-skill-implant.md",
    "assets/implant-manifest.schema.json",
    "assets/implant-request.template.json",
    "scripts/implant_skill.py",
    "scripts/validate_implant_manifest.py",
    "tests/test_implant_skill.py",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temp_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, stat.S_IMODE(mode))
        os.replace(temp_name, path)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve(strict=True)
    destination = args.destination
    if destination.is_symlink() or not destination.is_dir():
        raise SystemExit("destination must be an existing real directory")
    destination = destination.resolve(strict=True)
    if source == destination:
        raise SystemExit("source and destination must differ")

    for relative in FILES:
        candidate = source / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise SystemExit(f"reviewed source file missing or unsafe: {relative}")

    codex = Path("/home/ankit114/.codex/skills/clean-my-ai-harness-mission-fit")
    gemini = Path("/home/ankit114/.gemini/skills/clean-my-ai-harness-mission-fit")
    for alias in (codex, gemini):
        if not alias.is_symlink() or alias.resolve(strict=True) != destination:
            raise SystemExit(f"shared alias drift: {alias}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.artifacts.mkdir(parents=True, exist_ok=True)
    backup = args.artifacts / f"clean-my-ai-harness-mission-fit-before-implant-{stamp}.tar.gz"
    receipt = args.artifacts / f"clean-my-ai-harness-mission-fit-promotion-{stamp}.json"
    if backup.exists() or receipt.exists():
        raise SystemExit("promotion artifact collision")

    with tarfile.open(backup, "w:gz") as archive:
        archive.add(destination, arcname=destination.name, recursive=True)
    backup_hash = sha256_bytes(backup.read_bytes())

    originals: dict[str, tuple[bool, bytes, int]] = {}
    promoted: dict[str, str] = {}
    try:
        for relative in FILES:
            source_file = source / relative
            target = destination / relative
            if target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_file():
                    raise RuntimeError(f"unsafe existing target: {relative}")
                originals[relative] = (True, target.read_bytes(), target.stat().st_mode)
            else:
                originals[relative] = (False, b"", source_file.stat().st_mode)
            data = source_file.read_bytes()
            atomic_write(target, data, source_file.stat().st_mode)
            promoted[relative] = sha256_bytes(data)

        for relative, expected in promoted.items():
            target = destination / relative
            if target.is_symlink() or not target.is_file():
                raise RuntimeError(f"promoted target missing or unsafe: {relative}")
            if sha256_bytes(target.read_bytes()) != expected:
                raise RuntimeError(f"promoted hash mismatch: {relative}")
    except Exception:
        for relative, (existed, data, mode) in reversed(list(originals.items())):
            target = destination / relative
            if existed:
                atomic_write(target, data, mode)
            elif target.exists() and target.is_file() and not target.is_symlink():
                target.unlink()
        raise

    receipt_data = {
        "schema_version": "1.0.0",
        "destination": str(destination),
        "source": str(source),
        "backup": str(backup),
        "backup_sha256": backup_hash,
        "promoted_files": promoted,
        "file_count": len(promoted),
        "aliases_preserved": [str(codex), str(gemini)],
        "hermes_duplicate_created": False,
    }
    atomic_write(receipt, (json.dumps(receipt_data, indent=2, sort_keys=True) + "\n").encode(), 0o600)
    print(json.dumps({"backup": str(backup), "backup_sha256": backup_hash, "receipt": str(receipt), "file_count": len(promoted)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
