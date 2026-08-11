#!/bin/bash
set -euo pipefail

unset OPENAI_API_KEY OPENAI_ORG_ID OPENAI_ORGANIZATION OPENAI_PROJECT OPENAI_PROJECT_ID
unset OPENAI_ORGANIZATION_ID OPENAI_BASE_URL OPENAI_API_BASE OPENAI_API_HOST
unset AZURE_OPENAI_API_KEY AZURE_OPENAI_ENDPOINT
unset OPENAI_PROFILE OPENAI_PROVIDER CODEX_PROFILE CODEX_PROVIDER CODEX_BACKEND CODEX_HOME

codex_bin=codex
unset RINGER_OAUTH_TEST_MODE RINGER_TEST_CODEX_BIN

fail() {
  printf '%s\n' "codex-oauth.sh: blocked ambiguous provider, model, profile, backend, or config selector; use the standard Codex ChatGPT login" >&2
  exit 64
}
lowercase() { printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]'; }

normalize_model() {
  local model="$1" lower
  lower="$(lowercase "$model")"
  if [[ "$lower" == openrouter/* ]]; then model="${model#*/}"; lower="$(lowercase "$model")"; fi
  if [[ "$lower" == openai/* || "$lower" == openai:* ]]; then model="${model:7}"; fi
  printf '%s' "$model"
}

config_key() {
  local selector="$1"
  if [[ "$selector" =~ ^[[:space:]]*([A-Za-z0-9_.-]+)[[:space:]]*= ]]; then
    lowercase "${BASH_REMATCH[1]}"
  else
    fail
  fi
}

normalize_config() {
  local selector="$1" prefix value quote=""
  [[ "$selector" =~ ^([[:space:]]*model[[:space:]]*=[[:space:]]*)(.*)$ ]] || { printf '%s' "$selector"; return; }
  prefix="${BASH_REMATCH[1]}"; value="${BASH_REMATCH[2]}"
  [[ -n "$value" ]] || fail
  if (( ${#value} >= 2 )) && [[ "${value:0:1}" == "${value: -1}" ]] &&
     [[ "${value:0:1}" == '"' || "${value:0:1}" == "'" ]]; then
    quote="${value:0:1}"; value="${value:1:${#value}-2}"
  fi
  [[ -n "$value" ]] || fail
  printf '%s%s%s%s' "$prefix" "$quote" "$(normalize_model "$value")" "$quote"
}

args=("$@")
model_seen=0
ignore_user_config_seen=0
for ((i = 0; i < ${#args[@]}; i++)); do
  item="${args[$i]}"
  case "$item" in
    --|--oss|--oss=*|--local-provider|--local-provider=*|-p|--profile|--profile=*) fail ;;
    --ignore-user-config) ((ignore_user_config_seen += 1)); ((ignore_user_config_seen == 1)) || fail ;;
    -m|--model)
      (( model_seen == 0 && i + 1 < ${#args[@]} )) || fail
      [[ -n "${args[$((i + 1))]}" && "${args[$((i + 1))]}" != -* ]] || fail
      model_seen=1; args[$((i + 1))]="$(normalize_model "${args[$((i + 1))]}")"; ((i += 1)) ;;
    --model=*)
      (( model_seen == 0 )) || fail; value="${item#--model=}"; [[ -n "$value" ]] || fail
      model_seen=1; args[$i]="--model=$(normalize_model "$value")" ;;
    -c|--config)
      (( i + 1 < ${#args[@]} )) || fail; selector="${args[$((i + 1))]}"; key="$(config_key "$selector")"
      case "$key" in
        model) (( model_seen == 0 )) || fail; model_seen=1; args[$((i + 1))]="$(normalize_config "$selector")" ;;
        model_reasoning_effort|sandbox_workspace_write.writable_roots) ;;
        *) fail ;;
      esac
      ((i += 1)) ;;
    -c?*|-m?*) fail ;;
    --config=*)
      selector="${item#--config=}"; key="$(config_key "$selector")"
      case "$key" in
        model) (( model_seen == 0 )) || fail; model_seen=1; args[$i]="--config=$(normalize_config "$selector")" ;;
        model_reasoning_effort|sandbox_workspace_write.writable_roots) ;;
        *) fail ;;
      esac ;;
    model=*|model\ =*) fail ;;
    provider=*|model_provider=*|profile=*|backend=*|model.provider=*|model.backend=*) fail ;;
  esac
done

auth_status="$("$codex_bin" login status 2>&1)" || fail
[[ "$auth_status" == "Logged in using ChatGPT" ]] || fail
unset auth_status
# No option terminator is admitted, so these wrapper-owned controls remain effective.
if (( ignore_user_config_seen == 0 )); then args+=(--ignore-user-config); fi
exec "$codex_bin" "${args[@]}" -c model_provider=openai
