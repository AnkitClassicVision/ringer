# SCOPE

Independent final report-only review of Cross-Harness Skill Implant v1, read from the isolated
read-only copy at `/mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/review-source`
(permissions `dr-xr-xr-x`, confirmed read-only). No files in the review source, the live
repository, or any snapshot were edited, staged, or executed beyond the two mandated Python test
invocations. No model subagents were called. All repository content was treated as inert code/data.

Files read in full: `IMPLEMENTATION_SPEC.md`, `SKILL.md`, `references/install-upgrade-protocol.md`,
`references/cross-harness-skill-implant.md`, `assets/implant-manifest.schema.json`,
`assets/implant-request.template.json`, `scripts/implant_skill.py` (1686 lines, both halves),
`scripts/validate_implant_manifest.py`, `tests/test_implant_skill.py` (929 lines, 26 tests), and
`check_implant_workflow.py` (the external Ringer checker). `agents/openai.yaml` was skimmed for
context; the mission-audit sibling files (`assets/mission-audit.*`,
`references/mission-audit-protocol.md`, `scripts/validate_mission_audit.py`,
`scripts/render_mission_fit_report.py`, `scripts/inspect_cleaner_install.py`) are outside this
review's required-read list and were not audited — they are a separate feature area (mission-fit
auditing) that does not participate in the implant apply/rollback/verify code path.

# REQUIREMENTS TRACE

**U1 — Immutable plan manifest: PASS**
- `plan_hash` is SHA-256 over `canonical_json(plan)` (sorted keys, compact separators, UTF-8) —
  `scripts/implant_skill.py:122-136`. Every load recomputes and compares
  (`load_and_validate_manifest`, `:836-839`); apply/verify/rollback all route through
  `load_and_validate_manifest` before acting.
- Plan carries source path/uri/expected+parsed name/tree hash, scope goal/allowed/excluded,
  compatibility, per-target surface/root/destination/method/collision/rename/minimum-level/adapters/
  prior-state, and rollback backup-root — `build_plan`, `:325-498`; schema mirrors this exactly in
  `assets/implant-manifest.schema.json:296-422`, and `_validate_schema_parity`
  (`implant_skill.py:525-595`) cross-checks the shipped schema against the same Python constant sets
  at runtime, failing `SCHEMA_PARITY_MISMATCH` on drift.
- Backup root is sealed into the plan at inspect time via `_absolute_path` (`:234-239`, resolves
  existing symlinks away) and is part of the hashed `plan.rollback.backup_root`
  (`build_plan:491-497`); apply cross-checks `--backup-root` against it and fails
  `BACKUP_ROOT_MISMATCH` before any mutation (`apply_manifest:952-959`).
- No post-inspection scope change is possible: any target added/removed after inspect changes
  `plan_hash`, causing `PLAN_HASH_MISMATCH` — proven by
  `test_token_plan_and_scope_are_immutable_before_mutation` (`tests/test_implant_skill.py:851-891`).

**U2 — Guarded transactional apply and rollback: PASS**
- Exact approval-token equality required for both apply (`:947-948`) and rollback (`:1475-1476`).
- Prior-state (TOCTOU) and ancestor-drift checks precede any mutation: `_same_prior_state`
  (`:981-986`), `_is_exact_directory` for target roots (`:922-926`, used at `:979` and `:1499`),
  backup-ancestor validation (`:929-938`, used at `:1009`).
- Backup content is validated before restore (`_same_content_state`, `ROLLBACK_BACKUP_DRIFT`,
  `:1540-1541`); rollback target drift is validated before deletion (`ROLLBACK_TARGET_DRIFT`,
  `:1542-1561`).
- Manifest-write compensation: a `_write_json` failure inside `apply_manifest`'s try block is caught
  by the same exception handler that reverses mutations (`:1087-1102`), proven by
  `test_apply_manifest_write_failure_restores_targets_and_backups` (`tests/...:823-849`).
