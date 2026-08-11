# Contrarian review: v94 “latest time” quick fixes

## Recommendation

Do not ship any of the four choices as stated. Before opening, use the smallest reversible containment: keep the existing patient-visible progress sentence, add a narrowly scoped offer-node route for explicit late/latest/end-of-day intent into the existing late-search path, and prove it with a live or platform-equivalent replay that produces a final offer or explicit failure response. Do not add a new gateway latest-first mode today. If that replay cannot be completed before opening, leave the graph unchanged and have the owner accept the known patient-abandonment risk rather than deploy an unproved prompt-wide edit.

Confidence: 0.88. The graph and two live traces strongly establish the route/failure sequence. Bland's behavior on an empty generation is not established by the supplied evidence, so stripping output remains an untested platform-contract risk.

## The incident is not just a missing edge

The latest live trace ends on `n_miss_unread`, but it also records `POST /availability -> 409` immediately after the patient's question. Therefore the turn did reach an availability webhook. A direct `n_offer -> n_search` edge is not required for that to happen: the graph's broad offer edge, “wants a different day or time,” targets `n_negotiate`, whose only successful exit is “preference collected” to `n_search`. The observed filler, webhook, 409, and miss node fit that two-hop route.

The graph contains no edge or node identifier literally named `D5`. If “D5 catch-all” refers to the broad `n_offer -> n_negotiate` label, it already claims any “different day or time.” It competes with the more specific `n_offer -> n_page_2` label “wants later in the day.” “What's the last time of the day…” matches both semantically. Adding “last/latest/end of day” to another edge without establishing edge priority makes the overlap worse, not deterministic.

The likely failure boundary is after routing: the gateway saw the current turn, returned `raw_resolve from=None`, retained pathway fallback dates, and returned 409. The prior trace did the same (`raw_resolve=None`, fallback, 409), after which the recovery prompt emitted two different behaviors: “Let me check that for you” plus an office referral in one run, versus the canonical filler and silence in the other. This disproves a simple claim that the edge never searched.

## Attack on (a): strip the filler from about 20 prompts

This is a blast-radius edit to all 20 prompt nodes containing the shared sentence, not a targeted repair. The sentence is overloaded: it is both a safety fallback when no fresh schedule result exists and patient-visible progress copy while an automatic search is underway.

Nodes that explicitly depend on emitting progress before an automatic webhook are:

- `n_negotiate` (`userWait=false`) -> `n_search`: its prompt collects/interprets the preference and the graph immediately calls availability.
- `n_recheck` (`userWait=false`) -> `n_search`: its entire job is to tell the patient a selected slot was lost and that it is looking again.
- `n_offer` -> `n_page_2` and `n_offer_2` -> `n_page_3`: their prompts expressly require saying that the assistant will look before taking the later-in-day webhook path.

The same sentence is also a safety response in patient-wait nodes when a nudge arrives without fresh slot variables. Removing only the literal sentence leaves the surrounding command “say [removed text] and run the schedule search” incoherent. Removing the whole rule weakens the prohibition on repeating stale slot times. In either case, it does not fix the 409 or ensure the webhook result renders.

The supplied artifacts do not establish whether Bland permits an empty generated message, suppresses it cleanly, retries, stalls the node, or refuses the transition. Therefore a non-empty generation requirement is unknown, not safe to assume away. A 20-node removal before a one-node empty-output canary risks silent turns across intake, recovery, offers, gates, confirmation, help, office, and FAQ paths.

## Attack on (b): add last/latest/end-of-day edges

The offer graph already has overlapping intent claims:

- `n_offer -> n_page_2`: “wants later in the day.”
- `n_offer -> n_negotiate`: “wants a different day or time.”
- `n_offer -> n_which_intent`: selects a slot and asks for a different day/time.
- At `n_offer_2`, “wants later still in the day” competes with a narrower catch-all that only says “wants a different day.”
- At `n_offer_3` and `n_offer_near`, there is no same-day-later path; “different day” is the only negotiation exit.

Adding keyword-like labels does not prove precedence, exclusivity, or typo/paraphrase coverage. It may divert “What is your last appointment?” (office-hours/availability question), “I came last time at 4” (history), “not the latest one” (rejection), or “latest next Friday” (date plus time-band) into the wrong band. It also leaves `n_miss_unread` unable to recover from “Hello?” because its only productive edge requires a newly named day/date/week/weekend.

Most importantly, edge repair alone still feeds a gateway that has no explicit “latest slot” contract. The current `day_part=late` interpretation means a band, not “return the chronologically last available slot.” A route can become more reliable while the answer remains semantically wrong.

## Attack on (c): add gateway latest-first now

