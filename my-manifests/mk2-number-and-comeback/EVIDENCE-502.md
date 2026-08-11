# Evidence packet: booking commits but the patient is told it failed

All identifiers below are scrubbed. The test subject is a SYNTHETIC dummy record, not a real
patient. No PHI appears in this file.

## The defect

An SMS AI agent (vendor: **Bland AI**) runs a conversational "pathway" that books eye-exam
appointments into an EMR (Eye Cloud Pro) through a self-hosted booking gateway. On 2026-08-03 a
test conversation confirmed a slot, the agent replied **"I couldn't confirm that booking. Please
call the office so they can check it for you"**, and the appointment **was created in the EMR
anyway**.

This is live on a production phone line today.

## Architecture

- Pathway version **87**, 42 nodes, of which **12 are Webhook nodes**.
- A dump of all 12 webhook nodes shows **no `timeout`, `retry`, or `retryCount` field set on any
  of them**. They inherit the platform default, whose value is unmeasured.
- The vendor catalog for these nodes specifies `default_node_settings: {"timeout_seconds": 10,
  "retry_attempts": 0}`. So either the nodes drifted from catalog intent, or the export hides UI
  defaults. Unreconciled.
- Gateway: `https://<gw-host>`, edge is **nginx** (response headers: `Server: nginx`,
  `Connection: close`, no CDN headers, so nginx is the edge directly, nothing in front).
- Endpoints, all POST JSON with a bearer token: `/patient-search`, `/appt-list`, `/availability`,
  `/conflict-check`, `/sign`.
- `/sign` is the governed write path: `{"verb":"appt.book"|"appt.cancel","target":...,"store":...,
  "reason":...,"params":{...}}`.
- Booking node order: `n_verify_1` (POST /conflict-check) then `n_book_1` (POST /sign).
- Pathway routes on `book_success` from `$.success`. Non-success routes to End node
  `e_booking_failed`.
- A July snapshot of the gateway source shows Python **`ThreadingHTTPServer` +
  `BaseHTTPRequestHandler`** behind nginx (NOT gunicorn/uwsgi, so no worker-timeout reaper),
  `ECP_CLI_TIMEOUT_S` default **90**, and **every internal timeout path returns 504**, never 502.
  nginx's own read timeout also emits 504. The EMR is driven by shelling out to a CLI; the EMR
  keeps ONE session per user, logins serialize behind an exclusive lock with a 30s re-login
  cooldown and up to a 120s login budget. **Caveat: that snapshot predates `/sign` and may not
  match the deployed build.**

## Incident timeline (UTC, 2026-08-03)

```
14:47:22.797  USER   "1"      (picks offered slot 1)
14:47:26.083  AGENT  "To confirm, your eye exam would be 08/04/2026 01:00 pm. Reply YES to book it"
14:49:09.678  USER   "Yes"
14:49:57.901  AGENT  "I couldn't confirm that booking. Please call the office..."
```

Gap from YES to failure message: **48.2 seconds**.

End state: `current_node_id: e_booking_failed`, `ended_by_end_call_node: true`,
`is_active: false`, **`BlandStatusCode: 502`**, `appt_count: 0`, `slot_conflict: false`,
`slot_count: 25`, `ok: true`, `conflict_reason: ""`.

## Proof the write committed

`/appt-list` afterward returned exactly one upcoming appointment matching the confirmed slot.
Cancelling it returned `pre_state` with `start "08/04/2026 01:00:00 pm"`, `status "created"` —
byte-for-byte the slot the patient confirmed.

## Measurement lane 1: direct reproduction (operator workstation)

Posted the identical `/sign` appt.book body directly:

- **HTTP 200, `success: true`, in 16.0s.** Rolled back cleanly.
- A second independent direct book also returned 200.
- **Two out of two direct books succeeded. Zero 502s reproduced.**

## Measurement lane 2: latency, idle vs under load

Idle gateway:
```
/appt-list        7.9s
/sign appt.book   16.0s
/sign appt.cancel 17.1s / 17.5s
```

Under load (while a 33-scenario live test harness hammered the SAME gateway), twice each:
```
/patient-search   22.0s / 21.9s      /appt-list        24.4s / 18.1s
/availability     21.5s / 23.8s      /conflict-check   19.3s / 22.0s
```

**Latency roughly triples under load, uniformly across every endpoint, including 84-byte and
121-byte responses.** That uniformity appears to rule out payload-size and buffering
explanations.

**Critical timeline overlap:** the harness run that saturated the gateway ran **14:39:06 to
~14:54**. The patient's YES was at **14:49:09**. The live booking happened inside the load window
created by our own test harness. The direct reproduction that returned 200 in 16.0s ran later,
against an idle gateway.

## Measurement lane 3: the analyst brief (a separate model lane already run)

Its leading conclusion, ~60% confidence: a **client-side webhook timeout** on the book node,
which the platform records as a synthetic 502. Its key argument is that the non-reproduction is a
**prediction** of that theory, not a puzzle: a client that waits indefinitely is structurally
incapable of reproducing a client-timeout 502, so n could be 200 and prove nothing.

It also argues that with this stack, "caller sees error, write commits" is the DEFAULT outcome
for any client less patient than the gateway: when the platform aborts, nginx logs 499 and may
close the upstream connection, but the Python handler thread only notices at response-write time
while the EMR subprocess runs to completion. Nothing has to "break."

Its ranked alternatives: genuine nginx 502 from gateway process death mid-request (~20%);
platform-internal egress blip (~10%); everything else under 5%.

Its fix ranking, lowest risk first: (1) reword the failure message so it stops asserting a
failure that did not happen; (2) set explicit timeouts of 45-60s on the book and verify nodes;
(3) add a verify-on-failure branch that calls `/appt-list` and confirms whether the slot exists,
converting commit-plus-timeout into a truthful confirmation **without retrying the write**;
(4) keep the EMR session warm to cut p95 latency; (5) REFUSE automatic retry, because `/sign` has
no idempotency key and no dedupe on (patient, slot), so retry in exactly this state double-books.

## The strongest open objection, unresolved

If a flat webhook timeout were the whole story, the earlier read nodes in the SAME conversation
(`/patient-search`, `/appt-list`, and several `/availability` calls) were also running at ~20s
under the same load and should have timed out too. **They did not.** The conversation negotiated
normally through three rounds of availability and only the write failed. That argues against a
simple flat timeout applied uniformly to all nodes, and it is not yet explained.

## Constraints on any fix

- `/sign` has **no idempotency key**; the gateway has no visible dedupe on (patient, slot).
- The vendor catalog says "Never add allow_conflict and never retry automatically."
- Changing pathway node config requires the vendor dashboard for some operations; the
  `/v1/sms/update` API returns 500 for every payload including a no-op, so repointing a line is
  dashboard-only.
- The test harness and the live patient line **share one gateway**, so running the harness during
  business hours degrades the live booking path.