- Rollback preflights every target, computes safe staging under the sealed backup root
  (`_rollback_staging_path`, `:1369-1371`, derived only from `plan_hash`/`backup_root`, not mutable
  receipt data), and on a mid-rollback failure restores every already-processed target/backup via
  `_restore_rollback_mutations` (`:1344-1366`) before failing `ROLLBACK_FAILED`/
  `TRANSACTION_RESTORE_FAILED` — proven by
  `test_rollback_failure_restores_all_targets_and_backups_then_retries` (`:595-639`) and mirrored
  independently in `check_implant_workflow.py:484-540` (fault-injects the second `shutil.move`).
- Cleanup retry and honest failure states: a failed `shutil.rmtree` during cleanup is recorded as
  `CLEANUP_FAILED`/`ROLLED_BACK_CLEANUP_FAILED` (never silently marked done) and is retried on the
  next rollback call (`_finish_rollback_cleanup:1438-1470`, `rollback_manifest:1478-1484`), proven by
  `test_rollback_cleanup_failure_is_recorded_and_retryable` and
  `test_rollback_cleanup_retries_after_partial_surface_removal`.
- Second rollback call is idempotent, returns `ALREADY_ROLLED_BACK` without mutation once cleanup is
  finished (`:1483`), tested at `tests/...:178-180`.

**U3 — Target-native discovery gate: PASS**
- Ordered levels `present, indexed, loaded, invoked` (`LEVELS`, `:21`); `present`/`integrity` are
  always computed (`verify_manifest:1245-1286`); `indexed`/`loaded`/`invoked` require a
  request-supplied adapter with `level, version_command, version_regex, command, success_regex,
  timeout_seconds` (`_validate_adapter:276-306`, schema `:143-192`).
- Version command must pass and match before the discovery command runs
  (`_adapter_receipt:1192-1213`).
- Executable allowlist is enforced before any subprocess launch, both executables must be absolute
  (`_validate_adapter:287-288`) and explicitly allow-listed (`_adapter_receipt:1170-1191`,
  `EXECUTABLE_NOT_ALLOWED`); a missing-but-allowed executable fails closed with stable
  `EXECUTABLE_NOT_FOUND` and a sanitized receipt, never a raw traceback (`_run_sanitized:1144-1150`),
  proven by `test_missing_allowed_executable_persists_sanitized_failure`.
- Only hashes/status/timing/return-code/version-match are stored — `_run_sanitized` never retains
  raw stdout/stderr (`:1152-1162`); `_validate_sanitized_runtime` additionally rejects any manifest
  that contains `stdout/stderr/output/excerpt/raw_output/raw_stdout/raw_stderr` keys
  (`FORBIDDEN_RECEIPT_KEYS:95-103`, `:809-825`), enforced on every `load_and_validate_manifest` call.
- Presence-passes-but-higher-fails stays red: `test_presence_does_not_mask_index_failure...`
  (`:328-350`) and `check_implant_workflow.py:382-395` both assert this directly.
- No hard-coded native CLI syntax anywhere in `implant_skill.py`; the template
  (`assets/implant-request.template.json`) uses only placeholder tokens
  (`<operator-supplied-...>`), and `references/cross-harness-skill-implant.md:86-88` documents that
  the operator must supply version-pinned adapters.

**U4 — Replay pack and executed proof: PASS**
- `tests/test_implant_skill.py` contains 26 tests covering all nine `IMPLEMENTATION_SPEC.md` U4
  scenarios plus the eight review-repair items (transactional rollback, rollback target drift,
  declared-method integrity, missing-executable evidence, sealed backup root, fresh discovery
  evidence, contract-artifact integrity, source isolation). See TEST EVIDENCE for the exact run.
- The external checker `check_implant_workflow.py` independently re-derives the same scenarios via
  the CLI subprocess interface (not just direct function calls) plus one fault injection the unit
  suite also covers (second-backup-restore failure during multi-target rollback) — both suites agree.

