#!/bin/bash
# Ringer engine wrapper: run the Hermes agent one-shot under a macOS Seatbelt
# sandbox.
#
# Hermes has no OS-level sandbox of its own — its one-shot mode (`hermes -z`)
# runs a full agentic loop with tools. This wrapper supplies the real
# containment: full network and reads, writes confined to the task dir, a
# per-run scratch/cache dir, and Hermes's own state dirs (config, credentials,
# memory, skills) so the agent can resolve models and providers.
#
# Usage (as a ringer engine bin):
#   hermes-sandboxed.sh <taskdir> [--no-sandbox] <hermes args...>
#
# The first argument is the task directory (pass "{taskdir}" first in
# args_template). "--no-sandbox" as the second argument skips Seatbelt entirely
# — wire it as the engine's full_access_args so ringer's allow_full_access gate
# still applies. macOS only (sandbox-exec); on other platforms only
# --no-sandbox mode works.
#
# Environment / [engines.hermes.env] knobs:
#   HERMES_HOME                 Hermes config/credential tree (default: ~/.hermes)
#   HERMES_STATE                Hermes state directory (default: ~/.local/state/hermes)
#   PAPERCLIP_OLLAMA_CLOUD_ADMISSION_BIN      path to ollama_cloud_admission.py
#   PAPERCLIP_OLLAMA_CLOUD_ADMISSION_POLICY   path to cloud-admission-policy.v1.json
#   PAPERCLIP_OLLAMA_CLOUD_ADMISSION_STATE_DIR  path to admission state directory
# Cloud admission is required ONLY when a task pins an ollama-cloud route
# (model starts with "ollama-cloud:" or --provider ollama-cloud). Non-cloud
# routes ignore it entirely.
set -euo pipefail

TASKDIR="${1:?usage: hermes-sandboxed.sh <taskdir> [--no-sandbox] <args...>}"; shift
SANDBOX=1
if [ "${1:-}" = "--no-sandbox" ]; then SANDBOX=0; shift; fi

# Resolve hermes without tripping `set -e` (command -v returns nonzero when absent).
if ! HERMES_BIN="$(command -v hermes)" || [ -z "$HERMES_BIN" ]; then
  echo "hermes-sandboxed.sh: hermes not found on PATH" >&2
  exit 127
fi

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_STATE="${HERMES_STATE:-$HOME/.local/state/hermes}"

# Cloud admission is required only when a task pins an ollama-cloud route.
# Set these env vars (or use [engines.hermes.env] in config.toml) to enable.
CLOUD_ADM_BIN="${PAPERCLIP_OLLAMA_CLOUD_ADMISSION_BIN:-}"
CLOUD_ADM_POLICY="${PAPERCLIP_OLLAMA_CLOUD_ADMISSION_POLICY:-}"
CLOUD_ADM_STATE_DIR="${PAPERCLIP_OLLAMA_CLOUD_ADMISSION_STATE_DIR:-}"

