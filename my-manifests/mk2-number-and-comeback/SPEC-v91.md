# SPEC v91: rebase on v86, re-apply the four written deltas

Base: `pathway-v86.json` in this directory (42 nodes, 114 edges, the graph that ran live
until the morning of 2026-08-03).
Target: `pathway-v91-draft.json`, minted UNATTACHED, flipped manually only after the gates below.
Expected shape: **48 nodes, 125 edges.**

Direction: **(B) REBASE.** v86 is the base; four fully-written deltas go on top.

---

## Revision 3: panel amendments

Three review lanes (`workH/spec-review-{builder,contrarian,verifier}/report.md`) passed the spec with
amendments. Ankit ruled on the catches. This revision applies those rulings. Nothing else moved.

| # | Ruling | Landed in |
|---|---|---|
| 1 | `user_text` and `user_verbatim` stay in all four availability bodies. The P-A deletion branch is removed; the fix-week carrier requirement is not overridable by a probe result. | §1b P-A, §2.5, §4 assertion 10 |
| 2 | `first_available` is explicitly ABSENT from the four bodies, matching v86's proven behaviour, and the validator asserts its absence. | §2.5, §4 assertion 10c |
| 3 | D4's routing instruction now names the exact edge label that exists on `n_offer_3`, so two builders produce identical prompt text and identical routing. | §2.4 |
| 4 | `n_help` gets SPEC-v62 item 5's post-booking exclusion clause, which it never received because it did not exist in v87. Completing v62's intent, not new design. | §2.1, §4 assertion 3 |
| 5 | The incident scenario now asserts relational and inventory evidence, not a fixed clock floor plus the absence of a denial phrase. Requires a small named harness change. | §5 |
| 6 | Reconcile count-attribution, the relaxed-band sentinel, and `n_appt_check` pathway ordering are recorded as residuals rather than redesigned tonight. All three are proven-accepted v86/v88 behaviour. | §7 items 8, 9, 10 |

---

## 1. Why rebase, measured

The ADDENDUM listed the v87 regression as "four availability nodes plus `n_date_conflict` and
`n_help`". A field-level diff of v86 against v90 shows the lost surface is considerably larger.
Every item below is measured from the two JSON exports, not inferred, and corroborated by an
independently produced mechanical inventory, `DIFF-INVENTORY.md`, which scores the same diff as
**113 FIX-LOSS rows against 34 deliberate rows and 3 UNKNOWN** across 150 atomic changes.

| Lost in v87 (still missing in v90) | Scope |
|---|---|
| `callID` / `user_text` / `user_verbatim` in the availability bodies | 4 webhook nodes |
| `after: {{time_after}}` semantic filtering | 4 webhook nodes |
| `time_pref` set to a real band (`afternoon`, `late`) instead of `"none"` | 3 page nodes |
| `slots[0]/[1]` of a filtered query, replaced by hardcoded `slots[8]/[9]`, `slots[16]/[17]` | 3 page nodes |
| `$.result.slots[N].day_name` extraction | 4 webhook nodes |
| `{{slot_1_day_name}}` / `{{slot_2_day_name}}` in patient-facing offer copy | 5 offer nodes |
| `time_pref_relaxed != ""` route to `n_offer_near` | `n_page_2`, `n_page_3` |
| `date_conflict` extraction + `n_date_conflict` node and its 2 edges | 1 node, 2 edges |
| `n_help` (global HELP/INFO handler, carries the office number) | 1 node |
| `user_verbatim` and `time_after` extraction variables | 8 extraction nodes |
| The long-form `preference_from` / `day_part` / `preference_to` extraction prompts, including the whole "Recognizing Rejection", "Recognizing Acceptance" and "Context Awareness" sections and the "never extract a past day" rule | 8 extraction nodes |
| The `extractVars` flag triple `[false, false, true]` on `n_ask`, replaced by `[]` | `n_ask` |
| The `ABSOLUTE RULE ON TIMES` paragraph (never state a time not returned this turn) | **20 nodes**, every prompt-bearing node except `n_date_conflict`; **0 remain in v90** |
| Brand "MK2 Optical" downgraded to "MK2" in BACKGROUND and in patient-facing gate/offer copy | **19 nodes** |
| `n_ask` CONFLICT RULE and "never guess what day of the week a date falls on" | 1 node |
| `n_miss_unread` two-date TASK branch | 1 node |
| ESCALATION clauses ("call (212) 219-2219 and they will find the best time") | `n_miss_empty`, `n_miss_unread` |
| Richer routing edge labels ("says any day, weekday, date, week, weekend, or time preference...") | 7 edges |
| `retryAttempts: 1` on the four availability **reads** | 4 nodes |
| `n_ask.modelOptions = {"newTemperature": 0.2}` | 1 node |

Two of those are not merely regressions, they are violations of decisions already locked:

- SPEC-v62's brand ruling is "**MK2 Optical** in ALL patient-facing copy... must not introduce a
  third name variant". v90 introduces bare "MK2" across 19 nodes. v90 is the non-conforming graph,
  not v86.
- `n_help` is the HELP/INFO handler, added Jul 27 as a compliance response. It has been absent since
  Jul 31, so a patient texting HELP has had no handler for four days.

That first one carries a second lesson, and it is the reason this spec quotes strings rather than
pointing at v90: **v87 applied SPEC-v62 incompletely.** Re-applying the specs means re-applying what
they say, not reproducing v87's rendering of them. Where this spec cites `pathway-v90.json` for exact
text, it does so only for strings that are themselves the spec-mandated copy (the CLOSE line, the
DEFER line, the `n_appt_check` and reconcile node data, the greeting). Every other v90 string is
treated as suspect.

The provenance argument that makes rebase safe: `pathway-v87.json` → `pathway-v88.json` differs only
by the reconcile change set, and `pathway-v88.json` → `pathway-v90.json` differs by **exactly one
node** (`n_ask.prompt`). Therefore every other v86-vs-v90 difference originates at the v87 mint, and
v87's mint intent is written down in SPEC-v62. Anything in that difference set that is not in
SPEC-v62 and is not the greeting is stale-base residue, and v86's value is the newer one.

Backward-porting (direction A) would require enumerating all twenty rows above correctly and
hand-editing extraction prompts into v90, which also drags the date/timing extraction house-rule
template into a same-day repair. Rebase re-applies four things that are each written down in full.
The unknown-unknowns land on the side that keeps them, not the side that drops them.

The ratio decides it on its own. A merge should be based on whichever side carries more of what you
want to keep, and the count is **113 rows to restore against 34 to re-apply**, better than three to
one. Direction A hand-restores 113 things and gets each one wrong at some rate; direction B
hand-applies 34 things that are each specified in writing, and every one of the 113 arrives by doing
nothing. The 113 also includes items nobody had noticed until a machine diffed the files, which is
the definition of the risk direction A carries and direction B does not.

The booking write path makes rebase cheap: `n_book_1`, `n_book_2`, `n_verify_1` and `n_verify_2` are
byte-identical between v86 and v90 apart from the single catch-all destination in each book node. The
SPEC-v88 reconcile branch grafts onto v86 with no adaptation.

---

## 1b. Pre-build gateway probes (hard gate, run BEFORE editing any JSON)

Two research reports in `workG/` disagree on a point this whole rebase depends on, and the
disagreement is cheap to settle. Settle it first. All three probes are read-only `POST /availability`
calls against the live gateway with a synthetic store and date. None of them writes anything.

