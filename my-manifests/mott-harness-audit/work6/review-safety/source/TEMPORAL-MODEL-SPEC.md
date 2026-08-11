# Temporal Negotiation Model

## Summary

- The load-bearing insight: **absolute** temporal intent (a window, a part of day) must live in extracted variables, while **relative** intent (later, earlier, another day) must live in edge choices from the node the patient is standing on — the node is the only memory the platform gives you. The current design does half of this by accident; the model makes it deliberate and symmetric.
- One token per turn is survivable: keep the `{morning, afternoon, late, none}` enum unchanged, move all direction words into edges, and replace silent `monday`/`friday` guessing with an `unclear` sentinel routed to a clarifying question before any search.
- Fixed-offset paging is the right *read* primitive within a single day (the response is time-ordered, the offsets measured stable) and wrong for everything else; everything else is an edge, a clarifying question, or a filed gateway dependency.

## Findings

### Finding: A patient who asked for "late" is silently offered afternoon slots as "Great news"
Evidence: edge `n_page_3` → `n_page_2` labeled "Too thin for late, try the afternoon"; `n_offer_2`'s prompt opens "Great news, I have {{slot_1_start}} or {{slot_2_start}}" and describes the slots only as "in the afternoon".
Impact: a patient who said "after 4" (mapped to `late` per the `day_part` guidance) whose day has fewer than 17 slots is offered a midday time presented as satisfying their request, with no acknowledgment that the late request could not be met. They either book a time they didn't want or lose trust.
Fix: route the `n_page_3` thin-day fallback to a distinct offer node (same webhook remap as `n_page_2`, new prompt) whose script is "I don't have anything that late on that day — the closest I have is X or Y", per the uniform miss rule below.
Priority: P0
Confidence: high

### Finding: "When in doubt, put monday" makes the system search a week the patient never mentioned
Evidence: `n_ask`, `n_reask` and `n_negotiate` `extractVars` for `preference_from`: "This field must NEVER be left blank: when in doubt the answer is monday" (and `friday` for `preference_to`). Brief: "no, the week after that in August — cannot be expressed; now asks for a date" is handled only by offer-node prompts, not at `n_ask`.
Impact: a patient whose first message is "the week after next" or "in about a month" gets next Monday–Friday searched and real times offered as if they matched. The date inside the slot string is the only clue the window is wrong.
Fix: change the extraction fallback from `monday` to the literal `unclear`, and route `preference_from == unclear` (first-position condition before the search fires) to a clarify node that asks for one day in month-and-day form. `unclear` is a sentinel in an already-open-class field, not a second closed-class token, so it does not add to the one-token load.
Priority: P1
Confidence: high

### Finding: No path moves earlier; "anything earlier?" collapses to the start of the day or to a wrong re-search
Evidence: outbound edges of `n_offer_2`/`n_offer_3` climb only ("wants later still in the day"); no offer node has a downward edge; the brief marks "anything earlier?" untested. The only catch-all is the global `n_negotiate`, whose re-extraction of "anything earlier?" yields `day_part = none` and, with no day named, `preference_from = monday`.
Impact: a patient at the afternoon offer asking for something a bit earlier is either shown 8 a.m. slots or, worse, next Monday's slots — both presented as answers to their question.
Fix: add "wants earlier in the day" edges: `n_offer_3` → `n_page_2`, and `n_offer_2` → a new webhook node (call it `page_first`) that re-issues the identical query and remaps offsets 0/1 onto `slot_1_*`/`slot_2_*` (the exact proven pattern of `n_page_2`), targeting `n_offer`. This makes the band ladder bidirectional with zero new platform capabilities.
Priority: P1
Confidence: high

### Finding: The conflict path re-extracts the preference window from the word "YES"
Evidence: `n_verify_1`/`n_verify_2` route `overlap_id != ""` to `n_negotiate`, which carries the full `extractVars` block including the `monday`/`friday` fallbacks; the patient's most recent message on this path is their confirmation ("YES"), which contains no timing.
Impact: a patient confirms Tuesday 2:00, the slot is taken meanwhile, and the system says "Let me check that for you" then searches next Monday–Friday and offers unrelated times with no explanation that Tuesday 2:00 was lost.
Fix: route verify-conflicts to a dedicated silent node with no `extractVars` (preserving the existing window) that chains straight to `n_search`, with the resulting offer framed by the miss rule ("that time was just taken — closest I now have is…").
Priority: P1
Confidence: medium

