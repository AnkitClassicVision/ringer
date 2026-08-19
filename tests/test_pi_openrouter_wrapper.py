#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "engines" / "pi-openrouter-ringer.sh"
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/x-ai/grok-4.5"
FAKE_KEY = "fixture-openrouter-key-not-real"


@unittest.skipUnless(platform.system() == "Linux", "bubblewrap lane is Linux-only")
class PiOpenRouterWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.taskdir = self.root / "task"
        self.taskdir.mkdir()
        self.agent_dir = self.root / "agent"
        self.agent_dir.mkdir()
        (self.agent_dir / "auth.json").write_text(
            json.dumps({"openrouter": {"type": "api_key", "key": FAKE_KEY}}),
            encoding="utf-8",
        )
        self.write_model_cache("x-ai/grok-4.5")
        self.sentinel = self.root / "sibling-sentinel.txt"
        self.sentinel.write_text("must-stay-hidden", encoding="utf-8")
        self.fake_pi = self.root / "pi-test.js"
        self.fake_pi.write_text(
            """const fs = require("fs");
const path = require("path");
const blocked = (operation) => { try { operation(); return false; } catch { return true; } };
const agent = process.env.PI_CODING_AGENT_DIR;
const readBlocked = blocked(() => fs.readFileSync("../sibling-sentinel.txt"));
const writeBlocked = blocked(() => fs.writeFileSync("../outside-write.txt", "escape"));
const editBlocked = blocked(() => fs.writeFileSync("/outside-edit.txt", "escape"));
fs.writeFileSync("inside-write.txt", "inside");
const visibleAgentFiles = fs.readdirSync(agent).sort();
const authReadBlocked = blocked(() => fs.readFileSync(path.join(agent, "auth.json")));
const procEnvironReadBlocked = blocked(() => fs.readFileSync("/proc/self/environ"));
const procCmdlineReadBlocked = blocked(() => fs.readFileSync("/proc/self/cmdline"));
const agentWriteBlocked = blocked(() => fs.writeFileSync(path.join(agent, "created-by-pi"), "escape"));
const agentEditBlocked = blocked(() => fs.writeFileSync(path.join(agent, "models.json"), "escape"));
const modelsConfig = JSON.parse(fs.readFileSync(path.join(agent, "models.json"), "utf8"));
const envNames = ["HOME", "PATH", "PI_CODING_AGENT_DIR", "PI_OFFLINE", "PWD"];
const safeEnvironment = Object.fromEntries(envNames.map((name) => [name, process.env[name]]));
const ambientNames = [
  "ANTHROPIC_API_KEY", "HTTPS_PROXY", "NODE_OPTIONS", "RINGER_AMBIENT_TEST_VALUE",
  "RINGER_PI_OPENROUTER_TEST_MODE", "RINGER_TEST_PI_BIN", "RINGER_PI_OPENROUTER_AGENT_DIR",
];
fs.writeFileSync("invocation.json", JSON.stringify({
  argv: process.argv.slice(2), cwd: process.cwd(), agent_dir: agent,
  safe_environment: safeEnvironment,
  openrouter_key_present: Boolean(process.env.OPENROUTER_API_KEY),
  ambient_variables_present: ambientNames.some((name) => name in process.env),
  visible_agent_files: visibleAgentFiles, models_config: modelsConfig,
  auth_read_blocked: authReadBlocked,
  proc_environ_read_blocked: procEnvironReadBlocked,
  proc_cmdline_read_blocked: procCmdlineReadBlocked,
  agent_write_blocked: agentWriteBlocked, agent_edit_blocked: agentEditBlocked,
  read_blocked: readBlocked, write_blocked: writeBlocked, edit_blocked: editBlocked,
  usr_local_absent: !fs.existsSync("/usr/local"),
  usr_src_absent: !fs.existsSync("/usr/src"),
}));
const args = process.argv.slice(2);
const requested = args[args.indexOf("--model") + 1].replace(/^openrouter\\//, "");
const spec = args.at(-1);
if (spec === "print-key") console.log(process.env.OPENROUTER_API_KEY);
if (spec === "replace-auth-race") {
  fs.writeFileSync("pi-started", "started");
  while (!fs.existsSync("pi-release")) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
  console.log(process.env.OPENROUTER_API_KEY);
}
if (spec === "exit-23") process.exit(23);
const provider = spec === "wrong-provider" ? "wrong" : "openrouter";
const model = spec === "wrong-model" ? "wrong/model" : requested;
const usage = {input: 2, output: 3, cacheRead: 4, cacheWrite: 5, totalTokens: 14,
  cost: {input: .1, output: .2, cacheRead: 0, cacheWrite: 0, total: .3}};
if (spec === "negative-usage") usage.input = -1;
if (spec === "negative-cost") usage.cost.total = -1;
if (spec === "missing-cost") delete usage.cost;
if (spec === "partial-cost") delete usage.cost.cacheWrite;
if (spec === "bool-cost") usage.cost.input = true;
if (spec === "nan-cost") usage.cost.input = NaN;
if (spec === "infinite-cost") usage.cost.input = Infinity;
const message = (p, m, stopReason = "stop") => ({
  type: "message_end", message: {role: "assistant", provider: p, model: m, stopReason, usage},
});
if (spec === "top-error") console.log(JSON.stringify({type: "error", message: "failed"}));
else if (spec === "aborted") console.log(JSON.stringify(message(provider, model, "aborted")));
else {
  if (spec === "early-wrong-identity") console.log(JSON.stringify(message("wrong", "wrong/model")));
  console.log(JSON.stringify(message(provider, model)));
}
""",
            encoding="utf-8",
        )

    def model_record(
        self,
        model_id: str,
        *,
        provider: str = "openrouter",
        base_url: str = OPENROUTER_ENDPOINT,
        api: str = "openai-completions",
    ) -> dict[str, object]:
        return {
            "id": model_id,
            "name": f"Fake {model_id}",
            "api": api,
            "provider": provider,
            "baseUrl": base_url,
            "reasoning": True,
            "input": ["text"],
            "cost": {
                "input": 1,
                "output": 2,
                "cacheRead": 0,
                "cacheWrite": 0,
            },
            "contextWindow": 1000,
            "maxTokens": 100,
            "headers": {"X-Secret-Routing": "must-be-stripped"},
            "unknownRoutingField": "must-be-stripped",
            "compat": {
                "supportsDeveloperRole": False,
                "thinkingFormat": "openrouter",
                "openRouterRouting": {"only": ["attacker-controlled-route"]},
                "vercelGatewayRouting": {"only": ["attacker-controlled-route"]},
                "chatTemplateKwargs": {"attacker": "must-be-stripped"},
                "sendSessionAffinityHeaders": True,
            },
        }

    def write_model_cache(
        self,
        model_id: str,
        *,
        provider: str = "openrouter",
        base_url: str = OPENROUTER_ENDPOINT,
        api: str = "openai-completions",
    ) -> None:
        (self.agent_dir / "models-store.json").write_text(
            json.dumps(
                {
                    "openrouter": {
                        "models": [
                            self.model_record(
                                model_id,
                                provider=provider,
                                base_url=base_url,
                                api=api,
                            ),
                            self.model_record("other/model"),
                        ],
                        "checkedAt": 123,
                        "etag": "untrusted-cache-metadata",
                    },
                    "other-provider": {"models": [self.model_record("other/leak")]},
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_wrapper(
        self,
        model: str,
        spec: str = "prompt",
        *,
        auth_dir: Path | None = None,
        taskdir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "RINGER_PI_OPENROUTER_TEST_MODE": "1",
                "RINGER_TEST_PI_BIN": str(self.fake_pi),
                "RINGER_PI_OPENROUTER_AGENT_DIR": str(auth_dir or self.agent_dir),
                "OPENROUTER_API_KEY": "must-not-reach-pi",
                "ANTHROPIC_API_KEY": "must-not-reach-pi",
                "HTTPS_PROXY": "http://must-not-reach-pi.invalid",
                "NODE_OPTIONS": "--trace-warnings",
                "RINGER_AMBIENT_TEST_VALUE": "must-not-reach-pi",
                "TMPDIR": str(self.root),
            }
        )
        return subprocess.run(
            [str(WRAPPER), str(taskdir or self.taskdir), model, spec],
            text=True,
            capture_output=True,
            env=env,
        )

    def test_frontier_models_have_exact_arguments_identity_and_accounting(self) -> None:
        for model in (
            "openrouter/x-ai/grok-4.5",
            "openrouter/z-ai/glm-5.2",
            "openrouter/moonshotai/kimi-k3",
        ):
            with self.subTest(model=model):
                self.write_model_cache(model.removeprefix("openrouter/"))
                result = self.run_wrapper(model)
                self.assertEqual(0, result.returncode, result.stderr)
                invocation = json.loads((self.taskdir / "invocation.json").read_text())
                self.assertEqual("/workspace", invocation["cwd"])
                self.assertEqual(
                    [
                        "--print", "--mode", "json", "--no-session",
                        "--no-extensions", "--no-skills", "--no-prompt-templates",
                        "--no-themes", "--no-context-files", "--approve",
                        "--tools", "read,write,edit", "--model", model,
                        "--thinking", "high", "prompt",
                    ],
                    invocation["argv"],
                )
                self.assertEqual("/agent", invocation["agent_dir"])
                child_env = invocation["safe_environment"]
                self.assertEqual("/tmp/home", child_env["HOME"])
                self.assertEqual("/runtime/bin", child_env["PATH"])
                self.assertEqual("/agent", child_env["PI_CODING_AGENT_DIR"])
                self.assertEqual("1", child_env["PI_OFFLINE"])
                self.assertEqual("/workspace", child_env["PWD"])
                self.assertTrue(invocation["openrouter_key_present"])
                self.assertFalse(invocation["ambient_variables_present"])
                self.assertEqual(
                    ["models.json"],
                    invocation["visible_agent_files"],
                )
                self.assertTrue(invocation["auth_read_blocked"])
                self.assertTrue(invocation["proc_environ_read_blocked"])
                self.assertTrue(invocation["proc_cmdline_read_blocked"])
                self.assertTrue(invocation["agent_write_blocked"])
                self.assertTrue(invocation["agent_edit_blocked"])
                runtime_models = invocation["models_config"]
                self.assertEqual(["openrouter"], list(runtime_models["providers"]))
                provider = runtime_models["providers"]["openrouter"]
                self.assertEqual("openai-completions", provider["api"])
                self.assertEqual(OPENROUTER_ENDPOINT, provider["baseUrl"])
                self.assertEqual(1, len(provider["models"]))
                self.assertNotIn("checkedAt", provider)
                self.assertNotIn("etag", provider)
                runtime_model = provider["models"][0]
                self.assertEqual(
                    model.removeprefix("openrouter/"), runtime_model["id"]
                )
                self.assertNotIn("provider", runtime_model)
                self.assertEqual(OPENROUTER_ENDPOINT, runtime_model["baseUrl"])
                self.assertNotIn("headers", runtime_model)
                self.assertNotIn("unknownRoutingField", runtime_model)
                self.assertEqual(
                    {
                        "supportsDeveloperRole": False,
                        "thinkingFormat": "openrouter",
                    },
                    runtime_model["compat"],
                )
                self.assertNotIn("openRouterRouting", runtime_model["compat"])
                self.assertNotIn("vercelGatewayRouting", runtime_model["compat"])
                self.assertNotIn("chatTemplateKwargs", runtime_model["compat"])
                self.assertNotIn("sendSessionAffinityHeaders", runtime_model["compat"])
                self.assertTrue(invocation["read_blocked"])
                self.assertTrue(invocation["write_blocked"])
                self.assertTrue(invocation["edit_blocked"])
                self.assertTrue(invocation["usr_local_absent"])
                self.assertTrue(invocation["usr_src_absent"])
                self.assertEqual(
                    "inside",
                    (self.taskdir / "inside-write.txt").read_text(encoding="utf-8"),
                )
                self.assertFalse((self.root / "outside-write.txt").exists())
                self.assertFalse(Path("/outside-edit.txt").exists())
                self.assertIn(f'"model":"{model.removeprefix("openrouter/")}"', result.stdout)
                self.assertIn('"totalTokens":14', result.stdout)
                self.assertIn('"total":0.3', result.stdout)
                self.assertIn("tokens used: 14", result.stdout)
                self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
                self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))
                self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))

    def test_rejects_malformed_selectors(self) -> None:
        for model in (
            "OpenRouter/x-ai/grok-4.5",
            "openrouter/x-ai",
            "openrouter//grok-4.5",
            "openrouter/x-ai/grok/4.5",
            "x-ai/grok-4.5",
        ):
            with self.subTest(model=model):
                result = self.run_wrapper(model)
                self.assertEqual(64, result.returncode)
                self.assertIn("exact lowercase", result.stderr)

    def test_rejects_missing_and_malformed_auth_without_values(self) -> None:
        missing = self.root / "missing"
        result = self.run_wrapper("openrouter/x-ai/grok-4.5", auth_dir=missing)
        self.assertEqual(64, result.returncode)
        self.assertNotIn("must-not-reach-pi", result.stderr)
        (self.agent_dir / "auth.json").write_text('{"secret":"do-not-print"}', encoding="utf-8")
        result = self.run_wrapper("openrouter/x-ai/grok-4.5")
        self.assertEqual(64, result.returncode)
        self.assertIn("malformed", result.stderr)
        self.assertNotIn("do-not-print", result.stderr)

    def test_ignores_malicious_models_json_and_pins_cached_endpoint(self) -> None:
        (self.agent_dir / "models.json").write_text(
            json.dumps(
                {
                    "providers": {
                        "openrouter": {
                            "baseUrl": "https://attacker.invalid/v1",
                            "models": [{"id": "x-ai/grok-4.5"}],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        result = self.run_wrapper(DEFAULT_MODEL)
        self.assertEqual(0, result.returncode, result.stderr)
        invocation = json.loads((self.taskdir / "invocation.json").read_text())
        self.assertEqual(["models.json"], invocation["visible_agent_files"])
        model = invocation["models_config"]["providers"]["openrouter"]["models"][0]
        self.assertEqual(OPENROUTER_ENDPOINT, model["baseUrl"])
        self.assertNotIn("attacker.invalid", json.dumps(invocation))

    def test_rejects_bad_or_missing_exact_model_cache_before_invocation(self) -> None:
        cases = (
            ("missing", None, None, None),
            ("malformed-json", "{malformed", None, None),
            ("wrong-provider", None, "other", OPENROUTER_ENDPOINT),
            ("wrong-id", None, "openrouter", OPENROUTER_ENDPOINT),
            ("wrong-base-url", None, "openrouter", "https://proxy.invalid/v1"),
            ("wrong-api", None, "openrouter", OPENROUTER_ENDPOINT),
        )
        for name, raw, provider, base_url in cases:
            with self.subTest(name=name):
                invocation = self.taskdir / "invocation.json"
                invocation.unlink(missing_ok=True)
                cache_path = self.agent_dir / "models-store.json"
                if name == "missing":
                    cache_path.unlink(missing_ok=True)
                elif raw is not None:
                    cache_path.write_text(raw, encoding="utf-8")
                elif name == "wrong-id":
                    self.write_model_cache(
                        "different/model",
                        provider=provider or "openrouter",
                        base_url=base_url or OPENROUTER_ENDPOINT,
                    )
                elif name == "wrong-api":
                    self.write_model_cache(
                        "x-ai/grok-4.5",
                        api="openai-responses",
                    )
                else:
                    self.write_model_cache(
                        "x-ai/grok-4.5",
                        provider=provider or "openrouter",
                        base_url=base_url or OPENROUTER_ENDPOINT,
                    )
                result = self.run_wrapper(DEFAULT_MODEL)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("cache is missing or malformed", result.stderr)
                self.assertFalse(invocation.exists())
                self.assertNotIn("proxy.invalid", result.stdout + result.stderr)
                self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))
                self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))
                self.write_model_cache("x-ai/grok-4.5")

    def test_rejects_malformed_retained_model_fields_before_invocation(self) -> None:
        cases = (
            ("name-type", ("name",), 1, False),
            ("reasoning-type", ("reasoning",), "true", False),
            ("input-modality", ("input",), ["text", "audio"], False),
            ("input-duplicate", ("input",), ["text", "text"], False),
            ("cost-type", ("cost", "input"), "1", False),
            ("cost-missing", ("cost", "cacheRead"), None, True),
            ("context-bool", ("contextWindow",), True, False),
            ("max-zero", ("maxTokens",), 0, False),
            ("max-over-context", ("maxTokens",), 1001, False),
            ("compat-not-object", ("compat",), [], False),
            (
                "compat-bool-type",
                ("compat", "supportsDeveloperRole"),
                "false",
                False,
            ),
            (
                "compat-max-field",
                ("compat", "maxTokensField"),
                "attacker_field",
                False,
            ),
            (
                "compat-thinking-format",
                ("compat", "thinkingFormat"),
                "attacker_format",
                False,
            ),
            (
                "compat-cache-control",
                ("compat", "cacheControlFormat"),
                "attacker_format",
                False,
            ),
        )
        for name, path, value, delete in cases:
            with self.subTest(name=name):
                invocation = self.taskdir / "invocation.json"
                invocation.unlink(missing_ok=True)
                self.write_model_cache("x-ai/grok-4.5")
                cache_path = self.agent_dir / "models-store.json"
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
                parent = cache["openrouter"]["models"][0]
                for key in path[:-1]:
                    parent = parent[key]
                if delete:
                    del parent[path[-1]]
                else:
                    parent[path[-1]] = value
                cache_path.write_text(json.dumps(cache), encoding="utf-8")
                result = self.run_wrapper(DEFAULT_MODEL)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("cache is missing or malformed", result.stderr)
                self.assertFalse(invocation.exists())
                self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))
                self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))


    def test_rejects_symlink_and_unsafe_root_taskdirs(self) -> None:
        link = self.root / "task-link"
        link.symlink_to(self.taskdir, target_is_directory=True)
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "RINGER_PI_OPENROUTER_TEST_MODE": "1",
                "RINGER_TEST_PI_BIN": str(self.fake_pi),
                "RINGER_PI_OPENROUTER_AGENT_DIR": str(self.agent_dir),
            }
        )
        linked = subprocess.run(
            [str(WRAPPER), str(link), DEFAULT_MODEL, "prompt"],
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(64, linked.returncode)
        self.assertIn("symbolic link", linked.stderr)
        unsafe = subprocess.run(
            [str(WRAPPER), "/", DEFAULT_MODEL, "prompt"],
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(64, unsafe.returncode)
        self.assertIn("unsafe root", unsafe.stderr)

    def test_rejects_task_and_agent_directory_overlap_before_pi_starts(self) -> None:
        equal = self.agent_dir
        parent = self.root
        child = self.agent_dir / "task-child"
        child.mkdir()
        linked_agent = self.root / "agent-link"
        linked_agent.symlink_to(self.agent_dir, target_is_directory=True)
        cases = (
            ("equal", equal, self.agent_dir),
            ("parent", parent, self.agent_dir),
            ("child", child, self.agent_dir),
            ("symlinked-agent", child, linked_agent),
        )
        for name, taskdir, auth_dir in cases:
            with self.subTest(name=name):
                for marker in (equal / "invocation.json", parent / "invocation.json", child / "invocation.json"):
                    marker.unlink(missing_ok=True)
                result = self.run_wrapper(
                    DEFAULT_MODEL, auth_dir=auth_dir, taskdir=taskdir
                )
                self.assertEqual(64, result.returncode, result.stderr)
                self.assertIn("overlaps Pi agent", result.stderr)
                self.assertFalse((taskdir / "invocation.json").exists())
                self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)

    def test_unavailable_bwrap_and_fake_pi_fail_before_invocation(self) -> None:
        invocation = self.taskdir / "invocation.json"
        env_extra = {
            "RINGER_TEST_BWRAP_BIN": str(self.root / "missing-bwrap"),
        }
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "RINGER_PI_OPENROUTER_TEST_MODE": "1",
                "RINGER_TEST_PI_BIN": str(self.fake_pi),
                "RINGER_PI_OPENROUTER_AGENT_DIR": str(self.agent_dir),
                "TMPDIR": str(self.root),
                **env_extra,
            }
        )
        missing_bwrap = subprocess.run(
            [str(WRAPPER), str(self.taskdir), DEFAULT_MODEL, "prompt"],
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(127, missing_bwrap.returncode)
        self.assertIn("bubblewrap is unavailable", missing_bwrap.stderr)
        self.assertFalse(invocation.exists())

        env["RINGER_TEST_BWRAP_BIN"] = "/usr/bin/bwrap"
        env["RINGER_TEST_PI_BIN"] = str(self.root / "missing-pi")
        missing_pi = subprocess.run(
            [str(WRAPPER), str(self.taskdir), DEFAULT_MODEL, "prompt"],
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertNotEqual(0, missing_pi.returncode)
        self.assertIn("test Pi JavaScript worker is unavailable", missing_pi.stderr)
        self.assertFalse(invocation.exists())
        self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))

    def test_unsupported_production_package_layout_fails_before_invocation(self) -> None:
        fake_bin_dir = self.root / "bin"
        fake_bin_dir.mkdir()
        fake_command = fake_bin_dir / "pi"
        fake_command.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        fake_command.chmod(0o755)
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "PATH": f"{fake_bin_dir}:/usr/bin",
                "RINGER_PI_OPENROUTER_AGENT_DIR": str(self.agent_dir),
                "TMPDIR": str(self.root),
            }
        )
        result = subprocess.run(
            [str(WRAPPER), str(self.taskdir), DEFAULT_MODEL, "prompt"],
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(127, result.returncode)
        self.assertIn("package layout is unsupported", result.stderr)
        self.assertFalse((self.taskdir / "invocation.json").exists())
        self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))

    def test_requires_documented_openrouter_auth_metadata_shape(self) -> None:
        fixtures = (
            ("non-empty-malformed", {"openrouter": {"unexpected": "value"}}),
            ("wrong-type", {"openrouter": {"type": "oauth", "key": "value"}}),
            ("empty-key", {"openrouter": {"type": "api_key", "key": ""}}),
            ("whitespace-key", {"openrouter": {"type": "api_key", "key": "  "}}),
            ("non-string-key", {"openrouter": {"type": "api_key", "key": 123}}),
            ("command-key", {"openrouter": {"type": "api_key", "key": "!command"}}),
            ("interpolation-key", {"openrouter": {"type": "api_key", "key": "$TOKEN"}}),
        )
        for name, metadata in fixtures:
            with self.subTest(name=name):
                (self.agent_dir / "auth.json").write_text(
                    json.dumps(metadata), encoding="utf-8"
                )
                result = self.run_wrapper("openrouter/x-ai/grok-4.5")
                self.assertEqual(64, result.returncode)
                self.assertIn("malformed", result.stderr)
                self.assertNotIn("value", result.stderr)

        (self.agent_dir / "auth.json").write_text("{malformed", encoding="utf-8")
        malformed = self.run_wrapper("openrouter/x-ai/grok-4.5")
        self.assertEqual(64, malformed.returncode)
        self.assertIn("malformed", malformed.stderr)

        (self.agent_dir / "auth.json").write_text(
            json.dumps({"openrouter": {"type": "api_key", "key": "valid-metadata-key"}}),
            encoding="utf-8",
        )
        valid = self.run_wrapper("openrouter/x-ai/grok-4.5")
        self.assertEqual(0, valid.returncode, valid.stderr)
        self.assertNotIn("valid-metadata-key", valid.stdout + valid.stderr)

    def test_transcript_credential_leak_is_redacted_fatal_and_cleaned(self) -> None:
        result = self.run_wrapper(DEFAULT_MODEL, "print-key")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
        self.assertNotIn("[REDACTED]", result.stdout + result.stderr)
        self.assertIn("credential leak detected", result.stderr)
        self.assertNotIn("RINGER_PI_IDENTITY", result.stdout)
        self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))

    def test_source_auth_replacement_cannot_change_redaction_key(self) -> None:
        key_a = "fixture-openrouter-key-a-not-real"
        key_b = "fixture-openrouter-key-b-not-real"
        (self.agent_dir / "auth.json").write_text(
            json.dumps({"openrouter": {"type": "api_key", "key": key_a}}),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "RINGER_PI_OPENROUTER_TEST_MODE": "1",
                "RINGER_TEST_PI_BIN": str(self.fake_pi),
                "RINGER_PI_OPENROUTER_AGENT_DIR": str(self.agent_dir),
                "TMPDIR": str(self.root),
            }
        )
        process = subprocess.Popen(
            [str(WRAPPER), str(self.taskdir), DEFAULT_MODEL, "replace-auth-race"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        started = self.taskdir / "pi-started"
        for _ in range(500):
            if started.exists():
                break
            time.sleep(0.01)
        self.assertTrue(started.exists(), "fake Pi did not reach replacement barrier")
        replacement = self.agent_dir / "auth.new"
        replacement.write_text(
            json.dumps({"openrouter": {"type": "api_key", "key": key_b}}),
            encoding="utf-8",
        )
        replacement.replace(self.agent_dir / "auth.json")
        (self.taskdir / "pi-release").write_text("release", encoding="utf-8")
        stdout, stderr = process.communicate(timeout=10)
        combined = stdout + stderr
        self.assertNotEqual(0, process.returncode)
        self.assertNotIn(key_a, combined)
        self.assertNotIn(key_b, combined)
        self.assertNotIn("RINGER_PI_IDENTITY", stdout)
        self.assertIn("credential leak detected", stderr)
        self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-status.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))

    def test_nonzero_child_status_propagates_through_supervisor(self) -> None:
        result = self.run_wrapper(DEFAULT_MODEL, "exit-23")
        self.assertEqual(23, result.returncode, result.stderr)
        self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
        self.assertNotIn("RINGER_PI_IDENTITY", result.stdout)
        self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-status.*")))
        self.assertEqual([], list(self.root.glob("pi-openrouter-agent.*")))

    def test_rejects_identity_errors_aborts_and_negative_accounting(self) -> None:
        for spec in (
            "wrong-provider",
            "wrong-model",
            "early-wrong-identity",
            "top-error",
            "aborted",
            "negative-usage",
            "missing-cost",
            "partial-cost",
            "bool-cost",
            "nan-cost",
            "infinite-cost",
            "negative-cost",
        ):
            with self.subTest(spec=spec):
                result = self.run_wrapper("openrouter/x-ai/grok-4.5", spec)
                self.assertNotEqual(0, result.returncode)
                self.assertNotIn("RINGER_PI_IDENTITY", result.stdout)
                self.assertEqual([], list(self.root.glob("pi-openrouter-ringer.*")))

    def test_bash_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(WRAPPER)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
