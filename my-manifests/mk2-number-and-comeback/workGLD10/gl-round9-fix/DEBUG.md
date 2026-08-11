# Goal-loop round 9

## Scope

Round 9 fixes two defects measured on the live v104 Mott pathway while preserving the round-8 topology, edge labels, non-response prompts, gateway contract, and booking behavior.

## Measured defects

1. Extraction used keyword matching instead of sentence comprehension. The live patient message `I'm leaving town today and won't be back for 2 weeks about then?` caused `today`, from the unavailable clause, to be extracted and same-day slots to be offered. The correction `No I said two weeks` worked because the live gateway already parses relative offsets correctly.
2. The response loop was slower than production: v96 measured about 4.5 seconds between messages, while goal-loop v103/v104 measured about 7.6 to 8.3 seconds, approximately 8 seconds. `n_goal_response` combined a 5,617-character prompt, nine outbound edges, and six extractors.

## Changes

- Extended only the `preference_from` and `preference_to` descriptions with a whole-sentence availability rule. Leaving, being away or out of town, being unavailable, and not returning until a period now direct extraction to the patient's return or availability, never the date they said they cannot attend. The canonical leaving-town example is pinned in both descriptions.
- Applied the identical five-extractor set to `n_goal_response`, `n_date_conflict`, `n_date_conflict_retry`, `n_gate_1`, and `n_gate_2`. `user_verbatim`, `day_part`, and `time_after` remain byte-identical to v96. The portable pin is `frozen-extractors.json`.
- Compressed only the `n_goal_response` prompt from 5,617 to 3,477 characters. It retains the literal offer template, exact opening, one-clarify-then-search branches, and explicit bans on promises/waiting copy, invented clock times, and clock times outside offer-step slot variables. No edge label or other node prompt changed.
- Added validator assertion 9 for the shared extractor pin, availability semantics, and the 3,600-character prompt ceiling. Assertions 1 through 8 remain active.

## Regeneration

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
```

The build deterministically rewrites the draft, all fixtures, and `frozen-extractors.json` from the local source snapshots.
