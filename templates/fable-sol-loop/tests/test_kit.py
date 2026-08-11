#!/usr/bin/env python3
"""Focused executable proof for the OAuth-only Fable-to-Sol template kit."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
KIT = Path(__file__).resolve().parents[1]
FIXTURES = KIT / "tests" / "fixtures"
REPO_ROOT = KIT.parents[1]
RINGER_PATH = REPO_ROOT / "ringer.py"
CHECKS = KIT / "checks"
sys.path.insert(0, str(CHECKS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


import lib_packets as packets  # noqa: E402


ringer = load_module("fable_sol_loop_ringer", RINGER_PATH)
sol_status = load_module("fable_sol_loop_status", CHECKS / "validate_sol_status.py")


def safe_env() -> dict[str, str]:
    env = {name: os.environ[name] for name in ("PATH", "LANG", "LC_ALL", "TMPDIR") if name in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


class FableSolLoopKitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_context = tempfile.TemporaryDirectory(prefix="fable-sol-loop-kit-")
        cls.root = Path(cls.temp_context.name)
        cls.source_repo = cls.root / "source-repo"
        cls.source_repo.mkdir()
        cls.git_init(cls.source_repo)
        cls.brief = cls.root / "brief.md"
        cls.brief.write_text(
            "# Curated build brief\n\nCreate and verify the bounded output without changing decision rights or external state.\n",
            encoding="utf-8",
        )
        cls.output = cls.root / "generated-run"
        cls.source_before = cls.non_git_snapshot(cls.source_repo)
        proc = cls.run_process(
            [
                sys.executable,
                str(KIT / "new_run.py"),
                "--project-slug",
                "fixture-project",
                "--source-repo",
                str(cls.source_repo),
                "--owned-path",
                "owned",
                "--owned-path",
                "docs/product-contract.md",
                "--brief",
                str(cls.brief),
                "--output",
                str(cls.output),
            ],
            cwd=cls.root,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"generator setup failed:\n{proc.stdout}\n{proc.stderr}")
        cls.generator_output = proc.stdout + proc.stderr

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_context.cleanup()
        shutil.rmtree(KIT / "tests" / "__pycache__", ignore_errors=True)
        shutil.rmtree(CHECKS / "__pycache__", ignore_errors=True)

    @staticmethod
    def git_init(path: Path) -> None:
        proc = subprocess.run(
            ["git", "init", "-q"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
            env=safe_env(),
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git init failed: {proc.stderr}")

    @staticmethod
    def run_process(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            env=safe_env(),
        )

    @staticmethod
    def non_git_snapshot(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts
        }

    def fixture(self, name: str) -> dict[str, Any]:
        return read_json(FIXTURES / name)

    def make_repo(self, *, paths: dict[str, str] | None = None) -> Path:
        context = tempfile.TemporaryDirectory(prefix="fable-sol-validator-repo-")
        self.addCleanup(context.cleanup)
        repo = Path(context.name)
        self.git_init(repo)
        for relative, content in (paths or {"owned/output.txt": "ready"}).items():
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return repo

    def make_task(self) -> Path:
        context = tempfile.TemporaryDirectory(prefix="fable-sol-validator-task-")
        self.addCleanup(context.cleanup)
        return Path(context.name)

    def run_validator(self, script: str, args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        return self.run_process([sys.executable, str(CHECKS / script), *args], cwd=cwd)

    def assert_failure_with_why(self, proc: subprocess.CompletedProcess[str]) -> None:
        output = proc.stdout + proc.stderr
        self.assertNotEqual(0, proc.returncode, output)
        self.assertIn("WHY:", output)

    def stage_status_case(self, fixture_name: str) -> tuple[Path, Path]:
        task = self.make_task()
        shutil.copy2(FIXTURES / fixture_name, task / "status.json")
        shutil.copy2(FIXTURES / "decision-packet.json", task / "decision-packet.json")
        return task, self.make_repo()

    def write_gated_status(
        self,
        task: Path,
        *,
        status_fixture: str = "status-material-deviation.json",
        decision_fixture: str = "decision-packet.json",
    ) -> None:
        status = self.fixture(status_fixture)
        decision = self.fixture(decision_fixture)
        required, reasons, _rules = sol_status.compute_review_gate(status, decision)
        self.assertTrue(required)
        status["review_required"] = required
        status["review_reasons"] = reasons
        (task / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    def stage_review_case(
        self,
        fixture_name: str,
        *,
        status_fixture: str = "status-material-deviation.json",
        decision_fixture: str = "decision-packet.json",
    ) -> Path:
        task = self.make_task()
        shutil.copy2(FIXTURES / fixture_name, task / "review.json")
        shutil.copy2(FIXTURES / decision_fixture, task / "decision-packet.json")
        self.write_gated_status(task, status_fixture=status_fixture, decision_fixture=decision_fixture)
        (task / "notes.md").write_text("Verified staged round-two notes.\n", encoding="utf-8")
        return task

    def test_01_generator_runs_end_to_end_without_touching_source_repo(self) -> None:
        self.assertIn("PASS: generated OAuth-only", self.generator_output)
        self.assertEqual(self.source_before, self.non_git_snapshot(self.source_repo))
        self.assertTrue((self.output / "checks" / "validate_receipt.py").is_file())
        self.assertTrue((self.output / "rounds" / "01-fable-map" / "fable-map" / "sources" / "brief.md").is_file())
        self.assertTrue((self.output / "rounds" / "03-fable-review" / "fable-review" / "sources" / "answers.md").is_file())
        self.assertTrue((self.output / "rounds" / "04-sol-close" / "sol-close" / "sources" / "README.md").is_file())

    def test_02_generator_refuses_output_inside_source_repo(self) -> None:
        inside = self.source_repo / "forbidden-run-package"
        proc = self.run_process(
            [
                sys.executable,
                str(KIT / "new_run.py"),
                "--project-slug",
                "inside-rejected",
                "--source-repo",
                str(self.source_repo),
                "--owned-path",
                "owned",
                "--brief",
                str(self.brief),
                "--output",
                str(inside),
            ],
            cwd=self.root,
        )
        self.assert_failure_with_why(proc)
        self.assertFalse(inside.exists())

    def test_03_generator_rejects_secret_shaped_curated_input(self) -> None:
        secret_brief = self.root / "secret-brief.md"
        secret_brief.write_text(
            "# Invalid brief\n\nThis fixture contains client_secret=abcdefghijklmnop and must be rejected.\n",
            encoding="utf-8",
        )
        proc = self.run_process(
            [
                sys.executable,
                str(KIT / "new_run.py"),
                "--project-slug",
                "secret-rejected",
                "--source-repo",
                str(self.source_repo),
                "--owned-path",
                "owned",
                "--brief",
                str(secret_brief),
                "--output",
                str(self.root / "secret-output"),
            ],
            cwd=self.root,
        )
        self.assert_failure_with_why(proc)

    def test_generator_refuses_dirty_source_repo(self) -> None:
        dirty_repo = self.root / "dirty-source-repo"
        dirty_repo.mkdir()
        self.git_init(dirty_repo)
        (dirty_repo / "untracked-change.txt").write_text("dirty\n", encoding="utf-8")
        output = self.root / "dirty-source-output"
        proc = self.run_process(
            [
                sys.executable,
                str(KIT / "new_run.py"),
                "--project-slug",
                "dirty-rejected",
                "--source-repo",
                str(dirty_repo),
                "--owned-path",
                "owned",
                "--brief",
                str(self.brief),
                "--output",
                str(output),
            ],
            cwd=self.root,
        )
        self.assert_failure_with_why(proc)
        self.assertIn("source repo is dirty", proc.stdout + proc.stderr)
        self.assertFalse(output.exists())

    def test_04_all_generated_json_parses_and_no_placeholder_remains(self) -> None:
        json_paths = sorted(self.output.rglob("*.json"))
        self.assertGreaterEqual(len(json_paths), 5)
        for path in json_paths:
            with self.subTest(path=path.relative_to(self.output)):
                json.loads(path.read_text(encoding="utf-8"))
        for path in self.output.rglob("*"):
            if path.is_file():
                with self.subTest(path=path.relative_to(self.output)):
                    self.assertNotIn("{{", path.read_text(encoding="utf-8"))

    def test_05_generated_manifests_use_exact_locked_oauth_routes(self) -> None:
        manifests = [read_json(self.output / name) for name in (
            "manifest-round1-fable-map.json",
            "manifest-round2-sol-build.json",
            "manifest-round3-fable-review.json",
            "manifest-round4-sol-close.json",
        )]
        self.assertEqual({"fixture-project-fable-sol-loop"}, {item["run_name"] for item in manifests})
        for manifest in manifests:
            self.assertEqual(1, len(manifest["tasks"]))
            self.assertIs(manifest["tasks"][0]["full_access"], False)
            self.assertTrue(manifest["tasks"][0]["expect_files"])
            self.assertGreater(len(manifest["tasks"][0]["verified"]), 40)
        for index in (0, 2):
            task = manifests[index]["tasks"][0]
            self.assertEqual("claude-lean", task["engine"])
            self.assertEqual("fable", task["model"])
            self.assertNotIn("engine_args", task)
        prefix = ["-c", "model_reasoning_effort=ultra"]
        for index in (1, 3):
            task = manifests[index]["tasks"][0]
            self.assertEqual("codex", task["engine"])
            self.assertEqual("gpt-5.6-sol", task["model"])
            self.assertEqual(prefix, task["engine_args"][:2])
            self.assertTrue(any(item.startswith("sandbox_workspace_write.writable_roots=") for item in task["engine_args"][2:]))

        banned = ("anthropic", "openai", "openrouter", "z.ai", "zai/", "xai/", "ollama", "api key", "api-key", "api_key")
        for name in (
            "manifest-round1-fable-map.json",
            "manifest-round2-sol-build.json",
            "manifest-round3-fable-review.json",
            "manifest-round4-sol-close.json",
        ):
            raw = (self.output / name).read_text(encoding="utf-8").lower()
            for marker in banned:
                self.assertNotIn(marker, raw, f"{name} contains forbidden marker {marker}")

    def test_generator_rejects_poisoned_routes_and_run_name(self) -> None:
        cases = (
            ("alternate-provider-route", "manifest-round1-fable-map.json", lambda manifest: manifest["tasks"][0].update({"engine": "openrouter"}), "forbidden route or credential marker"),
            ("api-key-environment", "manifest-round1-fable-map.json", lambda manifest: manifest["tasks"][0].update({"engine_args": ["ANTHROPIC_API_KEY=forbidden"]}), "forbidden route or credential marker"),
            ("mismatched-run-name", "manifest-round4-sol-close.json", lambda manifest: manifest.update({"run_name": "poisoned-mismatch"}), "do not share one run_name"),
        )
        for case_name, manifest_name, poison, expected in cases:
            with self.subTest(poison=case_name):
                poison_kit = self.root / f"kit-{case_name}"
                shutil.copytree(KIT, poison_kit, ignore=shutil.ignore_patterns("__pycache__"))
                manifest_path = poison_kit / manifest_name
                manifest = read_json(manifest_path)
                poison(manifest)
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                output = self.root / f"output-{case_name}"
                proc = self.run_process(
                    [
                        sys.executable,
                        str(poison_kit / "new_run.py"),
                        "--project-slug",
                        f"poison-{case_name}",
                        "--source-repo",
                        str(self.source_repo),
                        "--owned-path",
                        "owned",
                        "--brief",
                        str(self.brief),
                        "--output",
                        str(output),
                    ],
                    cwd=self.root,
                )
                self.assert_failure_with_why(proc)
                self.assertIn(expected, proc.stdout + proc.stderr)
                self.assertFalse(output.exists())

    def test_06_generated_manifests_parse_and_lint_with_current_ringer_functions(self) -> None:
        self.assertRegex(RINGER_PATH.read_text(encoding="utf-8"), r"max_attempts\s*=\s*2")
        for path in sorted(self.output.glob("manifest-round*.json")):
            with self.subTest(path=path.name):
                manifest = ringer.Manifest.from_path(path)
                self.assertEqual([], ringer.lint_manifest(manifest))
                for task in manifest.tasks:
                    self.assertFalse(ringer.check_cannot_fail(task.check))

    def test_07_readme_and_catalog_contract_terms_exist(self) -> None:
        readme = (KIT / "README.md").read_text(encoding="utf-8")
        for term in ("OAuth", "four-round", "HOLD", "QUESTION", "review_required", "STOP_NO_API_FALLBACK", "probe"):
            self.assertIn(term, readme)
        source_guidance = (KIT / "prompts" / "source-packet-layout.md").read_text(encoding="utf-8")
        generator_source = (KIT / "new_run.py").read_text(encoding="utf-8")
        self.assertIn("Never pass a dirty live checkout directly", readme)
        self.assertIn("Never pass a dirty live checkout directly", source_guidance)
        self.assertIn("has no bypass or operator-attestation flag", readme)
        self.assertNotRegex(generator_source, r"add_argument\([^\n]*(?:operator|attestation)[^\n]*(?:snapshot|bypass)")
        self.assertIn("Dirty source input is never accepted directly", generator_source)
        catalog = (REPO_ROOT / "templates" / "README.md").read_text(encoding="utf-8")
        matching_rows = [line for line in catalog.splitlines() if line.startswith("| `fable-sol-loop` |")]
        self.assertEqual(1, len(matching_rows))
        self.assertTrue(matching_rows[0].endswith("| Blueprint |"))

    def test_08_valid_decision_and_fable_question_packets_pass(self) -> None:
        for fixture_name in ("decision-packet.json", "decision-question.json"):
            with self.subTest(fixture=fixture_name):
                proc = self.run_validator(
                    "validate_decision_packet.py",
                    [str(FIXTURES / fixture_name)],
                    cwd=KIT,
                )
                self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
                self.assertIn("PASS:", proc.stdout)

    def test_09_valid_ready_reexecutes_and_generates_skip_notice(self) -> None:
        task, repo = self.stage_status_case("status-ready.json")
        proc = self.run_validator(
            "validate_sol_status.py",
            ["--packet", "status.json", "--decision", "decision-packet.json", "--repo", str(repo)],
            cwd=task,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        status = read_json(task / "status.json")
        self.assertIs(status["review_required"], False)
        self.assertTrue(status["review_reasons"])
        notice = read_json(task / "skip-notice.json")
        self.assertIs(notice["review_required"], False)
        self.assertEqual(4, len(notice["gate_rules"]))
        self.assertTrue(all(rule["triggered"] is False for rule in notice["gate_rules"]))

    def test_10_valid_hold_is_controlled_pass_with_exit_zero(self) -> None:
        task, repo = self.stage_status_case("status-hold.json")
        proc = self.run_validator(
            "validate_sol_status.py",
            ["--packet", "status.json", "--decision", "decision-packet.json", "--repo", str(repo)],
            cwd=task,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        status = read_json(task / "status.json")
        self.assertEqual("HOLD", status["status"])
        self.assertIs(status["review_required"], True)
        self.assertFalse((task / "skip-notice.json").exists())

    def test_11_review_gate_true_and_false_cases_are_objective(self) -> None:
        decision = self.fixture("decision-packet.json")
        cases = (
            ("status-ready.json", False, None),
            ("status-hold.json", True, "hold_present"),
            ("status-material-deviation.json", True, "owned_path_or_material_deviation"),
            ("status-fable-touch.json", True, "fable_owned_surface_touched"),
        )
        for fixture_name, expected, triggered_rule in cases:
            with self.subTest(fixture=fixture_name):
                required, reasons, rules = sol_status.compute_review_gate(self.fixture(fixture_name), decision)
                self.assertIs(required, expected)
                self.assertTrue(reasons)
                if triggered_rule:
                    self.assertTrue(next(rule for rule in rules if rule["rule"] == triggered_rule)["triggered"])

        outside = self.fixture("status-ready.json")
        outside["diff_summary"]["paths_touched"] = ["outside.txt"]
        outside["diff_summary"]["files_changed"] = 1
        required, _reasons, rules = sol_status.compute_review_gate(outside, decision)
        self.assertTrue(required)
        self.assertTrue(next(rule for rule in rules if rule["rule"] == "owned_path_or_material_deviation")["triggered"])

        unclean = self.fixture("status-ready.json")
        unclean["build_units"][0]["state"] = "PARTIAL"
        unclean["build_units"][0]["verification_result"] = {
            "passed": False,
            "exit_code": None,
            "summary": "The verification was not completed cleanly in this negative gate case.",
        }
        required, _reasons, rules = sol_status.compute_review_gate(unclean, decision)
        self.assertTrue(required)
        self.assertTrue(next(rule for rule in rules if rule["rule"] == "verification_unclean")["triggered"])

    def test_12_approve_revise_and_escalate_fable_reviews_pass(self) -> None:
        for fixture_name in ("review-approve.json", "review-revise.json", "review-escalate.json"):
            with self.subTest(fixture=fixture_name):
                decision_fixture = "decision-question.json" if fixture_name == "review-escalate.json" else "decision-packet.json"
                task = self.stage_review_case(fixture_name, decision_fixture=decision_fixture)
                proc = self.run_validator(
                    "validate_fable_review.py",
                    ["--packet", "review.json", "--status", "status.json", "--decision", "decision-packet.json", "--evidence-root", "."],
                    cwd=task,
                )
                self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)

    def test_review_escalate_without_predeclared_founder_basis(self) -> None:
        task = self.stage_review_case(
            "review-escalate.json",
            status_fixture="status-fable-touch.json",
            decision_fixture="decision-packet.json",
        )
        decision = read_json(task / "decision-packet.json")
        status = read_json(task / "status.json")
        self.assertTrue(all(item["route"] != "founder_taste_strategy_courage_relationship_risk_appetite" for item in decision["unknowns"]))
        self.assertEqual("READY", status["status"])
        self.assertEqual([], status["holds"])
        self.assertEqual([], status["deviations"])
        proc = self.run_validator(
            "validate_fable_review.py",
            ["--packet", "review.json", "--status", "status.json", "--decision", "decision-packet.json", "--evidence-root", "."],
            cwd=task,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("PASS: valid Fable review packet (QUESTION)", proc.stdout)

    def test_13_valid_reviewed_receipt_reexecutes_verification(self) -> None:
        task = self.make_task()
        repo = self.make_repo()
        for source, target in (
            ("receipt.json", "receipt.json"),
            ("decision-packet.json", "decision-packet.json"),
            ("review-revise.json", "review.json"),
        ):
            shutil.copy2(FIXTURES / source, task / target)
        self.write_gated_status(task)
        proc = self.run_validator(
            "validate_receipt.py",
            ["--packet", "receipt.json", "--decision", "decision-packet.json", "--status", "status.json", "--repo", str(repo), "--review", "review.json"],
            cwd=task,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("verification was re-executed", proc.stdout)

    def test_14_valid_skipped_receipt_requires_generated_notice(self) -> None:
        gate_task, repo = self.stage_status_case("status-ready.json")
        gate = self.run_validator(
            "validate_sol_status.py",
            ["--packet", "status.json", "--decision", "decision-packet.json", "--repo", str(repo)],
            cwd=gate_task,
        )
        self.assertEqual(0, gate.returncode, gate.stdout + gate.stderr)
        task = self.make_task()
        for source, target in (
            (FIXTURES / "receipt-skipped.json", task / "receipt.json"),
            (FIXTURES / "decision-packet.json", task / "decision-packet.json"),
            (gate_task / "status.json", task / "status.json"),
            (gate_task / "skip-notice.json", task / "skip-notice.json"),
        ):
            shutil.copy2(source, target)
        proc = self.run_validator(
            "validate_receipt.py",
            ["--packet", "receipt.json", "--decision", "decision-packet.json", "--status", "status.json", "--repo", str(repo), "--skip-notice", "skip-notice.json"],
            cwd=task,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)

        forged = read_json(task / "skip-notice.json")
        forged["gate_rules"][0]["evidence"] = "Hand-authored evidence that does not match deterministic recomputation."
        (task / "forged-skip-notice.json").write_text(json.dumps(forged, indent=2) + "\n", encoding="utf-8")
        rejected = self.run_validator(
            "validate_receipt.py",
            ["--packet", "receipt.json", "--decision", "decision-packet.json", "--status", "status.json", "--repo", str(repo), "--skip-notice", "forged-skip-notice.json"],
            cwd=task,
        )
        self.assert_failure_with_why(rejected)

    def test_15_one_invalid_fixture_per_validator_fails_with_why(self) -> None:
        decision = self.run_validator(
            "validate_decision_packet.py",
            [str(FIXTURES / "decision-invalid.json")],
            cwd=KIT,
        )
        self.assert_failure_with_why(decision)

        status_task, repo = self.stage_status_case("status-invalid.json")
        status = self.run_validator(
            "validate_sol_status.py",
            ["--packet", "status.json", "--decision", "decision-packet.json", "--repo", str(repo)],
            cwd=status_task,
        )
        self.assert_failure_with_why(status)

        review_task = self.stage_review_case("review-invalid.json")
        review = self.run_validator(
            "validate_fable_review.py",
            ["--packet", "review.json", "--status", "status.json", "--decision", "decision-packet.json", "--evidence-root", "."],
            cwd=review_task,
        )
        self.assert_failure_with_why(review)

        receipt_task = self.make_task()
        for source, target in (
            ("receipt-invalid.json", "receipt.json"),
            ("decision-packet.json", "decision-packet.json"),
            ("review-revise.json", "review.json"),
        ):
            shutil.copy2(FIXTURES / source, receipt_task / target)
        self.write_gated_status(receipt_task)
        receipt = self.run_validator(
            "validate_receipt.py",
            ["--packet", "receipt.json", "--decision", "decision-packet.json", "--status", "status.json", "--repo", str(self.make_repo()), "--review", "review.json"],
            cwd=receipt_task,
        )
        self.assert_failure_with_why(receipt)

    def test_16_question_is_allowed_only_in_fable_packets(self) -> None:
        decision = self.run_validator(
            "validate_decision_packet.py",
            [str(FIXTURES / "decision-question.json")],
            cwd=KIT,
        )
        self.assertEqual(0, decision.returncode, decision.stdout + decision.stderr)
        review_task = self.stage_review_case("review-escalate.json", decision_fixture="decision-question.json")
        review = self.run_validator(
            "validate_fable_review.py",
            ["--packet", "review.json", "--status", "status.json", "--decision", "decision-packet.json", "--evidence-root", "."],
            cwd=review_task,
        )
        self.assertEqual(0, review.returncode, review.stdout + review.stderr)
        status_task, repo = self.stage_status_case("status-invalid.json")
        status = self.run_validator(
            "validate_sol_status.py",
            ["--packet", "status.json", "--decision", "decision-packet.json", "--repo", str(repo)],
            cwd=status_task,
        )
        self.assert_failure_with_why(status)

    def test_17_unsafe_authority_is_rejected_before_execution(self) -> None:
        decision = self.run_validator(
            "validate_decision_packet.py",
            [str(FIXTURES / "decision-unsafe-authority.json")],
            cwd=KIT,
        )
        self.assert_failure_with_why(decision)

        task = self.make_task()
        write_capable = self.fixture("decision-packet.json")
        write_capable["implementation_contract"]["build_units"][0]["verification_command"] = (
            "python3 -c \"from pathlib import Path; Path('owned/pwned.txt').write_text('unsafe', encoding='utf-8')\""
        )
        (task / "write-capable.json").write_text(json.dumps(write_capable, indent=2) + "\n", encoding="utf-8")
        write_probe = self.run_validator(
            "validate_decision_packet.py",
            ["write-capable.json"],
            cwd=task,
        )
        self.assert_failure_with_why(write_probe)
        self.assertFalse((task / "owned" / "pwned.txt").exists())

        mutating_repo = self.make_repo(
            paths={
                "owned/output.txt": "ready",
                "test_mutating.py": (
                    "import unittest\n"
                    "from pathlib import Path\n"
                    "class MutationProbe(unittest.TestCase):\n"
                    "    def test_mutates(self):\n"
                    "        Path('owned/mutated.txt').write_text('unsafe', encoding='utf-8')\n"
                ),
            }
        )
        mutating_decision = self.fixture("decision-packet.json")
        mutating_decision["owned_paths"] = ["owned", "test_mutating.py"]
        mutating_decision["fable_owned_surfaces"] = []
        mutating_decision["implementation_contract"]["build_units"][0]["verification_command"] = (
            "python3 -m unittest test_mutating.py"
        )
        mutating_status = self.fixture("status-ready.json")
        mutating_status["build_units"][0]["verification_command"] = "python3 -m unittest test_mutating.py"
        mutating_status["diff_summary"] = {
            "paths_touched": ["owned/output.txt", "test_mutating.py"],
            "files_changed": 2,
            "insertions": 6,
            "deletions": 0,
        }
        (task / "mutating-decision.json").write_text(json.dumps(mutating_decision, indent=2) + "\n", encoding="utf-8")
        (task / "mutating-status.json").write_text(json.dumps(mutating_status, indent=2) + "\n", encoding="utf-8")
        mutation_probe = self.run_validator(
            "validate_sol_status.py",
            ["--packet", "mutating-status.json", "--decision", "mutating-decision.json", "--repo", str(mutating_repo)],
            cwd=task,
        )
        self.assertEqual(0, mutation_probe.returncode, mutation_probe.stdout + mutation_probe.stderr)
        self.assertFalse((mutating_repo / "owned" / "mutated.txt").exists())

        arbitrary_executable = self.fixture("decision-packet.json")
        arbitrary_executable["implementation_contract"]["build_units"][0]["verification_command"] = "uname --all"
        (task / "arbitrary-executable.json").write_text(json.dumps(arbitrary_executable, indent=2) + "\n", encoding="utf-8")
        arbitrary_probe = self.run_validator(
            "validate_decision_packet.py",
            ["arbitrary-executable.json"],
            cwd=task,
        )
        self.assert_failure_with_why(arbitrary_probe)

        affirmative = self.fixture("decision-packet.json")
        affirmative["forbidden_actions"][0] = "Commit changes and push them after verification."
        (task / "affirmative-authority.json").write_text(json.dumps(affirmative, indent=2) + "\n", encoding="utf-8")
        authority_probe = self.run_validator(
            "validate_decision_packet.py",
            ["affirmative-authority.json"],
            cwd=task,
        )
        self.assert_failure_with_why(authority_probe)

        missing_question = self.fixture("decision-question.json")
        del missing_question["question"]
        (task / "missing-founder-question.json").write_text(json.dumps(missing_question, indent=2) + "\n", encoding="utf-8")
        question_probe = self.run_validator(
            "validate_decision_packet.py",
            ["missing-founder-question.json"],
            cwd=task,
        )
        self.assert_failure_with_why(question_probe)

        review_task = self.stage_review_case("review-unsafe-authority.json")
        review = self.run_validator(
            "validate_fable_review.py",
            ["--packet", "review.json", "--status", "status.json", "--decision", "decision-packet.json", "--evidence-root", "."],
            cwd=review_task,
        )
        self.assert_failure_with_why(review)

    def test_18_verification_sandbox_disables_network(self) -> None:
        repo = self.make_repo()
        argv = packets.sandboxed_verification_argv(
            [sys.executable, "-m", "unittest"],
            cwd=repo,
        )
        self.assertEqual("unshare", Path(argv[0]).name)
        self.assertEqual(["--user", "--map-root-user", "--net", "--"], argv[1:5])
        self.assertEqual("bwrap", Path(argv[5]).name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
