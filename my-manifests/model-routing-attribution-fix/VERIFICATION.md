# Ringer attribution and catalog-normalization verification

Date: 2026-07-10

## Highest true state

Local, uncommitted Ringer patch applied in `/home/ankit114/repos/ringer`; derived scoreboard rebuilt; no deployment, push, merge, global model-default change, workload reassignment, or automatic promotion.

`external_actions_taken: 0`

## Production changes

- `ringer.py`
  - Resolves and records effective model plus attribution source.
  - Supports `-m`, `--model`, `--model=`, `-c model=`, `--config model=`, and `--config=model=`.
  - Fails closed on malformed model selectors.
  - Fails closed on malformed Codex `-c`/`--config` key-value overrides without imposing Codex semantics on other engines.
  - Keeps retry attribution stable.
  - Normalizes `openrouter/` only for catalog-versus-tested comparison.
  - Rejects duplicate model selectors for engines whose command template already has a model placeholder.
- `registry/model-identity.toml`
  - Blank historical Codex rows display as `Codex CLI default (unpinned)`.
  - Explicit `gpt-5.5` remains a separate identity.
- Focused regression tests updated in:
  - `tests/test_model_field.py`
  - `tests/test_model_log.py`
  - `tests/test_catalog.py`
  - `tests/test_model_db.py`
  - `tests/test_scoreboard_page.py`

The pre-existing user change in `docs/MODEL-NOTES.md` was not modified by this work.

## Executed proof

- 57 focused tests passed in the working tree.
- The same seven-file patch applied cleanly to a fresh detached worktree and all 57 focused tests passed there.
- Python compile checks passed.
- Both changed Ringer manifests linted clean.
- `git diff --check` passed.
- Full discovery: 142 tests found; 141 passed. One unrelated test errors before assertion because `tests/test_design_reference.py` points to a missing external absolute fixture under `/private/tmp/.../design-reference.html`.
- Transparent exclusion gate: all 141 applicable tests passed.

## Runtime evidence

New explicit Codex review runs record:

- `model: gpt-5.6-luna`
- `model_source: engine-args`
- identical model and source on retry rows

The original implementation run predates the patch and remains unattributed. Historical `runs.jsonl` rows were not rewritten.

## Derived scoreboard

Rebuilt from the append-only run log:

- attempts ingested: 241
- skipped rows: 0
- pre-rebuild backup: `/home/ankit114/.ringer/ringer.db.bak-20260710T124852Z`

North Mini Code now appears only in its tested probation tier and is excluded from untested candidates.

## Artifacts

- Standalone patch: `/tmp/ringer-model-routing-final.patch`
- Routing recommendations: `/home/ankit114/repos/ringer/my-manifests/model-routing-attribution-fix/ROUTING-RECOMMENDATIONS.md`
- This verification packet: `/home/ankit114/repos/ringer/my-manifests/model-routing-attribution-fix/VERIFICATION.md`

## Decision boundary

No global default, saved workload route, or model promotion was changed automatically. Any next routing update should name the exact manifest task and model and receive human approval.
