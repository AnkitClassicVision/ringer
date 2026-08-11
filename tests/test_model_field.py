#!/usr/bin/env python3
"""Per-task model routing: the {model} placeholder, model_default, validation."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ringer import (  # noqa: E402
    AppConfig,
    ArtifactConfig,
    EngineConfig,
    EvalConfig,
    Manifest,
    TaskSpec,
    build_worker_command,
    load_engines,
    preflight_engine_bins,
    resolve_effective_model,
    validate_manifest_engines,
)

LONG_SPEC = (
    "Create the requested artifact in the current working directory, keep the change scoped, "
    "and make the check command able to explain any failure clearly."
)
GOOD_CHECK = (
    "test -s output.txt && grep -q 'ready' output.txt || "
    "{ echo 'FAIL: output.txt missing or does not contain ready'; exit 1; }"
)


def harness_engine(model_default: str = "openrouter/z-ai/glm-5.2") -> EngineConfig:
    return EngineConfig(
        name="opencode",
        bin="/usr/local/bin/opencode",
        args_template=("run", "-m", "{model}", "--dir", "{taskdir}", "{spec}"),
        full_access_args=(),
        sandbox_args=(),
        token_regex=None,
        model_default=model_default,
    )


def codex_like_engine(model_default: str = "") -> EngineConfig:
    return EngineConfig(
        name="codex",
        bin="/usr/local/bin/codex",
        args_template=("exec", "{engine_args}", "-C", "{taskdir}", "{spec}"),
        full_access_args=(),
        sandbox_args=(),
        token_regex=None,
        model_default=model_default,
    )


class ModelPlaceholderTests(unittest.TestCase):
    def test_model_default_fills_placeholder(self) -> None:
        cmd = build_worker_command(
            harness_engine(), taskdir=Path("/tmp/t"), spec="do it", full_access=False
        )
        self.assertEqual("openrouter/z-ai/glm-5.2", cmd[cmd.index("-m") + 1])

    def test_task_model_overrides_default(self) -> None:
        cmd = build_worker_command(
            harness_engine(),
            taskdir=Path("/tmp/t"),
            spec="do it",
            full_access=False,
            model="openrouter/moonshotai/kimi-k2.7-code",
        )
        self.assertEqual("openrouter/moonshotai/kimi-k2.7-code", cmd[cmd.index("-m") + 1])

    def test_task_spec_parses_and_validates_model(self) -> None:
        task = TaskSpec.from_obj(
            {
                "key": "a",
                "spec": LONG_SPEC,
                "check": GOOD_CHECK,
                "model": "  openrouter/x  ",
            }
        )
        self.assertEqual("openrouter/x", task.model)
        with self.assertRaisesRegex(ValueError, "model must be a string"):
            TaskSpec.from_obj(
                {"key": "a", "spec": LONG_SPEC, "check": GOOD_CHECK, "model": 5}
            )

    def test_load_engines_reads_model_default(self) -> None:
        engines = load_engines(
            {
                "harness": {
                    "bin": "/usr/local/bin/opencode",
                    "args_template": ["run", "-m", "{model}", "{spec}"],
                    "model_default": "openrouter/z-ai/glm-5.2",
                }
            }
        )
        self.assertEqual("openrouter/z-ai/glm-5.2", engines["harness"].model_default)


class EffectiveModelResolverTests(unittest.TestCase):
    def task(self, *, model: str = "", engine_args: tuple[str, ...] = ()) -> TaskSpec:
        return TaskSpec(
            key="a",
            spec=LONG_SPEC,
            check=GOOD_CHECK,
            engine="codex",
            model=model,
            engine_args=engine_args,
        )

    def test_recognizes_all_supported_engine_arg_selector_forms(self) -> None:
        selectors = (
            (("-m", "gpt-short"), "gpt-short"),
            (("--model", "gpt-long"), "gpt-long"),
            (("--model=gpt-equals",), "gpt-equals"),
            (("-c", "model=gpt-config"), "gpt-config"),
            (("--config", "model=gpt-config-long"), "gpt-config-long"),
            (("--config=model=gpt-config-equals",), "gpt-config-equals"),
        )
        for engine_args, expected in selectors:
            with self.subTest(engine_args=engine_args):
                resolved = resolve_effective_model(
                    self.task(engine_args=engine_args), codex_like_engine()
                )
                self.assertEqual((expected, "engine-args"), (resolved.model, resolved.source))

    def test_malformed_selectors_never_fall_through_to_a_default(self) -> None:
        malformed_cases = (
            ("-m",),
            ("--model",),
            ("--model=",),
            ("-c", "model"),
            ("-c", "model="),
            ("--config", "model"),
            ("--config", "model="),
            ("--config=model",),
            ("--config=model=",),
            ("-m", "--other-option"),
            ("-m", "first", "--model="),
        )
        engine = codex_like_engine(model_default="engine-default")
        for engine_args in malformed_cases:
            with self.subTest(engine_args=engine_args):
                resolved = resolve_effective_model(
                    self.task(engine_args=engine_args), engine
                )
                self.assertEqual(
                    ("", "malformed-engine-args"),
                    (resolved.model, resolved.source),
                )

    def test_precedence_and_source_are_explicit(self) -> None:
        engine = codex_like_engine(model_default="engine-default")

        explicit = resolve_effective_model(
            self.task(model="task-model", engine_args=("--model=engine-arg",)), engine
        )
        last_selector = resolve_effective_model(
            self.task(engine_args=("-m", "first", "-c", "model=last")), engine
        )
        defaulted = resolve_effective_model(self.task(), engine)
        unpinned = resolve_effective_model(self.task(), codex_like_engine())

        self.assertEqual(("task-model", "task-model"), (explicit.model, explicit.source))
        self.assertEqual(("last", "engine-args"), (last_selector.model, last_selector.source))
        self.assertEqual(("engine-default", "engine-default"), (defaulted.model, defaulted.source))
        self.assertEqual(("", "unpinned"), (unpinned.model, unpinned.source))

    def test_codex_selector_is_sent_without_rewriting_model_slug(self) -> None:
        cmd = build_worker_command(
            codex_like_engine(),
            taskdir=Path("/tmp/t"),
            spec="do it",
            full_access=False,
            engine_args=("-c", "model=gpt-5.5"),
        )
        self.assertEqual(["-c", "model=gpt-5.5"], cmd[2:4])


class ModelValidationTests(unittest.TestCase):
    def config(self, engines: dict[str, EngineConfig]) -> AppConfig:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        return AppConfig(
            path=None,
            identity_default=None,
            state_dir=root,
            dashboard_port_base=8787,
            hud_port=8700,
            hud_app_path=None,
            allow_full_access=False,
            eval=EvalConfig(backend="jsonl", jsonl_path=root / "eval.jsonl"),
            engines=engines,
            artifact=ArtifactConfig(
                enabled=False,
                out_template=str(root / "live.html"),
                report_template=str(root / "report.html"),
                index_out=root / "index.html",
            ),
        )

    def manifest(self, task: dict[str, object]) -> Manifest:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Manifest.from_obj(
            {
                "run_name": "model-test",
                "workdir": str(Path(temp.name) / "work"),
                "tasks": [task],
            }
        )

    def base_task(self, **extra: object) -> dict[str, object]:
        task: dict[str, object] = {
            "key": "a",
            "spec": LONG_SPEC,
            "check": GOOD_CHECK,
            "expect_files": ["output.txt"],
            "verified": "output exists with expected content",
        }
        task.update(extra)
        return task

    def test_model_on_non_harness_engine_is_rejected(self) -> None:
        config = self.config({"codex": codex_like_engine()})
        manifest = self.manifest(self.base_task(engine="codex", model="openrouter/x"))
        with self.assertRaisesRegex(ValueError, "silently ignored"):
            validate_manifest_engines(manifest, config)

    def test_harness_without_any_model_is_rejected(self) -> None:
        config = self.config({"opencode": harness_engine(model_default="")})
        manifest = self.manifest(self.base_task(engine="opencode"))
        with self.assertRaisesRegex(ValueError, "needs a model"):
            validate_manifest_engines(manifest, config)

    def test_harness_with_default_or_task_model_is_accepted(self) -> None:
        config = self.config({"opencode": harness_engine("provider/model")})
        validate_manifest_engines(self.manifest(self.base_task(engine="opencode")), config)

        config = self.config({"opencode": harness_engine(model_default="")})
        validate_manifest_engines(
            self.manifest(self.base_task(engine="opencode", model="provider/model")),
            config,
        )

    def test_model_placeholder_engine_rejects_engine_arg_model_selectors(self) -> None:
        config = self.config({"opencode": harness_engine()})
        selectors = (
            ["-m", "openrouter/x"],
            ["--model", "openrouter/x"],
            ["--model=openrouter/x"],
            ["-c", "model=openrouter/x"],
            ["--config", "model=openrouter/x"],
            ["--config=model=openrouter/x"],
        )
        for engine_args in selectors:
            with self.subTest(engine_args=engine_args):
                manifest = self.manifest(
                    self.base_task(engine="opencode", engine_args=engine_args)
                )
                with self.assertRaisesRegex(ValueError, r"\{model\} placeholder.*engine_args"):
                    validate_manifest_engines(manifest, config)

    def test_non_model_config_engine_arg_is_not_treated_as_a_model_selector(self) -> None:
        config = self.config({"codex": codex_like_engine(model_default="engine-default")})
        valid_cases = (
            ["-c", "model_reasoning_effort=high"],
            ["--config", "model_reasoning_effort=high"],
            ["--config=model_reasoning_effort=high"],
        )
        for engine_args in valid_cases:
            with self.subTest(engine_args=engine_args):
                manifest = self.manifest(
                    self.base_task(engine="codex", engine_args=engine_args)
                )
                validate_manifest_engines(manifest, config)

    def test_malformed_codex_config_overrides_are_rejected_without_affecting_other_engines(self) -> None:
        config = self.config({"codex": codex_like_engine(model_default="engine-default")})
        malformed_cases = (
            ["-c"],
            ["--config"],
            ["--config="],
            ["-c", ""],
            ["-c", "--other-option"],
            ["-c", "model"],
            ["--config", "model_reasoning_effort"],
            ["--config=model_reasoning_effort"],
            ["-c", "=high"],
            ["--config==high"],
        )
        for engine_args in malformed_cases:
            with self.subTest(engine_args=engine_args):
                manifest = self.manifest(
                    self.base_task(engine="codex", engine_args=engine_args)
                )
                with self.assertRaisesRegex(ValueError, "malformed -c/--config"):
                    validate_manifest_engines(manifest, config)

        opencode_config = self.config({"opencode": harness_engine("provider/model")})
        opencode_manifest = self.manifest(
            self.base_task(engine="opencode", engine_args=["-c"])
        )
        validate_manifest_engines(opencode_manifest, opencode_config)

    def test_malformed_model_selectors_are_rejected_for_every_engine_shape(self) -> None:
        engine_shapes = (
            ("codex", codex_like_engine(model_default="engine-default")),
            ("opencode", harness_engine()),
        )
        malformed_cases = (
            ["-m"],
            ["--model"],
            ["--model="],
            ["-c", "model"],
            ["-c", "model="],
            ["--config", "model"],
            ["--config", "model="],
            ["--config=model"],
            ["--config=model="],
            ["-m", "--other-option"],
            ["-m", "first", "--model="],
        )
        for engine_name, engine in engine_shapes:
            config = self.config({engine_name: engine})
            for engine_args in malformed_cases:
                with self.subTest(engine=engine_name, engine_args=engine_args):
                    manifest = self.manifest(
                        self.base_task(engine=engine_name, engine_args=engine_args)
                    )
                    with self.assertRaisesRegex(
                        ValueError,
                        r"malformed (?:model selector|-c/--config)",
                    ):
                        validate_manifest_engines(manifest, config)

    def test_preflight_catches_missing_engine_binary(self) -> None:
        broken = EngineConfig(
            name="codex",
            bin="/nonexistent/path/to/codex",
            args_template=("exec", "{spec}"),
            full_access_args=(),
            sandbox_args=(),
            token_regex=None,
        )
        config = self.config({"codex": broken})
        manifest = self.manifest(self.base_task(engine="codex"))
        with self.assertRaisesRegex(ValueError, "binary not found.*npm install -g @openai/codex"):
            preflight_engine_bins(manifest, config)

    def test_preflight_accepts_absolute_and_path_resolved_binaries(self) -> None:
        absolute = EngineConfig(
            name="worker",
            bin=sys.executable,
            args_template=("{spec}",),
            full_access_args=(),
            sandbox_args=(),
            token_regex=None,
        )
        bare = EngineConfig(
            name="shellworker",
            bin="sh",
            args_template=("{spec}",),
            full_access_args=(),
            sandbox_args=(),
            token_regex=None,
        )
        config = self.config({"worker": absolute, "shellworker": bare})
        preflight_engine_bins(self.manifest(self.base_task(engine="worker")), config)
        preflight_engine_bins(self.manifest(self.base_task(engine="shellworker")), config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
