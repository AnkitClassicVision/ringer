# Bland pathway v87 conformance review against SPEC-v62

Static review only. No source file, API, gateway, webhook, or network endpoint was modified or called.

## Failures and specification contradictions first

| Kind | Verdict | Evidence |
|---|---|---|
| Design item 3 | **FAIL** | `e_defer` itself conforms, but the exported top-level value is literally `analysis_options: null`. Therefore `deferred_after_booking` was not added there as the item claims. |
| G5 versus revised item 6 | **SPEC CONTRADICTION** | G5 requires an n_identity `booked_already` route. Revised item 6 explicitly says that variable is retired and replaced by n_appt_check. This review uses the later explicit revision: n_identity `count == 1` routes to n_appt_check, whose first response pathway is `appt_count >= 1 → e_defer`. On that revision-aware reading G5 passes. A strictly literal G5-only reading fails. |

The incident defect is outside SPEC-v62's stated gates: n_book_1 and n_book_2 route every `book_success != true` response to e_booking_failed. The graph has no UNKNOWN branch or read-after-write verification for HTTP 502 `gateway_unreachable` or HTTP 423 `write_unverified`, so a committed write can still produce `I couldn't confirm that booking.`

## Mechanical facts

These values were recomputed using only each node's concatenated `prompt`, `text`, `globalLabel`, and `name` fields for string searches.

| Fact | Exact value |
|---|---|
| `number_carrier_nodes` | `["n_confirm", "n_office", "n_faq", "e_safe_identity", "e_safe_failure", "e_booking_failed", "e_defer", "e_office", "e_declined", "e_stop", "e_not_me", "e_existing"]` |
| `nodes_containing_855` | `[]` |
| `close_carrier_nodes` | `["n_confirm"]` |
| `n_confirm_adjacency` | `["e_booked", "e_defer"]` |
| `e_defer.exists` | `true` |
| `e_defer.node_type` | `"End Call"` |
| `e_defer.outgoing_edge_count` | `0` |
| `e_defer.text_matches_defer_verbatim` | `true` |
| `analysis_options_value` | `null` |

## Gate verdicts

| Gate | Verdict | Evidence |
|---|---|---|
| G1 | **PASS** | Zero scanned nodes contain `855`. `(212) 219-2219` occurs in exactly the eleven specified carriers plus e_defer and nowhere else in the scanned fields. |
| G2 | **PASS** | The verbatim CLOSE occurs only in n_confirm.prompt, which says the English confirmation `must end exactly with` it. e_booked.text is `Thank you. We look forward to seeing you.` |
| G3 | **PASS** | e_defer exists, is an `End Call`, has zero outgoing edges, and its text exactly equals `For that you'll have to contact the MK2 Optical office at (212) 219-2219`. |
| G4 | **PASS** | n_confirm targets only e_booked and e_defer. `change requested after confirmation` and `anything else requested after booking` target e_defer; both targets are terminal, so no path reaches search, verify, book, offer, n_office, or n_faq. |
| G5 | **PASS** | Revision-aware reading used. Revised item 6 supersedes the stale `booked_already` wording. n_identity `count == 1 → n_appt_check`; n_appt_check orders `appt_count >= 1 → e_defer` first, before its two n_ask fallbacks. A literal unrevised reading would be FAIL. |
| G6 | **PASS** | n_office.globalLabel and n_faq.globalLabel both contain `This does not apply once a booking is confirmed.` Both nodes are global. |

## Design-item verdicts

| Item | Verdict | Evidence |
|---|---|---|
| 1 | **PASS** | All eleven named carrier nodes contain `(212) 219-2219`, and no scanned node contains `855`. The export alone cannot compare the separate byte-identical-to-an-earlier-version clause, but all v62-visible graph requirements are met. |
| 2 | **PASS** | n_confirm.prompt contains the exact CLOSE, requires the booked time, one bubble, exact mandated tail, and no earlier duplicate `all set`. The CLOSE occurs nowhere else; e_booked retains the non-claim text `Thank you. We look forward to seeing you.` |
| 3 | **FAIL** | e_defer is correctly typed and terminal with exact DEFER text and outcome `deferred_after_booking`, but top-level `analysis_options` is `null`, contradicting the claimed addition. |
| 4 | **PASS** | n_confirm has both required e_defer routes and no target beyond e_booked/e_defer. Its adjacency is exactly `{e_booked, e_defer}`. |
| 5 | **PASS** | n_office and n_faq carry the post-booking exclusion. e_existing is scoped to `an appointment made outside this conversation`. |
| 6 | **NOT_VERIFIABLE** | The exported graph conforms: n_appt_check uses POST /appt-list with patient_id/store, maps `$.ok` and `$.result.count`, orders the booked route first, and falls through to n_ask for zero/outage. Retired `booked_already` and `upcoming_appointment` mappings are absent. However, the same item requires send-queue exclusion and live probe P4 behavior, neither of which is present in or provable from this JSON. |
| 7 | **PASS** | n_confirm.prompt contains `您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219`: an all-arranged statement, Latin-script brand, ASCII digits, and no 预约成功 overclaim. e_defer remains English-only as documented. |

## Extra findings

1. **Critical:** Both /sign nodes, n_book_1 and n_book_2, send `book_success != true` directly to e_booking_failed. HTTP 502 and 423 unknown outcomes are not separated from definite non-success, and there is no verification branch. This matches the reported false-failure behavior after a committed write.
2. **High:** Both write nodes set `modelOptions.retryAttempts: 0`, correctly avoiding an unsafe automatic retry of the non-idempotent /sign operation.
3. **Scope note:** The redproof mutations M1-M7, live probes, send-queue behavior, and comparison to v61/prior graphs cannot be verified from pathway-v87.json alone and were not guessed.
