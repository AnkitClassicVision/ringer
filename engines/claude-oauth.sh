#!/bin/bash
set -euo pipefail

# Keep this lane on Claude Code's standard first-party login. Caller-selected
# API routes and alternate configuration roots are not trusted here.
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL ANTHROPIC_API_BASE
unset CLAUDE_API_KEY CLAUDE_BASE_URL CLAUDE_API_BASE CLAUDE_CONFIG_DIR
unset CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX CLAUDE_CODE_USE_FOUNDRY
unset ANTHROPIC_BEDROCK_BASE_URL ANTHROPIC_VERTEX_BASE_URL ANTHROPIC_FOUNDRY_BASE_URL
unset ANTHROPIC_VERTEX_PROJECT_ID CLOUD_ML_REGION AWS_REGION AWS_DEFAULT_REGION

claude_bin=claude
unset RINGER_OAUTH_TEST_MODE RINGER_TEST_CLAUDE_BIN

fail() {
  printf '%s\n' "claude-oauth.sh: blocked ambiguous or non-OAuth invocation; use the standard Claude Code claude.ai login" >&2
  exit 64
}

lowercase() { printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]'; }

normalize_model() {
  local original="$1" model="$1" lower
  lower="$(lowercase "$model")"
  if [[ "$lower" == openrouter/* ]]; then model="${model#*/}"; lower="$(lowercase "$model")"; fi
  if [[ "$lower" == anthropic/* || "$lower" == anthropic:* ]]; then
    model="${model:10}"; lower="$(lowercase "$model")"
  fi
  if [[ "$lower" =~ (^|[-.])fable([0-9].*|[-._]|$) ]]; then printf '%s' fable
  elif [[ "$lower" =~ (^|[-.])haiku([0-9].*|[-._]|$) ]]; then printf '%s' haiku
  elif [[ "$lower" =~ (^|[-.])sonnet([0-9].*|[-._]|$) ]]; then printf '%s' sonnet
  elif [[ "$lower" =~ (^|[-.])opus([0-9].*|[-._]|$) ]]; then printf '%s' opus
  elif [[ "$lower" =~ ^claude[0-9] ]]; then fail
  elif [[ "$lower" == claude-* ]]; then printf '%s' "$model"
  else printf '%s' "$original"
  fi
}

args=("$@")
model_seen=0
for ((i = 0; i < ${#args[@]}; i++)); do
  item="${args[$i]}"
  case "$item" in
    --) fail ;;
    -m|--model)
      (( model_seen == 0 )) || fail
      (( i + 1 < ${#args[@]} )) || fail
      [[ -n "${args[$((i + 1))]}" && "${args[$((i + 1))]}" != -* ]] || fail
      model_seen=1
      args[$((i + 1))]="$(normalize_model "${args[$((i + 1))]}")"
      ((i += 1))
      ;;
    --model=*)
      (( model_seen == 0 )) || fail
      value="${item#--model=}"
      [[ -n "$value" ]] || fail
      model_seen=1
      args[$i]="--model=$(normalize_model "$value")"
      ;;
    --safe-mode|--safe-mode=*|--settings|--settings=*|--setting-sources|--setting-sources=*) fail ;;
  esac
done

# Never echo or forward the status payload. Accept exactly one JSON object,
# reject duplicate keys, and require the effective values to have exact types.
auth_status="$("$claude_bin" auth status --json 2>/dev/null)" || fail
printf '%s' "$auth_status" | python3 -c '
import json
import sys

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result

try:
    status = json.load(sys.stdin, object_pairs_hook=unique_object)
except (json.JSONDecodeError, ValueError):
    raise SystemExit(1)
valid = (
    isinstance(status, dict)
    and status.get("loggedIn") is True
    and type(status.get("authMethod")) is str
    and status.get("authMethod") == "claude.ai"
    and type(status.get("apiProvider")) is str
    and status.get("apiProvider") == "firstParty"
)
raise SystemExit(0 if valid else 1)
' || fail
unset auth_status
# Safe mode disables customizations; an empty source list disables the normal
# user, project, and local settings files. Callers cannot replace either flag.
if (( ${#args[@]} )); then
  exec "$claude_bin" --safe-mode --setting-sources "" "${args[@]}"
else
  exec "$claude_bin" --safe-mode --setting-sources ""
fi
