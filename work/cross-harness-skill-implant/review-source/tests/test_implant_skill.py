from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from implant_skill import (  # noqa: E402
    WorkflowError,
    apply_manifest,
    build_plan,
    inspect_request,
    load_and_validate_manifest,
    plan_hash,
    rollback_manifest,
    tree_sha256,
    validate_contract_artifacts,
    verify_manifest,
)


LEVELS = ("present", "indexed", "loaded", "invoked")


class ImplantWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="implant-tests-")
        self.base = Path(self.temporary.name)
        self.source = self.base / "source" / "demo-skill"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: local test fixture\n---\n\n# Demo\n",
            encoding="utf-8",
        )
        (self.source / "reference.txt").write_text("canonical\n", encoding="utf-8")
        self.adapter_script = self.base / "fake_adapter.py"
        self.adapter_script.write_text(
            "import sys\n"
            "if sys.argv[1] == '--version': print('fake-adapter 1.0'); raise SystemExit(0)\n"
            "if sys.argv[1] == 'fail': print('DISCOVERY_FAILED'); raise SystemExit(9)\n"
            "print(sys.argv[1].upper() + '_OK')\n",
            encoding="utf-8",
        )
        self.backups = self.base / "backups"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def adapter(self, level: str, fail_level: str | None = None) -> dict:
        mode = "fail" if level == fail_level else level
        return {
            "level": level,
            "version_command": [sys.executable, str(self.adapter_script), "--version"],
            "version_regex": r"fake-adapter 1\.0",
            "command": [sys.executable, str(self.adapter_script), mode],
            "success_regex": rf"{level.upper()}_OK",
            "timeout_seconds": 5,
        }

    def request(
        self,
        roots: dict[str, Path],
        *,
        method: str = "link",
        collision: str = "BLOCK",
        rename_to: str | None = None,
        compatibility: str = "compatible",
        minimum_level: str = "invoked",
        fail_level: str | None = None,
    ) -> dict:
        return {
            "schema_version": "1.0.0",
            "implant_id": "local-replay",
            "source": {
                "path": str(self.source),
                "uri": self.source.as_uri(),
                "expected_skill_name": "demo-skill",
            },
            "scope": {
                "goal": "Install one local replay skill",
                "allowed_actions": ["link", "copy", "verify", "rollback"],
                "excluded_expansions": [
                    "remote rollout",
                    "repository migration",
                    "control plane",
                    "cron",
                ],
            },
            "compatibility": {
                "status": compatibility,
                "blocking_reasons": (
                    [] if compatibility == "compatible" else ["runtime is incompatible"]
                ),
            },
            "targets": [
                {
                    "surface": surface,
                    "root": str(root),
                    "destination_name": "demo-skill",
                    "ownership": f"{surface}-runtime",
                    "method": method,
                    "collision_action": collision,
                    "rename_to": rename_to,
                    "minimum_discovery_level": minimum_level,
                    "discovery_adapters": [
                        self.adapter(level, fail_level)
                        for level in ("indexed", "loaded", "invoked")
                    ],
                }
                for surface, root in roots.items()
            ],
            "rollback": {
                "required": True,
                "backup_root_required_for_replace": True,
                "backup_root": str(self.backups),
            },
        }

    def inspect(self, request: dict, name: str) -> tuple[Path, dict]:
        request_path = self.base / f"{name}-request.json"
        manifest_path = self.base / f"{name}-manifest.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        inspect_request(request_path, manifest_path)
        return manifest_path, load_and_validate_manifest(manifest_path)

    def assert_error(self, code: str, function, *args) -> None:
        with self.assertRaises(WorkflowError) as caught:
            function(*args)
        self.assertEqual(code, caught.exception.code)

    def test_four_root_link_install_all_discovery_levels_and_sanitized_receipts(self) -> None:
        roots = {
            surface: self.base / "roots" / surface
            for surface in ("hermes", "claude-code", "codex", "gemini")
        }
        for root in roots.values():
            root.mkdir(parents=True)
        manifest_path, manifest = self.inspect(self.request(roots), "four-root")
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        for root in roots.values():
            destination = root / "demo-skill"
            self.assertTrue(destination.is_symlink())
            self.assertTrue(os.path.samefile(destination, self.source))

        verify_manifest(manifest_path, "invoked", [sys.executable])
        verified = load_and_validate_manifest(manifest_path)
        self.assertEqual("VERIFIED", verified["status"])
        for surface in roots:
            receipt = verified["receipts"]["targets"][surface]
            for level in LEVELS:
                self.assertTrue(receipt[level]["passed"])
            self.assertTrue(receipt["integrity"]["passed"])

        serialized = json.dumps(verified["receipts"])
        for forbidden_key in (
            '"stdout"',
            '"stderr"',
            '"output"',
            '"excerpt"',
            '"raw_output"',
        ):
            self.assertNotIn(forbidden_key + ":", serialized)
        hashes = re.findall(r'"(?:command|stdout|stderr)_sha256": "([0-9a-f]{64})"', serialized)
        self.assertGreaterEqual(len(hashes), 3)

        rollback_manifest(manifest_path, verified["plan_hash"])
        for root in roots.values():
            self.assertFalse(os.path.lexists(root / "demo-skill"))
        with mock.patch("builtins.print") as printed:
            rollback_manifest(manifest_path, verified["plan_hash"])
        printed.assert_called_once_with("ALREADY_ROLLED_BACK")

    def test_narrower_verify_clears_stale_higher_level_receipts(self) -> None:
        root = self.base / "narrow-verify"
        root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}, minimum_level="loaded"),
            "narrow-verify",
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))

        verify_manifest(manifest_path, "invoked", [sys.executable])
        invoked = load_and_validate_manifest(manifest_path)
        self.assertTrue(invoked["receipts"]["targets"]["hermes"]["invoked"]["passed"])

        verify_manifest(manifest_path, "loaded", [sys.executable])
        loaded = load_and_validate_manifest(manifest_path)
        invoked_receipt = loaded["receipts"]["targets"]["hermes"]["invoked"]
        self.assertEqual("VERIFIED", loaded["status"])
        self.assertFalse(invoked_receipt["passed"])
        self.assertEqual("NOT_RUN", invoked_receipt["status"])
        self.assertIsNone(invoked_receipt["version"])
        self.assertIsNone(invoked_receipt["discovery"])

    def test_contract_artifacts_match_runtime_contract(self) -> None:
        schema_path = REPO / "assets" / "implant-manifest.schema.json"
        template_path = REPO / "assets" / "implant-request.template.json"
        validate_contract_artifacts(schema_path, template_path)

    def test_contract_rejects_weakened_path_state_schema(self) -> None:
        schema_path = REPO / "assets" / "implant-manifest.schema.json"
        template_path = REPO / "assets" / "implant-request.template.json"
        weakened = json.loads(schema_path.read_text(encoding="utf-8"))
        weakened["$defs"]["pathState"].pop("allOf")
        weakened_path = self.base / "weakened-schema.json"
        weakened_path.write_text(json.dumps(weakened), encoding="utf-8")

        self.assert_error(
            "SCHEMA_PARITY_MISMATCH",
            validate_contract_artifacts,
            weakened_path,
            template_path,
        )

    def test_contract_rejects_drifted_request_template(self) -> None:
        schema_path = REPO / "assets" / "implant-manifest.schema.json"
        template_path = REPO / "assets" / "implant-request.template.json"
        drifted = json.loads(template_path.read_text(encoding="utf-8"))
        drifted["rollback"].pop("backup_root")
        drifted_path = self.base / "drifted-template.json"
        drifted_path.write_text(json.dumps(drifted), encoding="utf-8")

        self.assert_error(
            "TEMPLATE_PARITY_MISMATCH",
            validate_contract_artifacts,
            schema_path,
            drifted_path,
        )

    def test_shipped_template_materializes_into_a_valid_plan(self) -> None:
        template_path = REPO / "assets" / "implant-request.template.json"
        request = json.loads(template_path.read_text(encoding="utf-8"))
        root = self.base / "template-root"
        root.mkdir()
        request["source"] = {
            "path": str(self.source),
            "uri": self.source.as_uri(),
            "expected_skill_name": "demo-skill",
        }
        request["targets"][0].update(
            {
                "surface": "hermes",
                "root": str(root),
                "destination_name": "demo-skill",
                "ownership": "test-runtime",
                "discovery_adapters": [
                    self.adapter(level) for level in ("indexed", "loaded", "invoked")
                ],
            }
        )
        request["rollback"]["backup_root"] = str(self.backups)

        plan = build_plan(request)
        self.assertEqual(str(self.source), plan["source"]["path"])
        self.assertEqual(str(root / "demo-skill"), plan["targets"][0]["destination"])

    def test_inspect_rejects_source_target_overlap_without_writing_manifest(self) -> None:
        cases = []

        same_replace = self.request(
            {"same-replace": self.source.parent}, collision="REPLACE"
        )
        cases.append(("same-replace", same_replace))

        same_rename = self.request(
            {"same-rename": self.source.parent},
            collision="RENAME",
            rename_to="demo-skill-v2",
        )
        cases.append(("same-rename", same_rename))

        ancestor = self.request(
            {"ancestor": self.source.parent.parent}, collision="REPLACE"
        )
        ancestor["targets"][0]["destination_name"] = self.source.parent.name
        cases.append(("ancestor", ancestor))

        descendant = self.request({"descendant": self.source})
        cases.append(("descendant", descendant))

        source_hash = tree_sha256(self.source)
        for name, request in cases:
            request_path = self.base / f"{name}-request.json"
            manifest_path = self.base / f"{name}-manifest.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            self.assert_error(
                "SOURCE_TARGET_OVERLAP",
                inspect_request,
                request_path,
                manifest_path,
            )
            self.assertFalse(manifest_path.exists())
        self.assertEqual(source_hash, tree_sha256(self.source))

    def test_manifest_validation_rejects_source_target_overlap(self) -> None:
        root = self.base / "manifest-overlap-root"
        root.mkdir()
        manifest_path, _ = self.inspect(
            self.request({"hermes": root}), "manifest-overlap"
        )
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        target = raw["plan"]["targets"][0]
        target["root"] = str(self.source.parent)
        target["destination"] = str(self.source)
        target["effective_destination"] = str(self.source)
        target["prior_state"] = {
            "path": str(self.source),
            "exists": True,
            "kind": "directory",
            "tree_sha256": tree_sha256(self.source),
        }
        raw["plan_hash"] = plan_hash(raw["plan"])
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")

        self.assert_error(
            "SOURCE_TARGET_OVERLAP", load_and_validate_manifest, manifest_path
        )

    def test_presence_does_not_mask_index_failure_and_allowlist_fails_closed(self) -> None:
        red_root = self.base / "red-root"
        red_root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"hermes": red_root}, fail_level="indexed"), "red"
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        self.assert_error(
            "DISCOVERY_FAILED", verify_manifest, manifest_path, "indexed", [sys.executable]
        )
        red = load_and_validate_manifest(manifest_path)["receipts"]["targets"]["hermes"]
        self.assertTrue(red["present"]["passed"])
        self.assertFalse(red["indexed"]["passed"])

        allow_root = self.base / "allow-root"
        allow_root.mkdir()
        allow_path, allow_manifest = self.inspect(
            self.request({"codex": allow_root}, minimum_level="indexed"), "allow"
        )
        apply_manifest(allow_path, allow_manifest["plan_hash"], str(self.backups))
        self.assert_error(
            "EXECUTABLE_NOT_ALLOWED", verify_manifest, allow_path, "indexed", []
        )

    def test_all_collision_actions_and_rollback(self) -> None:
        for action, code in (
            ("BLOCK", "COLLISION_BLOCKED"),
            ("MERGE", "MERGE_REQUIRES_HUMAN"),
        ):
            root = self.base / action.lower()
            existing = root / "demo-skill"
            existing.mkdir(parents=True)
            marker = existing / "marker.txt"
            marker.write_text(action, encoding="utf-8")
            path, manifest = self.inspect(
                self.request({"hermes": root}, collision=action), action.lower()
            )
            self.assert_error(
                code, apply_manifest, path, manifest["plan_hash"], str(self.backups)
            )
            self.assertEqual(action, marker.read_text(encoding="utf-8"))

        keep_root = self.base / "keep"
        keep_root.mkdir()
        (keep_root / "demo-skill").symlink_to(self.source, target_is_directory=True)
        keep_path, keep_manifest = self.inspect(
            self.request({"hermes": keep_root}, collision="KEEP"), "keep"
        )
        apply_manifest(keep_path, keep_manifest["plan_hash"], str(self.backups))
        rollback_manifest(keep_path, keep_manifest["plan_hash"])
        self.assertTrue(os.path.samefile(keep_root / "demo-skill", self.source))

        rename_root = self.base / "rename"
        original = rename_root / "demo-skill"
        original.mkdir(parents=True)
        (original / "marker.txt").write_text("original", encoding="utf-8")
        rename_path, rename_manifest = self.inspect(
            self.request(
                {"claude-code": rename_root},
                collision="RENAME",
                rename_to="demo-skill-v2",
            ),
            "rename",
        )
        apply_manifest(rename_path, rename_manifest["plan_hash"], str(self.backups))
        self.assertTrue((rename_root / "demo-skill-v2").is_symlink())
        rollback_manifest(rename_path, rename_manifest["plan_hash"])
        self.assertFalse(os.path.lexists(rename_root / "demo-skill-v2"))
        self.assertEqual("original", (original / "marker.txt").read_text(encoding="utf-8"))

        replace_root = self.base / "replace"
        replaced = replace_root / "demo-skill"
        replaced.mkdir(parents=True)
        (replaced / "old.txt").write_text("restore", encoding="utf-8")
        replace_path, replace_manifest = self.inspect(
            self.request({"gemini": replace_root}, collision="REPLACE"), "replace"
        )
        apply_manifest(replace_path, replace_manifest["plan_hash"], str(self.backups))
        self.assertTrue(replaced.is_symlink())
        rollback_manifest(replace_path, replace_manifest["plan_hash"])
        self.assertEqual("restore", (replaced / "old.txt").read_text(encoding="utf-8"))

    def test_copy_drift_and_incompatible_framework_remain_red(self) -> None:
        copy_root = self.base / "copy"
        copy_root.mkdir()
        copy_path, copy_manifest = self.inspect(
            self.request(
                {"gemini": copy_root}, method="copy", minimum_level="present"
            ),
            "copy",
        )
        apply_manifest(copy_path, copy_manifest["plan_hash"], str(self.backups))
        (copy_root / "demo-skill" / "reference.txt").write_text("drift\n", encoding="utf-8")
        self.assert_error(
            "INTEGRITY_FAILED", verify_manifest, copy_path, "present", []
        )
        copy_receipt = load_and_validate_manifest(copy_path)["receipts"]["targets"]["gemini"]
        self.assertTrue(copy_receipt["present"]["passed"])
        self.assertFalse(copy_receipt["integrity"]["passed"])

        incompatible_root = self.base / "incompatible"
        incompatible_root.mkdir()
        incompatible_path, incompatible = self.inspect(
            self.request(
                {"hermes": incompatible_root}, compatibility="incompatible"
            ),
            "incompatible",
        )
        self.assert_error(
            "INCOMPATIBLE_FRAMEWORK",
            apply_manifest,
            incompatible_path,
            incompatible["plan_hash"],
            str(self.backups),
        )
        self.assertFalse(os.path.lexists(incompatible_root / "demo-skill"))

    def test_copy_method_rejects_a_canonical_symlink_substitute(self) -> None:
        root = self.base / "copy-kind"
        root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"codex": root}, method="copy", minimum_level="present"),
            "copy-kind",
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        destination = root / "demo-skill"
        shutil.rmtree(destination)
        destination.symlink_to(self.source, target_is_directory=True)

        self.assert_error(
            "INTEGRITY_FAILED", verify_manifest, manifest_path, "present", []
        )
        receipt = load_and_validate_manifest(manifest_path)["receipts"]["targets"]["codex"]
        self.assertFalse(receipt["integrity"]["passed"])
        self.assertEqual("copy", receipt["integrity"]["method"])

    def test_missing_allowed_executable_persists_sanitized_failure(self) -> None:
        root = self.base / "missing-executable"
        root.mkdir()
        missing = str(self.base / "not-installed-native-cli")
        request = self.request({"hermes": root}, minimum_level="indexed")
        indexed = request["targets"][0]["discovery_adapters"][0]
        indexed["version_command"][0] = missing
        indexed["command"][0] = missing
        manifest_path, manifest = self.inspect(request, "missing-executable")
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))

        self.assert_error(
            "EXECUTABLE_NOT_FOUND", verify_manifest, manifest_path, "indexed", [missing]
        )
        failed = load_and_validate_manifest(manifest_path)
        receipt = failed["receipts"]["targets"]["hermes"]["indexed"]
        self.assertEqual("EXECUTABLE_NOT_FOUND", receipt["status"])
        self.assertEqual("EXECUTABLE_NOT_FOUND", receipt["version"]["status"])
        serialized = json.dumps(receipt)
        self.assertNotIn("not-installed-native-cli", serialized)
        self.assertNotIn("exception", serialized.lower())

    def test_apply_rejects_backup_root_different_from_sealed_plan(self) -> None:
        root = self.base / "backup-root-mismatch"
        root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}), "backup-root-mismatch"
        )
        self.assertEqual(str(self.backups), manifest["plan"]["rollback"]["backup_root"])

        wrong = self.base / "wrong-backups"
        self.assert_error(
            "BACKUP_ROOT_MISMATCH",
            apply_manifest,
            manifest_path,
            manifest["plan_hash"],
            str(wrong),
        )
        self.assertFalse(os.path.lexists(root / "demo-skill"))
        self.assertFalse(os.path.lexists(wrong))

    def test_apply_rejects_symlinked_backup_ancestor(self) -> None:
        root = self.base / "backup-ancestor-root"
        destination = root / "demo-skill"
        destination.mkdir(parents=True)
        (destination / "old.txt").write_text("preserve", encoding="utf-8")
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}, collision="REPLACE"),
            "backup-ancestor",
        )
        redirected = self.base / "redirected-backups"
        redirected.mkdir()
        self.backups.mkdir()
        (self.backups / "local-replay").symlink_to(
            redirected, target_is_directory=True
        )

        self.assert_error(
            "BACKUP_PATH_INVALID",
            apply_manifest,
            manifest_path,
            manifest["plan_hash"],
            str(self.backups),
        )
        self.assertEqual("preserve", (destination / "old.txt").read_text(encoding="utf-8"))
        self.assertEqual([], list(redirected.iterdir()))

    def test_target_root_ancestor_drift_stops_apply_and_rollback(self) -> None:
        apply_parent = self.base / "apply-root-parent"
        apply_root = apply_parent / "root"
        apply_root.mkdir(parents=True)
        apply_path, apply_manifest_data = self.inspect(
            self.request({"hermes": apply_root}), "apply-root-drift"
        )
        shutil.rmtree(apply_parent)
        redirected_parent = self.base / "apply-root-redirect"
        (redirected_parent / "root").mkdir(parents=True)
        apply_parent.symlink_to(redirected_parent, target_is_directory=True)

        self.assert_error(
            "TARGET_ROOT_NOT_FOUND",
            apply_manifest,
            apply_path,
            apply_manifest_data["plan_hash"],
            str(self.backups),
        )
        self.assertFalse(os.path.lexists(redirected_parent / "root" / "demo-skill"))

        rollback_parent = self.base / "rollback-root-parent"
        rollback_root = rollback_parent / "root"
        rollback_root.mkdir(parents=True)
        rollback_path, rollback_data = self.inspect(
            self.request({"codex": rollback_root}), "rollback-root-drift"
        )
        apply_manifest(rollback_path, rollback_data["plan_hash"], str(self.backups))
        moved_parent = self.base / "rollback-root-moved"
        rollback_parent.rename(moved_parent)
        rollback_parent.symlink_to(moved_parent, target_is_directory=True)

        self.assert_error(
            "TARGET_ROOT_DRIFT",
            rollback_manifest,
            rollback_path,
            rollback_data["plan_hash"],
        )
        installed = moved_parent / "root" / "demo-skill"
        self.assertTrue(installed.is_symlink())
        self.assertTrue(os.path.samefile(installed, self.source))

    def test_rollback_target_drift_preserves_human_changed_directory(self) -> None:
        root = self.base / "rollback-drift"
        root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}), "rollback-drift"
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        destination = root / "demo-skill"
        destination.unlink()
        destination.mkdir()
        human_change = destination / "human-change.txt"
        human_change.write_text("preserve\n", encoding="utf-8")

        self.assert_error(
            "ROLLBACK_TARGET_DRIFT",
            rollback_manifest,
            manifest_path,
            manifest["plan_hash"],
        )
        self.assertEqual("preserve\n", human_change.read_text(encoding="utf-8"))
        self.assertEqual("APPLIED", load_and_validate_manifest(manifest_path)["status"])

    def test_rollback_failure_restores_all_targets_and_backups_then_retries(self) -> None:
        roots = {
            "hermes": self.base / "rollback-transaction" / "hermes",
            "codex": self.base / "rollback-transaction" / "codex",
        }
        for surface, root in roots.items():
            destination = root / "demo-skill"
            destination.mkdir(parents=True)
            (destination / "old.txt").write_text(surface, encoding="utf-8")
        manifest_path, manifest = self.inspect(
            self.request(roots, collision="REPLACE"), "rollback-transaction"
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        real_move = shutil.move
        calls = 0

        def fail_second_move(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected rollback move failure")
            return real_move(*args, **kwargs)

        with mock.patch("implant_skill.shutil.move", side_effect=fail_second_move):
            self.assert_error(
                "ROLLBACK_FAILED",
                rollback_manifest,
                manifest_path,
                manifest["plan_hash"],
            )

        for surface, root in roots.items():
            destination = root / "demo-skill"
            backup = self.backups / "local-replay" / surface / "demo-skill"
            self.assertTrue(destination.is_symlink())
            self.assertTrue(os.path.samefile(destination, self.source))
            self.assertEqual(surface, (backup / "old.txt").read_text(encoding="utf-8"))
        self.assertEqual("APPLIED", load_and_validate_manifest(manifest_path)["status"])

        rollback_manifest(manifest_path, manifest["plan_hash"])
        for surface, root in roots.items():
            self.assertEqual(
                surface,
                (root / "demo-skill" / "old.txt").read_text(encoding="utf-8"),
            )

    def test_failed_compensation_preserves_recoverable_staging(self) -> None:
        root = self.base / "rollback-compensation" / "hermes"
        destination = root / "demo-skill"
        destination.mkdir(parents=True)
        (destination / "old.txt").write_text("original", encoding="utf-8")
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}, collision="REPLACE"),
            "rollback-compensation",
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        real_move = shutil.move
        calls = 0

        def fail_forward_and_compensation(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls in {2, 3}:
                raise OSError("injected move failure")
            return real_move(*args, **kwargs)

        with mock.patch(
            "implant_skill.shutil.move", side_effect=fail_forward_and_compensation
        ):
            self.assert_error(
                "TRANSACTION_RESTORE_FAILED",
                rollback_manifest,
                manifest_path,
                manifest["plan_hash"],
            )

        staging = self.backups / (
            ".rollback-staging-" + manifest["plan_hash"].removeprefix("sha256:")
        )
        staged_target = staging / "hermes" / "installed-target"
        self.assertTrue(staged_target.is_symlink())
        self.assertTrue(os.path.samefile(staged_target, self.source))
        backup = self.backups / "local-replay" / "hermes" / "demo-skill"
        self.assertEqual("original", (backup / "old.txt").read_text(encoding="utf-8"))

    def test_rollback_backup_drift_preserves_installed_target(self) -> None:
        root = self.base / "rollback-backup-drift"
        destination = root / "demo-skill"
        destination.mkdir(parents=True)
        (destination / "old.txt").write_text("original", encoding="utf-8")
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}, collision="REPLACE"),
            "rollback-backup-drift",
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        backup = self.backups / "local-replay" / "hermes" / "demo-skill"
        (backup / "old.txt").write_text("human change", encoding="utf-8")

        self.assert_error(
            "ROLLBACK_BACKUP_DRIFT",
            rollback_manifest,
            manifest_path,
            manifest["plan_hash"],
        )
        self.assertTrue(destination.is_symlink())
        self.assertTrue(os.path.samefile(destination, self.source))
        self.assertEqual("human change", (backup / "old.txt").read_text(encoding="utf-8"))
        self.assertEqual("APPLIED", load_and_validate_manifest(manifest_path)["status"])

    def test_rollback_cleanup_failure_is_recorded_and_retryable(self) -> None:
        root = self.base / "rollback-cleanup"
        root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}), "rollback-cleanup"
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        real_rmtree = shutil.rmtree
        calls = 0

        def fail_first_cleanup(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("injected staging cleanup failure")
            return real_rmtree(*args, **kwargs)

        with mock.patch("implant_skill.shutil.rmtree", side_effect=fail_first_cleanup):
            self.assert_error(
                "ROLLBACK_CLEANUP_FAILED",
                rollback_manifest,
                manifest_path,
                manifest["plan_hash"],
            )
        pending = load_and_validate_manifest(manifest_path)
        self.assertEqual("ROLLED_BACK", pending["status"])
        self.assertEqual(
            "CLEANUP_FAILED", pending["receipts"]["rollback"]["cleanup"]["status"]
        )
        self.assertFalse(os.path.lexists(root / "demo-skill"))

        with mock.patch("builtins.print") as printed:
            rollback_manifest(manifest_path, manifest["plan_hash"])
        printed.assert_called_once_with("ALREADY_ROLLED_BACK")
        cleaned = load_and_validate_manifest(manifest_path)
        self.assertTrue(cleaned["receipts"]["rollback"]["cleanup"]["passed"])
        self.assertEqual(
            "CLEANED", cleaned["receipts"]["rollback"]["cleanup"]["status"]
        )

    def test_rollback_cleanup_rejects_a_tampered_staging_path(self) -> None:
        root = self.base / "rollback-cleanup-receipt"
        root.mkdir()
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}), "rollback-cleanup-receipt"
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        real_rmtree = shutil.rmtree

        with mock.patch("implant_skill.shutil.rmtree", side_effect=OSError("cleanup")):
            self.assert_error(
                "ROLLBACK_CLEANUP_FAILED",
                rollback_manifest,
                manifest_path,
                manifest["plan_hash"],
            )

        pending = json.loads(manifest_path.read_text(encoding="utf-8"))
        approved_staging = pending["receipts"]["rollback"]["cleanup"]["staging_path"]
        unrelated = self.backups / (
            ".rollback-staging-" + manifest["plan_hash"].removeprefix("sha256:") + "-other"
        )
        unrelated.mkdir()
        marker = unrelated / "preserve.txt"
        marker.write_text("preserve", encoding="utf-8")
        pending["receipts"]["rollback"]["cleanup"]["staging_path"] = str(unrelated)
        manifest_path.write_text(json.dumps(pending), encoding="utf-8")

        self.assert_error(
            "ROLLBACK_RECEIPT_INVALID",
            rollback_manifest,
            manifest_path,
            manifest["plan_hash"],
        )
        self.assertEqual("preserve", marker.read_text(encoding="utf-8"))

        pending["receipts"]["rollback"]["cleanup"]["staging_path"] = approved_staging
        manifest_path.write_text(json.dumps(pending), encoding="utf-8")
        with mock.patch("implant_skill.shutil.rmtree", side_effect=real_rmtree):
            rollback_manifest(manifest_path, manifest["plan_hash"])

    def test_rollback_cleanup_retries_after_partial_surface_removal(self) -> None:
        roots = {
            "hermes": self.base / "partial-cleanup" / "hermes",
            "codex": self.base / "partial-cleanup" / "codex",
        }
        for root in roots.values():
            root.mkdir(parents=True)
        manifest_path, manifest = self.inspect(
            self.request(roots), "partial-cleanup"
        )
        apply_manifest(manifest_path, manifest["plan_hash"], str(self.backups))
        real_rmtree = shutil.rmtree
        attempted = False

        def remove_one_surface_then_fail(path, *args, **kwargs):
            nonlocal attempted
            if not attempted:
                attempted = True
                real_rmtree(Path(path) / "hermes")
                raise OSError("partial cleanup")
            return real_rmtree(path, *args, **kwargs)

        with mock.patch(
            "implant_skill.shutil.rmtree", side_effect=remove_one_surface_then_fail
        ):
            self.assert_error(
                "ROLLBACK_CLEANUP_FAILED",
                rollback_manifest,
                manifest_path,
                manifest["plan_hash"],
            )

        with mock.patch("builtins.print") as printed:
            rollback_manifest(manifest_path, manifest["plan_hash"])
        printed.assert_called_once_with("ALREADY_ROLLED_BACK")
        cleaned = load_and_validate_manifest(manifest_path)
        self.assertEqual("CLEANED", cleaned["receipts"]["rollback"]["cleanup"]["status"])

    def test_apply_manifest_write_failure_restores_targets_and_backups(self) -> None:
        root = self.base / "apply-write-failure"
        destination = root / "demo-skill"
        destination.mkdir(parents=True)
        (destination / "old.txt").write_text("original", encoding="utf-8")
        manifest_path, manifest = self.inspect(
            self.request({"hermes": root}, collision="REPLACE"),
            "apply-write-failure",
        )

        with mock.patch(
            "implant_skill._write_json",
            side_effect=WorkflowError("MANIFEST_WRITE_FAILED"),
        ):
            self.assert_error(
                "MANIFEST_WRITE_FAILED",
                apply_manifest,
                manifest_path,
                manifest["plan_hash"],
                str(self.backups),
            )

        self.assertFalse(destination.is_symlink())
        self.assertEqual("original", (destination / "old.txt").read_text(encoding="utf-8"))
        backup = self.backups / "local-replay" / "hermes" / "demo-skill"
        self.assertFalse(os.path.lexists(backup))
        self.assertEqual("INSPECTED", load_and_validate_manifest(manifest_path)["status"])

    def test_token_plan_and_scope_are_immutable_before_mutation(self) -> None:
        root = self.base / "immutable"
        root.mkdir()
        manifest_path, manifest = self.inspect(self.request({"codex": root}), "immutable")
        expected_exclusions = [
            "remote rollout",
            "repository migration",
            "control plane",
            "cron",
        ]
        self.assertEqual(expected_exclusions, manifest["plan"]["scope"]["excluded_expansions"])
        self.assert_error(
            "APPROVAL_TOKEN_MISMATCH",
            apply_manifest,
            manifest_path,
            "sha256:" + "0" * 64,
            str(self.backups),
        )
        self.assertFalse(os.path.lexists(root / "demo-skill"))

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        added = dict(raw["plan"]["targets"][0])
        added["surface"] = "unapproved"
        added["root"] = str(self.base / "unapproved")
        added["destination"] = str(self.base / "unapproved" / "demo-skill")
        added["effective_destination"] = added["destination"]
        added["prior_state"] = {
            "path": added["destination"],
            "exists": False,
            "kind": "absent",
        }
        raw["plan"]["targets"].append(added)
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        self.assert_error(
            "PLAN_HASH_MISMATCH",
            apply_manifest,
            manifest_path,
            manifest["plan_hash"],
            str(self.backups),
        )
        self.assertFalse(os.path.lexists(root / "demo-skill"))

    def test_apply_failure_restores_prior_targets_and_validator_rejects_raw_receipts(self) -> None:
        roots = {
            "hermes": self.base / "transaction" / "hermes",
            "codex": self.base / "transaction" / "codex",
        }
        for root in roots.values():
            root.mkdir(parents=True)
        manifest_path, manifest = self.inspect(self.request(roots), "transaction")
        real_symlink = os.symlink
        calls = 0

        def fail_second_symlink(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected target failure")
            return real_symlink(*args, **kwargs)

        with mock.patch("implant_skill.os.symlink", side_effect=fail_second_symlink):
            self.assert_error(
                "APPLY_FAILED",
                apply_manifest,
                manifest_path,
                manifest["plan_hash"],
                str(self.backups),
            )
        for root in roots.values():
            self.assertFalse(os.path.lexists(root / "demo-skill"))

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw["receipts"]["invalid"] = {"stdout": "must-not-be-stored"}
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        self.assert_error("UNSANITIZED_RECEIPT", load_and_validate_manifest, manifest_path)


if __name__ == "__main__":
    unittest.main()
