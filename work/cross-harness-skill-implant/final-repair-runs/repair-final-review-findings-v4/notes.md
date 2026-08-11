# Cross-Harness Skill Implant v1 final repair notes

Status: local repair verified. No live skill roots, runtime configuration, Ringer state, git state, network, MCP/apps, memory, cron, or remote systems were changed. No live promotion was attempted.

## Files changed in this repair

- `scripts/implant_skill.py`
- `tests/test_implant_skill.py`
- `assets/implant-manifest.schema.json`
- `references/cross-harness-skill-implant.md`
- This task-local `notes.md`

Pre-existing changes in `SKILL.md` and `references/install-upgrade-protocol.md` were observed during the read-only self-audit and preserved without edits. `scripts/validate_implant_manifest.py` and `assets/implant-request.template.json` were inspected but did not require changes.

## Findings closed

- Finding A: `verify_manifest` now overwrites every unrequested higher discovery level with a fresh `NOT_RUN` receipt. A new regression verifies `invoked` first and `loaded` second on the same manifest, with final status `VERIFIED` and `invoked.passed` false.
- Finding B: added standard-library `validate_contract_artifacts(schema_path, template_path)` with stable `SCHEMA_PARITY_MISMATCH` and `TEMPLATE_PARITY_MISMATCH` failures. Default artifacts are enforced by inspect and manifest loading, which also makes the standalone validator enforce them. The schema now includes the required `$defs.pathState.allOf` conditionals. Tests cover shipped artifacts, weakened schema rejection, drifted template rejection, and successful materialization through `build_plan`.
- Finding C: inspect and manifest validation reject resolved source/destination overlap with `SOURCE_TARGET_OVERLAP`. Checks run before prior-state capture, resolve target ancestors without following an installed target leaf symlink, and cover same-path REPLACE, same-path RENAME, source ancestor, source descendant, manifest tampering, no rejected-manifest write, and unchanged source bytes.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` -> PASS, 26 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 /mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/check_implant_workflow.py --repo .` -> PASS, 1 authoritative end-to-end acceptance checker.
- `PYTHONPYCACHEPREFIX=/tmp/skill-implant-final-repair-pyc python3 -m py_compile scripts/implant_skill.py scripts/validate_implant_manifest.py` -> PASS, 2 modules compiled.
- Bounded self-audit -> PASS. Scope, error-code behavior, source immutability, valid installed links, exact artifact parity, and owned-file boundaries were checked. No nested model workers were launched.

## Residual risks

- The artifact validator intentionally checks the published structural contract only; it is not a general JSON Schema engine.
- Verification is local. No live roots were inspected or changed, and no promotion state is claimed.
