# Cross-Harness Skill Implant v1

This workflow installs one canonical local skill package into explicitly named, existing roots. It uses only Python's standard library. It does not inspect or modify live roots unless the operator places those exact roots in a request and later approves the resulting plan hash.

## One job, one goal

Each request has one implant ID, one goal, one canonical source, and a finite target list. Put every allowed action and excluded expansion in `scope`. Stop and create a new request when the work adds another skill, repository migration, framework port, remote rollout, control plane, cron, download, runtime restart, or target root. Runtime commands consume only targets already sealed into the plan, so they cannot append a destination after inspection.

Cleaner installation is a different workflow. Do not combine the official Cleaner download, edition selection, or upgrade with an implant request or Mission Fit recommendation.

## Immutable plan

Start from `assets/implant-request.template.json`. The request names:

- the absolute canonical source path, source URI, and expected frontmatter name;
- the exact goal, allowed actions, and excluded expansions;
- compatibility status and any blocking reasons;
- each surface, existing root, destination, ownership, method, collision action, minimum discovery level, and adapter contract;
- the rollback requirement and exact absolute backup root.

Inspect parses the `SKILL.md` frontmatter, hashes the complete source tree deterministically, records the observed prior state, and writes `schema_version`, `plan`, `plan_hash`, `status`, `receipts`, and `events`. `plan_hash` is SHA-256 over canonical JSON of `plan`. Status, receipts, and events can change. The plan cannot.

Every CLI phase checks the published manifest schema and request template against the standard-library Python contract before processing a request or manifest. Schema drift fails `SCHEMA_PARITY_MISMATCH`; template drift fails `TEMPLATE_PARITY_MISMATCH`. The check covers the required key sets, enums, hashes, rollback fields, adapter shape, and kind-specific path-state requirements. It is a focused parity check, not a general JSON Schema implementation.

Every later phase and the standalone validator recomputes the hash. A changed plan fails `PLAN_HASH_MISMATCH` before target mutation. Apply and rollback also require exact token equality and fail `APPROVAL_TOKEN_MISMATCH` when the supplied token differs.

## Four separate phases

Run these commands from the skill package repository root:

```bash
python3 scripts/implant_skill.py inspect --request REQUEST.json --manifest MANIFEST.json
python3 scripts/validate_implant_manifest.py MANIFEST.json
python3 scripts/implant_skill.py apply --manifest MANIFEST.json --approval-token sha256:... --backup-root BACKUPS
python3 scripts/implant_skill.py verify --manifest MANIFEST.json --level invoked --allow-executable /absolute/native-cli
python3 scripts/implant_skill.py rollback --manifest MANIFEST.json --approval-token sha256:...
```

`--backup-root` is an operator cross-check against `plan.rollback.backup_root`; it is not runtime authority. Its resolved value must equal the absolute root sealed by inspect or apply fails `BACKUP_ROOT_MISMATCH` before changing a target or backup. `--allow-executable` repeats when an approved adapter uses more than one executable. Inspect is read-only for source and targets. Apply is the first target mutation. Verify does not install or repair. Rollback derives backup paths from the sealed plan and validates the apply receipts against those paths.

Before apply, show the complete plan and ask the operator to approve its exact `sha256:` value. Approval of a goal, a recommendation number, a prior hash, or the words "looks good" is insufficient.

## Canonical package and install methods

The source package remains read-only. Apply hashes it before and after target work. A mismatch fails closed and reverses target changes from that attempt.

`link` is the default. Each created symlink points to the same absolute canonical source directory. This avoids independent editable copies.

`copy` must be explicit in the immutable target plan. Apply records the copied tree hash. For a non-`KEEP` copy, verify requires a real non-symlink directory and exact tree parity; a symlink to the canonical source is the wrong declared method and fails `INTEGRITY_FAILED`. `KEEP` may still be either the canonical link or an exact-parity directory. Repair requires a new approved plan or rollback. Verify never silently resynchronizes a copy.

Target roots must already exist. Apply and rollback require each sealed root to remain the same resolved, non-symlink directory; ancestor symlink drift fails before target mutation. The workflow never searches for roots or creates one. An incompatible plan fails `INCOMPATIBLE_FRAMEWORK` before target mutation.

