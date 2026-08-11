# DIFF-INVENTORY: pathway-v86.json → pathway-v90.json

Method: mechanical JSON diff via `scratch_diff.py` (node/edge set membership, full-field
byte compare) and `scratch_diff2.py` (sentence-level prompt/text diff, extractVars
name-set diff, responseData/responsePathways structural diff), both in this directory.
Classification verified against `SPEC-v62.md` and `SPEC-v88.md`, read in full.

v86: 42 nodes, 114 edges. v90: 46 nodes, 121 edges (net +4 nodes, +7 edges).
28 of the 40 shared node ids have at least one field difference.

## 0. Totals

| Classification | Count |
|---|---|
| DELIBERATE-v62 | 16 |
| DELIBERATE-v88 | 17 |
| DELIBERATE-greeting | 1 |
| **DELIBERATE subtotal** | **34** |
| FIX-LOSS | 113 |
| UNKNOWN | 3 |
| **TOTAL DIFF ROWS** | **150** |

"Rows" = one atomic field/edge/node change each. The FIX-LOSS count is high mostly
because five systemic patterns (brand wording, the ABSOLUTE-RULE paragraph, the
extractVars trim, the webhook-body/hardcoded-index rewrite, and `n_search`-labeled
edge simplification) each repeat across 6-19 nodes. Section 4 groups those so the
signal isn't lost in repetition; every affected node id is still named.

---

## 1. Nodes only in v86 (removed) — 2

| id | type | name | Classification |
|---|---|---|---|
| `n_date_conflict` | Default | Clarify conflicting dates | **FIX-LOSS** |
| `n_help` | Default | HELP response | **FIX-LOSS** |

