# SPEC v88 — truthful booking-failure handling (reconcile, never lie)

Base: the exported `pathway-v87.json` in this directory (42 nodes, 115 edges).
Target: `pathway-v88-draft.json`, byte-stable JSON, ready to mint as a new unattached version.

## Why (one paragraph)

Measured incident 2026-08-03: the gateway's `/sign` write returned a real wire
`502 {"error":"gateway_unreachable"}` at 28.2s while the EMR write committed. v87's book nodes
route every non-success through one catch-all (`book_success != true`) into `e_booking_failed`,
whose text asserts a definite failure. Executed truth-table analysis (manifestD, 5/5 PASS)
confirmed a 502 is indistinguishable from a genuine refusal in the v87 graph, and that
`e_safe_failure` is unreachable from the write path. v88 makes the ambiguous case tell the truth:
on any unconfirmed write, read the EMR back (`/appt-list`) and let the source system decide the
message. No retry of the write, ever (`/sign` has no idempotency key).

## Design decisions (locked)

- **Catch-all reroutes to reconciliation** instead of testing 502-specific body fields. Robust to
  empty bodies, timeouts, 404s, malformed responses — anything that is not a confirmed success.
- **Reconciliation trusts `count >= 1`** because the thread-start gate (`n_appt_check`:
  `appt_count >= 1 → e_defer`) guarantees the subject had zero upcoming appointments when the
  conversation began. An appointment appearing by reconcile time was created during this
  conversation. Residual race (another channel booking mid-conversation) is accepted; the
  recovered message is deliberately slot-agnostic.
- **No new timeout fields.** Bland's effective node-timeout field semantics are unverified; the
  reconcile design is correct under any timeout. Timeout tuning is a separate gateway-side track.
- **`e_booking_failed` is kept but neutered** (reworded to uncertainty, zero inbound edges) as a
  safety net against any unexpected platform routing.
- **`analysis_options` stays `null`.** The SPEC-v62 conformance gap is real but out of scope here.

## Exact changes, v87 → v88 (complete list — anything else changing is a defect)

### 1. Retarget the two catch-alls

- `n_book_1.data.responsePathways[2]` becomes
  `["book_success", "!=", "true", {"id": "n_reconcile_1", "name": "Write outcome unknown - reconcile against the EMR"}]`
- `n_book_2.data.responsePathways[2]` becomes the same with `n_reconcile_2`.
- Delete edges `edge-n_book_1-e_booking_failed-book-success-true` and
  `edge-n_book_2-e_booking_failed-book-success-true`.
- Add edges (`type: "custom"`, `animated: true`, `sourceHandle/targetHandle: null`):
  - id `edge-n_book_1-n_reconcile_1-book-success-not-true`, source `n_book_1`, target
    `n_reconcile_1`, `data.label` `book_success != true`, `data.isHighlighted` false,
    `data.description` `Route from n_book_1 to n_reconcile_1 when: book_success != true.`
  - id `edge-n_book_2-n_reconcile_2-book-success-not-true`, mirrored.

### 2. New Webhook nodes `n_reconcile_1` and `n_reconcile_2`

Top-level: `type: "Webhook"`, `sourcePosition: "bottom"`, `targetPosition: "top"`,
`width: 320`, `height: 115`; positions `n_reconcile_1` x -560 y 1010, `n_reconcile_2` x -60
y 1010 (also mirrored into top-level `x`/`y` and `position: {x, y}` like every other node).

`data`:
- `name`: `Reconcile write outcome 1 (silent)` / `Reconcile write outcome 2 (silent)`
- `active`: copy the literal value from `n_appt_check.data.active`
- `url`: `https://mott-booking-gw.mail.mybcat.com/appt-list`
- `method`: `POST`
- `headers`: copy EXACTLY from `n_appt_check.data.headers` (secret placeholder included)
- `body`: copy EXACTLY from `n_appt_check.data.body`
- `text`: `""`
- `modelOptions`: `{"retryAttempts": 0, "skipUserResponse": true}`
- `responseData`: `[{"data": "$.ok", "name": "recon_ok"}, {"data": "$.result.count", "name": "recon_count"}]`
  (fresh names — never overwrite the trusted upstream `ok`/`appt_count`)
- `responsePathways`, in THIS order (conservative branch first, complement onto conservative):
  1. `["recon_ok", "!=", "true", {"id": "e_book_unknown", "name": "Reconcile read unavailable"}]`
  2. `["recon_count", ">=", "1", {"id": "e_booked_recovered", "name": "EMR shows the booking exists"}]`
  3. `["recon_count", "==", "0", {"id": "e_book_unknown", "name": "EMR shows no booking"}]`

Edges for these six routes, `type: "custom"`, `animated: true`, handles null, labels matching the
conditions verbatim (`recon_ok != true`, `recon_count >= 1`, `recon_count == 0`), descriptions in
the standard `Route from <src> to <dst> when: <label>.` pattern, ids:
- `edge-n_reconcile_1-e_book_unknown-recon-ok-not-true`
- `edge-n_reconcile_1-e_booked_recovered-recon-count-ge-1`
- `edge-n_reconcile_1-e_book_unknown-recon-count-0`
- and the three `n_reconcile_2` mirrors.

### 3. New End Call nodes

Both: `type: "End Call"`, `sourcePosition: "bottom"`, `targetPosition: "top"`, `width: 320`,
`height: 115`; positions `e_booked_recovered` x -310 y 1160, `e_book_unknown` x -310 y 1310
(top-level `x`/`y` + `position` mirrored). `data.active`: copy from `e_booking_failed.data.active`.

- `e_booked_recovered`: `data.name` `booked_after_reconcile`, `data.outcome`
  `booked_after_reconcile`, `data.tag` `{"color": "#455A64", "name": "outcome:booked_after_reconcile"}`,
  `data.text` EXACTLY:
  `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219`
- `e_book_unknown`: `data.name` `booking_unverified`, `data.outcome` `booking_unverified`,
  `data.tag` `{"color": "#455A64", "name": "outcome:booking_unverified"}`, `data.text` EXACTLY:
  `I wasn't able to confirm whether that booking went through. The MK2 Optical office will double-check it and reach out to you. If you'd like, you can also call them at (212) 219-2219.`

### 4. Reword the safety net

`e_booking_failed.data.text` becomes EXACTLY the `e_book_unknown` text above. All other
`e_booking_failed` fields unchanged. After the retargeting it has zero inbound edges; keep it.

## Invariants (the validator enforces these)

- Node count 46, edge count 121. Every v87 node/edge not named above is byte-identical.
- Top-level keys (`analysis_options`, `entity_schemas`, `memory_enabled`, `post_call_actions`)
  unchanged.
- No `855` anywhere. The `(212) 219-2219` carrier set is exactly v87's set plus
  `e_booked_recovered` and `e_book_unknown` (with `e_booking_failed` still carrying it).
- Every new/changed edge has a unique id and `type: "custom"`; every responsePathways entry's
  destination has a matching edge (source, target, label agreement).
- Only `n_confirm` (via `book_success == true`) and `e_booked_recovered` (via EMR read-back) may
  claim a booking. `e_booked_recovered` earns it by verifying against the source system, which is
  the design rule's intent.