**P-A: does the deployed gateway accept v86's exact body shape?**
`workG/gateway-contract/report.md` states the request whitelist is `store`, `from`, `to`, `doctor`,
`min_minutes`, `slot_minutes`, `after`, `before`, plus the gateway-consumed control fields
`time_pref`, `first_available`, `callID`, and that "unknown remaining fields fail the request"
(citation: `raise ValueError(f"unknown field {key!r} for {path}")`).
`workG/provenance-fix-week/report.md` states the healthy v65/v86 bodies also carry
`user_text: "{{lastUserMessage}}"` and `user_verbatim: "{{user_verbatim}}"` as "documented
fallback/diagnostic carriers". v86 ran live for a week with both fields present, which suggests the
deployed build consumes them, but that is inference, not measurement.

**Ruling 1 (rev 3) resolves this, and P-A no longer decides it.** `workG/provenance-fix-week/report.md`
lists both fields as required pathway-side carriers for the raw-text authority fix, and the gateway
contract lists `callID` among the fields consumed before whitelist validation. Both fields **stay in
all four bodies**. The earlier version of this spec let a failing P-A authorize deleting them; that
branch is **removed and superseded**. A probe result may not override a written requirement from an
independent source; if the two genuinely conflict, that is an escalation to Ankit, not a builder
decision at 1am.

P-A therefore becomes a confirmation, not a fork. Send v86's `n_search` body verbatim, with a real
`callID` from a harness chat and a real store. Expect HTTP 200 with `result.count` present.
**If it returns an unknown-field error, stop and escalate.** Do not build. That outcome would mean the
deployed gateway is not the build v86 ran against, which changes far more than two body fields, and
the right response is to find out which build is deployed, not to trim the body until the error goes
away.

**P-B: does the deployed tier honour `time_pref: "late"`?**
Per the same contract report, `late` maps to `--after 03:00 pm` in the LLM-intent v2 source, but
raw-text-authority v2 honours only `morning`, `afternoon` and `evening`, so on that tier `late`
silently adds no bound and `n_page_3` would return the whole day again, reproducing the incident with
different mechanics.

Send `{"store": ..., "from": <a day with known afternoon and late openings>, "to": same,
"after": "none", "before": "none", "time_pref": "late", "slot_minutes": "15", "callID": <valid>}`.
Every `result.slots[].start` must be at or after 03:00 PM, and `result.count` must be smaller than
the count returned by the same request with `time_pref: "none"`. If `late` is not honoured, **v91
must not be built as specified**: `n_page_3` needs `after: "03:00 PM"` instead of a band, which is a
different change set, and Ankit decides it.

**P-C (same call, free): confirm the response-envelope facts the routing depends on.** The contract
report states the envelope pads `slots` to at least two objects to clear stale Bland variables, so
`slots[0]` and `slots[1]` exist even when nothing matched. Verify by sending a band that is certainly
empty and checking that `result.count` is `0` while `result.slots` still has two entries. This is
what makes v86's `slot_count == "0"` routing correct and v90's `slot_1_start == ""` routing wrong,
and it is the reason §2 restores the `slot_count` form. In the same response, record the **literal**
value of `time_pref_relaxed`, which §7 item 9 depends on: the routes on `n_page_2` and `n_page_3`
test it against the empty string, so a non-empty sentinel such as `"none"` would preempt the
`slot_count == "0"` route and send padded empty slots to `n_offer_near`.

Record all three results in `v91-gateway-probe.md`. A failed or unrun probe blocks the build.

---

## 2. The four deltas

| id | delta | source of truth |
|---|---|---|
| **D1** | v62 graph delta: `e_defer`, `n_appt_check`, the `n_confirm` rewire, the mandated close, the global-label exclusions | SPEC-v62.md §"Design" 2-5, and `pathway-v90.json` for the exact strings |
| **D2** | SPEC-v88 reconcile branch (reconcile, never lie) | SPEC-v88.md §"Exact changes", and `pathway-v90.json` |
| **D3** | the new five-paragraph `n_ask` greeting | `pathway-v90.json` `n_ask.data.prompt`, TASK block only |
| **D4** | remove `n_offer_3`'s unearned "this is the latest" claim | this spec, §2.4 |

D1 must be applied before D2: `n_reconcile_1` and `n_reconcile_2` copy their `headers`, `body` and
`active` from `n_appt_check`, which D1 creates.

### 2.1 D1: v62 graph delta

**New node `e_defer`**, top level: `type: "End Call"`, `sourcePosition: "bottom"`,
`targetPosition: "top"`, `width: 320`, `height: 115`, `position: {x: 8230, y: 3500}` with `x`/`y`
mirrored at top level. `data`:

- `active`: `false` (the literal value carried by every v86 node)
- `name`: `deferred_after_booking`
- `outcome`: `deferred_after_booking`
- `tag`: `{"color": "#455A64", "name": "outcome:deferred_after_booking"}`
- `text` EXACTLY: `For that you'll have to contact the MK2 Optical office at (212) 219-2219`
- no outgoing edges

**New node `n_appt_check`**, top level: `type: "Webhook"`, `sourcePosition: "bottom"`,
`targetPosition: "top"`, `width: 320`, `height: 115`, `position: {x: 2895, y: 3500}` mirrored.
`data`, copied field-for-field from `pathway-v90.json`:

- `active`: `false`
- `name`: `Upcoming appointment check (silent)`
- `url`: `https://mott-booking-gw.mail.mybcat.com/appt-list`
- `method`: `POST`
- `headers`: `{"Authorization": "{{ SECRET.MottGatewayToken }}", "Content-Type": "application/json"}`
- `body`: `{"patient_id": "{{patient_id}}", "store": "{{store}}"}`
- `text`: `""`
- `modelOptions`: `{"retryAttempts": 0, "skipUserResponse": true}`
- `responseData`: `[{"data": "$.ok", "name": "ok"}, {"data": "$.result.count", "name": "appt_count"}]`
- `responsePathways`, in THIS order:
  1. `["appt_count", ">=", "1", {"id": "e_defer", "name": "Upcoming appointment found"}]`
  2. `["appt_count", "==", "0", {"id": "n_ask", "name": "No upcoming appointment"}]`
  3. `["ok", "!=", "true", {"id": "n_ask", "name": "Appointment check unavailable"}]`

**`n_identity` retarget.** `responsePathways[3]` becomes
`["count", "==", "1", {"id": "n_appt_check", "name": "Identity confirmed"}]`. Every other entry stays
byte-identical to v86. Delete edge `edge-n_identity-n_ask-count-1`; add
`edge-n_identity-n_appt_check-count-1`.

**`n_confirm` rewire.** Delete `edge-n_confirm-n_office-change-requested-after-confirmation`. Keep
`edge-n_confirm-e_booked-72-hour-silence-after-booking` unchanged. Add three edges:
`edge-n_confirm-e_booked-confirmation-delivered`,
`edge-n_confirm-e_defer-change-requested-after-confirmation`,
`edge-n_confirm-e_defer-anything-else-requested-after-booking`.
Result: adjacency(`n_confirm`) = {`e_booked`, `e_defer`}.

**`n_confirm.prompt`.** Replace the TASK paragraph only. The BACKGROUND paragraph keeps v86's text,
including `ABSOLUTE RULE ON TIMES` and "MK2 Optical office". The TASK paragraph becomes EXACTLY:

