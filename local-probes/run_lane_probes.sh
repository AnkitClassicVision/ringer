#!/usr/bin/env bash
# Prove each configured worker lane with a one-task checked probe.
# A lane is only probed if its [engines.<name>] block is uncommented in the
# live config (~/.config/ringer/config.toml); a commented/disabled lane is
# skipped with a message rather than failing the script. To enable a lane,
# uncomment its block in the config first, then re-run this.
set -euo pipefail
cd /home/ankit114/repos/ringer

config="${RINGER_CONFIG:-$HOME/.config/ringer/config.toml}"
engine_enabled() { grep -qE "^[[:space:]]*\[engines\.$1\]" "$config"; }

echo "== OpenCode + OpenRouter lane =="
if engine_enabled opencode; then
  ./ringer.py lint local-probes/opencode-probe.json
  ./ringer.py run   local-probes/opencode-probe.json
else
  echo "skip: [engines.opencode] is not enabled in $config"
fi

echo "== Grok Build lane =="
if engine_enabled grok; then
  ./ringer.py lint local-probes/grok-probe.json
  ./ringer.py run   local-probes/grok-probe.json
else
  echo "skip: [engines.grok] is not enabled in $config (no SuperGrok/X Premium Plus plan)"
fi
