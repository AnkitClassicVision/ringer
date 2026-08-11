# Cross-Harness Skill Implant v1 repair notes

CANARY: blue paperclip

## Highest verified state

Local development-repository artifacts only; all requested tests passed. No live skill, runtime configuration, git state, Ringer configuration, network service, remote system, or promotion target was changed. Live promotion was not attempted or claimed.

## Changed files

- `scripts/implant_skill.py`
- `tests/test_implant_skill.py`
- `assets/implant-manifest.schema.json`
- `assets/implant-request.template.json`
- `references/cross-harness-skill-implant.md`
- `references/install-upgrade-protocol.md`
- `SKILL.md`
- `repair-runs/repair-review-findings/notes.md` in the Ringer task directory

## Review findings closed

1. Transactional multi-target rollback: installed targets are staged under the sealed backup root, target-operation failures compensate every changed target and backup, the manifest remains at its pre-attempt state, and retry succeeds. Cleanup state is persisted honestly and failed cleanup is retryable.
2. Rollback target drift: every manifest-created link or copy is validated before the first rollback mutation. Drift returns `ROLLBACK_TARGET_DRIFT` and preserves human-changed content.
3. Declared-method verification: a non-`KEEP` copy must be a real non-symlink directory with exact tree parity. A canonical symlink substitute returns `INTEGRITY_FAILED`; `KEEP` retains its documented link-or-parity behavior.
4. Missing executable evidence: adapter launch `OSError`/`FileNotFoundError` becomes a sanitized hash-only `EXECUTABLE_NOT_FOUND` receipt, persisted verify failure, and stable `WorkflowError` without exception text or raw stdout/stderr.
5. Sealed backup root: request and immutable plan now contain the exact absolute `rollback.backup_root`. Apply treats `--backup-root` only as a resolved-value cross-check and fails `BACKUP_ROOT_MISMATCH` before mutation. Rollback derives backup paths from the sealed plan and cross-checks receipts.

## Acceptance evidence

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`
  - Exit 0
  - 12 tests run, 12 passed
- `PYTHONDONTWRITEBYTECODE=1 python3 /mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/check_implant_workflow.py --repo .`
  - Exit 0
  - 1 authoritative end-to-end checker passed, including rollback fault injection, rollback drift, copy-kind substitution, missing executable, and backup-root mismatch
- `PYTHONPYCACHEPREFIX=/tmp/skill-implant-repair-pyc python3 -m py_compile scripts/implant_skill.py scripts/validate_implant_manifest.py`
  - Exit 0
  - 2 Python modules compiled
- JSON parse check for `assets/implant-manifest.schema.json` and `assets/implant-request.template.json`
  - Exit 0
  - 2 JSON files parsed

## Report-only review

The authoritative external checker was run in a fresh Python process against the development repository after the final implementation changes. It passed every locked case. A final containment review found no target additions, hard-coded harness commands, shell execution, raw command output in receipts, automatic merge/overwrite behavior, or runtime authority outside the immutable plan.

## Residual risks

- If rollback compensation itself encounters another filesystem failure, the workflow returns `TRANSACTION_RESTORE_FAILED`; manual inspection may then be required because software cannot guarantee restoration when the recovery operations also fail.
- A hard process termination can leave hidden rollback staging. The manifest records cleanup pending before staging deletion, and rerunning the same approved rollback validates and cleans only the staging path inside the sealed backup root.
- Verification is local only. No live promotion or live-runtime discovery was performed.

## Decision residue

- Hardest decision: preserve exact installed targets during rollback by moving them into hidden staging, rather than trying to reconstruct links or copied trees after a failure.
- Rejected alternative: delete installed targets and recreate them from the canonical source during compensation; that would not prove restoration of the exact pre-rollback copy.
- Least-confident assumption: the underlying filesystem can complete compensation moves after the initiating move failure. A second recovery failure is surfaced explicitly as `TRANSACTION_RESTORE_FAILED`.