```
TASK. Confirm the appointment that was booked, in plain language, and name the booked time. For an English-language thread, the confirmation must end exactly with: "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219". This is one SMS bubble and must not contain any earlier duplicate 'all set' wording. For a Chinese-language thread, use this fixed close after naming the booked time: "您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219". If the patient then asks to change, cancel or move it, or asks for anything else, take the post-booking deferral path.
```

**Global labels.** Append ` This does not apply once a booking is confirmed.` to
`n_office.data.globalLabel` and `n_faq.data.globalLabel` (v86 text plus that sentence, one leading
space, nothing else changed). Replace `e_existing.data.globalLabel` with EXACTLY
`The patient has an appointment made outside this conversation they want to cancel or move.`

**`n_help` post-booking exclusion (ruling 4, rev 3).** SPEC-v62 item 5 scoped `n_office` and `n_faq`
out of the post-booking phase so that a patient asking for anything after confirmation lands on
`e_defer` instead of being re-engaged. `n_help` never received that clause, for the mechanical reason
that it did not exist in v87 when v62 was applied. Rebasing brings `n_help` back, and bringing it back
without the clause would reopen the hole v62 closed: a patient texting HELP after confirmation would
hit a global node whose prompt says "The booking conversation should continue after this reply."

Append ` This does not apply once a booking is confirmed.` to `n_help.data.globalLabel`, exactly as
for `n_office` and `n_faq`: v86 text, one leading space, that sentence, nothing else changed.
`n_help.data.prompt` is not touched. This is completing SPEC-v62's own intent on a node that was
absent when it was written, not new design.

**Not carried from v90:** `n_office.prompt`, `n_faq.prompt`, `n_gate_1.prompt`, `n_gate_2.prompt` and
every other prompt keep v86's text. SPEC-v62 changed labels and the confirm TASK, not those bodies.

**New edges from D1** (all `type: "custom"`, `animated: true`, `sourceHandle`/`targetHandle` `null`,
`data.isHighlighted` `false`, `data.description` in the house pattern
`Route from <src> to <dst> when: <label>.`):

| id | source → target | `data.label` |
|---|---|---|
| `edge-n_identity-n_appt_check-count-1` | n_identity → n_appt_check | `count == 1` |
| `edge-n_appt_check-e_defer-appt-count-1` | n_appt_check → e_defer | `appt_count >= 1` |
| `edge-n_appt_check-n_ask-appt-count-0` | n_appt_check → n_ask | `appt_count == 0` |
| `edge-n_appt_check-n_ask-ok-true` | n_appt_check → n_ask | `ok != true` |
| `edge-n_confirm-e_booked-confirmation-delivered` | n_confirm → e_booked | `confirmation delivered` |
| `edge-n_confirm-e_defer-change-requested-after-confirmation` | n_confirm → e_defer | `change requested after confirmation` |
| `edge-n_confirm-e_defer-anything-else-requested-after-booking` | n_confirm → e_defer | `anything else requested after booking` |

Net: +2 nodes, +7 edges, −2 edges (`edge-n_identity-n_ask-count-1`,
`edge-n_confirm-n_office-change-requested-after-confirmation`).

### 2.2 D2: SPEC-v88 reconcile branch

Apply SPEC-v88.md §"Exact changes" verbatim, with these base substitutions:

- The two catch-alls to retarget are v86's `n_book_1.data.responsePathways[2]` and
  `n_book_2.data.responsePathways[2]`, which are identical to v87's. Condition stays
  `["book_success", "!=", "true"]`; destination becomes `n_reconcile_1` / `n_reconcile_2` with
  `name` `Write outcome unknown - reconcile against the EMR`.
- Delete `edge-n_book_1-e_booking_failed-book-success-true` and
  `edge-n_book_2-e_booking_failed-book-success-true`.
- `n_reconcile_1` / `n_reconcile_2` copy `active`, `headers` and `body` from the `n_appt_check` that
  D1 just created, use fresh response names `recon_ok` / `recon_count`, `retryAttempts: 0`,
  `skipUserResponse: true`, and the conservative-first `responsePathways` ordering in SPEC-v88 §2.
- `e_booked_recovered` and `e_book_unknown` exactly as SPEC-v88 §3, including the two verbatim texts.
- `e_booking_failed.data.text` is reworded to the `e_book_unknown` text; every other field of
  `e_booking_failed` keeps v86's value; it ends with zero inbound edges and is kept.

Positions (v86 coordinate space, all in the empty band below y = 3282, mirrored into `x`/`y`):
`n_reconcile_1` (7720, 3500), `n_reconcile_2` (8750, 3500), `e_booked_recovered` (7720, 3720),
`e_book_unknown` (8235, 3720).

The eight new edges are exactly the ids, sources, targets and labels in `check_v88_graph.py`
`NEW_EDGES`. Net: +4 nodes, +8 edges, −2 edges.

`retryAttempts` stays `0` on `n_book_1` and `n_book_2`. No retry of the write, ever, anywhere.
`retryAttempts: 1` is restored only on the four availability **reads** (`n_search`, `n_page_2`,
`n_page_3`, `n_page_near`), which is v86's value and is idempotent.

### 2.3 D3: the new greeting

`n_ask.data.prompt`: the BACKGROUND paragraph, the GOAL line and the NEVER paragraph keep v86's text
verbatim. The TASK block (from `TASK. Send this message with the patient's first name filled in:`
through `...ask again when they would like to come in.`) is replaced byte-for-byte with the
corresponding block from `pathway-v90.json` `n_ask.data.prompt`, which is the five-paragraph greeting
with single blank lines between paragraphs.

`n_ask.data.modelOptions` stays v86's `{"newTemperature": 0.2}`. `n_ask.data` keeps v86's shape on
`userWait`, which is that the key is **absent entirely** (v90 added `userWait: true`; see OPEN-4).
`n_ask` `height` stays 111. `n_ask.data.extractVars` stays v86's five-variable list
(`user_verbatim`, `preference_from`, `day_part`, `time_after`, `preference_to`) with the
`[false, false, true]` flag triple on each.

Known copy inconsistency, deliberately left alone: the Chinese fallback inside the same TASK block
still carries the older long text (lenses, new glasses). The English body no longer does. This is
inherited from v90 as-is. Changing patient-facing Chinese copy is Ankit's call, not this repair's.

### 2.4 D4: `n_offer_3` must stop claiming "this is the latest"

**This delta is required, and it is not in the three named deltas. Here is why.**

The house constraint is that only verified data may be claimed to a patient. Under v86 semantics
`n_page_3` queries `time_pref: "late"` (which the gateway maps to `--after 03:00 pm`, per
`workG/gateway-contract/report.md`), `after: {{time_after}}`, and reads `slots[0]` and `slots[1]`,
which are the **earliest two openings in the late band**, not the latest openings of the day. When
the late band holds more than two slots, `n_offer_3`'s hardcoded claim is false, exactly as it was on
v90. `workG/v86-wiring-map/report.md` reaches the same verdict independently: "'Latest/as late as
this day goes' is not proven: no mapped field says the returned pair are the final slots of the day."

Rebasing fixes the first "any later time?" ask, because the band query genuinely moves the patient
from the afternoon band to the late band. It does not fix a second one, and the claim is stated in
the prompt as fact, so the model says it whether or not it is true.

