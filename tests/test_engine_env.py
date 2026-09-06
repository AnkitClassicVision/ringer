#!/usr/bin/env python3
"""Tests for per-engine environment-variable injection."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ringer  # noqa: E402
from ringer import (  # noqa: E402
    AppConfig,
    ArtifactConfig,
    EngineConfig,
    EvalConfig,
    Manifest,
    RingerRunner,
    SteeringConfig,
    load_engines,
)


def mock_engine(*, with_env: dict[str, str] | None = None) -> EngineConfig:
    return EngineConfig(
        name="mock",
        bin=sys.executable,
        args_template=(str(ROOT / "engines" / "mock_worker.py"), "{spec}"),
        full_access_args=(),
        sandbox_args=(),
        token_regex=None,
        env=with_env,
    )


def make_config(root: Path, engine: EngineConfig) -> AppConfig:
    return AppConfig(
        path=None,
        identity_default=None,
        state_dir=root / "state",
        dashboard_port_base=8787,
        hud_port=8700,
        hud_app_path=None,
        allow_full_access=False,
        eval=EvalConfig(backend="jsonl", jsonl_path=root / "eval.jsonl"),
        engines={"mock": engine},
        artifact=ArtifactConfig(
            enabled=False,
            out_template=str(root / "live.html"),
            report_template=str(root / "report.html"),
            index_out=root / "index.html",
        ),
        steering=SteeringConfig(dir=None),
    )


class EngineEnvConfigTests(unittest.TestCase):
    def test_load_engines_parses_env_table(self) -> None:
        engines = load_engines(
            {
                "mock": {
                    "bin": "mock",
                    "args_template": ["{spec}"],
                    "env": {"FOO": "bar", "BAZ": "qux"},
                }
            }
        )
        self.assertEqual(engines["mock"].env, {"FOO": "bar", "BAZ": "qux"})

    def test_load_engines_rejects_non_string_env_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "env must be a table of string keys to string values"):
            load_engines(
                {
                    "mock": {
                        "bin": "mock",
                        "args_template": ["{spec}"],
                        "env": {"FOO": 1},
                    }
                }
            )

    def test_load_engines_rejects_non_string_env_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "env must be a table of string keys to string values"):
            load_engines(
                {
                    "mock": {
                        "bin": "mock",
                        "args_template": ["{spec}"],
                        "env": {1: "bar"},
                    }
                }
            )

    def test_load_engines_defaults_env_to_none(self) -> None:
        engines = load_engines(
            {"mock": {"bin": "mock", "args_template": ["{spec}"]}}
        )
        self.assertIsNone(engines["mock"].env)


class EngineEnvWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_engine_env_passed_to_worker_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            manifest = Manifest.from_obj(
                {
                    "run_name": "engine-env-test",
                    "workdir": str(root / "work"),
                    "tasks": [
                        {
                            "key": "task-a",
                            "engine": "mock",
                            "spec": "MOCK_FILE: result.txt\nhello\nMOCK_END",
                            "check": "true",
                        }
                    ],
                }
            )
            engine = mock_engine(with_env={"RINGER_ENGINE_ENV_TEST": "injected"})
            runner = RingerRunner(
                manifest,
                make_config(root, engine),
                "test",
                dashboard_enabled=False,
            )
            runtime = runner.runtimes[0]
            runtime.taskdir.mkdir(parents=True)

            captured: list[dict[str, object]] = []

            async def fake_create_subprocess(*args, **kwargs) -> None:  # type: ignore[return]
                captured.append(kwargs)
                raise RuntimeError("injected spawn failure")

            with mock.patch.object(
                ringer.asyncio,
                "create_subprocess_exec",
                side_effect=fake_create_subprocess,
            ):
                result = await runner._run_worker(runtime, runtime.task.spec, 1)

            self.assertIn("injected spawn failure", str(result.error))
            self.assertEqual(len(captured), 1)
            env = captured[0].get("env")
            self.assertIsInstance(env, dict)
            assert isinstance(env, dict)
            self.assertEqual(env.get("RINGER_ENGINE_ENV_TEST"), "injected")

    async def test_worker_env_inherits_process_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            manifest = Manifest.from_obj(
                {
                    "run_name": "engine-env-inherit-test",
                    "workdir": str(root / "work"),
                    "tasks": [
                        {
                            "key": "task-a",
                            "engine": "mock",
                            "spec": "MOCK_FILE: result.txt\nhello\nMOCK_END",
                            "check": "true",
                        }
                    ],
                }
            )
            engine = mock_engine(with_env={"RINGER_ENGINE_ENV_TEST": "injected"})
            runner = RingerRunner(
                manifest,
                make_config(root, engine),
                "test",
                dashboard_enabled=False,
            )
            runtime = runner.runtimes[0]
            runtime.taskdir.mkdir(parents=True)

            captured: list[dict[str, object]] = []

            async def fake_create_subprocess(*args, **kwargs) -> None:  # type: ignore[return]
                captured.append(kwargs)
                raise RuntimeError("injected spawn failure")

            with mock.patch.dict("os.environ", {"RINGER_INHERIT_TEST": "present"}):
                with mock.patch.object(
                    ringer.asyncio,
                    "create_subprocess_exec",
                    side_effect=fake_create_subprocess,
                ):
                    await runner._run_worker(runtime, runtime.task.spec, 1)

            env = captured[0].get("env")
            assert isinstance(env, dict)
            self.assertEqual(env.get("RINGER_INHERIT_TEST"), "present")
            self.assertEqual(env.get("RINGER_ENGINE_ENV_TEST"), "injected")
