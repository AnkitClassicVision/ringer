#!/bin/bash
set -euo pipefail

gemini_bin=gemini

fail() {
  printf '%s\n' "gemini-oauth.sh: blocked ambiguous or non-OAuth invocation; use the standard Gemini CLI personal OAuth login" >&2
  exit 64
}

# Caller-controlled credentials, backends, configuration roots, and test hooks
# must not influence this lane.
unset GEMINI_API_KEY GOOGLE_API_KEY GOOGLE_APPLICATION_CREDENTIALS
unset GOOGLE_GENAI_USE_VERTEXAI GOOGLE_CLOUD_PROJECT GOOGLE_CLOUD_LOCATION
unset GOOGLE_GEMINI_BASE_URL GEMINI_CLI_HOME GEMINI_SYSTEM_MD
unset GEMINI_CLI_SYSTEM_SETTINGS_PATH
unset RINGER_OAUTH_TEST_MODE RINGER_TEST_GEMINI_BIN RINGER_TEST_GEMINI_AUTH_BIN
unset RINGER_TEST_GEMINI_AUTH_STATUS RINGER_TEST_AUTH_EXIT

wrapper_path="${BASH_SOURCE[0]}"
while [[ -L "$wrapper_path" ]]; do
  wrapper_dir="$(cd -P -- "$(dirname -- "$wrapper_path")" && pwd)"
  link_target="$(readlink -- "$wrapper_path")"
  if [[ "$link_target" == /* ]]; then wrapper_path="$link_target"
  else wrapper_path="$wrapper_dir/$link_target"
  fi
done
wrapper_dir="$(cd -P -- "$(dirname -- "$wrapper_path")" && pwd)"
export GEMINI_CLI_SYSTEM_SETTINGS_PATH="$wrapper_dir/gemini-oauth-settings.json"

user_settings="${HOME:?}/.gemini/settings.json"
[[ -f "$user_settings" ]] || fail
python3 - "$user_settings" <<'PY' >/dev/null 2>&1 || fail
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
        settings = json.load(stream, object_pairs_hook=unique_object)
    valid = (
        isinstance(settings, dict)
        and isinstance(settings.get("security"), dict)
        and isinstance(settings["security"].get("auth"), dict)
        and settings["security"]["auth"].get("selectedType") == "oauth-personal"
    )
except (OSError, ValueError, json.JSONDecodeError):
    valid = False
raise SystemExit(0 if valid else 1)
PY

[[ -e "$HOME/.gemini/oauth_creds.json" || -e "$HOME/.gemini/google_accounts.json" ]] || fail

normalize_model() {
  local model="$1"
  [[ -n "$model" && "$model" != -* ]] || fail
  case "$model" in
    google/gemini-*) printf '%s' "${model#google/}" ;;
    gemini-*) printf '%s' "$model" ;;
    */*|*:*) fail ;;
    *) fail ;;
  esac
}

args=("$@")
model_seen=0
prompt_seen=0
output_seen=0
approval_seen=0
skip_trust_seen=0

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
    -o|--output-format)
      (( output_seen == 0 && i + 1 < ${#args[@]} )) || fail
      value="${args[$((i + 1))]}"
      [[ "$value" == json || "$value" == stream-json ]] || fail
      output_seen=1
      ((i += 1))
      ;;
    --output-format=*)
      (( output_seen == 0 )) || fail
      value="${item#--output-format=}"
      [[ "$value" == json || "$value" == stream-json ]] || fail
      output_seen=1
      ;;
    --approval-mode)
      (( approval_seen == 0 && i + 1 < ${#args[@]} )) || fail
      value="${args[$((i + 1))]}"
      [[ "$value" == auto_edit || "$value" == plan ]] || fail
      approval_seen=1
      ((i += 1))
      ;;
    --approval-mode=*)
      (( approval_seen == 0 )) || fail
      value="${item#--approval-mode=}"
      [[ "$value" == auto_edit || "$value" == plan ]] || fail
      approval_seen=1
      ;;
    --skip-trust)
      (( skip_trust_seen == 0 )) || fail
      skip_trust_seen=1
      ;;
    *) fail ;;
  esac
done

(( model_seen == 1 )) || fail
exec "$gemini_bin" "${args[@]}"