“Latest” is underspecified. It can mean latest on the already selected date, latest across a date range, latest acceptable before closing, or simply later than the two shown. Reversing result order or selecting the final result risks changing ordinary earliest-offer behavior at all four duplicated availability call sites (`n_search`, `n_page_2`, `n_page_3`, `n_page_near`). It may also interact incorrectly with near/relaxed results, alternate-office fallback, two-slot padding, and the graph's assumption that slot 1 and slot 2 are presented in offer order.

The gateway currently normalizes an availability list and pads it to two entries because Bland retains stale mapped variables when JSON paths are absent. A rushed latest-first mode must preserve real `count`, clear both mapped slots, maintain doctor/store provenance, and return an explicit route/result contract. Otherwise it can resurrect stale slots or invert which slot a patient selects. This is a new behavior, not a quick parser fix, and needs fixtures plus a Mott-only canary.

## Attack on (d): do nothing today

Doing nothing knowingly leaves a conversion-breaking promise-and-ghost path after real offers. Common patient wording that can hit it includes:

- “What's the latest you have?” / “latest appointment?”
- “What is the last appointment of the day?” / “last time I can come in?”
- “Anything later?” / “Do you have something later in the day?”
- “How late are you open?” / “What's the latest time before you close?”
- “End of day?” / “near closing?” / “after work?” / “as late as possible?”
- Typos and speech-to-text variants such as “last time a lot of the day” and “last time … I cna come in,” both already observed.

The direct cost is abandonment after the system has shown viable openings, duplicate nudges, office-call deflection, and loss of trust because the assistant explicitly promises to check. The trace shows a nudge (“Hello?”) repeats the promise rather than recovering, so the failure can persist until the 72-hour timeout.

## Nondeterminism and the class size

`n_miss_unread` contains conflicting behavioral pressures in one prompt: ask for one concrete day, use the global filler when nudged after silence, and after two prior asks stop and refer to the office. The two live outcomes at the same node are consistent with model-dependent interpretation of conversation count and which instruction dominates. They do not prove randomness in the mathematical sense, but they do prove prompt behavior is not stable enough to treat wording edits as deterministic routing fixes. Every prompt-only repair inherits that limitation unless verified across repeated replays and paraphrases.

The closest same-shaped recovery class is seven nodes identified in the structure report: `n_date_conflict`, `n_clarify`, `n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, and `n_miss_time`. Six of those recovery nodes (`n_clarify` plus the five `n_miss_*`) have only three exits: a newly named day/date/week/weekend to search, explicit give-up, or 72-hour timeout. Their prompts ask and wait, but replies that answer the actual question only with a time band, clock constraint, acknowledgement, correction, “same day,” pronoun, or nudge may match no productive exit.

Additional ask-and-wait bottlenecks have the same structural risk with different narrow labels: `n_ask`; the four offer nodes; `n_which_intent`; `n_gate_1`; `n_gate_2`; and `n_faq`/`n_office`. `n_negotiate` and `n_recheck` are a related synchronous stall risk because they must generate patient copy while immediately traversing to a webhook. The class is therefore at least 6 near-identical narrow-exit recovery nodes besides `n_miss_unread`, and broader if all semantic wait gates are counted.

## Proof required before any opening-time change

1. Replay at `n_offer` with at least: latest, last appointment, end of day, anything later, after work, same day latest, latest next Friday, negated latest, historical “last time,” typo, Chinese equivalent, and a subsequent “Hello?”. Record node sequence, webhook status, and final patient-visible message.
2. Prove edge priority when both “later in the day” and “different day or time” match. A label audit alone is not proof.
3. Run a one-node empty-generation canary to determine Bland's contract before removing filler anywhere.
4. For any gateway latest mode, prove latest-on-selected-date semantics, stable two-slot ordering, no stale mapped fields at count 0/1, correct relaxed/near routing, and no behavior change for ordinary searches.
5. Require an owner gate for accepting either known live abandonment or an uncanaried production routing/gateway change before the line opens.

## Evidence boundaries

- `diag-de57-live-test` (10:47 run): latest-time question -> filler; `/availability` returned 409 with `raw_resolve=None`, `date_source=fallback`; node parked at `n_miss_unread`; “Hello?” repeated filler.
- Earlier diagnostic: malformed latest-time paraphrase -> “Let me check” plus office referral; the same gateway signature ended in 409 and `n_miss_unread`.
- v94 graph: 49 nodes, 127 edges; broad and specific offer labels overlap; `n_miss_unread` has only date-like recovery, decline, and timeout exits.
- Structure evaluation: 20 prompts duplicate the filler block; four availability call sites; seven recovery nodes; nine extraction configurations; the recommended redesign is a contracted hybrid funnel rather than another isolated symptom edit.
- Gateway: raw text parsing resolves dates, falls back when none is found, and the availability envelope pads two slots to prevent stale Bland variables. No supplied code establishes a latest-first request contract or Bland's empty-generation behavior.
