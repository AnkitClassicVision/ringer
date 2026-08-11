#!/usr/bin/env python3
"""Independent acceptance check for Cross-Harness Skill Implant v1."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from unittest import mock


LEVELS = ("present", "indexed", "loaded", "invoked")


def fail(message: str) -> None:
    raise AssertionError(message)


def run(argv: list[str], *, expect: int = 0, contains: str | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, text=True, capture_output=True, timeout=60)
    combined = proc.stdout + proc.stderr
    if proc.returncode != expect:
        fail(f"command return code {proc.returncode}, expected {expect}: {argv}\n{combined[-2500:]}")
    if contains and contains not in combined:
        fail(f"command did not report {contains!r}: {argv}\n{combined[-2500:]}")
    return proc


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def adapter(script: Path, level: str, *, fail_level: str | None = None) -> dict:
    mode = "fail" if level == fail_level else level
    return {
        "level": level,
        "version_command": [sys.executable, str(script), "--version"],
        "version_regex": r"fake-adapter 1\.0",
        "command": [sys.executable, str(script), mode],
        "success_regex": rf"{level.upper()}_OK",
        "timeout_seconds": 5,
    }


def request_for(source: Path, roots: dict[str, Path], script: Path, *, method: str = "link", collision: str = "BLOCK", rename_to: str | None = None, compatibility: str = "compatible", minimum_level: str = "invoked", fail_level: str | None = None) -> dict:
    targets = []
    for surface, root in roots.items():
        targets.append(
            {
                "surface": surface,
                "root": str(root),
                "destination_name": "demo-skill",
                "ownership": f"{surface}-runtime-owned",
                "method": method,
                "collision_action": collision,
                "rename_to": rename_to,
                "minimum_discovery_level": minimum_level,
                "discovery_adapters": [
                    adapter(script, level, fail_level=fail_level)
                    for level in ("indexed", "loaded", "invoked")
                ],
            }
        )
    return {
        "schema_version": "1.0.0",
        "implant_id": "acceptance-demo",
        "source": {
            "path": str(source),
            "uri": source.as_uri(),
            "expected_skill_name": "demo-skill",
        },
        "scope": {
            "goal": "Install one demo skill into the declared local roots",
            "allowed_actions": ["link", "copy", "verify", "rollback"],
            "excluded_expansions": ["remote rollout", "repository migration", "control plane", "cron"],
        },
        "compatibility": {
            "status": compatibility,
            "blocking_reasons": [] if compatibility == "compatible" else ["required runtime is unavailable"],
        },
        "targets": targets,
        "rollback": {
            "required": True,
            "backup_root_required_for_replace": True,
            "backup_root": str(source.parents[1] / "backups"),
        },
    }


def cli(repo: Path, *args: str) -> list[str]:
    return [sys.executable, str(repo / "scripts" / "implant_skill.py"), *args]


def load_product(repo: Path):
    path = repo / "scripts" / "implant_skill.py"
    spec = importlib.util.spec_from_file_location("implant_skill_acceptance", path)
    if spec is None or spec.loader is None:
        fail("could not load implant_skill.py for fault injection")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(repo: Path, request: dict, base: Path, name: str) -> tuple[Path, dict]:
    req = base / f"{name}-request.json"
    manifest = base / f"{name}-manifest.json"
    write_json(req, request)
    run(cli(repo, "inspect", "--request", str(req), "--manifest", str(manifest)))
    data = read_json(manifest)
    required = {"schema_version", "plan", "plan_hash", "status", "receipts", "events"}
    if not required.issubset(data):
        fail(f"manifest missing top-level keys: {sorted(required - set(data))}")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", data["plan_hash"]):
        fail("plan_hash is not a sha256 receipt")
    if not re.fullmatch(r"[0-9a-f]{64}", data["plan"]["source"]["tree_sha256"]):
        fail("source tree hash missing")
    run([sys.executable, str(repo / "scripts" / "validate_implant_manifest.py"), str(manifest)])
    return manifest, data


def approval(data: dict) -> str:
    return str(data["plan_hash"])


def assert_no_raw_output(receipts: object) -> None:
    forbidden = {"stdout", "stderr", "output", "excerpt", "raw_output", "raw_stdout", "raw_stderr"}
    stack = [receipts]
    hashes = 0
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            overlap = forbidden.intersection(item)
            if overlap:
                fail(f"receipt leaks raw output fields: {sorted(overlap)}")
            for key, value in item.items():
                if key in {"stdout_sha256", "stderr_sha256", "command_sha256"}:
                    if not re.fullmatch(r"[0-9a-f]{64}", str(value)):
                        fail(f"invalid receipt hash in {key}")
                    hashes += 1
                stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    if hashes < 3:
        fail("sanitized receipts did not contain command/stdout/stderr hashes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    required_files = [
        repo / "scripts" / "implant_skill.py",
        repo / "scripts" / "validate_implant_manifest.py",
        repo / "assets" / "implant-manifest.schema.json",
        repo / "assets" / "implant-request.template.json",
        repo / "references" / "cross-harness-skill-implant.md",
    ]
    for path in required_files:
        if not path.is_file():
            fail(f"required file missing: {path}")
    product = load_product(repo)

    with tempfile.TemporaryDirectory(prefix="ringer-skill-implant-") as tmp:
        base = Path(tmp)
        source = base / "source" / "demo-skill"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("---\nname: demo-skill\ndescription: acceptance fixture\n---\n\n# Demo\n", encoding="utf-8")
        (source / "reference.txt").write_text("canonical\n", encoding="utf-8")
        source_before = hashlib.sha256((source / "SKILL.md").read_bytes() + (source / "reference.txt").read_bytes()).hexdigest()

        fake = base / "fake_adapter.py"
        fake.write_text(
            "import sys\n"
            "if sys.argv[1] == '--version': print('fake-adapter 1.0'); raise SystemExit(0)\n"
            "if sys.argv[1] == 'fail': print('DISCOVERY_FAILED'); raise SystemExit(9)\n"
            "print(sys.argv[1].upper() + '_OK')\n",
            encoding="utf-8",
        )

        # Published schema/template are enforced by the same runtime contract.
        if not hasattr(product, "validate_contract_artifacts"):
            fail("validate_contract_artifacts is missing")
        schema_path = repo / "assets" / "implant-manifest.schema.json"
        template_path = repo / "assets" / "implant-request.template.json"
        product.validate_contract_artifacts(schema_path, template_path)
        weakened_schema = read_json(schema_path)
        weakened_schema["$defs"]["pathState"].pop("allOf", None)
        weakened_path = base / "weakened-schema.json"
        write_json(weakened_path, weakened_schema)
        try:
            product.validate_contract_artifacts(weakened_path, template_path)
        except product.WorkflowError as exc:
            if exc.code != "SCHEMA_PARITY_MISMATCH":
                fail(f"weakened schema returned unexpected code: {exc.code}")
        else:
            fail("weakened pathState schema was accepted")

        roots = {name: base / "roots" / name for name in ("hermes", "claude-code", "codex", "gemini")}
        for root in roots.values():
            root.mkdir(parents=True)

        # Clean link install across four surfaces.
        clean_manifest, clean_data = inspect(repo, request_for(source, roots, fake), base, "clean")
        backups = base / "backups"
        run(
            cli(
                repo,
                "apply",
                "--manifest",
                str(clean_manifest),
                "--approval-token",
                approval(clean_data),
                "--backup-root",
                str(base / "wrong-backups"),
            ),
            expect=1,
            contains="BACKUP_ROOT_MISMATCH",
        )
        if any(os.path.lexists(root / "demo-skill") for root in roots.values()):
            fail("backup-root mismatch mutated a target")
        run(cli(repo, "apply", "--manifest", str(clean_manifest), "--approval-token", approval(clean_data), "--backup-root", str(backups)))
        for root in roots.values():
            dest = root / "demo-skill"
            if not dest.is_symlink() or not os.path.samefile(dest, source):
                fail(f"target is not a canonical link: {dest}")
        run(cli(repo, "verify", "--manifest", str(clean_manifest), "--level", "invoked", "--allow-executable", sys.executable))
        verified = read_json(clean_manifest)
        if verified["status"] != "VERIFIED":
            fail(f"clean manifest not VERIFIED: {verified['status']}")
        for surface in roots:
            target_receipts = verified["receipts"]["targets"][surface]
            for level in LEVELS:
                if not target_receipts[level]["passed"]:
                    fail(f"{surface} did not pass {level}")
            if not target_receipts["integrity"]["passed"]:
                fail(f"{surface} integrity failed")
        assert_no_raw_output(verified["receipts"])
        source_after = hashlib.sha256((source / "SKILL.md").read_bytes() + (source / "reference.txt").read_bytes()).hexdigest()
        if source_before != source_after:
            fail("canonical source changed during apply/verify")

        # A narrower verify must clear stale higher-level discovery receipts.
        downgrade_root = base / "downgrade-root"
        downgrade_root.mkdir()
        downgrade_manifest, downgrade_data = inspect(
            repo,
            request_for(
                source,
                {"hermes": downgrade_root},
                fake,
                minimum_level="loaded",
            ),
            base,
            "downgrade",
        )
        run(
            cli(
                repo,
                "apply",
                "--manifest",
                str(downgrade_manifest),
                "--approval-token",
                approval(downgrade_data),
                "--backup-root",
                str(backups),
            )
        )
        run(
            cli(
                repo,
                "verify",
                "--manifest",
                str(downgrade_manifest),
                "--level",
                "invoked",
                "--allow-executable",
                sys.executable,
            )
        )
        if not read_json(downgrade_manifest)["receipts"]["targets"]["hermes"]["invoked"]["passed"]:
            fail("invoked discovery did not pass before downgrade replay")
        run(
            cli(
                repo,
                "verify",
                "--manifest",
                str(downgrade_manifest),
                "--level",
                "loaded",
                "--allow-executable",
                sys.executable,
            )
        )
        downgraded = read_json(downgrade_manifest)
        invoked_receipt = downgraded["receipts"]["targets"]["hermes"]["invoked"]
        if downgraded["status"] != "VERIFIED" or invoked_receipt["passed"]:
            fail("narrower verify retained a stale invoked pass")
        if invoked_receipt["status"] != "NOT_RUN":
            fail("narrower verify did not mark invoked as NOT_RUN")

        # Source and target paths may not overlap in either direction.
        overlap_requests = [
            (
                "same",
                request_for(
                    source,
                    {"hermes": source.parent},
                    fake,
                    collision="REPLACE",
                ),
            ),
            (
                "rename-same",
                request_for(
                    source,
                    {"claude-code": source.parent},
                    fake,
                    collision="RENAME",
                    rename_to="demo-skill-v2",
                ),
            ),
            (
                "ancestor",
                request_for(
                    source,
                    {"codex": source.parent.parent},
                    fake,
                    collision="REPLACE",
                ),
            ),
            (
                "descendant",
                request_for(source, {"gemini": source}, fake),
            ),
        ]
        overlap_requests[2][1]["targets"][0]["destination_name"] = source.parent.name
        for name, overlap_request in overlap_requests:
            overlap_request_path = base / f"overlap-{name}-request.json"
            overlap_manifest_path = base / f"overlap-{name}-manifest.json"
            write_json(overlap_request_path, overlap_request)
            run(
                cli(
                    repo,
                    "inspect",
                    "--request",
                    str(overlap_request_path),
                    "--manifest",
                    str(overlap_manifest_path),
                ),
                expect=1,
                contains="SOURCE_TARGET_OVERLAP",
            )
            if overlap_manifest_path.exists():
                fail(f"overlap request wrote a manifest: {name}")

        # Plan tampering and wrong approval fail before mutation.
        tamper_root = base / "tamper-root"
        tamper_root.mkdir()
        tamper_manifest, tamper_data = inspect(repo, request_for(source, {"hermes": tamper_root}, fake), base, "tamper")
        run(cli(repo, "apply", "--manifest", str(tamper_manifest), "--approval-token", "sha256:" + "0" * 64, "--backup-root", str(backups)), expect=1, contains="APPROVAL_TOKEN_MISMATCH")
        tampered = read_json(tamper_manifest)
        tampered["plan"]["scope"]["goal"] = "silently expand scope"
        write_json(tamper_manifest, tampered)
        run(cli(repo, "apply", "--manifest", str(tamper_manifest), "--approval-token", approval(tamper_data), "--backup-root", str(backups)), expect=1, contains="PLAN_HASH_MISMATCH")
        if (tamper_root / "demo-skill").exists():
            fail("tampered plan mutated target")

        # Existence-only red and executable allowlist red.
        red_root = base / "red-root"
        red_root.mkdir()
        red_manifest, red_data = inspect(repo, request_for(source, {"hermes": red_root}, fake, fail_level="indexed"), base, "red")
        run(cli(repo, "apply", "--manifest", str(red_manifest), "--approval-token", approval(red_data), "--backup-root", str(backups)))
        run(cli(repo, "verify", "--manifest", str(red_manifest), "--level", "indexed", "--allow-executable", sys.executable), expect=1)
        red_receipts = read_json(red_manifest)["receipts"]["targets"]["hermes"]
        if not red_receipts["present"]["passed"] or red_receipts["indexed"]["passed"]:
            fail("existence-only red case did not remain red")
        allow_root = base / "allow-root"
        allow_root.mkdir()
        allow_manifest, allow_data = inspect(repo, request_for(source, {"hermes": allow_root}, fake, minimum_level="indexed"), base, "allow")
        run(cli(repo, "apply", "--manifest", str(allow_manifest), "--approval-token", approval(allow_data), "--backup-root", str(backups)))
        run(cli(repo, "verify", "--manifest", str(allow_manifest), "--level", "indexed"), expect=1, contains="EXECUTABLE_NOT_ALLOWED")

        # BLOCK and MERGE stop without overwriting.
        for action, marker in (("BLOCK", "COLLISION_BLOCKED"), ("MERGE", "MERGE_REQUIRES_HUMAN")):
            root = base / f"collision-{action.lower()}"
            existing = root / "demo-skill"
            existing.mkdir(parents=True)
            marker_file = existing / "preserve.txt"
            marker_file.write_text(action, encoding="utf-8")
            manifest, data = inspect(repo, request_for(source, {"hermes": root}, fake, collision=action), base, action.lower())
            run(cli(repo, "apply", "--manifest", str(manifest), "--approval-token", approval(data), "--backup-root", str(backups)), expect=1, contains=marker)
            if marker_file.read_text(encoding="utf-8") != action:
                fail(f"{action} overwrote existing destination")

        # KEEP accepts only exact source identity.
        keep_root = base / "keep-root"
        keep_root.mkdir()
        (keep_root / "demo-skill").symlink_to(source, target_is_directory=True)
        keep_manifest, keep_data = inspect(repo, request_for(source, {"hermes": keep_root}, fake, collision="KEEP"), base, "keep")
        run(cli(repo, "apply", "--manifest", str(keep_manifest), "--approval-token", approval(keep_data), "--backup-root", str(backups)))
        if not os.path.samefile(keep_root / "demo-skill", source):
            fail("KEEP changed the approved existing destination")

        # RENAME leaves existing content and creates the declared alternate destination.
        rename_root = base / "rename-root"
        existing = rename_root / "demo-skill"
        existing.mkdir(parents=True)
        (existing / "preserve.txt").write_text("original", encoding="utf-8")
        rename_manifest, rename_data = inspect(repo, request_for(source, {"hermes": rename_root}, fake, collision="RENAME", rename_to="demo-skill-v2"), base, "rename")
        run(cli(repo, "apply", "--manifest", str(rename_manifest), "--approval-token", approval(rename_data), "--backup-root", str(backups)))
        if (existing / "preserve.txt").read_text(encoding="utf-8") != "original" or not (rename_root / "demo-skill-v2").is_symlink():
            fail("RENAME did not preserve original and create alternate")
        run(cli(repo, "rollback", "--manifest", str(rename_manifest), "--approval-token", approval(rename_data)))
        if (rename_root / "demo-skill-v2").exists() or not existing.exists():
            fail("RENAME rollback failed")

        # REPLACE backs up and restores on rollback.
        replace_root = base / "replace-root"
        old = replace_root / "demo-skill"
        old.mkdir(parents=True)
        (old / "old.txt").write_text("restore-me", encoding="utf-8")
        replace_manifest, replace_data = inspect(repo, request_for(source, {"hermes": replace_root}, fake, collision="REPLACE"), base, "replace")
        run(cli(repo, "apply", "--manifest", str(replace_manifest), "--approval-token", approval(replace_data), "--backup-root", str(backups)))
        if not (replace_root / "demo-skill").is_symlink():
            fail("REPLACE did not install canonical link")
        run(cli(repo, "rollback", "--manifest", str(replace_manifest), "--approval-token", approval(replace_data)))
        if not (replace_root / "demo-skill" / "old.txt").is_file():
            fail("REPLACE rollback did not restore backup")

        # Rollback refuses drift instead of deleting a human-changed target.
        rollback_drift_root = base / "rollback-drift-root"
        rollback_drift_root.mkdir()
        rollback_drift_manifest, rollback_drift_data = inspect(
            repo,
            request_for(source, {"hermes": rollback_drift_root}, fake),
            base,
            "rollback-drift",
        )
        run(
            cli(
                repo,
                "apply",
                "--manifest",
                str(rollback_drift_manifest),
                "--approval-token",
                approval(rollback_drift_data),
                "--backup-root",
                str(backups),
            )
        )
        drifted_target = rollback_drift_root / "demo-skill"
        drifted_target.unlink()
        drifted_target.mkdir()
        (drifted_target / "human-change.txt").write_text("preserve\n", encoding="utf-8")
        run(
            cli(
                repo,
                "rollback",
                "--manifest",
                str(rollback_drift_manifest),
                "--approval-token",
                approval(rollback_drift_data),
            ),
            expect=1,
            contains="ROLLBACK_TARGET_DRIFT",
        )
        if (drifted_target / "human-change.txt").read_text(encoding="utf-8") != "preserve\n":
            fail("rollback deleted or changed a drifted human-owned target")

        # A mid-rollback failure restores already-processed targets so retry is safe.
        transaction_roots = {
            "hermes": base / "rollback-transaction" / "hermes",
            "codex": base / "rollback-transaction" / "codex",
        }
        for surface, root in transaction_roots.items():
            destination = root / "demo-skill"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text(surface, encoding="utf-8")
        transaction_manifest, transaction_data = inspect(
            repo,
            request_for(source, transaction_roots, fake, collision="REPLACE"),
            base,
            "rollback-transaction",
        )
        run(
            cli(
                repo,
                "apply",
                "--manifest",
                str(transaction_manifest),
                "--approval-token",
                approval(transaction_data),
                "--backup-root",
                str(backups),
            )
        )
        real_move = product.shutil.move
        move_calls = 0

        def fail_second_restore(*args, **kwargs):
            nonlocal move_calls
            move_calls += 1
            if move_calls == 2:
                raise OSError("injected rollback move failure")
            return real_move(*args, **kwargs)

        with mock.patch.object(product.shutil, "move", side_effect=fail_second_restore):
            try:
                product.rollback_manifest(transaction_manifest, approval(transaction_data))
            except product.WorkflowError as exc:
                if exc.code != "ROLLBACK_FAILED":
                    fail(f"unexpected rollback failure code: {exc.code}")
            else:
                fail("fault-injected rollback unexpectedly succeeded")
        for surface, root in transaction_roots.items():
            destination = root / "demo-skill"
            backup = backups / "acceptance-demo" / surface / "demo-skill"
            if not destination.is_symlink() or not os.path.samefile(destination, source):
                fail(f"failed rollback did not restore installed target: {surface}")
            if not backup.is_dir() or (backup / "old.txt").read_text(encoding="utf-8") != surface:
                fail(f"failed rollback did not restore backup state: {surface}")
        product.rollback_manifest(transaction_manifest, approval(transaction_data))
        for surface, root in transaction_roots.items():
            restored = root / "demo-skill" / "old.txt"
            if restored.read_text(encoding="utf-8") != surface:
                fail(f"retry after failed rollback did not complete: {surface}")

        # Copy parity drift remains red.
        copy_root = base / "copy-root"
        copy_root.mkdir()
        copy_manifest, copy_data = inspect(repo, request_for(source, {"gemini": copy_root}, fake, method="copy", minimum_level="present"), base, "copy")
        run(cli(repo, "apply", "--manifest", str(copy_manifest), "--approval-token", approval(copy_data), "--backup-root", str(backups)))
        (copy_root / "demo-skill" / "reference.txt").write_text("drift\n", encoding="utf-8")
        run(cli(repo, "verify", "--manifest", str(copy_manifest), "--level", "present"), expect=1, contains="INTEGRITY_FAILED")
        copy_receipts = read_json(copy_manifest)["receipts"]["targets"]["gemini"]
        if not copy_receipts["present"]["passed"] or copy_receipts["integrity"]["passed"]:
            fail("copy drift did not separate presence from integrity")
        shutil.rmtree(copy_root / "demo-skill")
        (copy_root / "demo-skill").symlink_to(source, target_is_directory=True)
        run(
            cli(repo, "verify", "--manifest", str(copy_manifest), "--level", "present"),
            expect=1,
            contains="INTEGRITY_FAILED",
        )
        swapped_receipt = read_json(copy_manifest)["receipts"]["targets"]["gemini"]
        if swapped_receipt["integrity"]["passed"]:
            fail("copy-method target accepted a symlink substitute")

        # Missing but explicitly allowed executables fail closed and persist evidence.
        missing_root = base / "missing-executable-root"
        missing_root.mkdir()
        missing_executable = str(base / "not-installed-native-cli")
        missing_request = request_for(
            source,
            {"hermes": missing_root},
            fake,
            minimum_level="indexed",
        )
        indexed = missing_request["targets"][0]["discovery_adapters"][0]
        indexed["version_command"][0] = missing_executable
        indexed["command"][0] = missing_executable
        missing_manifest, missing_data = inspect(
            repo, missing_request, base, "missing-executable"
        )
        run(
            cli(
                repo,
                "apply",
                "--manifest",
                str(missing_manifest),
                "--approval-token",
                approval(missing_data),
                "--backup-root",
                str(backups),
            )
        )
        run(
            cli(
                repo,
                "verify",
                "--manifest",
                str(missing_manifest),
                "--level",
                "indexed",
                "--allow-executable",
                missing_executable,
            ),
            expect=1,
            contains="EXECUTABLE_NOT_FOUND",
        )
        missing_receipt = read_json(missing_manifest)["receipts"]["targets"]["hermes"]["indexed"]
        if missing_receipt["status"] != "EXECUTABLE_NOT_FOUND":
            fail("missing executable did not persist a fail-closed receipt")

        # Incompatible frameworks stop before target mutation.
        incompatible_root = base / "incompatible-root"
        incompatible_root.mkdir()
        incompatible_manifest, incompatible_data = inspect(repo, request_for(source, {"hermes": incompatible_root}, fake, compatibility="incompatible"), base, "incompatible")
        run(cli(repo, "apply", "--manifest", str(incompatible_manifest), "--approval-token", approval(incompatible_data), "--backup-root", str(backups)), expect=1, contains="INCOMPATIBLE_FRAMEWORK")
        if (incompatible_root / "demo-skill").exists():
            fail("incompatible framework mutated target")

        # Clean rollback removes only created links.
        clean_latest = read_json(clean_manifest)
        run(cli(repo, "rollback", "--manifest", str(clean_manifest), "--approval-token", approval(clean_latest)))
        for root in roots.values():
            if (root / "demo-skill").exists() or (root / "demo-skill").is_symlink():
                fail("clean rollback left a target")

    print("PASS: immutable plan, guarded mutations, discovery red case, collisions, parity, rollback, and sanitized receipts verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
