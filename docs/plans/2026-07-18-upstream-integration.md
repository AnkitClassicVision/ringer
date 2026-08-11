# Ringer Upstream Integration Plan

> **For Hermes:** Implement against unit IDs, keep the original dirty worktree untouched, and require fresh verification before review.

**Goal:** Build one reviewable Ringer branch that starts from current upstream, preserves Ankit's auth-first/OAuth and Seedance upgrades, and adopts the useful upstream runtime, identity, steering, dashboard, diagnostics, baseline, template, and CI improvements.

**Architecture:** `upstream/main` is the clean base. Local tracked changes are reapplied as a three-way patch, selected untracked source upgrades are copied from the untouched local worktree, and conflicts are reconciled in favor of upstream runtime structure plus local fail-closed auth routing. Automatic self-update remains disabled and no remote write is allowed.

**Tech stack:** Python 3 standard library, Bash wrappers, TOML, JSON manifests, pytest, git worktrees.

CANARY: blue paperclip

## Product contract

- Keep trusted `codex-oauth.sh`, `claude-oauth.sh`, and `opencode-auth-policy.sh` routing.
- Keep `--ignore-user-config`, provider/backend override rejection, restricted-family wrapper gates, and strict model-selector parsing.
- Keep Seedance engine, docs, validator, manifest, registry identities, and tests.
- Keep upstream graceful shutdown, setup diagnostics, baseline mode, Ringside overhaul, model taxonomy, harness-reported identity, steering infrastructure, portable checks, design fixture, CI, and contributor docs.
- Keep local model notes without importing upstream operator performance as local evidence.
- No automatic merge/update, push, PR, deploy, external send, or production action.

## U1: Preserve and stage local upgrades

**Files:** tracked local patch plus selected untracked files under `docs/`, `engines/`, `templates/`, and `tests/`.

**Proof:** original worktree status hash remains unchanged; integration branch contains the selected source files; no local operational manifests/probes/sales material is imported.

## U2: Reconcile core routing and attribution

**Files:** `ringer.py`, `config.sample.toml`, `registry/model-identity.toml`, `docs/MODEL-NOTES.md`, `tests/test_catalog.py`, `tests/test_model_db.py`, `tests/test_model_field.py`, `tests/test_model_log.py`, `tests/test_scoreboard_page.py`.

**Required behavior:**
- Model precedence: harness report, then last effective composed-command selector, then task model, then engine default.
- Preserve upstream DB schema/taxonomy and local auth-first guards.
- Add `{model_args}` and `model_report_regex` without permitting duplicate or conflicting selectors.
- Preserve both reserved-fixture filtering and local OpenRouter normalization.
- Preserve both `model_source` and `reasoning_effort` exclusions where appropriate.

**Proof:** targeted model, OAuth, database, taxonomy, steering, and scoreboard tests pass.

## U3: Apply safety hardening

**Files:** `ringer.py`, `config.sample.toml`, tests and docs.

**Required behavior:**
- `UpdateConfig.auto` defaults to false; startup/HUD never performs git updates unless explicitly enabled.
- Explicit self-update errors return nonzero at the CLI boundary.
- Steering remains unconfigured by default, requires actual TOML booleans, defaults candidate injection off, and does not persist raw check-output excerpts.
- Baseline retains advisory mode and gains a strict nonzero-on-failure mode for automation.
- Setup recovery does not recommend force-removing a dirty worktree without a warning.
- Registry confidence and source fields do not overstate aggregator-only evidence.

**Proof:** focused regression tests cover each safety rule.

## U4: Repair local template failures

**Files:** `templates/fable-sol-loop/manifest-round*.json` and relevant kit tests.

**Required behavior:** all shipped templates lint clean; packet validators and fixture tests continue to pass.

**Proof:** template lint suite and `templates/fable-sol-loop/tests/test_kit.py` pass.

## U5: Full verification and review

**Commands:**
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`
- `python3 ringer.py lint <representative manifests>`
- CLI smoke for `--baseline`, strict baseline, `models --json`, and update-disabled startup.
- Fresh-context read-only review against this plan and the final diff.

**Acceptance:** no conflict markers; all tests green; original dirty worktree unchanged; integration branch remains local and reviewable; no push/deploy/external action.

## Decision residue

- **Hardest decision:** use upstream as the structural base rather than trying to fast-forward the dirty local branch.
- **Alternatives rejected:** blind merge into dirty `main`; wholesale cherry-pick of mixed self-update commit; preserving the stale OAuth worktree implementation.
- **Least-confident assumption:** local model-notes additions can be retained without carrying stale identity semantics; tests and fresh review must validate the reconciliation.
