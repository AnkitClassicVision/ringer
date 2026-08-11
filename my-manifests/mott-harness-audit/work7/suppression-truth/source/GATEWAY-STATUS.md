# Mott gateway status — for the pathway agent

**STATUS: UP, and significantly more capable than earlier today.**
_Last verified 2026-07-25 18:30 ET by live probe, not by assumption._

Running image `mott-lane-10`, ECS task definition 23.

## THREE THINGS CHANGED THAT AFFECT YOUR NODES

**1. Patient contact and demographic fields are now LIVE.** The earlier warning not to
build on `phone_mobile` is withdrawn. `/patient-search` with `"profile": "contact"` now
returns `phone_mobile` populated, and `"profile": "full_demographics"` returns address,
address_2, city, state, zip, country, gender, gender_identity, name_middle and
name_preferred, plus a `profile` / `query_mode` / `sensitive_withheld` envelope.

**2. `home_store` now resolves to `MS`** instead of coming back empty. Nodes no longer
need the literal `711` workaround for that field, though `711` remains the store id you
send.

**3. `/appt-list` now accepts `last`, `dob`, `from`, `to` and `include_past`.** Previously
only `patient_id` worked and the rest returned 400.

## BOOKING IS NO LONGER ONE-WAY

`appt.cancel` and `appt.reschedule` are granted and proven working end to end: a real
appointment was booked and cancelled today, confirmed gone from `/appt-list`.

**Critical contract detail, it cost three failed attempts to find.** For the appt-key
verbs (`appt.cancel`, `appt.reschedule`, `appt.modify`) the `/sign` `target` field must be
the **APPOINTMENT ID**, not the patient id. Booking is the opposite: `appt.book` takes the
patient id as `target`.

Working cancel call:

`{"verb": "appt.cancel", "target": "<APPOINTMENT_ID>", "store": "711", "reason": "patient-request", "params": {"appt_id": "<APPOINTMENT_ID>", "day": "MM/DD/YYYY"}}`

A 422 `bad_request` means the appointment could not be resolved. It does **not** mean the
verb is ungranted: the dispatcher resolves the target against the EMR before it ever
checks authorization, so a 422 tells you nothing about permissions. An ungranted verb
returns 403 `authorization_denied`.

## `/sms-suppression` now exists

`{"phone_e164": "+1...", "reason": "stop", "source": "sms_reply"}`. Verified: records 200,
repeats return 200 without losing the original timestamp, a malformed phone returns 400,
an unknown reason returns 400, and the response never echoes the number. Valid reasons are
`stop`, `unsubscribe`, `complaint`, `manual`. Valid sources are `sms_reply`, `voice`,
`manual`, `import`.

**Wire your `e_stop` and `e_not_me` nodes to call it before ending.** Until now a patient
replying STOP was acknowledged and then forgotten, so the next campaign would text them
again.

## What was verified just now

| Probe | Result |
|---|---|
| `GET /health` | 200 |
| `/patient-search` contact profile | `phone_mobile` present and non-empty |
| `/patient-search` full_demographics | all 10 fields present, `home_store` = `MS` |
| `/appt-list` five request fields | all accepted |
| `/sign` `appt.book` past-dated | 409 `slot_conflict`, a real decision |
| `/sign` `appt.book` then `appt.cancel` | 200, `success: true`, appointment gone |
| `/sms-suppression` | 200, idempotent, 400 on bad input, no echo |

## Still true, do not forget these

- **`patient_id` without `phone`** returns `count: 0` in zero milliseconds with HTTP 200.
  It reads as "patient not found". It is not. Always send both.
- **Relative dates are rejected.** "next week" returns 409. Resolve dates in the pathway
  and send concrete `MM/DD/YYYY`.
- **A 200 on `/health` does not mean booking works.** It returned 200 for eight minutes
  today while every `/sign` failed. Exercise `/sign` if you need to know.
- **Set webhook node timeouts above 30 seconds for `/sign`.** Measured: availability
  about 9s, patient search 7 to 12s, `/sign` 12 to 27s, slowest in the first minute after
  a deploy.
- **A 409 on a read mentioning an unexpected `<`** is the upstream EMR returning HTML.
  Transient. Retry once rather than reporting "no appointments".

## `/book-new-patient` is LIVE as of 2026-07-26, and UNTESTED

Owner decision 2026-07-26: leave it on, test at a later stage. Read this before you build
a node against it.

It takes 17 fields: `first`, `last`, `dob`, `phone`, `email`, `gender`, `addr`, `city`,
`state`, `zip`, `ssn_last4`, `store`, `doctor`, `start`, `end`, `type`, `notes`.

Verified: the route is reachable, requires the bearer, and rejects unknown fields with
400. **Not verified: that a registration actually succeeds.** No patient has ever been
created through it. The first real call will be the first test.

Four things that make it different from every other write:

- It goes shim-side, **not** through the conductor. `appt.book_new_patient` returns
  `unknown_verb` on `/sign`, so this route is the only path. That means no audit row, no
  verb grant, no kill switch and no post-write verification.
- **A duplicate patient cannot be deleted through any API.** A mistake here is a phone
  call to Mott, not a rollback.
- The CLI runs **dry unless you send `confirm: true`** on that specific request. Sending
  it is the moment a real record is created.
- Rate limiting is `1r/m` with `burst=3`, but the nginx zone keys on
  `$binary_remote_addr` with no `real_ip` config, so the bucket belongs to the ALB node,
  not to you. Measured 2026-07-26: 6 requests passed before 429s appeared, spread across
  three ALB addresses. Treat it as roughly 3 per minute gateway-wide, shared with anything
  else calling the route.

## `/sign` verb grant, verified 2026-07-26

Granted: `appt.book`, `appt.cancel`, `appt.reschedule`. **Not granted: `appt.modify`.**
Store 711 in scope, patient allowlist empty so any Mott patient is bookable. Every
attempt writes an audit row, denials included.

An ungranted verb returns 403. An unknown verb returns 422 `unknown_verb`. For appt-key
verbs the target is resolved against the EMR **before** authorization is checked, so a
422 tells you nothing about permissions.

## Still not available

`/query` is release-gated to BLOCK. `/message` returns 503, no SES sender configured.
`phone_home`, `phone_work` and `email` came back empty for the test patient; that may be
missing data rather than a gap, and has not been confirmed against a second patient.

## Full contract

`WEBHOOK-CONTRACT-FOR-PATHWAY.md` in this directory. Note its traps 2, 3, 5 and 6 are now
superseded by this file.
