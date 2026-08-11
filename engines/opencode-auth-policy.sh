#!/bin/bash
set -euo pipefail

fail() { printf 'opencode-auth-policy.sh: blocked ambiguous or restricted model route: %s\n' "$1" >&2; exit 64; }
opencode_bin=opencode
verify_only=0
if [[ "${1:-}" == "--ringer-verify-config-only" ]]; then
  verify_only=1
  shift
fi
unset RINGER_OAUTH_TEST_MODE RINGER_TEST_OPENCODE_BIN RINGER_OAUTH_VERIFY_CONFIG_ONLY
args=("$@")
policy_args=("${args[@]}")
policy_index=0
(( ${#policy_args[@]} >= 9 )) || fail "canonical OpenCode argv is required"
taskdir="${policy_args[$policy_index]}"
[[ -n "$taskdir" && "$taskdir" != -* ]] || fail "task directory is missing"
((policy_index += 1))
if (( policy_index < ${#policy_args[@]} )) && [[ "${policy_args[$policy_index]}" == "--no-sandbox" ]]; then
  ((policy_index += 1))
fi
(( policy_index < ${#policy_args[@]} )) && [[ "${policy_args[$policy_index]}" == "run" ]] || fail "only canonical OpenCode run argv is allowed"
((policy_index += 1))
model_flag="${policy_args[$policy_index]:-}"
case "$model_flag" in
  -m|--model)
    ((policy_index += 1))
    model="${policy_args[$policy_index]:-}"
    [[ -n "$model" && "$model" != -* ]] || fail "model selector is missing a value"
    ;;
  --model=*)
    model="${model_flag#--model=}"
    [[ -n "$model" ]] || fail "model selector is missing a value"
    ;;
  *) fail "exactly one model selector is required" ;;
esac
((policy_index += 1))

[[ "${policy_args[$policy_index]:-}" == "--dangerously-skip-permissions" ]] || fail "required OpenCode permission mode is missing"
((policy_index += 1))
[[ "${policy_args[$policy_index]:-}" == "--format" ]] || fail "required JSON output format is missing"
((policy_index += 1))
[[ "${policy_args[$policy_index]:-}" == "json" ]] || fail "required JSON output format is missing"
((policy_index += 1))

if [[ "${policy_args[$policy_index]:-}" == "--variant" ]]; then
  ((policy_index += 1))
  case "${policy_args[$policy_index]:-}" in
    low|high|max) ;;
    *) fail "OpenCode variant must be low, high, or max" ;;
  esac
  ((policy_index += 1))
fi

[[ "${policy_args[$policy_index]:-}" == "--dir" ]] || fail "canonical task directory option is missing"
((policy_index += 1))
[[ "${policy_args[$policy_index]:-}" == "$taskdir" ]] || fail "OpenCode task directory must match the wrapper task directory"
((policy_index += 1))
prompt="${policy_args[$policy_index]:-}"
[[ -n "$prompt" && "$prompt" != -* ]] || fail "exactly one prompt is required"
((policy_index += 1))
(( policy_index == ${#policy_args[@]} )) || fail "unexpected or repeated OpenCode arguments are not allowed"

lower="$(printf '%s' "$model" | LC_ALL=C tr '[:upper:]' '[:lower:]')"
segments="/${lower//:/\/}/"
has_segment() { [[ "$segments" =~ /$1/ ]]; }
if [[ "$lower" == zai-coding-plan/glm-* && "${lower#zai-coding-plan/glm-}" != "" && "${lower#zai-coding-plan/glm-}" != */* ]]; then
  coding_plan=1
elif [[ "$lower" == zai-coding-plan/* || "$lower" == openrouter/z-ai/* || "$lower" == z-ai/* ]] ||
     has_segment 'glm([.-]?[0-9].*|-.*)?' ; then
  fail "GLM requires the Z.AI Coding Plan selector zai-coding-plan/glm-*"
elif has_segment 'anthropic' || has_segment 'claude([.-].*|[0-9].*)?' ||
     has_segment '(fable|haiku|sonnet|opus)([.-].*|[0-9].*)?' ; then
  fail "Anthropic models require the claude OAuth engine"
elif has_segment 'openai' || has_segment '(gpt|chatgpt)([.-].*|[0-9].*)?' ||
     has_segment 'o[0-9]+([.-].*)?' || has_segment 'codex([.-].*|[0-9].*)?' ; then
  fail "OpenAI models require the codex OAuth engine"
fi

# OpenCode normally merges global, project, environment, and plugin config.
# This wrapper owns those config surfaces while leaving XDG_DATA_HOME/HOME
# untouched so OpenCode can use its normal auth store. Unrelated built-in
# providers remain available, but caller-defined aliases and plugins do not.
unset OPENCODE_CONFIG OPENCODE_CONFIG_DIR OPENCODE_CONFIG_CONTENT XDG_CONFIG_HOME
unset OPENCODE_TUI_CONFIG OPENCODE_PLUGIN_META_FILE OPENCODE_MODELS_PATH OPENCODE_MODELS_URL
unset OPENCODE_TEST_HOME OPENCODE_TEST_MANAGED_CONFIG_DIR OPENCODE_AUTH_CONTENT
export OPENCODE_DISABLE_PROJECT_CONFIG=1
export OPENCODE_DISABLE_DEFAULT_PLUGINS=1
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1
export OPENCODE_DISABLE_CLAUDE_CODE=1
export OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1
export OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1
export OPENCODE_DISABLE_MODELS_FETCH=1
export OPENCODE_PURE=1
OPENCODE_CONFIG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ringer-opencode-config.XXXXXXXX")"
export OPENCODE_CONFIG_DIR
if [[ "${coding_plan:-0}" == 1 ]]; then
  export OPENCODE_CONFIG_CONTENT='{"provider":{"zai-coding-plan":{"npm":"@ai-sdk/openai-compatible","name":"Z.AI Coding Plan","options":{"baseURL":"https://api.z.ai/api/coding/paas/v4"}}},"enabled_providers":["zai-coding-plan"],"plugin":[]}'

  # Resolve config without a model call and inspect only the provider identity,
  # enabled-provider list, and base URL. Never echo the full config or auth data.
  if [[ "$verify_only" == 1 ]]; then verify_output=1; else verify_output=0; fi
  (cd "$taskdir" && "$opencode_bin" debug config --pure 2>/dev/null) | python3 -c '
import json
import sys

EXPECTED_URL = "https://api.z.ai/api/coding/paas/v4"
try:
    config = json.load(sys.stdin)
    providers = config.get("provider")
    provider = providers.get("zai-coding-plan") if isinstance(providers, dict) else None
    options = provider.get("options") if isinstance(provider, dict) else None
    valid = (
        isinstance(config, dict)
        and isinstance(providers, dict)
        and "zai-coding-plan" in providers
        and config.get("enabled_providers") == ["zai-coding-plan"]
        and isinstance(options, dict)
        and options.get("baseURL") == EXPECTED_URL
    )
except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
    valid = False
if not valid:
    raise SystemExit(1)
if sys.argv[1] == "1":
    print(json.dumps({
        "baseURL": EXPECTED_URL,
        "enabled_providers": ["zai-coding-plan"],
        "provider_ids": ["zai-coding-plan"],
    }, sort_keys=True))
' "$verify_output" || fail "resolved Z.AI Coding Plan provider configuration is not trusted"
  [[ "$verify_only" == 0 ]] || exit 0
else
  export OPENCODE_CONFIG_CONTENT='{"plugin":[]}'
  [[ "$verify_only" == 0 ]] || fail "config verification is available only for Z.AI Coding Plan"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
platform="$(uname -s)"
if [[ "$platform" == Darwin ]]; then
  exec "$SCRIPT_DIR/opencode-sandboxed.sh" "${args[@]}"
fi
linux_args=("${args[@]}")
if ((${#linux_args[@]})); then linux_args=("${linux_args[@]:1}"); fi
if ((${#linux_args[@]})) && [[ "${linux_args[0]}" == --no-sandbox ]]; then linux_args=("${linux_args[@]:1}"); fi
exec "$opencode_bin" "${linux_args[@]}"