Neither removal is named in SPEC-v62 or SPEC-v88. `n_date_conflict` is the node that
handled "tomorrow and the 31st might be different days" disambiguation; its loss is
corroborated by three more diffs below (n_ask's CONFLICT RULE text, n_miss_unread's
matching paragraph, and n_search's `date_conflict_detected` route/fields). `n_help`
had no spec-traceable replacement; nothing in v90 handles a HELP keyword.

## 2. Nodes only in v90 (added) — 6

| id | type | name | Classification |
|---|---|---|---|
| `e_defer` | End Call | deferred_after_booking | **DELIBERATE-v62** (design item 3) |
| `n_appt_check` | Webhook | Upcoming appointment check (silent) | **DELIBERATE-v62** (design item 6) |
| `e_book_unknown` | End Call | booking_unverified | **DELIBERATE-v88** (§3) |
| `e_booked_recovered` | End Call | booked_after_reconcile | **DELIBERATE-v88** (§3) |
| `n_reconcile_1` | Webhook | Reconcile write outcome 1 (silent) | **DELIBERATE-v88** (§2) |
| `n_reconcile_2` | Webhook | Reconcile write outcome 2 (silent) | **DELIBERATE-v88** (§2) |

All six match their spec sections field-for-field (name, url, headers/body-copy
instructions, responseData names `recon_ok`/`recon_count`, responsePathway order,
outcome/tag/text on the two End Call nodes). No discrepancies found.

---

## 3. Shared-node field diffs unique to one node (not part of a repeated pattern)

| Node | Field | v86 → v90 | Classification |
|---|---|---|---|
| `e_booking_failed` | text | "I couldn't confirm that booking. Please call MK2 Optical at (212) 219-2219 so they can check it for you." → "I wasn't able to confirm whether that booking went through. The MK2 Optical office will double-check it and reach out to you. If you'd like, you can also call them at (212) 219-2219." | **DELIBERATE-v88** (§4, exact text match) |
| `e_existing` | globalLabel | "already has a different appointment" → "has an appointment made outside this conversation" | **DELIBERATE-v62** (design item 5) |
| `n_ask` | prompt (greeting body) | "This is a great time to update your lenses, explore our newest eyewear collection, and even find a new pair of sunglasses while staying on top of your eye health…" → "Staying on top of your eye health with a comprehensive eye exam is important." (shorter, paragraph spacing tightened) | **DELIBERATE-greeting** |
| `n_ask` | prompt (CONFLICT RULE) | Removed: "CONFLICT RULE: if their answer mentions two different time references… point it out kindly… ask for one specific day or date." | **FIX-LOSS** (tied to `n_date_conflict` removal, item 1) |
| `n_ask` | modelOptions | `{"newTemperature": 0.2}` → `null` | **FIX-LOSS** (unexplained; no spec touches modelOptions) |
| `n_ask` | userWait | absent → `true` | **UNKNOWN** — every other `Default` conversational node already has `userWait: true`; n_ask was the one exception in v86. Looks like incidental normalization, not a functional change either way. |
| `n_confirm` | prompt (TASK/CLOSE) | Old "Great, you're all set for…" + office-number redirect + "AFTER THE CONFIRMATION" paragraph → new exact-copy CLOSE line ("You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"), Chinese fixed close, "take the post-booking deferral path" | **DELIBERATE-v62** (design items 2, 4, 7 — verbatim match) |
| `n_faq` | prompt (insurance-COVERS line) | "vision insurances typically have an allowance with co-pays, and for more information they can call the office at (212) 219-2219" → "vision benefits are usually separate coverage with their own copays, and our staff will be able to help them with this" | **UNKNOWN** — a content rewrite not named in either spec; can't tell if intentional copy edit or drift. |
| `n_faq` | globalLabel | + "This does not apply once a booking is confirmed." | **DELIBERATE-v62** (design item 5) |
| `n_office` | globalLabel | + "This does not apply once a booking is confirmed." | **DELIBERATE-v62** (design item 5) |
| `n_identity` | responsePathways | `count==1` route retargeted `n_ask` → `n_appt_check` | **DELIBERATE-v62** (design item 6) |
| `n_book_1` | responsePathways | `book_success!=true` retargeted `e_booking_failed` → `n_reconcile_1` | **DELIBERATE-v88** (§1) |
| `n_book_2` | responsePathways | `book_success!=true` retargeted `e_booking_failed` → `n_reconcile_2` | **DELIBERATE-v88** (§1) |
| `n_miss_empty` | prompt (ESCALATION) | Removed: "ESCALATION: if you have already told this patient two or more times… call (212) 219-2219 and they will find the best time for you. End the conversation there." | **FIX-LOSS** — no replacement; escalation valve is gone. |
| `n_miss_unread` | prompt (two-date flag) | Removed: "If the patient's last message contained two time references that could be different days… point that out kindly…" | **FIX-LOSS** (tied to `n_date_conflict` removal, item 1) |
| `n_miss_unread` | prompt (ESCALATION) | Removed: "ESCALATION: if you have already asked this patient for a date two or more times… Please call our office at (212) 219-2219…" | **FIX-LOSS** — no replacement. |
| `n_miss_unread` | prompt (replacement text) | Added: "If they have been asking for a week further out than next week, or described it only in relation to a week already discussed, ask for the month and the day." | **UNKNOWN** — new guidance not traceable to either spec; may be an intentional simplification bundled with the escalation removal, can't confirm. |
| `n_search` | responseData | Removed `conflict_option_1` (`$.result.date_conflict[3]`), `conflict_option_2` (`$.result.date_conflict[4]`), `date_conflict_detected` (`$.result.date_conflict[0]`) | **FIX-LOSS** (tied to `n_date_conflict` removal, item 1) |
| `n_search` | responsePathways | Removed route `date_conflict_detected == conflict → n_date_conflict` | **FIX-LOSS** (tied to `n_date_conflict` removal, item 1) |
| `n_confirm→e_booked` (edge) | new edge added | "confirmation delivered" edge added alongside the pre-existing "72-hour silence after booking" edge (multiplicity 1→2) | **DELIBERATE-v62** — not spelled out verbatim in the spec text, but it satisfies gate G4 ("adjacency(n_confirm) ⊆ {e_booked, e_defer}") and is the natural fast-path companion to the e_defer rewire. Flagged as inferred-deliberate, not verbatim-sourced. |

---

## 4. Systemic (repeated) FIX-LOSS patterns

### 4a. Brand wording regression — contradicts SPEC-v62 explicitly

SPEC-v62 "Brand naming — DECIDED by Ankit 2026-07-31" mandates: **"MK2 Optical" in ALL
patient-facing copy… must not introduce a third name variant.** v90 does exactly that:
bare "MK2" (no "Optical") appears as a third variant in patient-facing text and in the
BACKGROUND boilerplate of every prompt node, e.g. "to get them booked for a comprehensive
eye exam at the MK2 **Optical** office" → "…at the MK2 office", and "at MK2 **Optical**.
Reply YES…" → "at MK2. Reply YES…" (English + the parallel Chinese line, which drops
"Optical"/地点 wording to match).

