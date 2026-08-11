# v62 implementation report

## What changed and why

- Replaced the retired number with `(212) 219-2219` in the eleven specified carrier nodes and added it to `e_defer`.
- Replaced patient-facing `Mott Optical` with `MK2 Optical`. Internal gateway and secret identifiers remain unchanged.
- Made `n_confirm` the only positive booking-claim node. Its prompt requires the booked time, one bubble, no duplicated “all set,” and the exact mandated English tail.
- Added terminal End Call node `e_defer` with exact mandated text, outcome `deferred_after_booking`, an outcome tag, and no outgoing edges.
- Retargeted the post-confirmation change edge to `e_defer` and added an anything-else post-booking edge. `n_confirm` now has exactly the targets `e_booked` and `e_defer`.
- Added silent `n_appt_check` after unique identity. It calls the gateway's existing `POST /appt-list` endpoint with only `patient_id` and `store`, maps `appt_count` from `$.result.count`, and checks the booked route first. `appt_count >= 1` defers; zero count or a gateway outage falls through to the normal recall opener. Zero gateway changes are needed: the endpoint is already tested in `gw-diag-snap`, and probe P4 now verifies that its default window excludes past appointments and that count flips to `>= 1` after `/sign`. The send queue remains the first-line filter for already-scheduled patients; this graph route is the backstop.
- Scoped `n_office` and `n_faq` out after confirmation and narrowed `e_existing` to appointments made outside this conversation.
- Added 12 named v62 scenarios and changed the two stale `855` expectations to `212`, for 42 total scenarios.
- Added G1-G6 to the existing structural gate and retained the previous structural checks. Updated M6 for the `/appt-list` shape while retaining every other mutation class; redproof now exercises 21 mutations.

## Spec deviation and runtime limitation

**Chinese deferral is not implemented as runtime text.** G3 requires `e_defer` to be an `End Call` node whose `text` equals the mandated English DEFER line exactly. The v61 graph provides no demonstrated language-selectable End Call field, and adding a second language to `text` would violate the frozen verbatim requirement. I did not invent an unsupported schema or weaken G3. The Chinese scenario is present as required, but it is expected to expose this limitation until the copy and delivery mechanism are approved.

The fixed Chinese CLOSE is present in `n_confirm.prompt`. It is final-proposed copy for Ankit's read, not approved copy.

## Proposed Chinese renderings for sign-off

**FINAL-PROPOSED CLOSE FOR ANKIT'S READ**

`您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219`

**FINAL-PROPOSED DEFER FOR ANKIT'S READ**

`为此，您需要拨打 (212) 219-2219 联系 MK2 Optical 办公室。`

The digits remain ASCII in both renderings.

## Verification

- `python3 -m py_compile build_v62.py scenarios.py check_candidate_gate.py redproof_run.py`: passed.
- `python3 build_v62.py`: generated 42 nodes and 115 edges.
- `python3 check_candidate_gate.py v62_graph.json`: passed.
- `python3 check_candidate_gate.py /tmp/v62r2-v61-gate-copy.json` using a byte-identical copy of `source/v61_graph.json`: failed as required, including G1-G6 failures.
- `python3 redproof_run.py`: passed with `mutations_caught=21`.
- Repeated builder output produced the same SHA-256 both times, `f4992a7234a36374a69e715be126a247a8dcb495a6eda35a8abe880d2714fdcc`; output is deterministic.

## Could not verify

- No live SMS, gateway, or network probes were run. P1-P4 remain release gates.
- The scenario file is an inventory; the supplied source contains no behavioral scenario runner, so the 42 conversations were not executed against Bland.
- Bland behavior after an End Call, global precedence after booking, the gateway appointment-search response after `/sign`, and Chinese End Call delivery remain unverified.
- Probe P4 remains required to verify the existing `/appt-list` default window excludes past appointments and its count flips to `>= 1` after `/sign`.
