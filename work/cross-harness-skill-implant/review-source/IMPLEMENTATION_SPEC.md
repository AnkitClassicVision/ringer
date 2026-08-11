# Cross-Harness Skill Implant v1 Implementation Spec

Status: approved build yardstick
Owner: Ankit
Execution: Ringer with Codex/Sol
Live boundary: build and verify in this repository first. Do not edit live skill roots, shell configuration, runtime configuration, remote hosts, or external systems.

## Purpose

Turn the approved Mission Fit recommendations REC-1 through REC-5 into a deterministic, standard-library-only extension of this existing skill package. The result must preserve one canonical source package, apply only an explicitly approved immutable plan, avoid silent overwrites and independent editable copies, and prove target discovery separately from filesystem presence.

## Non-goals

- No network access, downloading, publishing, remote installation, or runtime restart.
- No automatic repository migration, framework port, control plane, cron, or unrelated scout.
- No hard-coded claims that Claude, Codex, or Gemini support a discovery command that has not been version-pinned in the request.
- No shell=True execution for discovery adapters.
- No secrets, raw command output, message bodies, or environment dumps in receipts.
- No live changes under ~/.hermes, ~/.claude, ~/.codex, or ~/.gemini during the Ringer build.

## Locked command interface

```bash
python3 scripts/implant_skill.py inspect --request REQUEST.json --manifest MANIFEST.json
python3 scripts/implant_skill.py apply --manifest MANIFEST.json --approval-token sha256:... --backup-root BACKUPS
python3 scripts/implant_skill.py verify --manifest MANIFEST.json --level invoked --allow-executable /absolute/native-cli
python3 scripts/implant_skill.py rollback --manifest MANIFEST.json --approval-token sha256:...
python3 scripts/validate_implant_manifest.py MANIFEST.json
```

`--allow-executable` is repeatable. Commands run as argv with `shell=False`. A discovery command or version command whose executable is not explicitly allowed must fail closed.

## U1: Immutable plan manifest

Add:

- `assets/implant-manifest.schema.json`
- `assets/implant-request.template.json`
- `scripts/validate_implant_manifest.py`

`inspect` reads a request and writes a manifest with these top-level keys:

- `schema_version`
- `plan`
- `plan_hash`
- `status`
- `receipts`
- `events`

The plan includes:

- source path, source URI, expected skill name, parsed frontmatter name, and deterministic source tree SHA-256;
- scope goal, allowed actions, excluded expansions;
- compatibility status and blocking reasons;
- target surface, root, destination name, ownership, install method, collision classification, rename destination where applicable, observed prior state, minimum discovery level, and adapter contract;
- rollback plan and backup-root requirement.

Compute `plan_hash` from canonical JSON of `plan`. Every apply, verify, rollback, and validation operation recomputes it and fails with `PLAN_HASH_MISMATCH` if the plan changed. Runtime status, events, and sanitized receipts may change without changing the plan.

## U2: Guarded apply and rollback

Add `scripts/implant_skill.py` with standard-library-only implementation.

Apply requirements:

- Requires exact `--approval-token` equality with `plan_hash`.
- Re-hashes the source before and after apply and fails if source content changed.
- Requires `compatibility.status == compatible`.
- Default install method is `link` to the canonical source.
- `copy` is allowed only when declared in the immutable plan and must record exact parity.
- Target roots must already exist. Never invent or scan roots.
- Use only the target destinations named in the plan.
- Be transaction-safe. On any target failure, revert mutations performed in that apply attempt and restore backups.

Collision classifications:

- `BLOCK`: fail before mutation.
- `KEEP`: leave the existing destination untouched. It passes apply only when it already resolves to or exactly matches the approved source.
- `MERGE`: classify and stop with `MERGE_REQUIRES_HUMAN`. Never auto-merge.
- `REPLACE`: move the prior destination into the approved backup root before installing. Record the backup path.
- `RENAME`: leave the prior destination untouched and install at the plan's `rename_to` destination. Refuse if that destination exists.

Rollback requirements:

- Requires the exact approval token.
- Removes only destinations created by this manifest.
- Restores recorded backups for REPLACE.
- Leaves KEEP destinations untouched.
- Is idempotent or returns an explicit already-rolled-back state.
- Records a rollback receipt without raw file content.

## U3: Target-native discovery gate

Verification levels are ordered: `present`, `indexed`, `loaded`, `invoked`.

