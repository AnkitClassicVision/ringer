#!/usr/bin/env bash
# Executable proof for the pi-openrouter key fix: run the REAL wrapper end to
# end against grok-4.5 with a one-word prompt. Prints WHY it fails.
set -u
WRAP=/mnt/d_drive/repos/ringer/engines/pi-openrouter-ringer.sh

if ! bash -n "$WRAP"; then
  echo "CHECK FAIL: wrapper has a bash syntax error"
  exit 1
fi

TD=$(mktemp -d /tmp/pi-keyfix-probe.XXXXXX) || { echo "CHECK FAIL: mktemp"; exit 1; }
out=$("$WRAP" "$TD" openrouter/x-ai/grok-4.5 'Reply with the single word PONG. Do not use any tools.' 2>&1)
rc=$?
printf '%s\n' "$out" | tail -15
if [ "$rc" -ne 0 ]; then
  echo "CHECK FAIL: wrapper exited rc=$rc (see transcript tail above)"
  rm -rf "$TD"
  exit 1
fi
if printf '%s' "$out" | grep -qi 'store read failed'; then
  echo "CHECK FAIL: sandboxed Pi still reports the store-read failure"
  rm -rf "$TD"
  exit 1
fi
if ! printf '%s' "$out" | grep -q 'RINGER_PI_IDENTITY.*x-ai/grok-4.5'; then
  echo "CHECK FAIL: no RINGER_PI_IDENTITY line for x-ai/grok-4.5 (no verified assistant message)"
  rm -rf "$TD"
  exit 1
fi
# Ownership guard on TRACKED modifications only: pre-existing untracked files
# under engines/ (e.g. the never-committed kimi-oauth.sh) are not the worker's.
changed=$(git -C /mnt/d_drive/repos/ringer diff --name-only -- engines/)
if [ -n "$changed" ] && [ "$changed" != "engines/pi-openrouter-ringer.sh" ]; then
  echo "CHECK FAIL: tracked files other than the owned wrapper modified under engines/: $changed"
  exit 1
fi
rm -rf "$TD"
echo "CHECK PASS: wrapper ran grok-4.5 end to end with verified identity"
