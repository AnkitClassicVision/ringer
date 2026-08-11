# OAuth-first and Pi/OpenRouter routing contract

Status: implementation yardstick
Owner: Ankit
Date: 2026-07-30

## Purpose

Ringer must use provider-native subscription/OAuth CLIs for the primary worker lane and Pi as the single text-agent harness for OpenRouter API models. OpenCode is not an approved OpenRouter harness for new routes.

## Route policy

1. OpenAI primary: Codex CLI through `engines/codex-oauth.sh`.
2. Anthropic primary: Claude Code through `engines/claude-oauth.sh`.
3. Google primary for headless Ringer workers: Gemini CLI through `engines/gemini-oauth.sh`. Antigravity remains the preferred interactive Google client, but its installed `chat` command opens an editor session and does not expose a headless stdout worker contract.
4. Z.AI/GLM primary: a provider-native Z.AI CLI only after one is installed, authenticated, and proven by a checked Ringer probe. No such executable is currently installed.
5. API fallback and API-only text models: `engine = "pi-openrouter"` with an explicit exact `model = "openrouter/<publisher>/<model>"` selector.
6. OpenRouter model families that also have an OAuth lane may use Pi only when the manifest explicitly selects `pi-openrouter`. Ringer must not silently spend API money after an OAuth failure.
7. OpenRouter video/media adapters remain separate because Pi's text-agent contract is not the Video API contract.
8. The Pi text lane is Linux-only and must run inside bubblewrap. If bubblewrap or the supported Pi package entrypoint is unavailable, Ringer fails before invoking Pi; there is no unconfined fallback.

## Pi containment contract

The wrapper canonicalizes the task directory and source agent directory before scratch creation or auth access. It rejects symbolic-link and unsafe root task directories plus every equal, ancestor, or descendant overlap with the agent directory; canonical common-path comparison prevents symlink aliases from bypassing the check. Production also rejects overlap with the resolved installed Pi package. The task directory is mounted read-write only at `/workspace`.

The sandbox has a private `/tmp`, minimal `/dev`, no `/proc`, no broad `/usr` mount, inherited networking, and no host home, repository, or sibling mounts. The wrapper resolves the trusted `/usr/bin/node`, strictly parses its `ldd` dependencies and ELF interpreter, rejects unresolved or malformed paths and basename collisions, mounts Node at `/runtime/bin/node`, mounts only resolved libraries at `/runtime/lib`, and supplies an explicit `LD_LIBRARY_PATH`. The interpreter is mounted at its ELF-required path. Only narrow NSS, TLS, DNS, and time data are exposed; `/usr/local`, `/usr/src`, shells, and unrelated host files are absent. With `/proc` absent, Pi's read tool cannot reach process environments or command lines. Pi retains only the `read,write,edit` tools; bash is not enabled.

Each invocation creates a host scratch directory containing only a sanitized one-model `models-store.json`, then mounts that directory read-only at `/agent`. No credential file is copied or mounted. One Python supervisor opens and validates the source `auth.json` exactly once without printing it, rejects unsupported command/interpolation strings beginning with `!` or `$`, and retains the literal key only in memory for both launch and transcript redaction. The supervisor calls bubblewrap with a clean environment containing only explicit safe values plus `OPENROUTER_API_KEY`; the key is absent from argv, temporary files, mounted filesystems, diagnostics, status, and success markers. Pinning launch and redaction to the same in-memory value removes the source-auth replacement race. The selected model record must have provider `openrouter`, an ID exactly equal to the requested selector suffix, and base URL `https://openrouter.ai/api/v1`. Unknown and routing-capable cached fields are removed. Source `models.json`, settings, extensions, prompts, and all other global agent state are ignored and cannot be read inside the sandbox. A missing, duplicate, or malformed exact cache record fails before Pi invocation without printing credential contents.

