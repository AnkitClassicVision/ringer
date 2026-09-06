#!/bin/bash
# omnigent-sandboxed.sh — Ringer engine wrapper for Omnigent.
#
# Contract (matches Ringer [engines.*] args_template):
#   $1 = taskdir   $2 = access_args   $3.. = spec/model/engine_args (varies)
# We accept the standard Ringer engine arg order and extract what we need.
# Omnigent's `run` is REPL-oriented, so we drive it headless via the HTTP
# session API: create session -> set codex_goal -> poll -> read result.
#
# Environment / [engines.omnigent.env] knobs:
#   OMNIGENT_SERVER         Omnigent session API endpoint
#                           (default: http://127.0.0.1:6767)
#   OMNIGENT_AGENT_ID       Agent ID for session creation (required)
#   OMNIGENT_DEFAULT_MODEL  Fallback model when -m is not supplied
#                           (default: ollama-cloud/deepseek-v4-pro)
set -uo pipefail

TASKDIR="${1:-.}"
shift || true
# remaining args: access_args, then -z SPEC -m MODEL [engine_args...]
SPEC=""
MODEL="${OMNIGENT_DEFAULT_MODEL:-ollama-cloud/deepseek-v4-pro}"
while [ $# -gt 0 ]; do
  case "$1" in
    -z) SPEC="$2"; shift 2 ;;
    -m) MODEL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

SERVER="${OMNIGENT_SERVER:-http://127.0.0.1:6767}"
AGENT_ID="${OMNIGENT_AGENT_ID:-}"

if [ -z "$AGENT_ID" ]; then
  echo "omnigent-sandboxed.sh: OMNIGENT_AGENT_ID is required" >&2
  exit 2
fi

if [ -z "$SPEC" ]; then
  echo "omnigent-sandboxed: no spec provided" >&2
  exit 2
fi

# 1. create session
SID=$(curl -s -m 10 -X POST "$SERVER/v1/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"$AGENT_ID\"}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

if [ -z "$SID" ]; then
  echo "omnigent-sandboxed: failed to create session" >&2
  exit 2
fi

# 2. set goal (the spec)
curl -s -m 10 -X PUT "$SERVER/v1/sessions/$SID/codex_goal" \
  -H "Content-Type: application/json" \
  -d "{\"objective\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$SPEC")}" >/dev/null 2>&1

# 3. poll goal status until terminal (timeout ~ task timeout)
DEADLINE=$(( $(date +%s) + 300 ))
while [ $(date +%s) -lt $DEADLINE ]; do
  ST=$(curl -s -m 10 "$SERVER/v1/sessions/$SID/codex_goal" 2>/dev/null)
  STATUS=$(echo "$ST" | python3 -c "import sys,json; d=json.load(sys.stdin); g=d.get('goal') or {}; print(g.get('status',''))" 2>/dev/null)
  case "$STATUS" in
    completed|done|succeeded) break ;;
    failed|error|cancelled) echo "omnigent goal $STATUS" >&2; exit 1 ;;
  esac
  sleep 5
done

# 4. read result items and write to taskdir
curl -s -m 10 "$SERVER/v1/sessions/$SID/items" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', d) if isinstance(d, dict) else d
out = []
for it in items:
    if isinstance(it, dict):
        for k in ('text','content','output','message'):
            if it.get(k):
                out.append(str(it[k]))
print('\n'.join(out))
" > "$TASKDIR/omnigent-result.txt" 2>/dev/null

echo "omnigent session $SID complete (status=$STATUS)"
exit 0
