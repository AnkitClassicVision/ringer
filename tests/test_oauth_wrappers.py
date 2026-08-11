#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
import importlib.util
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ROOT / "engines"
SENSITIVE_KEYS = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_BASE", "CLAUDE_API_KEY", "CLAUDE_BASE_URL", "CLAUDE_API_BASE",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL",
    "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_VERTEX_PROJECT_ID", "CLOUD_ML_REGION",
    "AWS_REGION", "AWS_DEFAULT_REGION", "OPENAI_API_KEY", "OPENAI_ORG_ID",
    "OPENAI_ORGANIZATION", "OPENAI_PROJECT", "OPENAI_PROJECT_ID",
    "OPENAI_ORGANIZATION_ID", "OPENAI_BASE_URL", "OPENAI_API_BASE", "OPENAI_API_HOST",
    "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "OPENAI_PROFILE", "OPENAI_PROVIDER",
    "CODEX_PROFILE", "CODEX_PROVIDER", "CODEX_BACKEND",
    "CODEX_HOME", "CLAUDE_CONFIG_DIR",
)


class WrapperTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bin_dir = Path(self.temp.name) / "bin"
        self.bin_dir.mkdir()
        self.invocation_marker = Path(self.temp.name) / "downstream-invoked"
        fake = self.bin_dir / "fake-cli"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "if sys.argv[1:] == ['login', 'status']:\n"
            "    print(os.environ.get('FAKE_CODEX_AUTH_STATUS', 'Logged in using ChatGPT'))\n"
            "    raise SystemExit(int(os.environ.get('FAKE_AUTH_EXIT', '0')))\n"
            "if sys.argv[1:] == ['auth', 'status', '--json']:\n"
            "    print(os.environ.get('FAKE_CLAUDE_AUTH_STATUS', "
            "'{\"loggedIn\":true,\"authMethod\":\"claude.ai\",\"apiProvider\":\"firstParty\"}'))\n"
            "    raise SystemExit(int(os.environ.get('FAKE_AUTH_EXIT', '0')))\n"
            "if sys.argv[1:] == ['debug', 'config', '--pure']:\n"
            "    print(os.environ.get('OPENCODE_CONFIG_CONTENT', '{}'))\n"
            "    raise SystemExit(0)\n"
            "marker = os.environ.get('FAKE_INVOCATION_MARKER')\n"
            "if marker:\n"
            "    open(marker, 'w', encoding='utf-8').write('invoked')\n"
            f"keys = {SENSITIVE_KEYS!r}\n"
            "print(json.dumps({'argv': sys.argv[1:], "
            "'sensitive_env_present': {key: key in os.environ for key in keys}, "
            "'ambient_secret_present': 'RINGER_AMBIENT_SECRET_TEST' in os.environ, "
            "'opencode_policy': {"
            "'isolated_config_root': bool(os.environ.get('OPENCODE_CONFIG_DIR')), "
            "'project_config_disabled': os.environ.get('OPENCODE_DISABLE_PROJECT_CONFIG') == '1', "
            "'default_plugins_disabled': os.environ.get('OPENCODE_DISABLE_DEFAULT_PLUGINS') == '1', "
            "'external_skills_disabled': os.environ.get('OPENCODE_DISABLE_EXTERNAL_SKILLS') == '1', "
            "'pure': os.environ.get('OPENCODE_PURE') == '1'}}, "
            "sort_keys=True))\n",
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        for name in ("claude", "codex", "opencode"):
            (self.bin_dir / name).symlink_to(fake)
        self.set_platform("Linux")

    def set_platform(self, platform: str) -> None:
        uname = self.bin_dir / "uname"
        uname.write_text(f"#!/bin/sh\nprintf '%s\\n' '{platform}'\n", encoding="utf-8")
        uname.chmod(uname.stat().st_mode | stat.S_IXUSR)

    def run_wrapper(
        self, wrapper: str, args: list[str], extra_env: dict[str, str] | None = None,
        *, wrapper_path: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        # Codex-hosted test runs carry launcher-only CODEX_* metadata that a
        # fail-closed OAuth wrapper correctly treats as an ambient override.
        # Tests add each routing variable explicitly when exercising it.
        for key in tuple(env):
            if key.startswith("CODEX_") and key not in SENSITIVE_KEYS:
                env.pop(key, None)
        env["PYTHONPATH"] = ""
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["FAKE_INVOCATION_MARKER"] = str(self.invocation_marker)
        env.update(extra_env or {})
        return subprocess.run(
            [str(wrapper_path or ENGINES / wrapper), *args],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def payload(self, result: subprocess.CompletedProcess[str]) -> dict[str, object]:
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def assert_blocked_without_downstream(
        self, result: subprocess.CompletedProcess[str], message: str
    ) -> None:
        self.assertEqual(64, result.returncode)
        self.assertIn(message, result.stderr)
        self.assertFalse(self.invocation_marker.exists(), "blocked route invoked downstream CLI")


class ClaudeOAuthTests(WrapperTestCase):
    def test_test_environment_cannot_override_downstream_binary(self) -> None:
        data = self.payload(self.run_wrapper("claude-oauth.sh", [], {
            "RINGER_OAUTH_TEST_MODE": "1",
            "RINGER_TEST_CLAUDE_BIN": "/does/not/exist",
        }))
        self.assertEqual(["--safe-mode", "--setting-sources", ""], data["argv"])

    def test_inherited_ringer_test_overrides_have_no_effect(self) -> None:
        data = self.payload(self.run_wrapper("claude-oauth.sh", ["--model", "sonnet"], {
            "RINGER_TEST_CLAUDE_BIN": "/does/not/exist",
            "RINGER_TEST_CLAUDE_AUTH_BIN": "/does/not/exist",
            "RINGER_TEST_CLAUDE_AUTH_STATUS": "not oauth",
            "RINGER_TEST_AUTH_EXIT": "99",
        }))
        self.assertEqual(["--safe-mode", "--setting-sources", "", "--model", "sonnet"], data["argv"])

    def test_scrubs_api_environment_and_normalizes_known_models(self) -> None:
        sensitive = {
            "ANTHROPIC_API_KEY": "sentinel",
            "ANTHROPIC_AUTH_TOKEN": "sentinel",
            "ANTHROPIC_BASE_URL": "https://invalid.example",
            "CLAUDE_API_KEY": "sentinel",
            "CLAUDE_BASE_URL": "https://invalid.example",
            "ANTHROPIC_API_BASE": "https://invalid.example",
            "CLAUDE_API_BASE": "https://invalid.example",
        }
        cases = [
            (["-m", "openrouter/anthropic/claude-3-5-sonnet"], ["-m", "sonnet"]),
            (["--model", "anthropic/claude-3-opus"], ["--model", "opus"]),
            (["--model=anthropic:claude-3-haiku"], ["--model=haiku"]),
            (["--model=openrouter/anthropic/claude-fable-1"], ["--model=fable"]),
            (["--model", "haiku3"], ["--model", "haiku"]),
            (["--model", "sonnet4"], ["--model", "sonnet"]),
            (["--model", "opus4"], ["--model", "opus"]),
            (["--model", "fable4"], ["--model", "fable"]),
            (["--model=OpenRouter/Anthropic/Claude-3-5-Sonnet"], ["--model=sonnet"]),
            (["--model", "unrelated/Model-X"], ["--model", "unrelated/Model-X"]),
            (["--model", "openrouter/example/octopus-1"], ["--model", "openrouter/example/octopus-1"]),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                data = self.payload(
                    self.run_wrapper(
                        "claude-oauth.sh", argv, sensitive
                    )
                )
                self.assertEqual(["--safe-mode", "--setting-sources", "", *expected], data["argv"])
                for name in sensitive:
                    self.assertFalse(data["sensitive_env_present"].get(name, False))

    def test_scrubs_alternate_backend_environment_without_changing_reasoning_args(self) -> None:
        alternate = {
            "CLAUDE_CODE_USE_BEDROCK": "1", "CLAUDE_CODE_USE_VERTEX": "1",
            "CLAUDE_CODE_USE_FOUNDRY": "1", "AWS_REGION": "us-test-1",
            "CLAUDE_CONFIG_DIR": "/tmp/alternate-claude-root",
        }
        data = self.payload(self.run_wrapper(
            "claude-oauth.sh", ["--model", "sonnet", "--effort", "high"],
            alternate,
        ))
        self.assertEqual(
            ["--safe-mode", "--setting-sources", "", "--model", "sonnet", "--effort", "high"],
            data["argv"],
        )
        for name in alternate:
            self.assertFalse(data["sensitive_env_present"].get(name, False))

    def test_rejects_settings_backend_bypasses(self) -> None:
        for argv in (["--settings", "/tmp/alternate.json"],
                     ["--settings=/tmp/alternate.json"],
                     ["--setting-sources", "project"], ["--safe-mode"]):
            with self.subTest(argv=argv):
                result = self.run_wrapper(
                    "claude-oauth.sh", list(argv)
                )
                self.assert_blocked_without_downstream(result, "blocked ambiguous")

    def test_execution_forces_isolated_settings_despite_hostile_normal_sources(self) -> None:
        home = Path(self.temp.name) / "home"
        project = Path(self.temp.name) / "project"
        (home / ".claude").mkdir(parents=True)
        project.mkdir()
        marker = "hostile-settings-marker-must-not-appear"
        (home / ".claude" / "settings.json").write_text(marker, encoding="utf-8")
        (project / ".claude").mkdir()
        (project / ".claude" / "settings.local.json").write_text(marker, encoding="utf-8")
        data = self.payload(self.run_wrapper(
            "claude-oauth.sh", ["--model", "sonnet"], {"HOME": str(home), "PWD": str(project)}
        ))
        self.assertEqual(
            ["--safe-mode", "--setting-sources", "", "--model", "sonnet"], data["argv"]
        )

    def test_fails_closed_on_wrong_or_unavailable_auth_without_exposing_status(self) -> None:
        cases = [
            ('{"loggedIn":false,"authMethod":"apiKey","apiProvider":"thirdParty","secret":"do-not-print"}', "0"),
            ('{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"thirdParty","secret":"do-not-print"}', "0"),
            ('{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty","secret":"do-not-print"}', "1"),
        ]
        for status, exit_code in cases:
            with self.subTest(status=status, exit_code=exit_code):
                result = self.run_wrapper("claude-oauth.sh", [], {
                    "FAKE_CLAUDE_AUTH_STATUS": status,
                    "FAKE_AUTH_EXIT": exit_code,
                    "CLAUDE_CONFIG_DIR": "/tmp/alternate-claude-root",
                })
                self.assert_blocked_without_downstream(result, "non-OAuth invocation")
                self.assertNotIn("do-not-print", result.stderr + result.stdout)

    def test_auth_status_requires_one_unambiguous_typed_json_object(self) -> None:
        cases = [
            'prefix {"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty","payload":"do-not-print"}',
            '{"loggedIn":true,"loggedIn":false,"authMethod":"claude.ai","authMethod":"apiKey","apiProvider":"firstParty","apiProvider":"thirdParty","payload":"do-not-print"}',
            '{"loggedIn":1,"authMethod":"claude.ai","apiProvider":"firstParty","payload":"do-not-print"}',
            '{"loggedIn":true,"authMethod":true,"apiProvider":"firstParty","payload":"do-not-print"}',
            '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":1,"payload":"do-not-print"}',
            '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty"}\n{"payload":"do-not-print"}',
            '[{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty"},"do-not-print"]',
        ]
        for status in cases:
            with self.subTest(status=status):
                result = self.run_wrapper("claude-oauth.sh", [], {
                    "FAKE_CLAUDE_AUTH_STATUS": status,
                })
                self.assert_blocked_without_downstream(result, "non-OAuth invocation")
                self.assertNotIn("do-not-print", result.stderr + result.stdout)

    def test_rejects_ambiguous_model_argv(self) -> None:
        cases = [["--"], ["-m"], ["--model="], ["--model", "claude3"], ["-m", "sonnet", "--model", "opus"]]
        for argv in cases:
            with self.subTest(argv=argv):
                result = self.run_wrapper("claude-oauth.sh", argv)
                self.assert_blocked_without_downstream(result, "ambiguous")


class CodexOAuthTests(WrapperTestCase):
    def test_test_environment_cannot_override_downstream_binary(self) -> None:
        data = self.payload(self.run_wrapper("codex-oauth.sh", ["exec"], {
            "RINGER_OAUTH_TEST_MODE": "1",
            "RINGER_TEST_CODEX_BIN": "/does/not/exist",
        }))
        self.assertEqual(
            ["exec", "--ignore-user-config", "-c", "model_provider=openai"], data["argv"]
        )

    def test_inherited_ringer_test_overrides_have_no_effect(self) -> None:
        data = self.payload(self.run_wrapper("codex-oauth.sh", ["-m", "o10"], {
            "RINGER_TEST_CODEX_BIN": "/does/not/exist",
            "RINGER_TEST_CODEX_AUTH_BIN": "/does/not/exist",
            "RINGER_TEST_CODEX_AUTH_STATUS": "not chatgpt",
            "RINGER_TEST_AUTH_EXIT": "99",
        }))
        self.assertEqual(
            ["-m", "o10", "--ignore-user-config", "-c", "model_provider=openai"], data["argv"]
        )

    def test_scrubs_api_environment_and_normalizes_selectors(self) -> None:
        sensitive = {
            "OPENAI_API_KEY": "sentinel",
            "OPENAI_ORG_ID": "sentinel",
            "OPENAI_ORGANIZATION": "sentinel",
            "OPENAI_PROJECT": "sentinel",
            "OPENAI_PROJECT_ID": "sentinel",
            "OPENAI_ORGANIZATION_ID": "sentinel",
            "OPENAI_BASE_URL": "https://invalid.example",
            "OPENAI_API_BASE": "https://invalid.example",
            "OPENAI_API_HOST": "https://invalid.example",
            "AZURE_OPENAI_API_KEY": "sentinel",
            "AZURE_OPENAI_ENDPOINT": "https://invalid.example",
        }
        cases = [
            (["exec", "-m", "openrouter/openai/gpt-5.6-sol"], ["exec", "-m", "gpt-5.6-sol"]),
            (["--model=openai/gpt-5.6-terra"], ["--model=gpt-5.6-terra"]),
            (["-c", "model=openrouter/openai/o3"], ["-c", "model=o3"]),
            (["--config", "model=openai/gpt-5.6-luna"], ["--config", "model=gpt-5.6-luna"]),
            (["--config=model = \"openrouter/openai/gpt-5.6-nova\""], ["--config=model = \"gpt-5.6-nova\""]),
            (["--config=model='OpenRouter/OpenAI/gpt-5.6-quasar'"], ["--config=model='gpt-5.6-quasar'"]),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                data = self.payload(self.run_wrapper(
                    "codex-oauth.sh", argv, sensitive
                ))
                self.assertEqual(
                    expected + ["--ignore-user-config", "-c", "model_provider=openai"], data["argv"]
                )
                for name in sensitive:
                    self.assertFalse(data["sensitive_env_present"].get(name, False))

    def test_rejects_alternate_provider_profile_and_backend_selectors(self) -> None:
        cases = [
            ["-c", "model_provider=openrouter"], ["--config=provider=azure"],
            ["--config", "backend=custom"], ["--profile", "metered"],
            ["--profile=metered"], ["-p", "metered"], ["profile=metered"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                result = self.run_wrapper("codex-oauth.sh", argv)
                self.assert_blocked_without_downstream(result, "blocked ambiguous")

    def test_rejects_oss_and_local_provider_in_every_flag_spelling(self) -> None:
        cases = [
            ["--oss"], ["--oss=true"], ["--oss=false"],
            ["--local-provider", "ollama"], ["--local-provider=ollama"],
            ["--local-provider", "lmstudio"], ["--local-provider=lmstudio"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                result = self.run_wrapper("codex-oauth.sh", argv)
                self.assert_blocked_without_downstream(result, "blocked ambiguous")

    def test_rejects_all_non_allowlisted_config_and_nested_provider_definitions(self) -> None:
        selectors = [
            ["-c", 'model_providers.openai.base_url="https://metered.invalid"'],
            ["--config=model_providers.openai.env_key=\"METERED_KEY\""],
            ["--config", " model_providers.openai.wire_api = 'responses' "],
            ["-c", "MODEL_PROVIDERS.OpenAI.BASE_URL = 'https://metered.invalid'"],
            ["--config", '"model_providers.openai.base_url=https://metered.invalid"'],
            ["-c", "model_provider=openrouter"],
            ["--config=local_provider=ollama"],
            ["--config", "approval_policy=never"],
        ]
        for argv in selectors:
            with self.subTest(argv=argv):
                result = self.run_wrapper("codex-oauth.sh", argv)
                self.assert_blocked_without_downstream(result, "blocked ambiguous")

    def test_scrubs_backend_environment_and_preserves_reasoning_config(self) -> None:
        data = self.payload(self.run_wrapper(
            "codex-oauth.sh", ["-c", "model_reasoning_effort=high"],
            {"CODEX_PROFILE": "metered", "CODEX_PROVIDER": "other", "CODEX_BACKEND": "other",
             "CODEX_HOME": "/tmp/alternate-codex-root"},
        ))
        self.assertEqual(
            ["-c", "model_reasoning_effort=high", "--ignore-user-config", "-c", "model_provider=openai"],
            data["argv"],
        )
        for name in ("CODEX_PROFILE", "CODEX_PROVIDER", "CODEX_BACKEND", "CODEX_HOME"):
            self.assertFalse(data["sensitive_env_present"].get(name, False))

    def test_allows_known_safe_split_config_and_writable_roots(self) -> None:
        data = self.payload(self.run_wrapper(
            "codex-oauth.sh",
            ["-c", "model_reasoning_effort=high", "-c", 'sandbox_workspace_write.writable_roots=["/tmp"]'],
        ))
        self.assertEqual(
            ["-c", "model_reasoning_effort=high", "-c", 'sandbox_workspace_write.writable_roots=["/tmp"]',
             "--ignore-user-config", "-c", "model_provider=openai"], data["argv"]
        )

    def test_execution_ignores_hostile_user_config_and_flag_appears_once(self) -> None:
        home = Path(self.temp.name) / "home"
        codex_home = home / ".codex"
        codex_home.mkdir(parents=True)
        marker = "hostile-provider-marker-must-not-appear"
        (codex_home / "config.toml").write_text(marker, encoding="utf-8")
        for argv in (["exec"], ["exec", "--ignore-user-config"]):
            with self.subTest(argv=argv):
                data = self.payload(self.run_wrapper(
                    "codex-oauth.sh", list(argv), {"HOME": str(home)}
                ))
                self.assertEqual(1, data["argv"].count("--ignore-user-config"))
                self.assertNotIn(marker, json.dumps(data))

    def test_rejects_duplicate_ignore_user_config(self) -> None:
        result = self.run_wrapper(
            "codex-oauth.sh", ["exec", "--ignore-user-config", "--ignore-user-config"]
        )
        self.assert_blocked_without_downstream(result, "blocked ambiguous")

    def test_rejects_ambiguous_or_model_changing_argv(self) -> None:
        cases = [
            ["--"], ["-m"], ["--model="], ["-c"], ["-cmodel_provider=openrouter"],
            ["-cmodel_reasoning_effort=high"], ["-mgpt-5"],
            ["model=openrouter/openai/codex-mini"], ["model = openai/o4-mini"],
            ["-m", "gpt-5", "--model", "o3"],
            ["-m", "gpt-5", "-cmodel=openai/o3"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                result = self.run_wrapper("codex-oauth.sh", argv)
                self.assert_blocked_without_downstream(result, "blocked ambiguous")

    def test_fails_closed_on_wrong_or_unavailable_auth_without_exposing_status(self) -> None:
        for exit_code in ("0", "1"):
            with self.subTest(exit_code=exit_code):
                result = self.run_wrapper("codex-oauth.sh", [], {
                    "FAKE_CODEX_AUTH_STATUS": "Logged in with API key do-not-print",
                    "FAKE_AUTH_EXIT": exit_code,
                    "CODEX_HOME": "/tmp/alternate-codex-root",
                })
                self.assert_blocked_without_downstream(result, "standard Codex ChatGPT login")
                self.assertNotIn("do-not-print", result.stderr + result.stdout)

    def test_auth_status_accepts_only_documented_single_line(self) -> None:
        rejected = [
            "Not logged in using ChatGPT do-not-print",
            "Logged in via ChatGPT do-not-print",
            "Logged in using ChatGPT\nNot logged in using ChatGPT do-not-print",
            "Warning do-not-print: Logged in using ChatGPT",
            "Logged in using ChatGPT do-not-print",
            "logged in using ChatGPT do-not-print",
            "ChatGPT login do-not-print",
        ]
        for status in rejected:
            with self.subTest(status=status):
                result = self.run_wrapper("codex-oauth.sh", [], {
                    "FAKE_CODEX_AUTH_STATUS": status,
                })
                self.assert_blocked_without_downstream(result, "standard Codex ChatGPT login")
                self.assertNotIn("do-not-print", result.stderr + result.stdout)


class OpenCodePolicyTests(WrapperTestCase):
    def test_test_environment_cannot_override_downstream_binary(self) -> None:
        result = self.run_wrapper("opencode-auth-policy.sh", [
            "/tmp", "run", "-m", "openrouter/example/octopus-1",
            "--dangerously-skip-permissions", "--format", "json",
            "--dir", "/tmp", "prompt",
        ], {
            "RINGER_OAUTH_TEST_MODE": "1",
            "RINGER_TEST_OPENCODE_BIN": "/does/not/exist",
        })
        self.assertEqual(
            [
                "run", "-m", "openrouter/example/octopus-1",
                "--dangerously-skip-permissions", "--format", "json",
                "--dir", "/tmp", "prompt",
            ],
            self.payload(result)["argv"],
        )

    def test_inherited_ringer_test_overrides_have_no_effect(self) -> None:
        result = self.run_wrapper("opencode-auth-policy.sh", [
            "/tmp", "run", "-m", "openrouter/example/octopus-1",
            "--dangerously-skip-permissions", "--format", "json",
            "--dir", "/tmp", "prompt",
        ], {
            "RINGER_TEST_OPENCODE_BIN": "/does/not/exist",
            "RINGER_TEST_OPENCODE_SANDBOX_BIN": "/does/not/exist",
            "RINGER_TEST_OPENCODE_PLATFORM": "Darwin",
        })
        self.assertEqual(
            [
                "run", "-m", "openrouter/example/octopus-1",
                "--dangerously-skip-permissions", "--format", "json",
                "--dir", "/tmp", "prompt",
            ],
            self.payload(result)["argv"],
        )

    def run_policy(
        self,
        model: str,
        flag: str = "-m",
        *,
        platform: str = "Linux",
        full_access: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.set_platform(platform)
        args = ["/tmp", "run"]
        if full_access:
            args.insert(1, "--no-sandbox")
        if flag == "--model=":
            args.append(f"--model={model}")
        else:
            args.extend([flag, model])
        args.extend([
            "--dangerously-skip-permissions", "--format", "json",
            "--dir", "/tmp", "prompt",
        ])
        wrapper_path = None
        if platform == "Darwin":
            wrapper_dir = Path(self.temp.name) / "darwin-wrapper"
            wrapper_dir.mkdir(exist_ok=True)
            wrapper_path = wrapper_dir / "opencode-auth-policy.sh"
            wrapper_path.write_text(
                (ENGINES / "opencode-auth-policy.sh").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR)
            (wrapper_dir / "opencode-sandboxed.sh").symlink_to(self.bin_dir / "fake-cli")
        return self.run_wrapper(
            "opencode-auth-policy.sh", args, wrapper_path=wrapper_path
        )

    def test_allows_zai_coding_plan_glm(self) -> None:
        result = self.run_policy("zai-coding-plan/glm-5.2", "--model=")
        data = self.payload(result)
        self.assertEqual("zai-coding-plan/glm-5.2", data["argv"][1].split("=", 1)[1])
        self.assertEqual(
            {
                "default_plugins_disabled": True,
                "external_skills_disabled": True,
                "isolated_config_root": True,
                "project_config_disabled": True,
                "pure": True,
            },
            data["opencode_policy"],
        )

    def test_hostile_config_environment_is_replaced_without_exposing_content(self) -> None:
        marker = "hostile-opencode-config-must-not-appear"
        result = self.run_wrapper("opencode-auth-policy.sh", [
            "/tmp", "run", "-m", "zai-coding-plan/glm-5.2",
            "--dangerously-skip-permissions", "--format", "json",
            "--dir", "/tmp", "prompt",
        ], {
            "OPENCODE_CONFIG": "/tmp/hostile-opencode.json",
            "OPENCODE_CONFIG_DIR": "/tmp/hostile-opencode-root",
            "OPENCODE_CONFIG_CONTENT": json.dumps({
                "provider": {"zai-coding-plan": {"options": {"baseURL": marker}}}
            }),
            "XDG_CONFIG_HOME": "/tmp/hostile-xdg-config",
        })
        data = self.payload(result)
        self.assertTrue(data["opencode_policy"]["isolated_config_root"])
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_real_opencode_debug_config_proves_hostile_overrides_cannot_redirect(self) -> None:
        real_opencode = shutil.which("opencode")
        if real_opencode is None:
            self.skipTest("installed OpenCode CLI is required for resolved-config verification")
        home = Path(self.temp.name) / "hostile-home"
        project = Path(self.temp.name) / "hostile-project"
        xdg_config = Path(self.temp.name) / "hostile-xdg"
        managed_config = Path(self.temp.name) / "hostile-managed"
        home.mkdir()
        project.mkdir()
        managed_config.mkdir()
        (project / ".opencode").mkdir()
        (xdg_config / "opencode").mkdir(parents=True)
        marker = "https://hostile.invalid/metered"
        hostile = json.dumps({
            "provider": {
                "zai-coding-plan": {"options": {"baseURL": marker}},
                "hostile-alias": {"options": {"baseURL": marker}},
            },
            "enabled_providers": ["hostile-alias"],
            "plugin": ["hostile-plugin"],
        })
        (project / "opencode.json").write_text(hostile, encoding="utf-8")
        (project / ".opencode" / "opencode.json").write_text(hostile, encoding="utf-8")
        (xdg_config / "opencode" / "opencode.json").write_text(hostile, encoding="utf-8")
        (managed_config / "opencode.json").write_text(hostile, encoding="utf-8")
        result = self.run_wrapper("opencode-auth-policy.sh", [
            "--ringer-verify-config-only",
            str(project), "run", "-m", "zai-coding-plan/glm-5.2",
            "--dangerously-skip-permissions", "--format", "json",
            "--dir", str(project), "prompt",
        ], {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(xdg_config),
            "OPENCODE_CONFIG_CONTENT": hostile,
            "OPENCODE_TEST_MANAGED_CONFIG_DIR": str(managed_config),
            "OPENCODE_AUTH_CONTENT": "hostile-auth-content-must-not-appear",
            "PATH": f"{Path(real_opencode).parent}{os.pathsep}{os.environ.get('PATH', '')}",
        })
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({
            "baseURL": "https://api.z.ai/api/coding/paas/v4",
            "enabled_providers": ["zai-coding-plan"],
            "provider_ids": ["zai-coding-plan"],
        }, json.loads(result.stdout))
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_blocks_non_coding_plan_glm_routes(self) -> None:
        for model in (
            "openrouter/z-ai/glm-5.2", "z-ai/glm-5.2", "glm-5.2", "glm", "GLM",
            "ollama/glm", "ollama/glm-4", "local/glm-4", "glm5", "local/glm5",
            "zai-coding-plan/glm5", "zai-coding-plan/glm-",
            "zai-coding-plan/glm-5.2/extra", "ZAI-CODING-PLAN/GLM5",
            "openrouter/other/glm5",
        ):
            with self.subTest(model=model):
                result = self.run_policy(model)
                self.assert_blocked_without_downstream(result, "Z.AI Coding Plan")
                self.assertNotIn("sentinel", result.stderr)

    def test_blocks_anthropic_and_openai_families(self) -> None:
        cases = {
            "openrouter/anthropic/claude-3-5-sonnet": "claude OAuth engine",
            "claude-fable-1": "claude OAuth engine",
            "openrouter/openai/gpt-5.6": "codex OAuth engine",
            "openai:gpt-5.6": "codex OAuth engine",
            "azure/gpt-4.1": "codex OAuth engine",
            "chatgpt-4o-latest": "codex OAuth engine",
            "azure/chatgpt-4o-latest": "codex OAuth engine",
            "some-provider/chatgpt-enterprise": "codex OAuth engine",
            "o3": "codex OAuth engine",
            "azure/o10": "codex OAuth engine",
            "openrouter/openai/o12-pro": "codex OAuth engine",
            "azure/o4-mini": "codex OAuth engine",
            "codex-mini": "codex OAuth engine",
            "gpt5": "codex OAuth engine",
            "chatgpt4o": "codex OAuth engine",
            "codex5": "codex OAuth engine",
            "claude3": "claude OAuth engine",
            "haiku3": "claude OAuth engine",
            "sonnet4": "claude OAuth engine",
            "opus4": "claude OAuth engine",
        }
        for model, message in cases.items():
            with self.subTest(model=model):
                result = self.run_policy(model)
                self.assert_blocked_without_downstream(result, message)

    def test_unrestricted_provider_is_unchanged(self) -> None:
        for model in (
            "openrouter/moonshotai/kimi-k2.7-code",
            "openrouter/example/octopus-1",
            "provider/fabulous-model",
            "provider/sonneteer-2",
            "provider/codexical-1", "provider/ocean-10",
        ):
            with self.subTest(model=model):
                result = self.run_policy(model, "--model")
                data = self.payload(result)
                self.assertEqual([
                    "run", "--model", model, "--dangerously-skip-permissions",
                    "--format", "json", "--dir", "/tmp", "prompt",
                ], data["argv"])
                self.assertTrue(data["opencode_policy"]["project_config_disabled"])

    def test_darwin_delegates_wrapper_argv_to_sandbox(self) -> None:
        result = self.run_policy(
            "zai-coding-plan/glm-5.2", platform="Darwin", full_access=True
        )
        self.assertEqual(
            [
                "/tmp", "--no-sandbox", "run", "-m",
                "zai-coding-plan/glm-5.2", "--dangerously-skip-permissions",
                "--format", "json", "--dir", "/tmp", "prompt",
            ],
            self.payload(result)["argv"],
        )

    def test_linux_removes_wrapper_only_argv_before_opencode(self) -> None:
        result = self.run_policy(
            "zai-coding-plan/glm-5.2", platform="Linux", full_access=True
        )
        self.assertEqual(
            [
                "run", "-m", "zai-coding-plan/glm-5.2",
                "--dangerously-skip-permissions", "--format", "json",
                "--dir", "/tmp", "prompt",
            ],
            self.payload(result)["argv"],
        )

    def test_sample_config_has_no_active_opencode_lane(self) -> None:
        with (ROOT / "config.sample.toml").open("rb") as handle:
            sample = tomllib.load(handle)
        self.assertNotIn("opencode", sample["engines"])
        self.assertNotIn("glm-coding-plan", sample["engines"])
        self.assertIn("pi-openrouter", sample["engines"])

    def test_rejects_terminator_repeated_and_missing_model_values(self) -> None:
        canonical = [
            "/tmp", "run", "-m", "zai-coding-plan/glm-5.2",
            "--dangerously-skip-permissions", "--format", "json",
        ]
        cases = [
            ["/tmp", "run", "--"],
            ["/tmp", "run", "-m"],
            ["/tmp", "run", "--model="],
            ["/tmp", "run", "-m", "openrouter/openai/gpt-5.6", "--", "-m", "openrouter/moonshotai/kimi"],
            ["/tmp", "run", "-m", "openrouter/moonshotai/kimi", "--model", "openrouter/openai/gpt-5.6"],
            [*canonical, "--attach", "http://remote.invalid", "--dir", "/tmp", "prompt"],
            [*canonical, "--attach=http://remote.invalid", "--dir", "/tmp", "prompt"],
            [*canonical, "--agent", "remote-agent", "--dir", "/tmp", "prompt"],
            [*canonical, "--variant", "turbo", "--dir", "/tmp", "prompt"],
            [*canonical, "--dir", "/tmp/other", "prompt"],
            [*canonical, "--dir", "/tmp", "prompt", "extra"],
            [*canonical, "--dir", "/tmp", "--attach=http://remote.invalid"],
        ]
        for argv in cases:
            for platform in ("Linux", "Darwin"):
                with self.subTest(argv=argv, platform=platform):
                    self.set_platform(platform)
                    result = self.run_wrapper("opencode-auth-policy.sh", argv)
                    self.assert_blocked_without_downstream(result, "blocked ambiguous")



class TestOutputSafetyTests(WrapperTestCase):
    def test_fake_cli_reports_presence_without_serializing_secret_values(self) -> None:
        marker = "ambient-secret-value-must-not-appear"
        result = self.run_wrapper(
            "claude-oauth.sh", [],
            {"RINGER_AMBIENT_SECRET_TEST": marker},
        )
        data = self.payload(result)
        self.assertTrue(data["ambient_secret_present"])
        self.assertNotIn(marker, result.stdout)


class HostBashSyntaxSmokeTests(unittest.TestCase):
    def test_wrappers_parse_with_host_bash_and_avoid_lowercase_expansion(self) -> None:
        for name in ("claude-oauth.sh", "codex-oauth.sh", "opencode-auth-policy.sh"):
            text = (ENGINES / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertNotIn(",,}", text)
                result = subprocess.run(
                    ["/bin/bash", "-n", str(ENGINES / name)], text=True,
                    capture_output=True, check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
