#!/bin/bash
set -euo pipefail

# Kimi K3 primary lane: Kimi Code CLI with the standard first-party OAuth
# login (kimi login). Caller-selected API keys, provider routes, and alternate
# configuration roots are not trusted here. OpenRouter/API K3 access belongs
# to the explicit kimi-api / pi-openrouter backup lane, never this wrapper.
unset KIMI_API_KEY MOONSHOT_API_KEY KIMI_BASE_URL MOONSHOT_BASE_URL
unset KIMI_CODE_API_KEY KIMI_CODE_BASE_URL KIMI_CONFIG_DIR KIMI_HOME
unset OPENROUTER_API_KEY OPENAI_API_KEY OPENAI_BASE_URL ANTHROPIC_BASE_URL
unset RINGER_OAUTH_TEST_MODE RINGER_TEST_KIMI_BIN

kimi_bin=kimi

fail() {
  printf '%s\n' "kimi-oauth.sh: blocked ambiguous or non-OAuth invocation; use the standard Kimi Code OAuth login (kimi login)" >&2
  exit 64
}

# Require a real stored OAuth credential; never print it.
creds="${HOME:?}/.kimi-code/credentials/kimi-code.json"
[[ -f "$creds" ]] || fail
python3 - "$creds" <<'PY' >/dev/null 2>&1 || fail
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
    with open(sys.argv[1], encoding="utf-8") as stream:
        stored = json.load(stream, object_pairs_hook=unique_object)
    valid = (
        isinstance(stored, dict)
        and type(stored.get("access_token")) is str
        and len(stored["access_token"]) > 20
        and type(stored.get("refresh_token")) is str
        and len(stored["refresh_token"]) > 20
        and type(stored.get("expires_at")) is int
    )
except (OSError, ValueError, json.JSONDecodeError):
    valid = False
raise SystemExit(0 if valid else 1)
PY
unset creds

normalize_model() {
  local original="$1" model="$1" lower
  lower="$(printf '%s' "$model" | LC_ALL=C tr '[:upper:]' '[:lower:]')"
  # OpenRouter/API selectors never belong on the OAuth lane.
  case "$lower" in
    openrouter/*|moonshotai/*|api/*) fail ;;
  esac
  case "$lower" in
    kimi-code/k3|kimi-code/k3-256k|kimi-code/kimi-for-coding|kimi-code/kimi-for-coding-highspeed)
      printf '%s' "$lower" ;;
    k3|k3-256k|kimi-for-coding|kimi-for-coding-highspeed)
      printf 'kimi-code/%s' "$lower" ;;
    kimi-k3)
      printf '%s' "kimi-code/k3" ;;
    *) fail ;;
  esac
}

args=("$@")
model_seen=0
prompt_seen=0
output_seen=0

for ((i = 0; i < ${#args[@]}; i++)); do
  item="${args[$i]}"
  case "$item" in
    -m|--model)
      (( model_seen == 0 && i + 1 < ${#args[@]} )) || fail
      args[$((i + 1))]="$(normalize_model "${args[$((i + 1))]}")"
      model_seen=1
      ((i += 1))
      ;;
    --model=*)
      (( model_seen == 0 )) || fail
      value="${item#--model=}"
      [[ -n "$value" ]] || fail
      args[$i]="--model=$(normalize_model "$value")"
      model_seen=1
      ;;
    -p|--prompt)
      (( prompt_seen == 0 && i + 1 < ${#args[@]} )) || fail
      prompt_seen=1
      ((i += 1))
      ;;
    --prompt=*)
      (( prompt_seen == 0 )) || fail
      [[ -n "${item#--prompt=}" ]] || fail
      prompt_seen=1
      ;;
    --output-format)
      (( output_seen == 0 && i + 1 < ${#args[@]} )) || fail
      value="${args[$((i + 1))]}"
      [[ "$value" == text || "$value" == stream-json ]] || fail
      output_seen=1
      ((i += 1))
      ;;
    --output-format=*)
      (( output_seen == 0 )) || fail
      value="${item#--output-format=}"
      [[ "$value" == text || "$value" == stream-json ]] || fail
      output_seen=1
      ;;
    *) fail ;;
  esac
done

(( prompt_seen == 1 )) || fail
exec "$kimi_bin" "${args[@]}"
