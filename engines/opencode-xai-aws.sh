#!/usr/bin/env bash
# Runs xAI models through OpenCode, obtaining the API key from the environment
# or a locally configured AWS Secrets Manager reference.

set -euo pipefail

OPENCODE_BIN="${RINGER_OPENCODE_BIN:-}"
if [[ -z "$OPENCODE_BIN" ]]; then
  OPENCODE_BIN="$(command -v opencode || true)"
fi

if [[ -z "$OPENCODE_BIN" || ! -x "$OPENCODE_BIN" ]]; then
  printf '%s\n' 'error: opencode not found; set RINGER_OPENCODE_BIN or add opencode to PATH' >&2
  exit 127
fi

if [[ -z "${XAI_API_KEY:-}" ]]; then
  if [[ "${XAI_SECRET_ID+x}" == x ]]; then
    XAI_SECRET_REF="$XAI_SECRET_ID"
  else
    if [[ -n "${RINGER_XAI_SECRET_REF_FILE:-}" ]]; then
      XAI_SECRET_REF_FILE="$RINGER_XAI_SECRET_REF_FILE"
    elif [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
      XAI_SECRET_REF_FILE="$XDG_CONFIG_HOME/ringer/xai-secret-ref"
    elif [[ -n "${HOME:-}" ]]; then
      XAI_SECRET_REF_FILE="$HOME/.config/ringer/xai-secret-ref"
    else
      printf '%s\n' 'error: xAI secret reference is not configured' >&2
      exit 1
    fi

    if [[ ! -r "$XAI_SECRET_REF_FILE" ]]; then
      printf '%s\n' 'error: xAI secret reference file is unavailable' >&2
      exit 1
    fi

    XAI_SECRET_REF=""
    XAI_SECRET_REF_LINE_SEEN=0
    while IFS= read -r line || [[ -n $line ]]; do
      if (( XAI_SECRET_REF_LINE_SEEN )); then
        XAI_SECRET_REF="${XAI_SECRET_REF}"$'\n'
      fi
      XAI_SECRET_REF="${XAI_SECRET_REF}${line}"
      XAI_SECRET_REF_LINE_SEEN=1
    done < "$XAI_SECRET_REF_FILE"
  fi

  if [[ -z "$XAI_SECRET_REF" || "$XAI_SECRET_REF" == *$'\r'* || "$XAI_SECRET_REF" == *$'\n'* ]]; then
    printf '%s\n' 'error: xAI secret reference is invalid' >&2
    exit 1
  fi

  if ! command -v aws >/dev/null 2>&1; then
    printf '%s\n' 'error: aws CLI not found' >&2
    exit 127
  fi

  aws_status=0
  if [[ -n "${RINGER_AWS_HOME:-}" ]]; then
    XAI_API_KEY="$(HOME="$RINGER_AWS_HOME" aws secretsmanager get-secret-value \
      --secret-id "$XAI_SECRET_REF" \
      --region "${AWS_REGION:-us-east-1}" \
      --query SecretString \
      --output text 2>/dev/null)" || aws_status=$?
  else
    XAI_API_KEY="$(aws secretsmanager get-secret-value \
      --secret-id "$XAI_SECRET_REF" \
      --region "${AWS_REGION:-us-east-1}" \
      --query SecretString \
      --output text 2>/dev/null)" || aws_status=$?
  fi
  if [[ "$aws_status" -ne 0 ]]; then
    printf '%s\n' 'error: unable to retrieve xAI API key' >&2
    exit 1
  fi

  if [[ -z "$XAI_API_KEY" || "$XAI_API_KEY" == 'None' ]]; then
    printf '%s\n' 'error: xAI API key is empty' >&2
    exit 1
  fi
fi

export XAI_API_KEY
exec "$OPENCODE_BIN" "$@" </dev/null