**Two sentences change, both in `n_offer_3.data.prompt`.**

In TASK, replace:

```
These are as late as this day goes. If they want something later, say plainly that this is the latest the office has that day and offer to look at another day.
```

with EXACTLY:

```
These are the latest openings you have been shown for that day, and you have not been shown everything the day holds. If they ask for something later, do NOT claim this is the latest the office has and do NOT say the day has nothing later, because you have not been told that. Do not name any other time. Say you will look at another day for them, ask which day they would like, and take the path labelled "wants a different day".
```

The phrase "the path labelled 'wants a different day'" names the literal `data.label` of the edge
`n_offer_3 → n_negotiate` as it exists in v86 and in the v91 draft (ruling 3, rev 3). The four other
outgoing edges from `n_offer_3` are labelled "both selects an opening and asks for a different day or
time", "takes only the first opening offered", "takes only the second opening offered", and "declines
this offer", none of which a later-time request should match. Naming the label rather than describing
the intent is what makes two builders produce the same prompt and the same routing; "take the path
for a different day" was ambiguous against the first of those four labels.

In NEVER, replace:

```
Never suggest there is anything later that day than these two.
```

with EXACTLY:

```
Never say or imply that the office has nothing later that day than these two, because you have not been told that.
```

The surrounding NEVER sentence, "NEVER write any appointment time other than the two given to you
above", already carries the anti-invention rule, so removing the false denial does not open a hole.

Nothing else in `n_offer_3` changes: same routing, same edges, same variables, no phone number added,
so the carrier set is unaffected. This is a prompt-only, single-node, zero-routing-risk change that
converts two false statements into honest ones.

What it costs: a patient who asks for something later a third time is offered another day rather than
the genuinely later slot that exists. That is a documented limitation, not a lie. §7 carries the v92
design that removes the limitation.

### 2.5 The availability body field set is frozen (rulings 1 and 2, rev 3)

All four availability nodes send exactly these ten fields, in v86's order, and nothing else:

```json
{
  "store": "{{store}}",
  "from": "{{preference_from}}",
  "to": "{{preference_to}}",
  "after": "{{time_after}}",
  "before": "none",
  "time_pref": "<none | afternoon | late | afternoon>",
  "slot_minutes": "15",
  "callID": "{{callID}}",
  "user_text": "{{lastUserMessage}}",
  "user_verbatim": "{{user_verbatim}}"
}
```

`time_pref` is `none` on `n_search`, `afternoon` on `n_page_2`, `late` on `n_page_3`, `afternoon` on
`n_page_near`. This is v86's exact shape; the rebase inherits it and no delta touches it.

**`first_available` is deliberately absent.** `workG/gateway-contract/report.md` lists it in a
"should contain at least" example body, and the builder lane flagged its absence as a
contract-completeness miss. The ruling is to keep it absent, for three reasons: v86 ran a week
without it, the same report states that an absent `first_available` is treated as false, which is the
value this pathway wants on every one of these four calls, and adding a field to a webhook body on
the night of a regression repair buys nothing and can only break something. The validator asserts
absence, so a future builder who adds it has to change the check deliberately rather than by
accident. If a soonest-available search is ever wanted, it belongs to a separate node and a separate
decision.

`doctor` and `min_minutes` are likewise absent. They are accepted optional inputs, not required
fields, and availability forces the store's configured doctor anyway.

---

## 3. Completeness gate: classify every difference, do not assume this list is complete

A sibling lane may produce a mechanical diff inventory this spec has not seen. This spec does not
depend on it and does not assume its own inventory in §1 is exhaustive. The builder must run the
classification itself and the result is a hard gate:

Enumerate every field-level difference between `pathway-v86.json` and `pathway-v90.json` (all nodes,
all `data` keys, all edges, all top-level keys). Assign each one to exactly one bucket:

1. **D1**: named in SPEC-v62's design list
2. **D2**: named in SPEC-v88's change list
3. **D3**: the `n_ask` TASK block
4. **D4**: the `n_offer_3` claim sentence
5. **layout**: `position` / `x` / `y` / `height` only
6. **stale-base residue**: everything else; v86's value wins by default

`DIFF-INVENTORY.md` is a valid input to this step and its bucketing agrees with §1 and §2 of this
spec on every row checked. It is not a substitute for running the classification: the builder must
produce `v91-classification.json` from the JSON, then reconcile it against the inventory and against
§1, and report any row where the three disagree. Three disagreements are already known and resolved
here:

- `DIFF-INVENTORY.md` §4a heads its brand list "(17)" and then lists 19 node ids. The measured count
  is **19**. Use 19.
- `DIFF-INVENTORY.md` §4b says the `ABSOLUTE RULE ON TIMES` paragraph sits on "19 of the 20
  prompt-bearing nodes". The measured count is **20 of 21** prompt-bearing nodes; the one without it
  is `n_date_conflict`. Use 20.
- `DIFF-INVENTORY.md` §4d says `user_verbatim` was in the body of "the three paging nodes". Measured,
  it is in **all four**, `n_search` included. Use four.

Write the classification to `v91-classification.json` as `{node_or_edge_id: {field: bucket}}`. Any
difference that cannot be placed in buckets 1-5 and that the builder is not confident calling residue
is an **OPEN** item: it blocks the flip until Ankit rules on it. Five are already known. In every
case the default is v86's value, because under a rebase the default is to change nothing:

- **OPEN-1: `n_faq.prompt` insurance sentence.** v86: "vision insurances typically have an allowance
  with co-pays, and for more information they can call the office at (212) 219-2219." v90: "vision
  benefits are usually separate coverage with their own copays, and our staff will be able to help
  them with this." Not in SPEC-v62. Provenance unknown. Default v86 (it keeps the office number in
  the coverage answer). Ankit decides.
- **OPEN-2: `analysis_options` is `null` in both.** SPEC-v62 §3 requires `deferred_after_booking` in
  `analysis_options`; SPEC-v88 explicitly deferred it. v91 keeps `null` and inherits the documented
  conformance gap. Not a flip blocker; do not silently "fix" it here.
- **OPEN-3: `n_miss_unread` added guidance.** v90 adds "If they have been asking for a week further
  out than next week, or described it only in relation to a week already discussed, ask for the month
  and the day." The same rule exists verbatim in v86's four offer prompts, so it is plausibly a
  deliberate carry rather than drift, but it is in neither spec. Default v86 (omit). Low stakes.
- **OPEN-4: `n_ask.userWait`.** Absent in v86, `true` in v90. Every other conversational `Default`
  node in v86 sets it explicitly; `n_ask` is the single exception. Default v86 (omit the key), because
  that is the shape that ran live for a week. The Phase 1 scenario `opening asks, does not offer`
  covers the behaviour either way, so this resolves by measurement rather than argument.
- **OPEN-5: `n_offer_near`'s "you asked for something LATE" framing is wrong on one inbound route.**
  `workG/v86-wiring-map/report.md` establishes that `n_page_2` can reach `n_offer_near` via
  `time_pref_relaxed`, in which case the patient asked for the afternoon, not for something late, and
  the copy "I don't have anything that late that day" misdescribes their request. This is
  **pre-existing in v86 and is not introduced by v91**, so it is not a required delta. Proposed v92
  wording, band-agnostic: "I don't have anything open in that part of the day. The closest I have
  is...". Ankit decides whether to take it now or later.

