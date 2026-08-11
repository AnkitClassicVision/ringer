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
    def manifest(
        self,
        engine: str,
        model: str = "",
        engine_args: tuple[str, ...] = (),
        *,
        full_access: bool = False,
        spec: str = "prompt",
    ):
        task = ringer.TaskSpec(
            key="route", spec=spec, check="true", engine=engine,
            model=model, engine_args=engine_args, full_access=full_access,
        )
        return ringer.Manifest(
            run_name="auth-route-test", workdir=Path("/tmp/ringer-auth-route-test"),
            max_parallel=1, worktrees=False, repo=None, tasks=(task,),
        )

    def auth_config(self, *engine_names: str) -> SimpleNamespace:
        engines: dict[str, ringer.EngineConfig] = {"codex": ringer.built_in_codex_engine()}
        for name in engine_names:
            if name == "local":
                engines[name] = ringer.EngineConfig(
                    name=name,
                    bin=str(ENGINES / "opencode-auth-policy.sh"),
                    args_template=("run", "-m", "{model}", "{spec}"),
                    sandbox_args=(), full_access_args=(), token_regex=None,
                )
            else:
                engines[name] = ringer.EngineConfig(
                    name=name, bin=f"{name}-worker",
                    args_template=("run", "{engine_args}", "{spec}"),
                    sandbox_args=(), full_access_args=(), token_regex=None,
                    auth_routing_trusted=True,
                )
        return SimpleNamespace(engines=engines)

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

    def test_model_args_lane_requires_capability(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="renamed-model-cli",
            args_template=("run", "{model_args}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
        )
        config = SimpleNamespace(
            engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
        )
        with self.assertRaisesRegex(ValueError, "auth_routing_trusted=true"):
            ringer.validate_manifest_engines(
                self.manifest("custom", model="provider/model"), config
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

    def test_custom_static_protected_routes_require_the_matching_oauth_wrapper(self) -> None:
        config = SimpleNamespace(engines={"codex": ringer.built_in_codex_engine()})
        cases = (
            (("run", "--provider", "openai", "{spec}"), (), "openai"),
            (("run", "--provider=openai", "{spec}"), (), "openai"),
            (("run", "provider=openai", "{spec}"), (), "openai"),
            (("run", "-c", "provider=openai", "{spec}"), (), "openai"),
            (("run", "--config=backend=anthropic", "{spec}"), (), "anthropic"),
            (("run", "--backend", "anthropic", "{spec}"), (), "anthropic"),
            (("run", "--provider='OPENAI'", "{spec}"), (), "openai"),
            (("run", "{spec}"), ("--provider", "openai"), "openai"),
            (("run", "{spec}"), ("--provider=openai",), "openai"),
            (("run", "{spec}"), ("provider=openai",), "openai"),
            (("run", "{spec}"), ("-c", "provider=openai"), "openai"),
            (("run", "{spec}"), ("--backend", "anthropic"), "anthropic"),
            (("run", "{spec}"), ("--backend=anthropic",), "anthropic"),
            (("run", "{spec}"), ("backend=anthropic",), "anthropic"),
            (("run", "{spec}"), ("--config", "backend=anthropic"), "anthropic"),
            (("run", "{spec}"), ("--config=backend=anthropic",), "anthropic"),
        )
        for args_template, engine_args, family in cases:
            with self.subTest(args_template=args_template, engine_args=engine_args):
                custom = ringer.EngineConfig(
                    name="custom",
                    bin="trusted-custom-cli",
                    args_template=args_template,
                    sandbox_args=(), full_access_args=(), token_regex=None,
                    auth_routing_trusted=True,
                )
                config.engines["custom"] = custom
                with self.assertRaisesRegex(ValueError, f"restricted {family}.*trusted engines/"):
                    ringer.validate_manifest_engines(
                        self.manifest("custom", engine_args=engine_args), config
                    )

    def test_custom_benign_static_routes_remain_accepted(self) -> None:
        custom = ringer.EngineConfig(
            name="custom",
            bin="trusted-custom-cli",
            args_template=("run", "--provider=example", "-c", "backend=local", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(
            engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
        )
        ringer.validate_manifest_engines(self.manifest("custom"), config)

    def test_composed_split_protected_selectors_require_matching_wrapper(self) -> None:
        config = SimpleNamespace(engines={"codex": ringer.built_in_codex_engine()})
        cases = (
            (("run", "--provider", "{engine_args}", "{spec}"), ("openai",), "openai"),
            (("run", "-m", "{engine_args}", "{spec}"), ("gpt-5.6",), "openai"),
            (("run", "--model", "{engine_args}", "{spec}"), ("claude-sonnet",), "anthropic"),
            (("run", "-c", "{engine_args}", "{spec}"), ("model=zai-coding-plan/glm-5.2",), "glm"),
        )
        for args_template, engine_args, family in cases:
            with self.subTest(args_template=args_template, engine_args=engine_args):
                config.engines["custom"] = ringer.EngineConfig(
                    name="custom", bin="trusted-custom-cli",
                    args_template=args_template,
                    sandbox_args=(), full_access_args=(), token_regex=None,
                    auth_routing_trusted=True,
                )
                with self.assertRaisesRegex(ValueError, f"restricted {family}.*trusted engines/"):
                    ringer.validate_manifest_engines(
                        self.manifest("custom", engine_args=engine_args), config
                    )

    def test_composed_static_access_placeholders_require_matching_wrapper(self) -> None:
        config = SimpleNamespace(engines={"codex": ringer.built_in_codex_engine()})
        cases = (
            (("run", "--provider", "{access_args}", "{spec}"), ("openai",), (), False, "openai"),
            (("run", "--model", "{sandbox_args}", "{spec}"), ("claude-sonnet",), (), False, "anthropic"),
            (("run", "-c", "{full_access_args}", "{spec}"), (), ("model=zai-coding-plan/glm-5.2",), True, "glm"),
        )
        for args_template, sandbox_args, full_access_args, full_access, family in cases:
            with self.subTest(args_template=args_template):
                config.engines["custom"] = ringer.EngineConfig(
                    name="custom", bin="trusted-custom-cli",
                    args_template=args_template,
                    sandbox_args=sandbox_args, full_access_args=full_access_args,
                    token_regex=None, auth_routing_trusted=True,
                )
                with self.assertRaisesRegex(ValueError, f"restricted {family}.*trusted engines/"):
                    ringer.validate_manifest_engines(
                        self.manifest("custom", full_access=full_access), config
                    )

    def test_composed_benign_value_and_prompt_text_remain_inert(self) -> None:
        custom = ringer.EngineConfig(
            name="custom", bin="trusted-custom-cli",
            args_template=("run", "--provider", "{engine_args}", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config = SimpleNamespace(
            engines={"custom": custom, "codex": ringer.built_in_codex_engine()}
        )
        ringer.validate_manifest_engines(
            self.manifest("custom", engine_args=("example",)) , config
        )
        custom = ringer.EngineConfig(
            name="custom", bin="trusted-custom-cli",
            args_template=("run", "{spec}"),
            sandbox_args=(), full_access_args=(), token_regex=None,
            auth_routing_trusted=True,
        )
        config.engines["custom"] = custom
        ringer.validate_manifest_engines(
            self.manifest(
                "custom",
                spec="Do not route --provider openai or -c model=zai-coding-plan/glm-5.2.",
            ),
            config,
        )

    def test_canonical_wrappers_accept_composed_protected_selectors(self) -> None:
        cases = (
            ("codex", "codex-oauth.sh", ("run", "--provider", "{engine_args}", "{spec}"), ("openai",)),
            ("claude", "claude-oauth.sh", ("run", "--model", "{engine_args}", "{spec}"), ("claude-sonnet",)),
            ("opencode", "opencode-auth-policy.sh", ("run", "-c", "{engine_args}", "{spec}"), ("model=zai-coding-plan/glm-5.2",)),
        )
        for engine_name, wrapper, args_template, engine_args in cases:
            with self.subTest(engine=engine_name):
                engine = ringer.EngineConfig(
                    name=engine_name, bin=str(ENGINES / wrapper), args_template=args_template,
                    sandbox_args=(), full_access_args=(), token_regex=None,
                )
                config = SimpleNamespace(
                    engines={engine_name: engine, "codex": ringer.built_in_codex_engine()}
                )
                ringer.validate_manifest_engines(
                    self.manifest(engine_name, engine_args=engine_args), config
                )

    def test_composed_model_selector_malformed_and_duplicate_checks(self) -> None:
        config = SimpleNamespace(engines={"codex": ringer.built_in_codex_engine()})
        cases = (
            (("run", "-m", "{engine_args}", "{spec}"), ("--other-option",), "malformed model selector"),
            (("run", "-m", "gpt-5.6", "{engine_args}", "{spec}"), ("--model", "gpt-5.5"), "second model selector"),
        )
        for args_template, engine_args, message in cases:
            with self.subTest(args_template=args_template, engine_args=engine_args):
                config.engines["custom"] = ringer.EngineConfig(
                    name="custom", bin="trusted-custom-cli", args_template=args_template,
                    sandbox_args=(), full_access_args=(), token_regex=None,
                    auth_routing_trusted=True,
                )
                with self.assertRaisesRegex(ValueError, message):
                    ringer.validate_manifest_engines(
                        self.manifest("custom", engine_args=engine_args), config
                    )

    def test_codex_rejects_compact_and_positional_model_selectors(self) -> None:
        config = self.auth_config()
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

        live = self.auth_config("xai", "seedance")
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
        config = self.auth_config("local")
        for model in ("glm", "GLM", "ollama/glm", "ollama/glm-4.7"):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "Z.AI Coding Plan selector"):
                    ringer.validate_manifest_engines(
                        self.manifest("local", model),
                        config,
                    )

    def test_model_family_boundaries(self) -> None:
        self.assertEqual("anthropic", ringer.restricted_model_family("opus4"))
        self.assertEqual("openai", ringer.restricted_model_family("azure/o12-mini"))
        self.assertEqual("glm", ringer.restricted_model_family("local/glm5"))
        self.assertEqual("glm", ringer.restricted_model_family("glm"))
        self.assertEqual("glm", ringer.restricted_model_family("ollama/GLM"))
        self.assertIsNone(ringer.restricted_model_family("example/octopus-1"))
        self.assertIsNone(ringer.restricted_model_family("example/sonneteer"))


if __name__ == "__main__":
    unittest.main()
