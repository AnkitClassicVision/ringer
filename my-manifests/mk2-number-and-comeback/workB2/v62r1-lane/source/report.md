# v62 implementation report

## What changed and why

- Replaced the retired number with `(212) 219-2219` in the eleven specified carrier nodes and added it to `e_defer`.
- Replaced patient-facing `Mott Optical` with `MK2 Optical`. Internal gateway and secret identifiers remain unchanged.
- Made `n_confirm` the only positive booking-claim node. Its prompt requires the booked time, one bubble, no duplicated “all set,” and the exact mandated English tail.
- Added terminal End Call node `e_defer` with exact mandated text, outcome `deferred_after_booking`, an outcome tag, and no outgoing edges.
- Retargeted the post-confirmation change edge to `e_defer` and added an anything-else post-booking edge. `n_confirm` now has exactly the targets `e_booked` and `e_defer`.
- Added `booked_already <- $.result.campaign_booked` to `n_identity`; its explicit-true route to `e_defer` is ordered before the existing unique-identity route. Missing or malformed values retain the old fall-through behavior.
- Scoped `n_office` and `n_faq` out after confirmation and narrowed `e_existing` to appointments made outside this conversation.
- Added 12 named v62 scenarios and changed the two stale `855` expectations to `212`, for 42 total scenarios.
- Added G1-G6 to the existing structural gate and retained the previous structural checks. Added M1-M7 to redproof while retaining the previous mutation classes; redproof now exercises 19 mutations.

## Spec deviation and runtime limitation

**Chinese deferral is not implemented as runtime text.** G3 requires `e_defer` to be an `End Call` node whose `text` equals the mandated English DEFER line exactly. The v61 graph provides no demonstrated language-selectable End Call field, and adding a second language to `text` would violate the frozen verbatim requirement. I did not invent an unsupported schema or weaken G3. The Chinese scenario is present as required, but it is expected to expose this limitation until the copy and delivery mechanism are approved.

The fixed Chinese CLOSE is present in `n_confirm.prompt`. It is proposed copy, not approved copy.

## Proposed Chinese renderings for sign-off

**PROPOSED CLOSE, REQUIRES ANKIT/OPS SIGN-OFF**

`您已预约成功。如有其他问题，请致电 MK2 Optical：(212) 219-2219`

**PROPOSED DEFER, REQUIRES ANKIT/OPS SIGN-OFF**

`为此，您需要联系 MK2 Optical 门店，电话：(212) 219-2219`

The digits remain ASCII in both renderings.

## Verification

- `python3 -m py_compile build_v62.py scenarios.py check_candidate_gate.py redproof_run.py`: passed.
- `python3 build_v62.py`: generated 41 nodes and 113 edges.
- `python3 check_candidate_gate.py v62_graph.json scenarios.py`: passed.
- `python3 check_candidate_gate.py source/v61_graph.json`: failed as required, with G1-G6 failures.
- `python3 redproof_run.py`: passed with `mutations_caught=19`.
- Repeated builder output and SHA-256 comparison: see final verification run; output is deterministic.

## Could not verify

- No live SMS, gateway, or network probes were run. P1-P4 remain release gates.
- The scenario file is an inventory; the supplied source contains no behavioral scenario runner, so the 42 conversations were not executed against Bland.
- Bland behavior after an End Call, global precedence after booking, the gateway flag flip after `/sign`, and Chinese End Call delivery remain unverified.
- The gateway must deploy `campaign_booked` before the graph for come-back protection to be active. Graph-first safely falls through to v61 behavior but does not prevent rebooking on re-entry.
