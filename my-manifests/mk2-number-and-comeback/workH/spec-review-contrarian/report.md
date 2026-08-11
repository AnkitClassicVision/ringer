# Attacks

## 1. The rebase direction is plausible, but its proof counts fields instead of consequences

The 113-to-34 ratio gives every atomic diff equal weight. A coordinate, a label phrase, a webhook body field, and a booking-confirmation route each count as one row even though their failure costs differ radically. Rebase is still the better default because v86 contains the availability and conflict machinery that v90 lost, but the ratio does not decide the direction “on its own.” The argument also treats every v86-v90 difference outside D1-D3 and the greeting as stale-base residue. That is provenance evidence, not intent evidence: a deliberate but undocumented v87 change is indistinguishable from residue. The required classification repeats the same assumption instead of independently proving it.

The spec partly recognizes this with OPEN-1 through OPEN-5, but then requires “zero open items” before flip without specifying who records the rulings or how those rulings alter the validator. Two builders can therefore produce different graphs while both claiming compliance: one preserves every v86 default; another applies an Ankit ruling to an OPEN item and updates the expected set.

## 2. D1 is not a faithful re-application of SPEC-v62

SPEC-v62 Design item 3 requires `deferred_after_booking` to be added to top-level `analysis_options`. SPEC-v91 explicitly keeps `analysis_options: null`. That is an intentional waiver, but it makes the repeated framing “re-apply D1” and “named in SPEC-v62's design list” false unless the waiver is elevated into D1’s normative definition. A builder following D1 literally from SPEC-v62 changes the top level; a builder following v91 OPEN-2 does not.

SPEC-v62 also mandates a number swap in eleven named carriers and its G1 expects the carrier set plus `e_defer`. SPEC-v91’s validator expects seventeen nodes because the v86 base and D2 add more number-bearing nodes. That larger set may be correct for v91, but it is not a transcription of the v62 carrier rule. The spec needs a requirement matrix that distinguishes `implemented by D1`, `already satisfied by v86`, `added by D2`, and `waived`. Today those categories are blended.

The Chinese ruling is also under-tested. SPEC-v62 requires faithful sentence-for-sentence Chinese renderings, yet v91’s mechanical gate only checks English CLOSE/DEFER placement and the live plan has no explicit Chinese confirmation or post-booking deferral scenario. A builder can pass while mis-copying the locked Chinese close.

## 3. “Byte-identical positions” can reject an honest build

The preservation goal is sound, but whole-node equality including `position`, mirrored `x`/`y`, `height`, and `width` conflates semantic integrity with exporter behavior. An import/export cycle can normalize numeric representation, recompute node dimensions, or move nodes to avoid overlap without changing routing or copy. If the validator runs only on the hand-built pre-import JSON, it cannot prove the minted export retained semantics. If it runs on a dashboard export, it can false-fail harmless layout normalization.

Use two gates: strict equality on the pre-import artifact, then a normalized semantic diff on the post-import export. Record coordinate deltas separately and fail only on unapproved movement above an explicit tolerance or on movement of untouched nodes caused by regeneration. The present wording gives no tolerance and no stage distinction.

## 4. D4 removes the false claim but does not fully specify the next route

The replacement TASK says “take the path for a different day.” The actual JSON has no edge labeled “asks for something later” or “different time”; `n_offer_3` only has `wants a different day` to `n_negotiate`, plus selection, mixed-intent, decline, and timeout edges. The removed sentences previously collapsed “later” into “another day,” which matched that edge. The new copy tells the model both that later might exist and that it must treat a later-time request as a different-day intent. That semantic mismatch is exactly where two model/build outcomes can diverge: one routes “anything later?” to `n_negotiate`; another stays in `n_offer_3` because the user did not request another day; a third treats repeated refusal as `e_declined`.

The proposed repeated-run scenario allows four different nodes (`n_offer_3`, `n_offer_near`, `n_negotiate`, `n_miss_thin`), so it cannot prove the mandated route. D4 needs a dedicated edge or an explicit routing-label expansion such as `wants a different day or asks for a later time after the late-band offer`, plus one exact expected next node.

## 5. Dangerous interaction: `n_help` can override post-booking truth and lifecycle

In v86, `n_help` is global, has auto-return enabled, says “The booking conversation should continue after this reply,” and forbids claiming a booking exists. D1 scopes `n_office`, `n_faq`, and `e_existing` after confirmation, but does not scope `n_help`. After `n_confirm`, a patient sending `HELP` or `INFO` can therefore invoke `n_help`, receive language that implies the booking is not complete, and auto-return into a node whose intended lifecycle is already terminal/deferral-only. The static path check cannot see global interception because `n_help` has zero graph edges. The Phase 1 HELP scenario only tests pre-booking behavior, while Phase 2 tests a change request and re-entry, not HELP/INFO after confirmation.