---

## 4. Mechanical validator: `checks/check_v91_graph.py`

Invocation, both required, exit 0 is the only pass:

```
python3 checks/check_v91_graph.py --base pathway-v86.json --draft pathway-v91-draft.json \
        --v88-ref pathway-v90.json --classification v91-classification.json
```

Every assertion prints why it failed. No assertion may be satisfied by `true`, `exit 0` or an echo.

**Structure**

1. Node count is 48. Edge count is 125.
2. All 42 v86 node ids are present. The only new ids are `e_defer`, `n_appt_check`, `n_reconcile_1`,
   `n_reconcile_2`, `e_booked_recovered`, `e_book_unknown`.
3. `n_date_conflict` and `n_help` exist. `n_help` has `isGlobal: true`,
   `enableGlobalAutoReturn: true`, `userWait: true`, zero edges, and carries `(212) 219-2219`. Its
   `globalLabel` is v86's ("The patient texts HELP, INFO, or a bare request for help or more
   information.") **plus** the post-booking exclusion sentence, and the check asserts all three
   globals (`n_office`, `n_faq`, `n_help`) carry that identical sentence, so a future global added
   without it is caught. `n_date_conflict` carries the full five-variable extraction set and its
   `{{conflict_option_1}}` / `{{conflict_option_2}}` prompt.
4. Every v86 node **not** in {`n_identity`, `n_confirm`, `n_office`, `n_faq`, `e_existing`,
   `n_book_1`, `n_book_2`, `e_booking_failed`, `n_ask`, `n_offer_3`} is byte-identical to v86,
   including `position`, `x`, `y`, `height` and `width`. Mass position drift is the fingerprint of a
   regeneration from a stale base, which is the defect that caused this incident, so positions are
   asserted, not ignored.
5. Every v86 edge except `edge-n_identity-n_ask-count-1`,
   `edge-n_confirm-n_office-change-requested-after-confirmation`,
   `edge-n_book_1-e_booking_failed-book-success-true` and
   `edge-n_book_2-e_booking_failed-book-success-true` is byte-identical to v86.
6. Every edge id is unique across the graph; every edge has `type: "custom"`; every edge's
   `source` and `target` resolve to existing node ids.
7. For every node with `responsePathways`, every destination id has a matching edge from that node to
   that destination whose `data.label` agrees with the condition.
8. Every `responsePathways` comparison literal is a JSON string, not a number or boolean.
9. Top-level `analysis_options`, `entity_schemas`, `memory_enabled` and `post_call_actions` are
   byte-identical to v86.

**Availability semantics (the incident)**

10. Each of `n_search`, `n_page_2`, `n_page_3`, `n_page_near` has a `body` that parses as JSON and
    whose key set is **exactly** the ten keys frozen in §2.5, no more and no fewer, with
    `"callID": "{{callID}}"`, `"after": "{{time_after}}"`, `"user_text": "{{lastUserMessage}}"`,
    `"user_verbatim": "{{user_verbatim}}"`, `"before": "none"` and `"slot_minutes": "15"` matching
    verbatim. This is no longer contingent on the probe (ruling 1, rev 3): the field set is fixed by
    spec and P-A confirms the gateway accepts it.
10b. Every one of the four bodies is byte-identical to v86's, apart from nothing. The key-set check
    in 10 is the readable failure message; this one is the guarantee.
10c. `first_available` does not appear in any webhook body anywhere in the graph, nor do `doctor`,
    `min_minutes`, `date_conflict` or `either_days` (ruling 2, rev 3). The failure message must say
    that absence is deliberate and point at §2.5, so the next builder does not "fix" it.
11. `time_pref` is `"none"` on `n_search`, `"afternoon"` on `n_page_2` and `n_page_near`, `"late"` on
    `n_page_3`. No availability body anywhere sets `after` to `"none"` or `"" `.
12. No `responseData` JSONPath anywhere in the graph matches `slots\[(?!0|1)\d+\]`. Hardcoded indices
    above 1 are the defect; the check fails and names the node and the path.
13. Each of the four availability nodes extracts `slot_1_day_name` and `slot_2_day_name` from
    `$.result.slots[0].day_name` and `$.result.slots[1].day_name`, and each of `n_offer`,
    `n_offer_2`, `n_offer_3`, `n_offer_near` renders both in its patient-facing copy (see 33).
14. `n_search` extracts `date_conflict_detected`, `conflict_option_1`, `conflict_option_2` and routes
    `date_conflict_detected == "conflict"` to `n_date_conflict`, **positioned before every
    `slot_count` route** in `responsePathways`; `n_date_conflict` routes back to `n_search`.
15. `n_page_2` and `n_page_3` each carry the `time_pref_relaxed != ""` route to `n_offer_near`,
    positioned before the `slot_count` routes.
15b. Every band-empty and band-found route on `n_page_2`, `n_page_3` and `n_page_near` tests
    `slot_count`, never `slot_1_start`. The availability envelope pads `slots` to at least two
    objects to clear stale Bland variables, so `slot_1_start` is not a reliable emptiness signal;
    `count` is the only true one. Probe P-C proves this before the check is trusted.
16. `retryAttempts` is `1` on the four availability nodes and `0` on `n_book_1`, `n_book_2`,
    `n_reconcile_1`, `n_reconcile_2`, `n_appt_check`, `n_identity`, `n_verify_1`, `n_verify_2`.
    A non-zero `retryAttempts` on any node whose `body` contains `"verb":"appt.book"` is a hard fail.

**`time_after` is extracted and wired**