- `present` proves the destination exists.
- `integrity` is always checked: a link resolves to the canonical source; a copy has exact tree parity.
- `indexed`, `loaded`, and `invoked` require a request-supplied adapter for that exact level.
- Every adapter contains `level`, argv `version_command`, `version_regex`, argv `command`, `success_regex`, and `timeout_seconds`.
- Version command must pass and match before the discovery command runs.
- An adapter must use an explicitly allowed executable.
- Store only return code, pass/fail, duration, command hash, stdout hash, stderr hash, and version-match result. Never store raw stdout/stderr or excerpts.
- Overall verification fails if presence passes but any required higher level fails. The existence-only red case must remain red.
- Do not hard-code unverified native CLI syntax. Documentation must explain how an operator supplies version-pinned adapters for Hermes, Claude Code, Codex, and Gemini.

## U4: Replay pack and executed proof

Add `tests/` using `unittest` and temporary directories. Cover at least:

1. Clean package, four roots, canonical links, and all four levels passing through fake native adapters.
2. Existence-only red case where the destination exists but `indexed` fails.
3. Collision behavior for BLOCK, KEEP, MERGE, REPLACE, and RENAME, including rollback.
4. Copy parity drift detected after apply.
5. Incompatible framework correct-stop.
6. Plan tampering and wrong approval token fail before mutation.
7. Discovery executable allowlist fails closed.
8. Receipts contain hashes and statuses but no raw output.
9. Scope exclusions remain in the immutable plan and no operation can add a target after inspection.

The external Ringer checker is authoritative in addition to repository tests.

## U5: Skill and operator contract

Update:

- `SKILL.md`
- `references/install-upgrade-protocol.md`
- add `references/cross-harness-skill-implant.md`

Documentation must:

- keep Cleaner installation separate from mission recommendations;
- require explicit approval of the immutable plan hash before target mutation;
- separate inspect from apply, verify, and rollback;
- distinguish present, indexed, loaded, and invoked;
- state one canonical package and link-first policy;
- define copy-only parity and drift checks;
- define the one-job/one-goal scope stop;
- include a rollback and sanitized receipt example;
- avoid stale or invented CLI commands for target-native discovery.

## Review repair addendum

The first independent review returned `REVISE`. Promotion remains blocked until all four repairs are proven:

1. **Transactional rollback:** a failure on any target must restore every target and backup to the pre-rollback state so the same approved rollback can be retried. Persist no false rolled-back state.
2. **Rollback target drift:** before deleting a manifest-created destination, prove it still matches the exact installed method and recorded installed tree. If it differs, fail `ROLLBACK_TARGET_DRIFT` without changing any target.
3. **Declared-method integrity:** a non-KEEP `copy` target must remain a real directory with exact tree parity. A symlink substitute is not acceptable even when it points to the canonical source.
4. **Missing executable evidence:** an allowed but unavailable adapter executable must produce a persisted sanitized failure receipt and a stable `EXECUTABLE_NOT_FOUND` error, not an unhandled traceback.
5. **Sealed backup root:** the exact absolute backup root must be part of the immutable plan. Apply must fail `BACKUP_ROOT_MISMATCH` before mutation when its CLI argument differs from the approved plan.
6. **Fresh discovery evidence:** every verify run must overwrite unrequested higher levels as `NOT_RUN`; no previously green `loaded` or `invoked` receipt may survive a narrower run.
7. **Executable contract artifacts:** runtime validation must enforce structural parity with `assets/implant-manifest.schema.json`, including conditional path-state requirements, and a concrete request derived from the template must pass `build_plan()`.
8. **Source isolation:** inspect must fail `SOURCE_TARGET_OVERLAP` when any destination or effective destination is the canonical source, its ancestor, or its descendant, including `REPLACE` and `RENAME` cases.

Add unit tests for every repair. The external checker fault-injects the second backup restore during a multi-target rollback and is authoritative.

## Acceptance commands

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 /mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/check_implant_workflow.py --repo .
python3 -m py_compile scripts/implant_skill.py scripts/validate_implant_manifest.py
```

All must exit 0. Git status may contain only the files owned by the Ringer task and this committed spec.

## Decision residue

- Hardest decision: target-native commands are configuration, not hard-coded assumptions. The workflow verifies a version-pinned adapter without pretending all harness versions expose the same interface.
- Alternatives rejected: four copied packages, filesystem-only proof, automatic MERGE, and editing live skill roots before build verification.
- Least-confident assumption: some target harnesses may not provide a non-model native command capable of proving `loaded` or `invoked`; the correct state then remains unproven rather than green.