This is a direct restored-v86 versus D1 interaction. Add the same post-booking exclusion to `n_help` or define explicit precedence that sends post-booking HELP to `e_defer`. Then run confirm → HELP and confirm → INFO transcripts and assert no duplicate confirmation, no “not booked” language, and correct termination.

## 6. Dangerous interaction: the appointment gate does not make reconcile attribution sound

`n_appt_check` proves only that `/appt-list` returned count zero at thread start. `n_reconcile_1/2` later treat any `recon_count >= 1` as proof that the ambiguous write created the intended appointment. A concurrent booking, staff-created appointment, delayed visibility of a prior appointment, or another appointment created during the conversation can satisfy that count. Neither reconcile node compares appointment ID, requested doctor, requested start/end, creation time, or a before/after set. The spec’s claim that the gate makes recovered confirmation sound is therefore too strong.

The two-run gate probe only validates initial gating. It never forces an ambiguous write while introducing a different appointment between the baseline and reconcile read. The safest fix is attribution: capture the baseline appointment identifiers and confirm the exact requested slot or a new matching appointment after the write. If the endpoint cannot support that, `recon_count >= 1` must end at `e_book_unknown`, not at a patient-facing “You're all set.”

## 7. Dangerous interaction: ordered predicates can route stale or contradictory webhook data

Both `n_appt_check` and the availability nodes depend on first-match ordering. On `n_appt_check`, `appt_count >= 1` and `appt_count == 0` precede `ok != true`. If a failed webhook leaves a prior value in `appt_count`, the node can route on stale count rather than the outage path. On `n_page_2` and `n_page_3`, `time_pref_relaxed != ""` precedes count checks. If the gateway uses a non-empty sentinel such as `"none"`, or returns relaxed metadata alongside `count == 0`, the graph goes to `n_offer_near` with padded/empty slots.

SPEC-v91 assumes ordering and variable clearing behavior but has no engine probe where two predicates are simultaneously true and no failed-webhook probe after variables were previously populated. Static matching of pathways to edges cannot catch either runtime semantic.

## 8. The harness plan misses several high-value failure classes

- It allows broad `expect_node` lists for the repeated-later and conflict scenarios, so materially different routes can all pass.
- It does not test HELP or INFO after `n_confirm`, despite restoring a global auto-return node into a newly terminal post-booking design.
- It does not test STOP precedence after booking, although SPEC-v62 explicitly called for that probe.
- It does not test `n_appt_check` outage with stale `appt_count`, or relaxed-band responses with contradictory `time_pref_relaxed` and `slot_count` values.
- It does not test multi-digit string comparison even though `slot_count >= "2"` can see counts up to 28.
- It does not test Chinese locked confirmation/deferral copy.
- It cannot distinguish a recovered booking from an unrelated appointment because it asserts count, not identity/slot attribution.
- It verifies a precondition before each Phase 1 scenario but does not specify isolation/reset of conversation variables, which matters for stale-value routing.

# Confirmed problems

1. **D1 transcription is internally contradictory.** Evidence: SPEC-v62 requires the new outcome in `analysis_options`; SPEC-v91 says it remains `null`. This is a written, not inferred, conflict.
2. **D4 has no exact route for its mandated behavior.** Evidence: the v86/v90 ground-truth edges from `n_offer_3` include `wants a different day`, but no later-time edge. The new prompt converts a later-time request into a different-day route without changing the label or adding an edge.
3. **Post-booking HELP is unscoped.** Evidence: v86’s `n_help` is global and auto-returning, explicitly says the booking conversation continues, and denies booking knowledge. D1 scopes three other globals/branches but leaves `n_help` byte-identical.
4. **Reconcile success is not attributable to the attempted write.** Evidence: v90’s reconcile response extracts only `recon_ok` and aggregate `recon_count`; `>= 1` reaches `e_booked_recovered`. No appointment record or slot is compared.
5. **The layout gate has no import/export normalization policy.** Evidence: assertion 4 demands untouched nodes remain identical including all coordinate and dimension fields, while residual risk 6 admits legitimate layout changes can trip it.
6. **The harness does not prove global-node precedence.** Evidence: its HELP test occurs before booking; Phase 2 does not send HELP or INFO after confirmation.
7. **The harness does not prove ordered-pathway runtime semantics.** Evidence: the static validator checks ordering, but no scenario creates overlapping true predicates or stale webhook variables.

# False alarms I considered and dismissed

