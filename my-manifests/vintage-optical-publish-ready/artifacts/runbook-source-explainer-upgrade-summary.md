# Fix Summary

## Summary

One operating file changed: `RUNBOOK_COMPETITIVE_ANALYSIS.md`. It now defines the executable public-data collection, fallback, null handling, catchment, supply census, VDU, scoring, number-explainer, QA, release, and Ringer-lane contract. No scoring formula or external-action authority changed. `fix-summary.md` is the required local handoff artifact.

## Files Changed

- `RUNBOOK_COMPETITIVE_ANALYSIS.md`: Replaced the generic 65-line list with the loopable 423-line GROW runbook.
- `fix-summary.md`: Added this required verification summary.

## Verification

Command:

```text
python3 /home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_competitive_runbook_upgrade.py --path RUNBOOK_COMPETITIVE_ANALYSIS.md
```

Real validator output:

```text
PASS: competitive-analysis runbook defines the required source ladder, fallbacks, completeness rules, mandatory number explainer, checked Ringer lanes, and human Project Room gate
```

`git diff --check -- RUNBOOK_COMPETITIVE_ANALYSIS.md` also returned no errors.

## Assumptions

- This change defines the operating contract only. It does not run a practice analysis or collect external evidence.
- Tool availability and paid-source access vary by engagement, so the runbook requires preflight, named fallbacks, frozen gap receipts, and nulls when evidence remains unavailable.
- The change remains uncommitted.
