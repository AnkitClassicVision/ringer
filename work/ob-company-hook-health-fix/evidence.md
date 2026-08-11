# ob_company staff hook alert evidence packet

## Current alert

- Job: `ob_company_daily_staff_audit` (`ba484b0d6dbb`)
- Scheduled daily at 08:00 America/New_York from the `full-access-worker-a` Hermes profile.
- 2026-08-09 output: `continuous hook needs attention` for `vince/claude-code`; proof says no qualifying lifecycle event exists inside the seven-day completed-window bound.
- The scheduler reported `last_status=ok`. This is an operational-health alert, not a cron crash.

## Verified current implementation

- Cron wrapper: `/home/ankit114/.hermes/profiles/full-access-worker-a/scripts/ob_company_daily_staff_audit.sh`
- Runtime repo: `/home/ankit114/repos/ob_company_deploy`
- Main runner: `/home/ankit114/repos/ob_company_deploy/scripts/run_ob_company_daily_watchdog.sh`
- Detector: `/home/ankit114/repos/ob_company_deploy/scripts/ob_company_daily_watchdog.py`
- Policy: `/home/ankit114/repos/ob_company_deploy/config/ob_company_daily_watchdog_policy.json`
- State: `/home/ankit114/.hermes/profiles/full-access-worker-a/cron/state/ob_company_daily_staff_audit_v2.json`

The policy classifies `vince/claude-code` and `ziad/claude-code` as `continuous`. A continuous pair is unhealthy whenever `last_lifecycle_at` is null inside the completed seven-day query window. Qualifying types are `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SessionEnd`, and `PreCompact`.

The current route tells Bre/ops to produce one sanitized lifecycle test event. That clears the condition temporarily but does not create a durable health signal.

## Live evidence already measured

A bounded read-only aggregate on 2026-08-07 returned:

- `pair_count=36`
- `truncated=false`
- `trusted_complete=true`
- `continuous_hook_gap=2`
- `retention_decision_required=1`

Thus both configured continuous staff hooks were stale at that time. The current state has three active fingerprints: Vince gap, Ziad gap, and the separate retention decision. The Vince fingerprint was first seen on 2026-07-21 and reminded again on 2026-08-09. The scheduler emits only one selected packet per run, so today naming Vince does not prove Ziad is healthy.

A second bounded read-only aggregate on 2026-08-09 classified event types without reading event bodies:

- Vince: 10 total rows, comprising 8 `test`, 1 `TranscriptSnapshot`, and 1 natural `UserPromptSubmit`; the last natural lifecycle event was 2026-06-02.
- Ziad: 10 total rows, comprising 9 `test` and 1 `TranscriptSnapshot`; no qualifying lifecycle event exists.
- The newest `test` rows for both were 2026-08-06. They prove the ingest endpoint and credentials were exercised centrally, not that Claude Code invoked a staff-machine hook.
- The watchdog already canonicalizes `claude_code` and `claude-code` into the same pair, and the live aggregate returned one canonical `claude-code` pair per employee. Surface spelling is not the cause of the current alert.

## Deployment evidence

- The repo records successful historical test ingests for both Vince and Ziad.
- A Vince setup package was delivered in June 2026.
- No reviewed evidence in the current source set proves that Vince's hook remains installed and fires on his current machine.
- The current Vince and Ziad packages are static hook scripts plus Claude settings snippets, not centrally observable installers with an independent machine heartbeat.
- The event hook fails open on network/config errors, so Claude Code can keep working while telemetry silently stops.

## Decision constraints

1. Do not silence a real broken-hook condition by deleting staff from policy without replacement evidence.
2. Do not call ordinary staff inactivity a broken hook unless there is an independent hook/runtime health signal.
3. Do not emit synthetic `SessionStart` or other user-activity events from a timer; synthetic health proof must have its own explicit event type or channel.
4. Preserve aggregate-only read paths, fail-open developer behavior, no secret/PII/PHI output, no raw event-body exposure, one bounded daily query, deduplication, reminder continuity, recovery notices, and three-line cron output.
5. The source checkout is dirty. Do not reset, stage, commit, or alter unrelated paths.
6. No external sends, remote installs, database writes, cron force-runs, secrets, MCP calls, or staff-machine claims are authorized in the review phase.

## User goal

Find the real cause, choose the smallest durable fix, implement it through Ringer, and prove the repair without fabricating a lifecycle event or hiding an unresolved staff-machine installation gap.
