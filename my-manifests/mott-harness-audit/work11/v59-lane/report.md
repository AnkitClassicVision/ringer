# v59 And Verification Stack

## Summary

- v59 encodes a vague week as `next week` through `friday next week`, preserving all other v58 extraction behavior.
- Both structural gates ban the former `monday next week` vague-week start, and the redproof battery now catches nine mutations.
- The harness has an explicit fail-closed diagnostic mode and refuses default certification while TEMPORAL-CONTRACT rev 3 section 4 remains release-blocking.

## Changes

| File | Ruling item | Change |
|---|---|---|
| `build_v59.py` | Q1 | Changed only vague-week extraction guidance and the generated filename. |
| `v59_graph.json` | Q1 | Generated candidate with extraction-description-only deltas from v58. |
| `scenarios.py` | Q1 | Updated only the vague-week scenario pair; retained its date assertion and 30 cases. |
| `check_candidate_gate.py` | Q1/Q4 | Requires qualifier preservation and the approved pair; rejects the inverted-range mapping. |
| `check_v58_builder.py` | Q1 | Enforces the approved pair and bans the old vague-week start while retaining scope and safety checks. |
| `redproof_run.py` | Q4 | Added an attributable ninth mutation restoring the banned Monday mapping. |
| `pathway_harness.py` | Q2/Q3 | Added `--diagnostic`, nonzero diagnostic exits, prominent labeling, and the section 4 certification refusal with `--acknowledge-blocked`. |
| `report.md` | Output contract | Records the amendments and executed local evidence. |

## Gate Sensitivity

The updated candidate gate still fails `source/v56_graph.json`. I ran:

`python3 check_candidate_gate.py --graph source/v56_graph.json --scenarios scenarios.py`

It exited 1 and reported all four missing offer-to-`n_which_intent` edges plus the missing outside-hours route. The v59 candidate passed. A temporary graph restoring the banned `monday next week` vague-week mapping failed both structural gates, and `redproof_run.py` printed `mutations_caught=9`.

## Assumptions

- TEMPORAL-CONTRACT rev 3 section 4 remains release-blocking until an external gateway fix is independently verified.
- `--acknowledge-blocked` is a deliberate human override to run the unchanged certification suite after that fix; it does not itself prove the fix.
- No API, gateway, SMS, appointment write, certification artifact, mint, commit, or external action was performed.
