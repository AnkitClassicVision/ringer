# Candidate Gate

## Summary

- Replaces global prompt greps with topology, route-order, prompt-consistency, and declared-delta checks.
- The red proof applies eight isolated mutations and requires every one to fail its relevant checker.
- These are structural gates. A pass never substitutes for the live behavioral suite.

## Invariants Enforced

| # | Structural invariant | Reviewer requirement |
|---:|---|---|
| 1 | Every offer reaches `n_which_intent`; clarification exits only through gates, negotiation, decline, or timeout | R1.4 / requirement 1 |
| 2 | Offers and clarification cannot enter booking directly; each book node has only its verify node inbound | R1.4 / requirement 2 |
| 3 | `day_part == outside` precedes slot offers and reaches a non-booking dead end | R1.4 / requirement 3 |
| 4 | Temporal extractors preserve `tuesday next week` and map vague weeks from `monday next week`; stripping language is forbidden | R1.4 / requirement 4 |
| 5 | `n_confirm` has the booking-claim monopoly; `e_booked` cannot repeat it | R1.4 / requirement 5 |
| 6 | Every offer prompt exposes exactly `slot_1_start` and `slot_2_start` | R1.4 / requirement 6 |
| 7 | Suppression exits are webhook-only, honor the endpoint/body/retry contract, make no persistence claim, and isolate undeclared nodes | R1.4 / requirement 7 |
| 8 | Optional scenario inventory contains at least 30 cases, no retired fields, and only recorded assertion keys | R1.4 / requirement 8 |

## Mutations Proven Caught

| Mutation | Checker |
|---|---|
| Remove offer-to-clarification edge | Candidate |
| Rewire clarification directly to `n_book_1` | Candidate |
| Delete outside-hours route | Candidate |
| Move outside-hours route after offer routes | Candidate |
| Reinsert `must become tuesday` stripping instruction | Candidate |
| Add booking claim to `e_booked` | Candidate |
| Add `slot_3_start` to an offer | Candidate |
| Add direct edge bypassing suppression webhook | Suppression |

## What This Still Cannot Prove

The gates cannot prove model routing behavior, date resolution by the gateway, webhook persistence, actual appointment writes, or patient-visible wording across live turns. Those require the exact minted artifact, the live 30-scenario suite, resolver evidence, and suppression integration evidence.

## Assumptions

`source/v57_graph.json` is a stale pre-correction fixture: it contains the forbidden ``tues nxt wk` must become tuesday` instruction, lacks both explicit qualified-week canon examples, and lets `n_miss_time` return to `n_search`. `redproof_run.py` applies those reviewer-mandated temporal corrections in memory before establishing its clean candidate. The on-disk candidate checker correctly rejects the stale source. The optional scenario parser accepts JSON or a Python literal list and treats the embedded retired-field and assertion-key sets as the recorded manifest.
