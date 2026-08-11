# Evidence packet: slot pagination offers wrong times and denies later availability

Synthetic test patient; no PHI. All data measured 2026-08-03 ~18:52-19:10 UTC.

## The incident (live SMS conversation, pathway v90)

Patient asked "Friday afternoon" → agent offered **12:30 pm or 12:45 pm**.
Patient asked "Any later time?" → agent replied **"That is the latest the office has that day.
Would you like to look at a different day?"**

Ground truth at that moment: Friday 08/07 had ~28 open slots running to **05:15 pm**. Times from
12:45 through 5:15 existed and were never offered. Immediately after that reply, the
conversation variables held `slot_1_start = 02:30 pm`, `slot_2_start = 02:45 pm`,
`slot_count = 28` — the system had loaded later times and then denied they existed.

## Mechanism, fully established from the pathway JSON

The availability gateway endpoint accepts `from`, `to`, `after`, `before`, `time_pref`
parameters. The pathway's four slot-offer webhook nodes ALL send
`"after":"none","before":"none","time_pref":"none"` — the full day, unfiltered — and fake
their semantics with hardcoded response indices:

| Node | Purpose per its name | Slot indices used | Actual meaning |
|---|---|---|---|
| n_search | first offer for the request | slots[0]/[1] | first two of the whole day |
| n_page_2 | "Afternoon openings" | slots[8]/[9] | whatever is 9th/10th that day |
| n_page_near | "Closest openings to a late request" | slots[8]/[9] | same as n_page_2 |
| n_page_3 | "Late openings" | slots[16]/[17] | whatever is 17th/18th that day |

With 28 open slots, [16]/[17] = 02:30/02:45 pm — mid-afternoon, not late. The real latest
([26]/[27]) is structurally unreachable. Index meanings drift as bookings consume slots:
ground truth re-measured ~20 min later showed 26 slots with [16] = 03:00 pm.

The "Friday afternoon" offer of 12:30/12:45 was index luck: `day_part=afternoon` was extracted
by the conversation but never sent to the gateway (`time_pref:"none"`), and [8]/[9] of a
28-slot day happened to be 12:30/12:45.

Compounding it, n_offer_3's prompt HARD-CODES the false claim: "These are as late as this day
goes. If they want something later, say plainly that this is the latest the office has that
day and offer to look at another day." The model obeyed its prompt. The prompt's premise
(indices 16/17 are the latest) is false by construction. The same prompt opens with "you never
invent either" — the invention is baked into the node design, not the model's behavior.

Also observed: on entry to n_offer_3 after "Any later time?", the model skipped its mandated
offer template ("I have {{slot_1_start}} or {{slot_2_start}}…") and jumped straight to the
this-is-the-latest clause, so 02:30/02:45 were never even shown.

## Constraints

- The gateway ALREADY supports `after` and `time_pref` filters (catalog: availability ops).
- Pathway edits are minted as new UNATTACHED versions and flipped in the dashboard; the
  reconcile/booking write path (n_verify_*, n_book_*, n_reconcile_*) was just proven live and
  must not be perturbed.
- Bland responsePathways route on string comparisons of extracted variables; extraction
  JSONPaths are per-node config. Comparison literals are strings.
- Date/timing extraction prompt changes have their own mandatory template (house rule) —
  extraction is NOT implicated here; extraction produced the right day and day_part.
- The house design rule says only verified data may be claimed; "never invent" is the spine.

## Question for the panel

Design the minimal, safe fix set for: (1) semantic pagination — "afternoon"/"late"/"closest"
must mean what they say regardless of array shifts; (2) never denying availability that
exists; (3) preserving the just-proven booking path untouched. Rank fixes by risk, name what
each could break, define executed checks that would prove each fix, and name the residual
risks. Consider explicitly: passing `time_pref`/`after` through to the gateway vs computing
indices; making time_pref/day_part flow from extraction into the webhook bodies; whether
n_offer_3's "this is the latest" claim should exist at all and what evidence would justify it
(e.g. a gateway response field, count comparison); and the retest scenarios needed for the
v62 harness suite so this class of defect is caught before any future flip.

## ADDENDUM — root cause found: v87 forked from a stale base (measured)

Bland version archaeology: v78 through v86 (live until this morning) ALL carry
`callID` in the availability bodies (which engages the gateway's raw-text LLM authority:
the gateway fetches the conversation and interprets the patient's actual words;
`ECP_LLM_INTENT=authoritative` is STILL enabled server-side), plus `after: {{time_after}}`
semantic filtering, and page nodes take `slots[0]` of a FILTERED query. v87 (minted Jul 31
during the closing-number/deferral work) has callID gone, after/time_pref "none", hardcoded
indices, and ALSO dropped nodes n_date_conflict and n_help present in v86. Zero
`date_source=` log lines on the gateway tonight confirms the raw-text authority is never
engaged by v87+. Conclusion: the v62 build regenerated the graph from a pre-v78 base and
silently erased roughly a week of proven fixes; v88/v90 inherited that.

## The actual decision for the panel

Two merge directions to produce v91:
(A) BACKWARD-PORT: keep v90 as base; copy the four availability nodes' full data + n_date_conflict
+ n_help + their edges + whatever extraction feeds {{time_after}} from v86 into v90.
Unknown risk: we may not know everything else v87 lost.
(B) REBASE: take v86 as base (the proven-good graph) and RE-APPLY the three deliberate,
fully-specified deltas on top: the v62 spec changes (212 number, e_defer, n_appt_check gate,
adjacency — all in SPEC-v62.md), the reconcile branch (SPEC-v88.md, validator exists), and the
new greeting (exact text known). Everything re-applied is written down; nothing unknown is lost.
Pick a direction, design the exact change set, the validators, and the harness scenarios
(including 'friday afternoon' -> 'any later time?' must surface genuinely later slots and never
deny existing availability), and name residual risks. The booking/reconcile path was proven live
today and must end up in v91 intact either way.
