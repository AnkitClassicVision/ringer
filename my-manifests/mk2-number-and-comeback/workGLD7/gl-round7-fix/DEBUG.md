# Goal-loop round 7

## Scope

Round 7 repairs two platform defects measured against the minted round-6 v102 pathway. It preserves the round-6 direct user-wait-to-webhook topology and the existing booking, gate, decline, timeout, retry, response-data, retry, and skip behavior.

## Measured defects

1. The only scheduling edge from `n_goal_response` was labelled `wants a different day or time`. An opening reply such as `thursday please` matched no edge. The live runtime remained parked on the user-wait node, extraction variables stayed empty, and `BlandStatusCode` remained 200. The node then used its offer-shaped prompt without fresh slots and fabricated dates. A control message that literally matched the label, `can we do a different day please`, did run extraction and fire the webhook. This isolated the fault to the narrow edge label rather than the extraction/webhook pipeline.

2. The round-6 availability request invented `anchor`, `time_from`, and `time_to` body keys. The gateway returned HTTP 400 with `unknown field anchor for /availability`. The offline gateway reproduction showed that the stored production v96 ten-field body returns HTTP 200 and 24 real slots with `time_pref` set to `none`; the same contract with `time_pref` set to `latest` returns real late-day slots. Round-6 extractors also emitted the literal sentinel `retain`, and one probe fabricated `preference_from=monday` from a message containing no day.

## Changes

- Replaced the single search behavior with three availability webhook nodes selected by semantic edges:
  - `n_goal_search`: `time_pref` is the literal `none`.
  - `n_goal_search_latest`: `time_pref` is the literal `latest`.
  - `n_goal_search_anchor`: `time_pref` is the literal `anchor={{goal_anchor}}`.
- Each availability body is restricted to the v96 gateway contract: `store`, `from`, `to`, `after`, `before`, `time_pref`, `slot_minutes`, `callID`, `user_text`, and `user_verbatim`. There are no `anchor`, `time_from`, or `time_to` keys.
- Broadened the `n_goal_response` none-search edge to recognize opening day, weekday, date, week, weekend, and time-preference statements, plus first/soonest/earliest/whenever and different-day requests. Separate edges route late-day intent to the latest search and specific-clock proximity intent to the anchor search.
- Replaced extractor definitions on all five user-wait feeders with the frozen five-element v96 `n_ask` extractor set. `n_goal_response` alone adds `goal_anchor`, which extracts only a specifically named target clock time and otherwise leaves the value empty. No extractor contains `retain`; no `goal_relation`, `time_from`, or `time_to` extractor exists.
- Added validator assertion 7 for the strict body contract, literal time preferences, sentinel exclusion, three-way semantic routing, and frozen production extractor equality.

## Regeneration

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
```

`build_goalloop.py --fixtures` deterministically rewrites the draft, all mutation fixtures, and `fixture-v96-n-ask-extractors.json`.