The canonical source and each declared or effective destination must be disjoint after absolute path resolution. A destination equal to the source, above it, or below it fails `SOURCE_TARGET_OVERLAP` during inspect before prior-state capture and during manifest validation. A rejected inspect does not write a manifest.

## Collision actions

Collision actions are uppercase and immutable:

| Action | Behavior |
|---|---|
| `BLOCK` | Install only when the named destination is absent. An existing destination fails `COLLISION_BLOCKED`. |
| `KEEP` | Leave the destination untouched. It passes only when it resolves to the canonical source or has exact source tree parity. |
| `MERGE` | Stop with `MERGE_REQUIRES_HUMAN`. The workflow never merges automatically. |
| `REPLACE` | Move the approved prior destination under the sealed backup root, then install. Rollback removes the manifest-created target and restores the backup. |
| `RENAME` | Leave the original destination untouched and install at `rename_to`. An occupied alternate fails closed. |

Apply preflights every target before its first target write. If a later mutation fails, it removes destinations created during that attempt and restores backups from that attempt.

## Discovery and integrity

Integrity is always a separate gate. A link passes only when it resolves to the canonical source. A copy passes only when its tree hash exactly matches the source.

Discovery levels are ordered:

| Level | Proof |
|---|---|
| `present` | The effective destination exists. This check is built in. |
| `indexed` | The target's native index reports the skill through an approved adapter. |
| `loaded` | The target's native runtime reports the skill loaded through an approved adapter. |
| `invoked` | The target's native runtime proves invocation through an approved adapter. |

Presence does not imply any higher level. If presence is green and indexed is red, overall verification remains red.

Each verification rewrites every unrequested higher discovery level to a fresh `NOT_RUN` receipt with `passed: false` and null version and discovery fields. A narrower verification cannot retain a pass from an earlier higher-level run.

The request owner supplies an adapter for each required higher level. An adapter contains `level`, argv `version_command`, `version_regex`, argv `command`, `success_regex`, and `timeout_seconds`. Both argv executables must be absolute and explicitly repeated through `--allow-executable`. The version command must exit zero and match before the discovery command runs. Commands use `shell=False`. An allow-listed executable that cannot be launched fails with stable code `EXECUTABLE_NOT_FOUND`; verification persists only the status, timing, return-code placeholder, and command/stdout/stderr hashes, never exception text or raw output.

Native command syntax is version-specific configuration. This package does not claim built-in discovery commands for Hermes, Claude Code, Codex, or Gemini. The operator must obtain a supported command from the target's installed version, pin its version result, and put that exact contract in the request.

## Sanitized receipts

Discovery receipts keep only status, return code, duration, command hash, stdout hash, stderr hash, match result, and pass/fail state. They never store argv output, excerpts, or message bodies. A representative receipt shape is:

```json
{
  "passed": true,
  "status": "PASSED",
  "return_code": 0,
  "duration_seconds": 0.012345,
  "command_sha256": "<64 lowercase hex characters>",
  "stdout_sha256": "<64 lowercase hex characters>",
  "stderr_sha256": "<64 lowercase hex characters>",
  "version_match": true
}
```

Raw stdout and stderr exist only in process memory long enough to test the approved regular expression and compute hashes.

## Rollback

Rollback requires the exact plan hash token. Before its first mutation, it validates every manifest-created link or copy against the declared method and apply hash, and it checks each `REPLACE` backup against the prior-state kind and content hash sealed in the plan. Target drift fails `ROLLBACK_TARGET_DRIFT`; backup drift fails `ROLLBACK_BACKUP_DRIFT`. Both stop before changing any target or backup, so human changes are preserved. `KEEP` destinations remain untouched.

Rollback derives each backup path and its exact hidden staging path from the immutable plan, not mutable runtime receipt data. Backup-path ancestors must remain real directories under the sealed root. Rollback validates the staging path and staged target set before cleanup, including a verified partial remainder after a recorded cleanup failure. If any target operation fails, it moves every restored backup and staged target back to the pre-rollback state, leaves the manifest at its prior status, and permits the same approved rollback to be retried. If compensation itself fails, recoverable staging is preserved for human review rather than deleted. A successful rollback removes normal staging, records `ROLLED_BACK`, and a second rollback reports `ALREADY_ROLLED_BACK` without another mutation.

Rollback is not permission to delete an unplanned path. If receipt paths, methods, collision actions, installed hashes, or backup paths disagree with the immutable plan, rollback fails closed for human review.