17. Exactly nine nodes carry `extractVars`: `n_ask`, `n_date_conflict`, `n_miss_empty`,
    `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, `n_miss_time`, `n_negotiate`, `n_clarify`.
18. Every one of those except `n_clarify` extracts `time_after`; all nine extract `user_verbatim`.
    Each extraction entry is byte-identical to v86's, including the `[false, false, true]` flags.
19. The `time_after` extraction prompt contains the literal string `Use none when no specific clock
    time was named`, so the null default matches what the gateway is sent.
20. Every `{{...}}` placeholder appearing in any webhook `body` resolves to a variable that is either
    a Bland built-in (`callID`, `lastUserMessage`) or is produced by some node's `extractVars` or
    `responseData` in this graph. An unresolvable placeholder is a hard fail and is named.

**SPEC-v88 invariants still hold**

21. `n_book_1.responsePathways[2]` and `n_book_2.responsePathways[2]` are
    `["book_success", "!=", "true"]` targeting `n_reconcile_1` / `n_reconcile_2`; entries [0] and [1]
    are byte-identical to v86.
22. `n_reconcile_1` and `n_reconcile_2` have `url`, `headers` and `body` byte-identical to
    `n_appt_check`'s, `responseData` exactly `{recon_ok: $.ok, recon_count: $.result.count}`, and the
    three `responsePathways` in conservative-first order.
23. `e_booked_recovered.text` and `e_book_unknown.text` match SPEC-v88 §3 exactly;
    `e_booking_failed.text` equals the `e_book_unknown` text and `e_booking_failed` has zero inbound
    edges.
24. `n_appt_check.responsePathways[0]` is `["appt_count", ">=", "1"]` targeting `e_defer`, and it is
    first. Reconcile's trust in `recon_count >= 1` is only sound because this gate guarantees the
    subject had zero upcoming appointments at thread start; if the gate is missing or reordered,
    `e_booked_recovered` can tell a patient "You're all set" about someone else's prior appointment.
25. Reachability: the only nodes that may reach `e_booked_recovered` are `n_reconcile_1` and
    `n_reconcile_2`. `e_defer` has zero outgoing edges. adjacency(`n_confirm`) is exactly
    {`e_booked`, `e_defer`}. There is no path from `n_confirm` or `e_defer` to any of
    `n_search`, `n_page_*`, `n_offer*`, `n_verify_*`, `n_book_*`, `n_office`, `n_faq`.

**Copy invariants**

26. The string `855` does not appear anywhere in the serialized graph.
27. The exact set of nodes whose `data` contains `(212) 219-2219` is exactly these 17:
    `e_book_unknown`, `e_booked_recovered`, `e_booking_failed`, `e_declined`, `e_defer`, `e_existing`,
    `e_not_me`, `e_office`, `e_safe_failure`, `e_safe_identity`, `e_stop`, `n_confirm`, `n_faq`,
    `n_help`, `n_miss_empty`, `n_miss_unread`, `n_office`. `e_booked` must NOT be in the set.
28. The v62 CLOSE line appears verbatim in `n_confirm.prompt` and in `e_booked_recovered.text`, and
    in no other node. The v62 DEFER line appears verbatim in `e_defer.text` and nowhere else.
29. `n_ask.prompt` contains the exact five-paragraph greeting block from `pathway-v90.json`,
    byte-for-byte, and also contains `ABSOLUTE RULE ON TIMES` and `CONFLICT RULE`.
30. All **20** nodes that carry `ABSOLUTE RULE ON TIMES` in v86 still carry it, byte-identical. The
    check names the expected 20 ids explicitly, so a silent drop on any one of them fails.
31. The literal `at MK2.` and the literal `the MK2 office` do not appear anywhere; `MK2 Optical`
    appears at least 60 times. (v86: 63. v90: 33, with six `at MK2.` across 19 regressed nodes.)
32. `n_offer_3.prompt` does not contain `as late as this day goes`, `this is the latest`,
    `the latest the office has`, or `Never suggest there is anything later`, and does contain both D4
    replacement sentences verbatim.
33. Every offer prompt that names `{{slot_1_start}}` also names `{{slot_1_day_name}}`, and the same
    for slot 2, across `n_offer`, `n_offer_2`, `n_offer_3`, `n_offer_near`.

**Classification gate**

34. `v91-classification.json` exists, covers every field-level v86↔v90 difference, and has zero
    entries in an `open` or `unclassified` bucket.

**Redproof, each mutation must make the validator fail, and the validator must be seen failing**

| id | mutation | must trip |
|---|---|---|
| R1 | set `after` back to `"none"` in `n_page_3` | 10, 11 |
| R2 | restore `slots[16]` in `n_page_3.responseData` | 12 |
| R3 | drop `time_after` from `n_negotiate.extractVars` | 18, 20 |
| R4 | reorder `n_appt_check.responsePathways` so `appt_count == 0` is first | 24 |
| R5 | retarget `n_book_1`'s catch-all back to `e_booking_failed` | 21, 23 |
| R6 | delete `n_help` | 3, 27 |
| R7 | put the greeting back to v86's lenses-and-sunglasses text | 29 |
| R8 | restore the "this is the latest" sentence in `n_offer_3` | 32 |
| R9 | set `retryAttempts: 1` on `n_book_2` | 16 |
| R10 | change one v86 node's `position.x` | 4 |
| R11 | change `n_page_2`'s band-empty route back to `slot_1_start == ""` | 15b |
| R12 | change one BACKGROUND paragraph back to "at the MK2 office" | 31 |
| R13 | drop the `ABSOLUTE RULE ON TIMES` paragraph from `n_offer_near` | 30 |
| R14 | move `n_search`'s conflict route after the `slot_count == "0"` route | 14 |
| R15 | drop `user_verbatim` from `n_page_2`'s body | 10, 10b |
| R16 | add `"first_available": "false"` to `n_search`'s body | 10, 10c |
| R17 | drop the post-booking exclusion clause from `n_help.globalLabel` | 3 |

The clean draft must pass. The validator must also be run against `pathway-v86.json` and
`pathway-v90.json` and must FAIL both. A validator that passes the graph it is supposed to reject is
not a validator. All seventeen mutations must be observed failing with their text captured; a
mutation nobody watched fail is not covered.

---

## 5. Live harness: run against the minted UNATTACHED version, never against the attached one

Driver: `checks/phase_run.py` through `/home/ankit114/repos/mott-v21-snap/harness`, scenario source
`workB3/v62r2-lane/scenarios.py`, transcripts validated by `checks/check_phase_transcript.py`.

**Phase 1: 33 scenarios, subject has zero upcoming appointments.** Precondition asserted by the
driver before every scenario. Required: 33/33 pass. Any pre-existing known failure must be named and
approved before the run, not after.

**Phase 1 additions, the incident, in the existing scenario schema.** These are new and belong in
`scenarios.py`:

```python
{
 'name': 'afternoon then any later time offers genuinely later slots',
 'turns': ['hi', 'friday afternoon', 'any later time?'],
 'expect_node': ['n_offer_3', 'n_offer_near'],
 'expect_slot_floor': '03:00 PM',
 'expect_strictly_later_than_turn': 2,
 'expect_offer_membership': True,
 'expect_inventory_later': {'after_turn': 2, 'time_pref': 'late'},
 'reject_text': r'(that is|this is) the latest|nothing later|no later',
 'why': 'the 2026-08-03 incident: v90 offered 12:30/12:45 then denied later slots that existed',
},
{
 'name': 'any later time never denies availability',
 'turns': ['hi', 'friday afternoon', 'any later time?', 'anything later than that?'],
 'expect_node': ['n_offer_3', 'n_offer_near', 'n_negotiate', 'n_miss_thin'],
 'expect_offer_membership': True,
 'reject_text': r'(that is|this is) the latest|the latest (the office|we) ha|nothing later that day',
 'why': 'D4: a third ask may steer to another day, but may never claim the day has nothing later',
},
{
 'name': 'explicit clock floor is honoured',
 'turns': ['hi', 'friday after 3pm'],
 'expect_node': ['n_offer_3', 'n_offer_near'],
 'expect_slot_floor': '03:00 PM',
 'why': 'proves time_after reaches the gateway; every offered time must be at or after the floor',
},
{
 'name': 'late request that the day cannot satisfy relaxes honestly',
 'turns': ['hi', 'monday after 5pm'],
 'expect_node': ['n_offer_near', 'n_miss_thin'],
 'expect_text': r"(don't have anything that late|closest I have)",
 'why': 'time_pref_relaxed route restored in v86; must offer the closest, never invent a late slot',
},
{
 'name': 'HELP gets a handler',
 'turns': ['hi', 'HELP'],
 'expect_text': r'\(212\) 219-2219',
 'expect_node': ['n_help', 'n_ask'],
 'why': 'n_help has had no handler since Jul 31',
},
{
 'name': 'two conflicting dates ask which one',
 'turns': ['hi', 'tomorrow or the 31st, whichever'],
 'expect_node': ['n_date_conflict', 'n_ask', 'n_clarify'],
 'reject_text': r'\d{1,2}:\d{2}\s?(am|pm)',
 'why': 'n_date_conflict restored; must ask, never guess and never name a time',
},
{
 'name': 'offers name the day not just the time',
 'turns': ['hi', 'next tuesday'],
 'expect_node': 'n_offer',
 'expect_text': r'(mon|tues|wednes|thurs|fri|satur|sun)day',
 'why': 'slot_*_day_name restored to the offer copy',
},
{
 'name': 'new greeting is the one that goes out',
 'turns': ['hi'],
 'expect_node': 'n_ask',
 'expect_text': r'Staying on top of your eye health with a comprehensive eye exam is important',
 'reject_text': r'newest eyewear collection',
 'why': 'D3 shipped and the old body did not come back with the rebase',
},
```

`expect_slot_floor` is already implemented in `pathway_harness.run_scenario` and fails on any offered
time earlier than the floor.

**The other three keys are new and require a harness change (ruling 5, rev 3).** Saying so plainly
matters: a fixed clock floor plus the absence of a denial phrase proves "at or after 3 PM and nothing
forbidden was said", which is not the same claim as "genuinely later real slots surfaced and existing
availability was never denied". A repeated non-advancing offer, an invented time, and a vacuous pass
on a day that had no later slots anyway all survive the floor check.

`run_scenario` currently overwrites `variables` on every turn and appends to one flat `said` list, so
nothing per-turn is recoverable. Change it to accumulate `turns_seen`, one record per turn holding
that turn's `assistant_responses`, `current_node_id` and `variables`, and keep the existing return
signature. Then add three assertions:

1. **`expect_strictly_later_than_turn: N`** (relational). Let `prev` be the maximum offered clock time
   in turn `N`'s record and `now` the minimum offered clock time in the final turn's record, both via
   the existing `offered_times` over that turn's `said` plus that turn's `slot_*_start` variables.
   Fail unless `now > prev`. This is what catches an offer that repeats or moves backwards, which is
   the exact shape of the live defect and which a floor at 03:00 PM cannot see.
2. **`expect_offer_membership: True`** (anti-invention). For every turn, every clock time the
   assistant said must equal that turn's `slot_1_start` or `slot_2_start`. The pathway never binds
   more than two slots, so any third time in the text was invented. Fail naming the invented value.
3. **`expect_inventory_later: {after_turn: N, time_pref: <band>}`** (anti-vacuous). Side-call the
   gateway directly, using the same `store`, the `preference_from`/`preference_to` in turn `N`'s
   variables, `after: "none"`, and the given band, following the `checks/gw_appt.py` pattern. Require
   that the response contains at least one slot strictly later than turn `N`'s maximum offered time.
   If it does not, the scenario **errors as inconclusive rather than passing**: the fixture day had
   nothing later, so the conversation was never tested. If it does, require the final turn's offered
   times to be members of that returned inventory. This is the assertion that distinguishes "the
   pathway surfaced a real later slot" from "the pathway said something that parsed as a time".

Fixture selection follows from 3: the scenario needs a day with a known-populated late band. Pick it
from the same side call before the run rather than assuming Friday always has one.

**Phase 2: exactly one real booking round trip.** The two existing scenarios in `PHASE2_ORDER`:
`post-booking change defers`, then `booked re-entry not re-offered`. This writes one real appointment
for the synthetic test subject and proves the mandated close, the same-thread deferral, and the
thread-start gate. Required: 2/2 pass.

**Reconcile gate probe, see §6.** Runs before Phase 2, on the same unattached version.

**Spot check.** Before anything is called done, open at least one passing transcript by hand and read
what the patient would actually have received. A green check is evidence, not acceptance.

---

## 6. The sharpest risk, and the one measurement that catches it

**Sharpest risk of rebasing:** the D1 re-application is a hand edit against a 267 KB JSON, and a
silent omission or reordering in `n_appt_check` would be invisible in normal use while breaking
SPEC-v88's core assumption. SPEC-v88 lets `e_booked_recovered` tell a patient "You're all set" purely
because `recon_count >= 1`, and that is only sound because the thread-start gate proved the subject
had zero upcoming appointments when the conversation began. If `n_appt_check` is missing, misrouted,
or has its pathways reordered so `appt_count == 0` evaluates first, then a patient who already had an
appointment, hit an ambiguous write, and got reconciled would be told their new booking is confirmed
when nothing was written. That is a false booking claim to a patient, delivered silently, on the exact
path that was proven live today. It is worse than the slot bug it sits next to, and no static check on
the reconcile subgraph alone can see it, because the reconcile subgraph would be perfectly correct.

**The one measurement, run on the minted unattached v91 before the flip:**

Seed the synthetic test subject with exactly one upcoming appointment, then open a fresh thread and
send `hi`. The thread must terminate at `e_defer` with the DEFER line, `appt_count >= 1`, and must
never reach `n_ask`. Then remove that appointment, open another fresh thread, send `hi`, and assert
the thread reaches `n_ask` with `appt_count == 0`. Two runs, one variable, opposite outcomes.

If run one lands on `n_ask`, the gate is not firing, reconcile's `count >= 1` trust is unfounded, and
**v91 must not be flipped** regardless of every other green check. Assert `appt_count` from the
harness `variables` payload, not from the assistant's words.

This is deliberately a read-only probe on both sides. It requires no forced write failure, so it does
not go anywhere near the no-retry constraint on `/sign`.

---

## 7. Residual risks, stated plainly

1. **A third "later" ask still does not surface the genuinely latest slot.** D4 makes the pathway
   honest, not complete. The patient is offered another day instead. Fix candidate for v92: the
   filtered late query already returns the true band count as `slot_count`, and the gateway maps
   `late` to `--after 03:00 pm`, so the claim can be gated on string equality only
   (`slot_count == "1"` or `slot_count == "2"` routes to a claim-allowed offer node; everything else
   routes to the no-claim node). Before anyone builds that, **measure whether Bland's `>=` on
   extracted variables is numeric or lexicographic for multi-digit strings**; v86 already relies on
   `slot_count >= "2"` with counts up to 28, and nobody has tested `"10" >= "2"`. That measurement is
   a five-minute probe and it must precede the design, not follow it.
2. **The `time_after` / `callID` path re-engages the gateway's raw-text authority**
   (`ECP_LLM_INTENT=authoritative`, still enabled server-side, zero `date_source=` log lines since
   Jul 31). Probes P-A and P-B (§1b) settle whether the deployed build accepts the body shape and
   honours the `late` band before anything is built, but they do not prove the conversation-fetch
   path end to end, which needs a real `callID` with a real transcript. Phase 1 exercises that 33
   times before any patient does. Watch the gateway log for the diagnostic sequence, not only for
   `date_source=raw`: per `workG/gateway-contract/report.md`, `date_source=fallback` means authority
   engaged and did not replace the dates, `error_fallback` means it engaged and failed, and on the
   raw-text-authority tier a silent absence is ambiguous. Read `raw_gate` and `raw_fetch` lines to
   tell "not engaged" from "engaged and declined". Absence of all of them is a failure to
   investigate, not a pass.
2b. **Do not "fix" the apparent redundancy of sending both `after` and `time_pref`.** On the
   LLM-intent tier an explicit non-`none` `after` deliberately suppresses the band, so a patient who
   named a clock time gets their exact bound and a patient who named only a part of day gets the
   band. That is the intended precedence, not a bug.
3. **The Chinese greeting no longer matches the English greeting** (§2.3). Inherited, not introduced.
4. **OPEN-1 through OPEN-5** (§3) are unresolved by design and are Ankit's calls. OPEN-5 in
   particular ships a known wording defect that is already live on v86, so v91 is no worse; it is
   listed so nobody discovers it later and thinks v91 introduced it.
5. **`analysis_options` stays `null`**, so `deferred_after_booking`, `booked_after_reconcile` and
   `booking_unverified` are not declared as analysis outcomes. Known SPEC-v62 conformance gap,
   carried forward deliberately.
6. **Position assertions could annoy a future legitimate layout change.** Accepted: catching a silent
   regeneration is worth more than layout freedom, and the assertion is one line to relax
   deliberately.
8. **Reconcile proves count, not attribution (ruling 6, rev 3).** `e_booked_recovered` fires on
   `recon_count >= 1`, which says an appointment exists, not that this conversation created it. The
   `n_appt_check` gate narrows it to "created since thread start", and SPEC-v88 accepted the
   remaining race explicitly, which is why the recovered message is deliberately slot-agnostic. The
   contrarian lane is right that a strict proof would capture the baseline appointment identifiers
   and confirm the requested slot after the write, and right that the §6 gate probe does not test
   this, since it never introduces an unrelated appointment mid-thread. That is a v88 redesign, not a
   v91 repair, and the branch it would change was proven live today. **Carried unchanged, on the
   record.** If Ankit wants it closed, the design is: extract `$.result.appointments[0].id` at
   `n_appt_check`, compare at reconcile, and route a non-match to `e_book_unknown`.
9. **The relaxed-band route uses an empty-string sentinel (ruling 6, rev 3).** `time_pref_relaxed
   != ""` is evaluated before the `slot_count` routes on `n_page_2` and `n_page_3`. If the deployed
   gateway ever returns a non-empty sentinel such as `"none"`, or returns relaxation metadata
   alongside `count == 0`, the graph reaches `n_offer_near` with padded empty slots and offers
   nothing readable. The contract report says the field initialises to `""` and is set only to a
   rejected band name, so the sentinel is correct on the LLM-intent tier; that is documentation, not
   a measurement of the deployed build. Probe P-C can check it in the same call at no extra cost:
   send a band that is certainly empty and record the literal `time_pref_relaxed` value. **Carried
   unchanged; v86 shipped this route for a week.**
10. **`n_appt_check` evaluates `ok != true` last (ruling 6, rev 3).** The order is `appt_count >= 1`,
   then `appt_count == 0`, then `ok != true`. If a failed webhook leaves a stale `appt_count`, the
   node can route on the stale count before reaching the outage branch. This ordering is deliberate
   SPEC-v62 design: conservative branch first, health check last, so that a gateway outage falls
   through to the normal recall flow and never blocks the campaign on a side check. Both
   `appt_count == 0` and `ok != true` lead to `n_ask`, so the only reachable divergence is a stale
   count of 1 or more sending a patient to `e_defer` who has no appointment, which fails safe toward
   "call the office". **Kept as designed, noted here so it is not rediscovered as a bug.**
11. **Anything v87 lost that is not in §1, not in `DIFF-INVENTORY.md`, and not in the classification
   file.** The §3 gate is the mechanism that surfaces it. If the classification cannot account for a
   difference, the flip waits. This spec does not claim its own §1 inventory is complete, it does not
   assume the sibling inventory is complete either, and no check in §4 depends on either being
   complete. The checks assert v86 byte-identity outside a named change set, which is complete by
   construction rather than by enumeration.

---

## 8. Flip checklist

1. Gateway probes P-A, P-B, P-C (§1b) run and recorded in `v91-gateway-probe.md`. P-B failing means
   the change set itself is wrong and goes back to Ankit before any editing.
2. `check_v91_graph.py` PASS on the draft, FAIL on `pathway-v86.json`, FAIL on `pathway-v90.json`.
3. All seventeen redproof mutations R1-R17 observed failing, with the failure text captured.
4. `v91-classification.json` complete and reconciled against `DIFF-INVENTORY.md`, zero open items,
   OPEN-1 through OPEN-5 ruled on by Ankit.
5. Mint v91 UNATTACHED.
6. Reconcile gate probe (§6), both runs, opposite outcomes.
7. Harness change landed: per-turn `turns_seen` capture plus the three new assertions (§5).
8. Phase 1: 33/33 plus the 8 new scenarios, with the incident scenario's relational, membership and
   inventory assertions all executing and none reporting inconclusive.
9. Phase 2: 2/2, one real appointment written for the synthetic subject.
10. Gateway log read for the `raw_gate` / `raw_fetch` / `date_source=` sequence during Phase 1.
11. At least one passing transcript read by hand.
12. Ankit flips in the dashboard. Nobody else, nothing automatic.

---

## 9. Sources

| Input | Used for |
|---|---|
| `pathway-v86.json` | the base; every "v86 value" in this spec was read from it |
| `pathway-v87.json`, `pathway-v88.json`, `pathway-v90.json` | the provenance chain that proves the deliberate set is closed (v88→v90 differs by exactly one node) |
| `SPEC-v62.md`, `SPEC-v88.md` | D1 and D2, quoted rather than copied from v87's rendering |
| `checks/check_v88_graph.py` | the D2 edge ids, node names and invariants; `check_v91_graph.py` extends its diff-against-base pattern |
| `DIFF-INVENTORY.md` | independent corroboration and the classification input; three counts corrected in §3 |
| `workG/provenance-fix-week/report.md` | the Jul 27-31 fix-to-pathway-requirement map: the eight extraction nodes, the per-node `time_pref` values, `day_name` mappings, the `n_search` conflict route ordering, `n_help`'s field set |
| `workG/v86-wiring-map/report.md` | v86's exact bodies, extractions and edges; `callID` established as Bland runtime context rather than an extracted variable; the independent finding that `n_offer_3`'s "latest" claim is unproven (D4) and that `n_offer_near`'s framing is wrong on one route (OPEN-5) |
| `workG/gateway-contract/report.md` | the `/availability` request contract, `late` = `--after 03:00 pm` on the LLM-intent tier only, explicit `after` suppressing the band, `time_pref_relaxed` semantics, the two-slot response padding, and the `date_source` log vocabulary. Its whitelist claim is what P-A exists to test |
| `checks/phase_run.py`, `workB3/v62r2-lane/scenarios.py`, `mott-v21-snap/harness/pathway_harness.py` | the harness contract and the scenario schema, including `expect_slot_floor` |

## Revision 4 — coordinator ruling after live harness (2026-08-03)

Live proof hz-happy exposed a v86-era latent gap: the `n_ask -> n_search` edge label enumerates
day-word phrasings only, so ASAP-family requests ("the first available time works", "soonest",
"whenever") match no edge and the conversation loops at n_ask. Extraction itself was proven
correct (preference_from = "tomorrow"). D5, one edge only: the label of `edge-n_ask-n_search-*`
becomes EXACTLY:

"says any day, weekday, date, week, weekend, or time preference — including Saturday, this
weekend, next week, or a month and day — or asks for the first available, soonest, earliest,
or whenever opening"

The v86 wording is kept verbatim and extended, not replaced, to avoid regressing the precise
routing the suite scenarios depend on. Everything else in this spec is unchanged. The validator
moves that edge to the mutable set and asserts the new label exactly.
