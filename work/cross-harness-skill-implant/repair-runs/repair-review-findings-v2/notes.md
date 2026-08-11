# Cross-Harness Skill Implant v1 repair notes

CANARY: blue paperclip

## Result

The five locked pre-promotion defects are closed in the development repository. The final fresh report-only review returned `APPROVE`. This run did not promote or modify any live skill, runtime, Ringer state, git state, network service, MCP/App, memory, cron, or remote system.

Highest true state: local repair worktree with all required tests passed. No commit, push, merge, deploy, or live promotion was performed.

## Changed files

- `scripts/implant_skill.py`: sealed-backup enforcement, declared-method verification, sanitized missing-executable handling, transactional apply/rollback compensation, target and backup drift preflight, exact staging derivation, and guarded cleanup retry.
- `scripts/validate_implant_manifest.py`: standalone immutable-manifest validation entry point.
- `tests/test_implant_skill.py`: 19 unit tests covering the locked repairs and reviewer-discovered transaction/path edge cases.
- `assets/implant-manifest.schema.json`: manifest plan shape, including sealed `plan.rollback.backup_root`.
- `assets/implant-request.template.json`: operator-supplied absolute rollback backup root.
- `references/cross-harness-skill-implant.md`: operator contract for plan hashing, apply/verify/rollback, drift, staging, receipts, and backup-root authority.
- `references/install-upgrade-protocol.md`: cross-harness implant boundary and approval separation.
- `SKILL.md`: four-phase implant workflow and safety boundary.

## Acceptance evidence

1. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`
   - Exit 0.
   - 19 tests run, 19 passed, 0 failures, 0 errors.
2. `PYTHONDONTWRITEBYTECODE=1 python3 /mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/check_implant_workflow.py --repo .`
   - Exit 0.
   - 1 authoritative checker invocation, 1 PASS result.
   - Receipt: `PASS: immutable plan, guarded mutations, discovery red case, collisions, parity, rollback, and sanitized receipts verified`.
3. `PYTHONPYCACHEPREFIX=/tmp/skill-implant-repair-pyc python3 -m py_compile scripts/implant_skill.py scripts/validate_implant_manifest.py`
   - Exit 0.
   - 2 modules compiled.

## Review findings closed

- Repair 1: a second rollback move failure restores every completed forward mutation and permits retry; failed compensation preserves recoverable staging instead of deleting it.
- Repair 2: rollback rejects changed manifest-created links or copies before any target or backup mutation; human-changed targets remain intact.
- Repair 3: a non-`KEEP` copy must remain a real non-symlink directory with exact tree parity; a canonical symlink substitute fails `INTEGRITY_FAILED`.
- Repair 4: an allow-listed missing executable persists a hash-only `EXECUTABLE_NOT_FOUND` receipt, sets verification failure, and returns a stable workflow error without raw output or exception text.
- Repair 5: the exact absolute backup root is sealed into the request and plan hash; apply only cross-checks it, and rollback derives paths from the immutable plan.
- Fresh-review closure: backup content drift, tampered cleanup receipt paths, apply manifest-write failure, symlinked backup ancestors, target-root ancestor drift, and partial staging cleanup retry now fail closed or recover safely. The focused reviewer confirmed all findings closed.

## Residual risks

- Verification used temporary local fixtures and the authoritative checker. No live harness root or native runtime was exercised, and no live promotion is claimed.
- Filesystem preflight and mutation are separate operations, so an adversarial concurrent path change can still create a time-of-check/time-of-use race. The workflow detects ordinary drift before mutation but is not an operating-system transaction.
- If rollback compensation itself encounters an unrecoverable filesystem error, the workflow returns `TRANSACTION_RESTORE_FAILED` and preserves recoverable staging for human review. Automatic retry is guaranteed only after compensation restores the pre-rollback state.
