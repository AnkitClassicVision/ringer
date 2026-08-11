#!/usr/bin/env python3
"""Codex workers ignore user configuration while preserving task routing."""
from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ringer import build_worker_command, built_in_codex_engine, load_engines  # noqa: E402


class CodexIsolationTests(unittest.TestCase):
    def assert_isolated_template(self, args_template: tuple[str, ...] | list[str]) -> None:
        self.assertEqual(1, args_template.count("--ignore-user-config"))
        isolation_index = args_template.index("--ignore-user-config")
        self.assertLess(isolation_index, args_template.index("{engine_args}"))
        self.assertLess(isolation_index, args_template.index("{spec}"))

    def test_builtin_codex_engine_is_isolated(self) -> None:
        self.assert_isolated_template(built_in_codex_engine().args_template)

    def test_sample_codex_engine_is_isolated(self) -> None:
        with (ROOT / "config.sample.toml").open("rb") as config_file:
            args_template = tomllib.load(config_file)["engines"]["codex"]["args_template"]

        self.assert_isolated_template(args_template)

    def test_legacy_configured_codex_template_gains_isolation(self) -> None:
        engines = load_engines(
            {"codex": {"args_template": ["exec", "{engine_args}", "{spec}"]}}
        )

        self.assert_isolated_template(engines["codex"].args_template)

    def test_already_isolated_codex_template_is_not_duplicated(self) -> None:
        engines = load_engines(
            {
                "codex": {
                    "args_template": [
                        "exec",
                        "--ignore-user-config",
                        "{engine_args}",
                        "{spec}",
                        "--ignore-user-config",
                    ]
                }
            }
        )

        self.assert_isolated_template(engines["codex"].args_template)

    def test_non_codex_engine_template_is_unchanged(self) -> None:
        template = ["run", "{engine_args}", "{spec}"]

        engines = load_engines({"other": {"args_template": template}})

        self.assertEqual(tuple(template), engines["other"].args_template)

    def test_worker_command_preserves_task_model_and_reasoning_args(self) -> None:
        command = build_worker_command(
            built_in_codex_engine(),
            taskdir=Path("/tmp/codex-isolation-task"),
            spec="do the task",
            full_access=False,
            engine_args=("-m", "gpt-explicit", "-c", "model_reasoning_effort=high"),
        )

        self.assertEqual(1, command.count("--ignore-user-config"))
        self.assertLess(command.index("--ignore-user-config"), command.index("-m"))
        self.assertEqual("gpt-explicit", command[command.index("-m") + 1])
        config_index = command.index("-c")
        self.assertEqual("model_reasoning_effort=high", command[config_index + 1])
        self.assertLess(command.index("--ignore-user-config"), config_index)
        self.assertLess(config_index, command.index("do the task"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