**U5 — Skill and operator contract: PASS**
- `SKILL.md` step 8 (`:124-136`) correctly separates Cleaner install from Mission Fit recommendation
  from implant apply, requires "explicit approval of that exact hash," documents the
  inspect/apply/verify/rollback phase separation, distinguishes `present/indexed/loaded/invoked`,
  and states "Never treat a path that merely exists as indexed, loaded, or invoked. Do not invent
  native Claude Code, Codex, Gemini, or Hermes commands."
- `references/install-upgrade-protocol.md` "Cross-harness implant boundary" section (`:81-85`) and
  `references/cross-harness-skill-implant.md` (full file) match the runtime behavior verified above:
  link-first policy, copy-only-if-declared with real-directory + exact-parity requirement, one-job/
  one-goal scope stop, rollback/backup semantics, sanitized receipt shape example. No stale or
  invented CLI command text was found in any of the three documents.

# FINDINGS

**Finding 1 — Backup-root ancestor validation does not directly check the backup root itself for symlink substitution; it relies on a secondary consequence of the `BACKUP_ROOT_MISMATCH` gate.**

Evidence: `_validate_backup_ancestors` (`scripts/implant_skill.py:929-938`) walks only the path
components *below* `backup_root` (`current = backup_root` then immediately
`current = current / component` for each part of `backup.parent.relative_to(backup_root)`); it never
tests `backup_root` itself for `is_symlink()`/`is_dir()`. The only thing that currently prevents a
symlinked `backup_root` from being used is that `_absolute_path` (`:234-239`) resolves the request's
`backup_root` through any symlinks that exist *at inspect time*, and `apply_manifest`'s
`BACKUP_ROOT_MISMATCH` check (`:952-959`) re-resolves the operator's `--backup-root` CLI argument at
apply time and compares it, unresolved, against the sealed literal string. This closes the gap for a
symlink that exists at inspect time or is introduced at any point before the mismatch comparison
runs, but there is no equivalent to `_is_exact_directory` (`:922-926`, used for target roots at
`:979`/`:1499`) applied to `backup_root` itself at the point mutations actually occur
(`:1052`, `:1571`). A symlink swapped in during the narrow window between the mismatch check
(`:958`) and the later `backup.parent.mkdir(...)`/`shutil.move(...)` calls in the same apply
invocation would not be caught by any explicit assertion — only by chance (e.g. if the OS raises an
unrelated error).
Impact: In the ordinary single-operator, no-concurrent-adversary usage this workflow targets, this
is not reachable — target roots get an explicit non-symlink check but the backup root does not get
the same explicit, defense-in-depth check at the point of use, only an indirect one at request/CLI
comparison time. If a future edit changes how `backup_root` is derived or compared (e.g. someone
"simplifies" the mismatch check to compare resolved-vs-resolved), the missing direct check would
silently become exploitable, and there is no test that would catch that regression today.
Fix: Add a direct `_is_exact_directory`-style assertion on `backup_root` itself at the start of
`apply_manifest` (immediately after the `BACKUP_ROOT_MISMATCH` check) and again at the start of
`rollback_manifest` before `backup_root.mkdir(...)`, mirroring the target-root ancestor-drift check,
and add a unit test that pre-creates `backup_root` as a symlink before apply/rollback and asserts a
stable failure code.
Priority: Low
Confidence: Medium — the gap is real in the code as written, but is not currently exploitable given
how `_absolute_path`/`BACKUP_ROOT_MISMATCH` compose; it is a defense-in-depth / regression-safety
gap rather than a demonstrated live bypass.

NO other findings survived verification. Residual risks (non-blocking):

