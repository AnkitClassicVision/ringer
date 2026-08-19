#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ROOT / "engines"

spec = importlib.util.spec_from_file_location("ringer_auth_local_test", ROOT / "ringer.py")
assert spec and spec.loader
ringer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ringer
spec.loader.exec_module(ringer)


class AuthFirstRoutingLocalTests(unittest.TestCase):
    def manifest(self, engine: str, model: str = "", engine_args: tuple[str, ...] = ()):
        task = ringer.TaskSpec(
            key="route", spec="prompt", check="true", engine=engine,
            model=model, engine_args=engine_args,
        )
        return ringer.Manifest(
            run_name="auth-route-test", workdir=Path("/tmp/ringer-auth-route-test"),
            max_parallel=1, worktrees=False, repo=None, tasks=(task,),
        )

    def test_builtin_codex_uses_repo_oauth_wrapper(self) -> None:
        engine = ringer.built_in_codex_engine()
        self.assertEqual(str(ENGINES / "codex-oauth.sh"), engine.bin)

    def test_config_cannot_replace_codex_wrapper(self) -> None:
        with self.assertRaisesRegex(ValueError, "trusted engines/codex-oauth.sh"):
            ringer.load_engines({"codex": {"bin": "codex"}})

    def test_restricted_families_require_trusted_wrapper(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="renamed-model-cli",
            args_template=("run", "-m", "{model}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(engines={"custom": custom, "codex": ringer.built_in_codex_engine()})
        for model, family in (
            ("gpt-5.6", "openai"),
            ("sonnet4", "anthropic"),
            ("zai-coding-plan/glm-5.2", "glm"),
        ):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, f"restricted {family}"):
                    ringer.validate_manifest_engines(self.manifest("custom", model), config)

    def test_custom_model_harness_requires_capability_gate(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="renamed-opencode",
            args_template=("run", "-m", "{model}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
        )
        config = SimpleNamespace(engines={"custom": custom, "codex": ringer.built_in_codex_engine()})
        with self.assertRaisesRegex(ValueError, "auth_routing_trusted=true"):
            ringer.validate_manifest_engines(self.manifest("custom", "provider/model"), config)

    def test_capability_requires_exact_toml_boolean(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a TOML boolean"):
            ringer.load_engines({
                "custom": {
                    "bin": "custom-cli",
                    "args_template": ["run", "-m", "{model}", "{spec}"],
                    "auth_routing_trusted": "false",
                }
            })

    def test_engine_args_only_model_lane_requires_capability(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="renamed-model-cli",
            args_template=("run", "{engine_args}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
        )
        config = SimpleNamespace(
            engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
        )
        with self.assertRaisesRegex(ValueError, "auth_routing_trusted=true"):
            ringer.validate_manifest_engines(
                self.manifest("custom", engine_args=("-m", "provider/model")),
                config,
            )

    def test_hardcoded_restricted_model_requires_capability(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="renamed-model-cli",
            args_template=("run", "openai/gpt-5.6", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
        )
        config = SimpleNamespace(
            engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
        )
        with self.assertRaisesRegex(ValueError, "auth_routing_trusted=true"):
            ringer.validate_manifest_engines(self.manifest("custom"), config)

    def test_hardcoded_openrouter_model_requires_exact_pi_wrapper(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="custom-cli",
            args_template=("run", "openrouter/qwen/qwen3-coder", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(
            engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
        )
        with self.assertRaisesRegex(ValueError, "pi-openrouter-ringer.sh"):
            ringer.validate_manifest_engines(self.manifest("custom"), config)

    def test_embedded_static_openrouter_selectors_fail_closed(self) -> None:
        for token in (
            "model=openrouter/x-ai/grok-4.5",
            "prefix:openrouter/x-ai/grok-4.5",
            "--route=openrouter/x-ai/grok-4.5",
            "OpenRouter/x-ai/grok-4.5",
            "prefix:OPENROUTER/x-ai/grok-4.5",
            "openrouter/x-ai/grok/4.5",
        ):
            with self.subTest(token=token):
                custom = ringer.EngineConfig(
                    name="custom",
                    bin="trusted-custom-cli",
                    args_template=("run", token, "{spec}"),
                    sandbox_args=(),
                    full_access_args=(),
                    token_regex=None,
                    auth_routing_trusted=True,
                )
                config = SimpleNamespace(
                    engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
                )
                with self.assertRaisesRegex(ValueError, "embedded OpenRouter"):
                    ringer.validate_manifest_engines(self.manifest("custom"), config)

    def test_codex_rejects_compact_and_positional_model_selectors(self) -> None:
        config = SimpleNamespace(engines={"codex": ringer.built_in_codex_engine()})
        for args in (
            ("-cmodel=anthropic/claude-sonnet",),
            ("-mglm",),
            ("model=glm",),
        ):
            with self.subTest(args=args):
                with self.assertRaisesRegex(ValueError, "compact selector"):
                    ringer.validate_manifest_engines(
                        self.manifest("codex", engine_args=args),
                        config,
                    )

    def test_manifest_route_overrides_are_blocked_on_custom_harness(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="trusted-custom-cli",
            args_template=("run", "-m", "{model}", "{engine_args}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(engines={"custom": custom, "codex": ringer.built_in_codex_engine()})
        for args in (
            ("--provider", "metered"),
            ("--base-url", "https://example.invalid"),
            ("endpoint=https://example.invalid",),
        ):
            with self.subTest(args=args):
                with self.assertRaisesRegex(ValueError, "manifest-controlled"):
                    ringer.validate_manifest_engines(
                        self.manifest("custom", "provider/model", args),
                        config,
                    )

        live = SimpleNamespace(engines={
            name: ringer.EngineConfig(
                name=name,
                bin=f"{name}-cli",
                args_template=("-m", "{model}", "{engine_args}", "{spec}"),
                sandbox_args=(), full_access_args=(), token_regex=None,
                auth_routing_trusted=True, model_default="provider/model",
            )
            for name in ("xai", "seedance")
        })
        live.engines["codex"] = ringer.built_in_codex_engine()
        for engine in ("xai", "seedance"):
            with self.subTest(live_engine=engine):
                with self.assertRaisesRegex(ValueError, "manifest-controlled"):
                    ringer.validate_manifest_engines(
                        self.manifest(
                            engine,
                            engine_args=("--base-url", "https://example.invalid"),
                        ),
                        live,
                    )

    def test_non_coding_plan_glm_selector_is_rejected(self) -> None:
        local = ringer.EngineConfig(
            name="local",
            bin="local-cli",
            args_template=("-m", "{model}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(
            engines={"local": local, "codex": ringer.built_in_codex_engine()}
        )
        for model in ("glm", "GLM", "ollama/glm", "ollama/glm-4.7"):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "Z.AI Coding Plan selector"):
                    ringer.validate_manifest_engines(
                        self.manifest("local", model),
                        config,
                    )

    def test_openrouter_text_routes_use_only_trusted_pi_wrapper(self) -> None:
        pi_openrouter = ringer.EngineConfig(
            name="pi-openrouter",
            bin=str(ENGINES / "pi-openrouter-ringer.sh"),
            args_template=("{taskdir}", "{model}", "{spec}"),
            sandbox_args=(),
            full_access_args=(),
            token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(
            engines={
                "pi-openrouter": pi_openrouter,
                "codex": ringer.built_in_codex_engine(),
            }
        )
        custom = ringer.EngineConfig(
            name="custom",
            bin="custom-cli",
            args_template=("run", "-m", "{model}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        opencode = ringer.EngineConfig(
            name="opencode",
            bin=str(ENGINES / "opencode-auth-policy.sh"),
            args_template=("{taskdir}", "run", "-m", "{model}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config.engines.update({"custom": custom, "opencode": opencode})
        for model in (
            "openrouter/x-ai/grok-4.5",
            "openrouter/z-ai/glm-5.2",
            "openrouter/moonshotai/kimi-k3",
            "openrouter/openai/gpt-5.6",
            "openrouter/anthropic/claude-opus-4.1",
            "openrouter/google/gemini-2.5-pro",
            "openrouter/qwen/qwen3-coder",
        ):
            with self.subTest(model=model):
                ringer.validate_manifest_engines(
                    self.manifest("pi-openrouter", model), config
                )
                for engine in ("custom", "opencode"):
                    with self.assertRaisesRegex(ValueError, "pi-openrouter-ringer.sh"):
                        ringer.validate_manifest_engines(
                            self.manifest(engine, model), config
                        )

        for model in ("openrouter/X-ai/grok-4.5", "openrouter/x-ai/grok/4.5"):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "exact lowercase"):
                    ringer.validate_manifest_engines(
                        self.manifest("pi-openrouter", model),
                        config,
                    )

    def test_route_policy_is_enforced_without_any_trusted_wrapper_in_config(self) -> None:
        custom = ringer.EngineConfig(
            name="custom",
            bin="/tmp/custom-model-cli",
            args_template=("run", "-m", "{model}", "{spec}"),
            sandbox_args=(),
            full_access_args=(),
            token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(engines={"custom": custom})
        for model, error in (
            ("openrouter/x-ai/grok-4.5", "pi-openrouter-ringer.sh"),
            ("openai/gpt-5.6", "restricted openai"),
            ("anthropic/claude-sonnet-5", "restricted anthropic"),
            ("google/gemini-3.6-flash", "restricted google"),
            ("kimi-code/k3", "restricted kimi"),
            ("moonshotai/kimi-k3", "restricted kimi"),
            ("zai-coding-plan/glm-5.2", "restricted glm"),
        ):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, error):
                    ringer.validate_manifest_engines(
                        self.manifest("custom", model),
                        config,
                    )

    def test_model_family_boundaries(self) -> None:
        self.assertEqual("anthropic", ringer.restricted_model_family("opus4"))
        self.assertEqual("openai", ringer.restricted_model_family("azure/o12-mini"))
        self.assertEqual("glm", ringer.restricted_model_family("local/glm5"))
        self.assertEqual("glm", ringer.restricted_model_family("glm"))
        self.assertEqual("glm", ringer.restricted_model_family("ollama/GLM"))
        self.assertEqual("google", ringer.restricted_model_family("gemini-2.5-pro"))
        self.assertEqual("kimi", ringer.restricted_model_family("kimi-code/k3"))
        self.assertEqual("kimi", ringer.restricted_model_family("kimi-k3"))
        self.assertEqual("kimi", ringer.restricted_model_family("moonshotai/kimi-k3"))
        self.assertEqual("kimi", ringer.restricted_model_family("k3-256k"))
        self.assertIsNone(ringer.restricted_model_family("example/octopus-1"))
        self.assertIsNone(ringer.restricted_model_family("example/sonneteer"))
        self.assertIsNone(ringer.restricted_model_family("example/k3s-inference"))

    def test_kimi_oauth_wrapper_satisfies_kimi_family(self) -> None:
        kimi = ringer.EngineConfig(
            name="kimi",
            bin=str(ENGINES / "kimi-oauth.sh"),
            model_default="kimi-code/k3",
            args_template=("-m", "{model}", "{engine_args}", "-p", "{spec}"),
            sandbox_args=(),
            full_access_args=(),
            token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(engines={"kimi": kimi})
        ringer.validate_manifest_engines(self.manifest("kimi", "kimi-code/k3"), config)
        ringer.validate_manifest_engines(self.manifest("kimi"), config)

    def test_kimi_openrouter_backup_stays_on_pi_wrapper(self) -> None:
        kimi_api = ringer.EngineConfig(
            name="kimi-api",
            bin=str(ENGINES / "pi-openrouter-ringer.sh"),
            model_default="openrouter/moonshotai/kimi-k3",
            args_template=("{taskdir}", "{model}", "{spec}"),
            sandbox_args=(),
            full_access_args=(),
            token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(engines={"kimi-api": kimi_api})
        ringer.validate_manifest_engines(self.manifest("kimi-api"), config)


if __name__ == "__main__":
    unittest.main()
