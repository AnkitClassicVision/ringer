#!/usr/bin/env bash
# Uses AWS secret mybcat/ai/api-keys/xai by default; models use xai/<model>.

set -euo pipefail

readonly OPENCODE_BIN=/home/ankit114/.npm-global/bin/opencode

if [[ ! -x "$OPENCODE_BIN" ]]; then
  printf '%s\n' 'error: opencode not found' >&2
  exit 127
fi

if [[ -z "${XAI_API_KEY:-}" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    printf '%s\n' 'error: aws CLI not found' >&2
    exit 127
  fi

  if ! XAI_API_KEY="$(
    HOME="${RINGER_AWS_HOME:-/home/ankit114}" aws secretsmanager get-secret-value \
      --secret-id "${XAI_SECRET_ID:-mybcat/ai/api-keys/xai}" \
      --region "${AWS_REGION:-us-east-1}" \
      --query SecretString \
      --output text
  )"; then
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