The installed `pi` command must resolve to the package `dist/cli.js`. The package is mounted read-only at `/opt/pi-package` and invoked with `/runtime/bin/node`, so its installation under a host home directory does not expose that home tree. Test mode mounts JavaScript at `/opt/pi-test.js` and executes it with the same minimal Node runtime, without a Python standard-library mount. The supervisor constructs the environment from scratch, so bubblewrap does not use `--clearenv`, captures combined stdout/stderr directly to the mode-0600 transcript, waits for the exact child status, and scans with the same in-memory key. A match is replaced in scratch output with `[REDACTED]` before any shell read, only a generic credential-leak error is emitted, the run fails, and the shell never prints a leaked transcript. The supervisor reports only non-secret machine-readable state through a mode-0600 status file. The status file, output transcript, and ephemeral agent directory are removed on every exit and before success markers.

## Current frontier examples

These exact OpenRouter catalog IDs were present on 2026-07-30:

- `openrouter/x-ai/grok-4.5`
- `openrouter/z-ai/glm-5.2`
- `openrouter/moonshotai/kimi-k3`

Catalog presence proves availability metadata only, not task quality or current endpoint health. Every new model/harness combination still needs a one-task checked probe before broad routing.

## Implementation units

- U1: Generalize `engines/pi-openrouter-ringer.sh` from one GLM model to any exact `openrouter/<publisher>/<model>` text selector while keeping provider/model identity and usage validation fail-closed.
- U2: Change manifest validation so every `openrouter/*` text selector requires the trusted Pi wrapper. Native OpenAI, Anthropic, and Google selectors continue to require their native OAuth wrappers. GLM without a proven native CLI uses Pi/OpenRouter.
- U3: Add the `pi-openrouter` engine to sample and live configuration. Replace active OpenCode/OpenRouter aliases with Pi-backed aliases or remove them when they cannot be represented safely.
- U4: Update model identity, README, model menu, and the Ringer skill so OpenCode is not described as the universal OpenRouter harness.
- U5: Add focused tests for generic Pi routing, model identity/accounting, route rejection, and native OAuth precedence; run the affected suite and the full test suite.
- U6: Confine Pi with mandatory Linux bubblewrap, sanitized ephemeral agent state, and a pinned exact-model OpenRouter cache while preserving the existing output, accounting, exit, and signal contract.

## Acceptance proof

1. `bash -n engines/pi-openrouter-ringer.sh` passes.
2. Fake-Pi tests prove exact argv, API-key environment scrubbing, provider/model identity matching, usage/cost markers, malformed selector rejection, wrong identity rejection, and no secret output.
3. Manifest tests accept Grok 4.5, GLM 5.2, Kimi K3, and OpenAI/Anthropic/Google OpenRouter fallbacks only through `pi-openrouter`.
4. Manifest tests reject OpenRouter text models through OpenCode or arbitrary trusted custom wrappers.
5. Native Codex, Claude, and Gemini OAuth routes remain accepted.
6. `config.sample.toml` and the live config parse, contain a Pi/OpenRouter engine, and no active OpenRouter text model points at OpenCode.
7. Focused tests and the full repository test suite pass without making a paid inference call.
8. Offline fake-Pi tests prove `/workspace` cwd, `/agent` isolation, ambient environment clearing, exact single-model cache pinning, sibling read and outside-write denial, inside-task writes, unsafe-task rejection, pre-invocation failure modes, and scratch cleanup.
9. `python3 /tmp/check_ringer_pi_boundary_final.py` passes and exports `/tmp/ringer-pi-openrouter-boundary-final.patch`.

## Non-goals

- No automatic paid failover after an OAuth/auth/runtime failure.
- No credential values in repository files, logs, tests, or chat.
- No claim that Antigravity is a headless Ringer engine before its CLI exposes a machine-readable completion contract.
- No claim that catalog presence proves model quality.
- No removal of specialized media adapters.
- No claim that the partial Codex Security exit-2 run passed; its Trusted Access account gate left coverage incomplete.