### Finding: Band offsets are only meaningful for single-day windows; multi-day requests answer about day one
Evidence: `n_page_2` extracts `$.result.slots[8]` and `n_page_3` `slots[16]`; measured, `monday` to `friday` returns 126 time-ordered slots (18–27 per day), so offset 8 and 16 always land inside the window's first day. Brief: "do you have anything later on any other day?" answers about the current day only.
Impact: "next week, late afternoon" quietly means "Monday late afternoon"; a patient asking across days is answered about one day, and cannot discover Thursday's 5:15 exists.
Fix: define this as the model's semantics rather than a bug — a banded query answers about the first day of the window — and make cross-day movement an edge to `n_negotiate` whose extraction guidance explicitly allows re-anchoring the window by weekday word (patient offered Tuesday, wants another day → `preference_from = wednesday`, keep `preference_to`), which is pass-through of accepted forms, not date arithmetic. Exact cross-day time filtering stays a gateway dependency (below).
Priority: P1
Confidence: high

### Finding: What a patient hears on a miss depends on which of six edges dropped them into n_reask
Evidence: `n_reask` is the target of `ok != true` and `slot_count == 0` from `n_search`, `ok != true` and `slot_1_start == ""` from `n_page_2`, `ok != true` from `n_page_3`, and `conflict_reason != ""` from both verify nodes — one script for "we searched and it's empty", "we never searched", "your band is thin", and "that slot was fake", and the prompt forbids stating any of them.
Impact: the patient gets the same vague apology whether their request was impossible to express, out of range, or genuinely unavailable, and cannot tell what to change next.
Fix: split into two new nodes, `miss_empty` (reached only by `slot_count == 0`; may say the searched window had no openings, because that is proven) and `miss_unread` (rejected/unparseable/sentinel; says it couldn't check yet, asks for one day, two accepted-form examples). Thin-band arrivals go to the nearest-band offer variant from the P0 fix instead.
Priority: P1
Confidence: high

### Finding: "Not Friday" is expressible today at the window edge and nobody told the extractor
Evidence: brief lists "not Friday" as cannot be expressed; the gateway accepts `monday` to `thursday` style spans (`monday`→`friday` measured working).
Impact: patients excluding an end-of-window day are re-asked for a date they already gave by exclusion.
Fix: extend the `preference_to` guidance: an excluded day at the edge of the discussed window trims the window (`not Friday` in a next-week context → `to = thursday next week`). Mid-window exclusion stays deliberately unrepresentable (see The Model).
Priority: P2
Confidence: medium

## Clean

- The booking chain is structurally sound: the only inbound edge to `n_book_1`/`n_book_2` is the verify node's `overlap_id == ""` pathway, so the conflict check cannot be skipped; every payload field in `n_book_1` and `n_book_2` interpolates a gateway-extracted variable; only `n_confirm` may claim an appointment exists, and it is reachable only from a 200/201 signer response.
- The two-slot visibility rule is respected everywhere: no offer prompt interpolates more than its own pair, matching the measured 5:15-Friday/11:30-Monday incident.
- `n_search` sends `after`/`before`/`time_pref` as the literal `none` sentinel, so the null-body type error cannot occur on the main path, and its pathway ordering checks `ok` and `slot_count` before band routing.

## Assumptions

- Extraction on a node runs against the patient's most recent message at node entry (basis of the "YES" finding; marked medium).
- The measured band offsets (0 morning, 8 early afternoon, 16 late; ≥18 slots per open weekday) hold while clinic hours are unchanged; a schedule change silently mis-bands and nothing in-graph can detect it.
- `weekday + next week` generalizes across all five weekdays (measured for two); `a week from <weekday>` is used sparingly since only Wednesday was measured.
- The model can reliably emit the `unclear` sentinel; this needs a scripted-run pass before migration step 2 ships, but it changes a fallback value, not the token count.

## The Model

**Representation.** Per patient turn the model produces exactly three fields, two open-class and one closed-class:

- `preference_from`, `preference_to`: one **contiguous day window**, both ends verbatim in the gateway's accepted grammar (weekday, weekday + next week, month-day, explicit date), or the literal `unclear` when the patient's words cannot be honestly rendered in that grammar. Never a guessed default, never model-computed dates.
- `day_part`: exactly one of `morning, afternoon, late, none` — unchanged. "First thing" → morning; "the latest / after 4 / end of day" → late; direction words (later, earlier) are **not** in this enum.

It deliberately cannot hold: disjunction ("Monday or Wednesday"), mid-window exclusion, clock-time precision beyond three bands, cross-visit memory, or more than one window. Each has a defined degradation: disjunction → the covering span; edge exclusion → window trim; mid-window exclusion → the sub-window before the excluded day, the rest reachable by negotiation; clock precision → nearest band, named as nearest; memory → a clarifying question (interim) and a gateway dependency (final); multiple windows → sequential turns. Direction and relativity ride on **which edge the model picks from which node**, never on extraction — that keeps the closed-class load at one token, the ceiling the three documented failures established.

**Resolution rule.** (1) `preference_from == unclear` → clarify node, no query. (2) Otherwise exactly one availability query: `from`/`to` verbatim, `after`/`before`/`time_pref` = `none`, `slot_minutes` 15. "In about a month" is not a span problem — the 14-day cap binds spans, not horizons — so it resolves to a month-and-day question, then `from = to = that date`. (3) A band request reads fixed offsets from that response, re-issued idempotently per band node; a multi-day window plus a band means, by definition, *the first day of the window* — the slot string shows the date, so this is honest. (4) Budget: at most **two** gateway reads per patient turn (search plus one band fallback), then verify + book on acceptance. Three is too many: anything needing more (exhaustive latest-across-a-week, occupied-middle disjunction) gets the best single query, a plain statement of what wasn't covered, and navigation. With no counter, longer unrolled webhook chains are a maintenance and latency trap; the gateway filter defect, not more chaining, is their real fix.

**Navigation.** A bidirectional band ladder over one day: bands 1 (offsets 0/1), 2 (8/9), 3 (16/17), each a silent webhook re-issuing the identical query and remapping its offsets onto `slot_1_*`/`slot_2_*` (the proven `n_page_2` pattern), each with its own offer node. "Later" is an edge up, "earlier" (new) an edge down, "the latest" enters at band 3 and falls to 2 with the miss framing, "the earliest" enters at band 1, "a different day" is an edge to re-anchoring extraction, where the model may shift the window by weekday word relative to the day just offered. Position is the node you are on; no counter needed. **Judgement:** fixed-offset paging is the right primitive for within-day movement under these constraints — the response is time-ordered, the offsets are measured, and node-as-position substitutes for the missing counter — and the wrong primitive for exact time bounds and cross-day time preference, which only the filed `after`/`before`/`time_pref` fix can serve. Keep the ladder as the interim shape; when the gateway fix lands, band webhooks collapse into parameters and the ladder shrinks to one search plus one offer.

**Miss rule (single, everywhere).** Every non-exact outcome message has three parts: name what was checked, only if a search ran; claim emptiness only when routing proves it (`slot_count == 0` proves the window empty; an empty offset proves only that band thin — "nothing that late", never "nothing that day"); and always end with either two bookable times labeled as nearest ("closest I have to after 4 is…") or a request for one day with two accepted-form examples. "Great news" is reserved for exact matches. Partially matched → nearest-band offer node; out of range → month-and-day question; unparseable/`unclear` → the new `miss_unread` node; empty → the new `miss_empty` node. The arrival edge, not the prompt, decides which.

## Node Shape

- **Extractors** (`n_ask`, `n_negotiate`, re-anchor variant): decide the window and the one band token; forbidden from computing dates, defaulting silently, or naming any time.
- **Clarify node** (new, `clarify_day`): decides nothing; asks for one day; forbidden from implying a search happened or any emptiness.
- **`n_search`**: decides routing only — `ok`, then `slot_count == 0`, then band; forbidden from carrying message content.
- **Band webhooks** `page_first` (new, offsets 0/1) / `n_page_2` / `n_page_3`: decide only the offset remap and empty-fallback direction; forbidden from tone — a thin band routes to the *nearest-band offer variant*, never silently to a "Great news" node.
- **Offer nodes** (exact and nearest variants per band): decide accept/1-or-2/navigate-direction via edges; see exactly two slots; forbidden from any other time, from emptiness claims beyond their band, from booking language.
- **Verify-conflict return node** (new, silent, no `extractVars`): preserves the window; forbidden from re-extracting.
- **Gates, verify, book, confirm**: unchanged; only the confirm node may say "booked".

## Migration

Each step ships alone and leaves the system no worse:

1. **P0 fallback labeling**: add the nearest-band offer variant and repoint `n_page_3` → thin-day fallback at it. Pure addition plus one edge retarget.
2. **`unclear` sentinel**: change extraction fallbacks and add the clarify route. Worst case is one extra question where a wrong-week search used to happen.
3. **Miss split**: replace `n_reask` with the new `miss_empty` / `miss_unread` pair and retarget the six inbound edges by class. Message-only.
4. **Earlier edges + `page_first`**: pure addition; nothing existing changes.
5. **Conflict-return node**: retarget two verify edges; removes the "YES"-re-extraction path.
6. **Extraction guidance widening** (edge exclusion trim, weekday re-anchoring): prompt changes to fields whose grammar is already proven; test scripted before live.
7. In parallel, file/escalate gateway dependencies: honor `after`/`before`/`time_pref` (already filed — escalate as the item that retires the ladder); add last-appointment time to the patient-search response; extend `from`/`to` grammar ("week after next", bare month).

## Not Fixed By This

- Exact time bounds ("after 4" precisely) remain three-band approximations until the gateway filter defect is fixed.
- "Same time as last time" remains a clarifying question until history is exposed by the gateway.
- True disjunctions and mid-window exclusions remain degraded, by design.
- "In about a month" still costs the patient one question; the gateway grammar cannot express it.
- Band calibration is unverifiable in-graph: if clinic hours change, the offsets mis-band and only re-measurement catches it.
- The one-closed-class-token ceiling itself: this model works inside it, it does not lift it.
