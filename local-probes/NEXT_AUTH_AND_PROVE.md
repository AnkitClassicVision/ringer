# Ringer worker-lane sign-in and proof

No secrets go in chat. Run these in a local terminal on this machine.

`run_lane_probes.sh` only probes lanes whose `[engines.<name>]` block is
uncommented in the live config (`~/.config/ringer/config.toml`). A disabled
lane is skipped, not failed.

## Current OpenRouter text route (2026-07-30)

OpenCode is no longer an active OpenRouter text lane. Current manifests use
`engine: pi-openrouter` with an exact `openrouter/<publisher>/<model>` selector.
The Pi wrapper is verified offline without a paid inference call:

```bash
cd /home/ankit114/repos/ringer
python3 -S -m unittest discover -s tests -p test_pi_openrouter_wrapper.py
```

Catalog presence and offline wrapper tests do not prove live model quality or
endpoint health. A live Pi/OpenRouter task probe requires separate approval for
the paid API call. See `docs/PI-OPENROUTER-ROUTING.md`.

## Historical: OpenCode + OpenRouter — proved, then superseded

The commands and result below are retained only as 2026-07-08 evidence. Do not
use them to configure or probe the current lane.

```bash
opencode auth login -p openrouter
# paste your OpenRouter key into the local terminal when prompted
cd /home/ankit114/repos/ringer
./ringer.py run local-probes/opencode-probe.json
```

Expected proof: the run prints `PASS` for `opencode-openrouter`, and the check
executed `lane_probe.py` and saw `OPENCODE_OPENROUTER_OK`. Proved 2026-07-08.

## Codex — DONE, proved

Proved by `./ringer.py demo` and by the load-bearing tasks in the sales-ops
manifests (Codex is the built-in default engine). Auth: `codex login` with a
ChatGPT plan.

## Grok Build — NOT available (no plan)

Grok Build requires a SuperGrok or X Premium Plus plan, which this machine's
operator does not have. The `[engines.grok]` block is therefore intentionally
kept commented out in `~/.config/ringer/config.toml`, and Ringer must not route
work to Grok.

If that changes later:

```bash
grok login --device-auth      # complete the browser/device login yourself
# then uncomment [engines.grok] in ~/.config/ringer/config.toml
cd /home/ankit114/repos/ringer
./ringer.py run local-probes/grok-probe.json
```

Expected proof once enabled: the run prints `PASS` for `grok-build`, and the
check executed `lane_probe.py` and saw `GROK_BUILD_OK`.

## Historical lane status (as of 2026-07-08; superseded 2026-07-30)

- **Codex** — enabled, proved (default engine).
- **OpenCode + OpenRouter** — historical proof only; now inactive and replaced
  by the explicit Pi/OpenRouter text lane.
- **Claude Code (OAuth)** — enabled, custom lane via `engines/claude-oauth.sh`
  (not probed here; assessed separately in the model scoreboard).
- **Grok** — disabled (no SuperGrok/X Premium Plus plan).

## Historical probe manifests

Both probe manifests were lint-clean for the 2026-07-08 configuration. They do
not prove the current Pi/OpenRouter route:

- `local-probes/opencode-probe.json`
- `local-probes/grok-probe.json` (only run after Grok is enabled)