Affected nodes (17): `n_ask`, `n_clarify`, `n_confirm` (background sentence only —
the CLOSE line itself correctly keeps "MK2 Optical", see §3), `n_faq`, `n_gate_1`,
`n_gate_2`, `n_miss_empty`, `n_miss_thin`, `n_miss_time`, `n_miss_unbookable`,
`n_miss_unread`, `n_negotiate`, `n_offer`, `n_offer_2`, `n_offer_3`, `n_offer_near`,
`n_office`, `n_recheck`, `n_which_intent` — **19 nodes**, each counted once below.

**Classification: FIX-LOSS** (directly contradicts a locked SPEC-v62 decision).

### 4b. "ABSOLUTE RULE ON TIMES" paragraph dropped from BACKGROUND

v86's BACKGROUND section on 19 of the 20 prompt-bearing nodes carries: *"ABSOLUTE RULE
ON TIMES: the only dates and times you may ever say are the exact values currently in
the slot variables from a schedule lookup that ran in THIS turn. If the lookup has not
returned in this turn, or the patient is nudging after a silence, never state or
estimate any date or time from memory or from the patient's words; say 'One moment
while I check the schedule for you.' and run the schedule search."* This sentence is
absent from every one of those nodes in v90, with no replacement guardrail. Neither
spec mentions removing it. Same 19-node list as 4a (both changes land in the same
BACKGROUND paragraph of the same nodes).

**Classification: FIX-LOSS.**

### 4c. extractVars trimmed — `user_verbatim` and `time_after` dropped, definitions shortened

Affected nodes and what each lost:

| Node | Lost vars | Definition shape change |
|---|---|---|
| `n_ask` | `user_verbatim`, `time_after` | `preference_from`/`day_part`/`preference_to` collapsed from 6-field bot-instruction format (Role/Default Behavior/Critical Rules/Recognizing Acceptance/Recognizing Rejection/Null Prevention/Output Requirement sections) to a 3-field single-paragraph description |
| `n_clarify` | `user_verbatim` | `preference_from`/`preference_to` collapsed similarly |
| `n_miss_empty` | `user_verbatim`, `time_after` | same collapse |
| `n_miss_thin` | `user_verbatim`, `time_after` | same collapse |
| `n_miss_time` | `user_verbatim`, `time_after` | same collapse |
| `n_miss_unbookable` | `user_verbatim`, `time_after` | same collapse |
| `n_miss_unread` | `user_verbatim`, `time_after` | same collapse |
| `n_negotiate` | `user_verbatim`, `time_after` | same collapse |

The collapsed definitions lose the explicit "Recognizing Acceptance / Recognizing
Rejection" phrase lists and the "Context Awareness" tracking rules — real behavioral
detail, not just formatting. Not named in either spec.

**Classification: FIX-LOSS** (all rows: var removal + definition-shape change, per node).

### 4d. Availability-webhook body/response gutted — most consequential regression

All four availability-search Webhook nodes (`n_search`, `n_page_2`, `n_page_3`,
`n_page_near`) lost, identically:

- `"callID":"{{callID}}"`, `"user_text":"{{lastUserMessage}}"`, and (on the three
  paging nodes) `"user_verbatim":"{{user_verbatim}}"` — dropped from the POST body entirely.
- `"after":"{{time_after}}"` → `"after":"none"` — the earliest-acceptable-clock-time
  filter is no longer sent to the gateway.
