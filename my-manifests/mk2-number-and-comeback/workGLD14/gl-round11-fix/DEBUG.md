# Goal-loop round 11

## Measured no-edge evidence

On live v106, `3pm works for me` was sent before any opening had been offered. At `n_goal_response`, the raw envelope showed an empty extraction and an untouched `BlandStatusCode`; no edge fired. The node then either asked for a day or fabricated 2024 dates. This isolates a semantic-router abstention on an agreement-phrased clock-only preference when no standing offer exists.

## Strictly label-scoped changes

Only these three `n_goal_response` edge labels changed; each generated edge description mirrors its label:

- `n_goal_search`: `says any day, weekday, date, week, weekend, or time preference - including Saturday, this weekend, next week, or a month and day - or asks for the first available, soonest, earliest, or whenever opening - or asks for a different day than offered - or gives only a time preference when no date has been offered yet - including agreement-phrased times like 3pm works for me when no opening has been offered yet`
- `n_goal_search_offered_time`: `after an opening has been offered, gives only a time preference on the already offered date, excluding late, latest, last appointment, or end of day`
- `n_goal_search_offered_latest`: `after an opening has been offered, wants late, latest, last appointment, or end of day on the offered date`

Assertion 11 requires the none-search label to contain `works for me` and both offered-date labels to begin with `after an opening has been offered, `. Assertions 1 through 10 remain active.

## Defects and evidence

The proof-ladder classifier isolated three real defects in `CLASSIFICATION.md` under `# Real defects`:

1. **High, mixed intent:** with offers standing, one message selected an opening and requested a different day. v105 silently searched the new day instead of asking which instruction controlled. This is consent-sensitive because either silent interpretation can choose the wrong booking path.
2. **Medium, out of hours:** a 3am request received unrelated daytime offers without acknowledging that no opening existed at the requested hour.
3. **Medium, day-less clock:** a clock-only request such as 3pm dead-ended by asking for a day instead of searching the gateway's standing today-through-plus-13-day window.

## Changes

- Added `n_mixed_intent`, derived from stored production-v96 `n_which_intent`. It retains v96's one direct clarification and user-wait `Default` behavior, with only the node identity/name and as-built extractor ownership adapted. The response routes mixed intent to it; its answer routes to either branch gate, `n_goal_search`, decline, or the existing 72-hour timeout. There is no second clarification. Its five extractors are byte-identical to `frozen-extractors.json` so a new preference can flow directly to the search webhook.
- Added `out_of_hours` from `$.result.out_of_hours` and `requested_clock` from `$.result.requested_clock` to all five availability webhooks, building against lane 41's gateway contract. `n_goal_response` now states honestly that no opening exists at `{{requested_clock}}`, offers only the nearest real slot variables verbatim, and asks for another day or time. It never presents the out-of-hours clock as available.
- Extended only the none-search edge label with `or gives only a time preference when no date has been offered yet`. The offered-date time edge remains unchanged.
- Added assertion 10 for the mixed-intent node/wiring/extractors, both gateway response mappings, the out-of-hours prompt branch and budget, and the pre-offer time-only label. Assertions 1 through 9 remain active.
- Preserved round 9's intentional `n_goal_response` prompt compression: the production-derived 5,617-character prompt remains compressed to 3,600 characters after adding the round-10 out-of-hours branch. The compressed prompt still retains the exact opening and offer templates, one-clarify-then-search behavior, and the bans on promises/waiting copy and invented or non-slot clock times. No other node prompt was compressed.
- Preserved the five availability bodies, branch confirmations, gate labels, and all unrelated round 6-9 nodes and edges. `frozen-extractors.json` remains byte-identical to round 9.

## Regeneration

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
```

The build deterministically rewrites the draft, all fixtures, and `frozen-extractors.json` from the local source snapshots.
