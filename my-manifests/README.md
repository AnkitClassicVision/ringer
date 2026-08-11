# My Ringer manifests

Manifests are the to-do lists Ringer runs. A manifest is just a JSON file you
point `./ringer.py run` at — Ringer does not scan this folder automatically.
These are organized by purpose so you can find them.

## Layout

```
probes/      one-task checked manifests that prove a worker lane works.
             Run one when you add a new engine or want to audition a model.
             Cheap, safe, designed to pass or fail fast.

recurring/   jobs you run more than once — weekly cleanups, batch processing,
             anything with a repeatable shape. Save the manifest, re-run on
             demand. The recipe, not the data.

one-off/     a single job that produced real output you want to keep evidence
             of (e.g. baldev75-slideshows.json). Kept for reference and
             re-runnability, not for scheduling.
```

## How to use a manifest

```bash
# lint first (catches design mistakes before spending money)
./ringer.py lint my-manifests/recurring/sales-ops-batch1.json

# run it
./ringer.py run my-manifests/recurring/sales-ops-batch1.json
```

## Copying from Nate's templates

Built-in patterns live in `templates/` (read-only reference — don't edit them).
To start a new job from one:

```bash
cp templates/research-with-proof/manifest.json my-manifests/one-off/my-job.json
# then edit my-job.json: fill in the {{PLACEHOLDERS}}, swap engines, tune checks
```

## Naming

- `probes/<lane>-probe.json` — proves a lane
- `recurring/<job-name>.json` — a saved recipe
- `one-off/<project>-<date>.json` — evidence of a finished job

## See also

- `docs/MODEL-MENU.md` — which engine/model to route to
- `templates/README.md` — what each built-in pattern is for
- `~/.config/ringer/config.toml` — the engine lanes these manifests reference