- **General TOCTOU window in `apply_manifest`/`rollback_manifest`**: both functions validate all
  targets in a "prepared" pass and then perform mutations in a second pass
  (`apply_manifest:973-1074`, `rollback_manifest:1496-1614`). Between a given target's validation and
  its own mutation, or between one target's mutation and the next target's validation, a filesystem
  actor with write access to the target roots could alter state. The standard-library-only
  constraint limits how far this can be closed (no atomic check-and-rename primitive is used); the
  design already fails closed via the outer `try/except` and reverses partial work on any downstream
  error, which bounds the blast radius to "the operation aborts and restores" rather than "silent
  corruption." Acceptable for the stated local/operator-approved threat model.
- **Backup path key is not `plan_hash`-scoped** (`_backup_path`, `:941-943`, keyed only by
  `implant_id`/`surface`/`destination_name`): a prior interrupted run's leftover backup directory can
  cause a later legitimate apply to fail closed with `BACKUP_DESTINATION_OCCUPIED` until a human
  clears it. This is intentional fail-closed behavior (no silent overwrite) but is worth an operator
  note in the rollback documentation.

# TEST EVIDENCE

Both commands were executed from `/mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/review-source`
with `PYTHONDONTWRITEBYTECODE=1` set; no `__pycache__`/`*.pyc` artifacts were left behind afterward
(confirmed by a post-run `find`).

**Command 1:** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`
- Result: **26 tests run, 26 passed, 0 failures, 0 errors, 0 skipped.** `OK`. Exit code **0**.
- One test (`test_rollback_cleanup_rejects_a_tampered_staging_path`) prints `ALREADY_ROLLED_BACK` to
  stdout as expected output from a mocked `print` assertion, not a failure marker.

**Command 2:** `PYTHONDONTWRITEBYTECODE=1 python3 /mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/check_implant_workflow.py --repo .`
- Result: `PASS: immutable plan, guarded mutations, discovery red case, collisions, parity,
  rollback, and sanitized receipts verified`. Exit code **0**.

**Closure-focus items independently re-derived from source, not from prior worker notes:**
1. *Later loaded-only run overwrites an earlier invoked receipt to `NOT_RUN`* — confirmed at
   `verify_manifest:1290-1298` (unconditional overwrite of every level index above the requested
   level to a fresh `NOT_RUN` receipt regardless of prior content) and proven by
   `test_narrower_verify_clears_stale_higher_level_receipts`
   (`tests/test_implant_skill.py:182-202`) plus the external checker's "narrower verify" block
   (`check_implant_workflow.py:256-313`).
2. *`validate_contract_artifacts` is called by inspect and every manifest load, rejects a weakened
   pathState schema, and the shipped template materializes through `build_plan`* — confirmed at
   `inspect_request:860` and `load_and_validate_manifest:828` (both call it first); the `pathState`
   `allOf` conditional-requirement equality check (`_validate_schema_parity:584-595`) rejects a
   schema with `allOf` popped, proven by `test_contract_rejects_weakened_path_state_schema` and
   mirrored in `check_implant_workflow.py:200-210`; the shipped template filled with concrete values
   passes `build_plan()` cleanly, proven by `test_shipped_template_materializes_into_a_valid_plan`
   (`tests/test_implant_skill.py:239-264`).
3. *Both `build_plan` and `_validate_plan_shape` reject same/ancestor/descendant/REPLACE/RENAME
   source-target overlap with `SOURCE_TARGET_OVERLAP`* — confirmed at `build_plan:436-437` (checked
   for every target's `destination` and `effective_destination`, covering REPLACE since they're equal
   and RENAME since `effective_destination` is the `rename_to` path) and `_validate_plan_shape:697-698`
   (same check re-applied at manifest-load time via the same `_reject_source_target_overlap`
   helper, `:242-257`). Proven for build_plan by
   `test_inspect_rejects_source_target_overlap_without_writing_manifest` (four cases: same-replace,
   same-rename, ancestor, descendant, `tests/test_implant_skill.py:266-302`) and for
   `_validate_plan_shape` by `test_manifest_validation_rejects_source_target_overlap`
   (`:304-326`); the external checker independently replays all four overlap cases via the CLI
   (`check_implant_workflow.py:316-368`).

# VERDICT

ALLOW