1. **“Rebase is categorically wrong.”** Dismissed. v86 demonstrably contains `n_date_conflict`, `n_help`, filtered slot indices, day names, clock-floor input, and relaxed-band routes that v90 lacks. Rebase remains the lower-omission starting point; only the spec’s quantitative proof is overstated.
2. **“D4 permits invented later times.”** Dismissed. The surrounding NEVER paragraph still forbids naming any time other than the two returned slots. The problem is route determinism, not time invention.
3. **“`n_date_conflict` is unreachable.”** Dismissed. In v86, `n_search` extracts conflict fields, places `date_conflict_detected == conflict` before slot-count routes, and has a matching edge to `n_date_conflict`; that node has a return edge to `n_search`.
4. **“Relaxed-band fallback has no route.”** Dismissed. v86 has `time_pref_relaxed != ""` before slot-count checks on both `n_page_2` and `n_page_3`, with edges to `n_offer_near`.
5. **“The v62 gate requires a retired `booked_already` variable.”** Dismissed. SPEC-v62’s revised Design item 6 explicitly retires that invented field in favor of `n_appt_check`; the stale G5 wording is a defect in v62’s gate summary, not a reason to restore the variable.

# recommendation

**REVISE before build.** Keep v86 as the base, but do not call D1 faithful until every SPEC-v62 item is classified as applied, already satisfied, superseded, or explicitly waived. Make D4 routing deterministic, scope `n_help` after booking, replace count-only reconcile recovery with attributable matching, and split pre-import strict preservation from post-export semantic/layout validation. Add runtime probes for global precedence, stale variables, overlapping predicates, multi-digit comparisons, Chinese copy, and unrelated-appointment reconcile contamination.

# unique_catches

1. `n_help` is the restored global most likely to violate the new post-booking lifecycle because its own prompt says booking should continue and that no booking can be known.
2. The baseline-zero appointment gate prevents only pre-existing appointments; it does not identify which appointment caused a later nonzero count.
3. D4’s phrase “take the path for a different day” has no matching later-time edge, and the harness’s four-node allowance masks the ambiguity.
4. A failed `n_appt_check` can be misrouted if Bland evaluates stale `appt_count` before `ok != true`; pathway ordering alone does not establish variable clearing.
5. A non-empty relaxed-band sentinel can preempt `slot_count == 0` and send padded empty slots to `n_offer_near`.
6. The spec’s 113:34 ratio is not risk-weighted and cannot, by itself, establish the safer merge direction.

# proof_slots

| proof | current state | required evidence |
|---|---|---|
| D1 transcription | failed | Line-by-line SPEC-v62 matrix: `applied`, `already in v86`, `superseded`, or `explicit v91 waiver`, including Brand and `analysis_options` |
| D4 routing | failed | One exact route for a second later-time request; repeated runs must land on that node, not any of four allowed nodes |
| Layout preservation | unproven | Pre-import strict equality; post-export normalized semantic diff; separately reviewed coordinate/dimension delta |
| Post-booking global precedence | missing | Confirm booking, then send HELP and INFO; record node sequence, reply, auto-return, and terminal state |
| Reconcile attribution | failed by design | Begin at zero, create an unrelated appointment during the thread, force ambiguous write, and prove no recovered confirmation |
| Ordered pathway semantics | missing | Engine probe with two true predicates; failed webhook after prior nonzero variables; record chosen route and variable payload |
| Relaxed empty response | missing | Return non-empty relaxed sentinel with count zero and padded slots; prove no patient offer is rendered |
| Multi-digit comparison | missing | Runtime observations for `"2"`, `"10"`, and `"28"` against `>= "2"` |
| Chinese locked copy | missing | Hand-reviewed Chinese confirmation and post-booking behavior against SPEC-v62’s sentence-level ruling |

```json CITATIONS
[
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"The ratio decides it on its own."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v62.md","quote":"outcome `deferred_after_booking`\n   (added to analysis_options), no outgoing edges."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"v91 keeps `null` and inherits the documented\n  conformance gap."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v62.md","quote":"**\"MK2 Optical\" in ALL patient-facing copy.**"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"including `position`, `x`, `y`, `height` and `width`."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"Offer to look at another day instead, and take the path for a different day."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json","quote":"The booking conversation should continue after this reply."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json","quote":"\"enableGlobalAutoReturn\": true"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v90.json","quote":"\"name\": \"EMR shows the booking exists\""},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json","quote":"\"name\": \"Band empty, closest offered instead\""},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json","quote":"Never suggest there is anything later that day than these two."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v62.md","quote":"P3 global precedence post-booking: STOP vs e_defer vs e_existing."}
]
```