- On `n_page_2`/`n_page_3`/`n_page_near` only: `"time_pref":"afternoon"`/`"late"`/`"afternoon"`
  → `"time_pref":"none"` — the afternoon/late band filter is no longer sent either.
- `responseData` slot extraction changed from the filtered array positions
  `$.result.slots[0]`/`[1]` to **hardcoded** `slots[8]`/`[9]` (n_page_2, n_page_near) or
  `slots[16]`/`[17]` (n_page_3) — a guess at where the desired band would land in an
  *unfiltered* slot list, now that the actual filter parameters are gone.
- `slot_1_day_name`/`slot_2_day_name` responseData entries removed on all four nodes;
  the corresponding `{{slot_1_day_name}}`/`{{slot_2_day_name}}` template references
  were also stripped from the `n_offer`/`n_offer_2`/`n_offer_3`/`n_offer_near` prompts
  (patient-facing offers now show only the raw `slot_1_start` value, no day name).
- On `n_page_2`/`n_page_3`: the `time_pref_relaxed != ''  → n_offer_near` responsePathway
  route (graceful "nothing in that exact band, here's the closest" fallback) was deleted
  outright, not retargeted — no replacement path exists.
- `responsePathways` band-empty/found checks changed from `slot_count == 0`/`>= 1` to
  `slot_1_start == ''`/`!= ''` on `n_page_2`, `n_page_3`, `n_page_near` — a direct
  consequence of switching to hardcoded indices (slot_count no longer means what the
  route logic assumes).
- `modelOptions.retryAttempts` dropped `1 → 0` on all four nodes — no webhook retry on
  a transient failure.

None of this is named in SPEC-v62 or SPEC-v88 (SPEC-v88's own invariant says everything
outside its 4 listed changes must be byte-identical to v87). This is the most
functionally severe bundle in the whole diff: real afternoon/late filtering is gone,
replaced by a fixed offset guess into an unfiltered list, with no retry and no
graceful-degradation path.

**Classification: FIX-LOSS** (all rows).

### 4e. Edge-label precision loss on the `→ n_search` re-search routes

