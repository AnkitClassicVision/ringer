#!/usr/bin/env bash
# Render and run the 20/20 Brief episode red team against a staged episode.
# Usage: ./run-redteam-episode.sh content/20-20-brief/episodes/YYYY-WW
set -euo pipefail

EP="${1:?usage: run-redteam-episode.sh <episode-dir>}"
EP_ABS="$(readlink -f "$EP")"
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="/tmp/ringer-2020-brief-redteam-$(basename "$EP")"
mkdir -p "$OUT"
MANIFEST="$OUT/redteam-episode.rendered.json"

sed "s|{{EPISODE_DIR}}|$EP_ABS|g" \
  "$MANIFEST_DIR/redteam-episode.template.json" > "$MANIFEST"

sed -i "s|\"workdir\": \"/tmp/ringer-2020-brief-redteam-ep\"|\"workdir\": \"$OUT\"|" "$MANIFEST"

echo "Rendered manifest: $MANIFEST"
echo "Workdir: $OUT"
cd /mnt/d_drive/repos/ringer
python3 ringer.py run "$MANIFEST"