CLOUD_PINNED=0
_args=("$@")
for ((i = 0; i < ${#_args[@]}; i++)); do
  if [ "${_args[$i]}" = "-m" ] && [[ "${_args[$((i + 1))]:-}" == ollama-cloud:* ]]; then
    CLOUD_PINNED=1
  fi
  if [ "${_args[$i]}" = "--provider" ] && [ "${_args[$((i + 1))]:-}" = "ollama-cloud" ]; then
    CLOUD_PINNED=1
  fi
done

admit_cloud() {
  if [ -z "$CLOUD_ADM_BIN" ] || [ -z "$CLOUD_ADM_POLICY" ] || [ -z "$CLOUD_ADM_STATE_DIR" ]; then
    echo "hermes-sandboxed.sh: ollama-cloud route requires PAPERCLIP_OLLAMA_CLOUD_ADMISSION_BIN, PAPERCLIP_OLLAMA_CLOUD_ADMISSION_POLICY, and PAPERCLIP_OLLAMA_CLOUD_ADMISSION_STATE_DIR" >&2
    exit 74
  fi
  if [ ! -f "$CLOUD_ADM_BIN" ] || [ ! -d "$CLOUD_ADM_STATE_DIR" ]; then
    echo "hermes-sandboxed.sh: cloud admission binary or state dir not found" >&2
    exit 74
  fi
  export PAPERCLIP_OLLAMA_CLOUD_ADMISSION_POLICY="$CLOUD_ADM_POLICY"
  export PAPERCLIP_OLLAMA_CLOUD_ADMISSION_STATE_DIR="$CLOUD_ADM_STATE_DIR"
  python3 "$CLOUD_ADM_BIN" passthrough -- "$@"
}

if [ "$SANDBOX" = "0" ]; then
  if [ "$CLOUD_PINNED" = "1" ]; then
    admit_cloud "$HERMES_BIN" "$@" < /dev/null
    exit $?
  fi
  exec "$HERMES_BIN" "$@" < /dev/null
fi

if [ ! -x /usr/bin/sandbox-exec ]; then
  echo "hermes-sandboxed.sh: /usr/bin/sandbox-exec not available (macOS only)." >&2
  echo "Use the engine's full-access mode (--no-sandbox) or add your own sandbox." >&2
  exit 1
fi

TASKDIR_REAL="$(cd "$TASKDIR" && pwd -P)"

# Per-run scratch root — becomes both TMPDIR and XDG_CACHE_HOME for Hermes, so
# we never have to open all of /private/tmp or ~/.cache to the sandboxed agent.
# Resolve to the real path (/var/folders symlinks to /private/var/folders);
# Seatbelt subpath matching needs the canonical path or writes EPERM-crash.
SCRATCH="$(cd "$(mktemp -d -t ringer-hermes-scratch.XXXXXX)" && pwd -P)"
PROFILE="$(mktemp -t ringer-hermes-prof.XXXXXX)"
cleanup() { rm -rf "$SCRATCH" "$PROFILE"; }
trap cleanup EXIT

# Paths are passed to the profile via sandbox-exec -D parameters, NOT string
# interpolation — a task dir containing quotes/parens/newlines can't inject rules.
cat > "$PROFILE" <<'SBEOF'
(version 1)
(allow default)
(deny file-write*)
(allow file-write*
  (subpath (param "TASKDIR"))
  (subpath (param "SCRATCH"))
  (subpath (param "HERMES_HOME"))
  (subpath (param "HERMES_STATE")))
; /dev is needed for /dev/null, /dev/urandom, etc.; writes there can't create
; persistent files without root, so a few literals are allowed rather than via param.
(allow file-write-data
  (literal "/dev/null")
  (literal "/dev/dtracehelper")
  (literal "/dev/tty"))
SBEOF

export TMPDIR="$SCRATCH"
export XDG_CACHE_HOME="$SCRATCH/cache"
mkdir -p "$XDG_CACHE_HOME"

# Run as a child (not exec) so the EXIT trap fires and cleans up the profile +
# scratch dir even on the success path; propagate the child's exit status.
# Cloud-pinned tasks run the whole sandboxed child under the admission
# semaphore (the lock fd passes through sandbox-exec into hermes).
set +e
if [ "$CLOUD_PINNED" = "1" ]; then
  admit_cloud /usr/bin/sandbox-exec \
    -D "TASKDIR=$TASKDIR_REAL" \
    -D "SCRATCH=$SCRATCH" \
    -D "HERMES_HOME=$HERMES_HOME" \
    -D "HERMES_STATE=$HERMES_STATE" \
    -f "$PROFILE" "$HERMES_BIN" "$@" < /dev/null
  status=$?
else
  /usr/bin/sandbox-exec \
    -D "TASKDIR=$TASKDIR_REAL" \
    -D "SCRATCH=$SCRATCH" \
    -D "HERMES_HOME=$HERMES_HOME" \
    -D "HERMES_STATE=$HERMES_STATE" \
    -f "$PROFILE" "$HERMES_BIN" "$@" < /dev/null
  status=$?
fi
set -e
exit "$status"