Six edges into `n_search` (from `n_ask`, `n_clarify`, `n_miss_empty`, `n_miss_thin`,
`n_miss_time`, `n_miss_unbookable`, `n_miss_unread` — 7 sources, 6 shown as diffs
because `n_ask`'s is diffed separately above) had their natural-language routing label
shortened from an enumerated list ("says any day, weekday, date, week, weekend, or time
preference — including Saturday, this weekend, next week, or a month and day") to a
generic phrase ("says when they want to come in" / "names a specific day"). Since these
labels are the actual classification instruction Bland uses to decide whether to take
the edge, this is a real precision loss in routing behavior, not cosmetic.

**Classification: FIX-LOSS** (7 edges: `n_ask→n_search`, `n_clarify→n_search`,
`n_miss_empty→n_search`, `n_miss_thin→n_search`, `n_miss_time→n_search`,
`n_miss_unbookable→n_search`, `n_miss_unread→n_search`).

---

## 5. Edge diffs, full accounting

### Removed edges (8)

| Edge | Classification |
|---|---|
| `n_book_1 → e_booking_failed` (book_success != true) | DELIBERATE-v88 (retargeted to n_reconcile_1) |
| `n_book_2 → e_booking_failed` (book_success != true) | DELIBERATE-v88 (retargeted to n_reconcile_2) |
| `n_confirm → n_office` (change requested after confirmation) | DELIBERATE-v62 (retargeted to e_defer) |
| `n_identity → n_ask` (count == 1) | DELIBERATE-v62 (retargeted to n_appt_check) |
| `n_date_conflict → n_search` | FIX-LOSS (source node removed) |
| `n_search → n_date_conflict` | FIX-LOSS (target node removed) |
| `n_page_2 → n_offer_near` (time_pref_relaxed != '') | FIX-LOSS (§4d) |
| `n_page_3 → n_offer_near` (time_pref_relaxed != '') | FIX-LOSS (§4d) |

### Added edges (15, incl. the n_confirm→e_booked second edge from §3)

| Edge | Classification |
|---|---|
| `n_appt_check → e_defer` (appt_count >= 1) | DELIBERATE-v62 |
| `n_appt_check → n_ask` (appt_count == 0) | DELIBERATE-v62 |
| `n_appt_check → n_ask` (ok != true) | DELIBERATE-v62 |
| `n_identity → n_appt_check` (count == 1) | DELIBERATE-v62 |
| `n_confirm → e_defer` (change requested after confirmation) | DELIBERATE-v62 |
| `n_confirm → e_defer` (anything else requested after booking) | DELIBERATE-v62 |
| `n_confirm → e_booked` (confirmation delivered) | DELIBERATE-v62 (inferred, see §3) |
| `n_book_1 → n_reconcile_1` | DELIBERATE-v88 |
| `n_book_2 → n_reconcile_2` | DELIBERATE-v88 |
| `n_reconcile_1 → e_book_unknown` (recon_ok != true) | DELIBERATE-v88 |
| `n_reconcile_1 → e_book_unknown` (recon_count == 0) | DELIBERATE-v88 |
| `n_reconcile_1 → e_booked_recovered` (recon_count >= 1) | DELIBERATE-v88 |
| `n_reconcile_2 → e_book_unknown` (recon_ok != true) | DELIBERATE-v88 |
| `n_reconcile_2 → e_book_unknown` (recon_count == 0) | DELIBERATE-v88 |
| `n_reconcile_2 → e_booked_recovered` (recon_count >= 1) | DELIBERATE-v88 |

### Retargeted / relabeled shared edges (7, from §4d's slot_count→slot_1_start change)

`n_page_2→n_miss_thin`, `n_page_2→n_offer_2`, `n_page_3→n_offer_3`,
`n_page_3→n_page_near`, `n_page_near→n_miss_thin`, `n_page_near→n_offer_near` — label
changed `slot_count == 0`/`>= 1` → `slot_1_start == ''`/`!= ''`. **FIX-LOSS** (§4d).

(The 6th `→n_search` label-precision edge, and n_ask's, are covered in §4e.)

---

## 6. Orphaned variables — extracted in v86, referenced in v86 webhook bodies, gone in v90

Verified by script: every var v86 extracts, cross-referenced against v90's extraction
set and against every `{{var}}` template reference in both graphs.

| Variable | v86 extracting nodes | v86 body usage | Status in v90 |
|---|---|---|---|
| `time_after` | `n_ask`, `n_date_conflict`, `n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, `n_miss_time`, `n_negotiate` | `n_search`, `n_page_2`, `n_page_3`, `n_page_near` bodies (`"after":"{{time_after}}"`) | **Not extracted anywhere in v90.** The 4 bodies now hardcode `"after":"none"`. |
| `user_verbatim` | same 8 nodes as above | same 4 bodies (`"user_verbatim":"{{user_verbatim}}"`, `n_search`/`n_page_2`/`n_page_3`/`n_page_near`) | **Not extracted anywhere in v90.** Field dropped from all 4 bodies. |

Two more v86 body fields are system variables, not LLM-extracted, so they don't appear
in the extractVars check but are equally gone from all 4 webhook bodies in v90:
`{{callID}}` (Bland's built-in call id) and `{{lastUserMessage}}` (used as `user_text`).

`day_part` remains extracted in v90 by the same 7 non-conflict nodes (`n_ask`,
`n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, `n_miss_time`,
`n_negotiate`) — this one survived; only `time_after` and `user_verbatim` were lost.

---

## Files

- Method: two ad hoc Python comparator scripts (node/edge set membership + full-field
  byte compare; sentence-level prompt/text diff + extractVars/responseData structural
  diff), run against `pathway-v86.json` and `pathway-v90.json` in this directory, then
  removed after this report was written (scratch tooling, not a deliverable).
- Every number in this report was either read directly off a script's printed diff or,
  where noted (§0 systemic-pattern counts), independently re-derived with a second,
  narrower verification script before being written down.
