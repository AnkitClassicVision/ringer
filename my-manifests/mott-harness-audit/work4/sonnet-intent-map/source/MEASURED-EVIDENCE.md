# Measured evidence, 2026-07-25

Everything here was executed against the live gateway and the live pathway. None of it is
inferred. Treat it as fact; do not re-derive it and do not contradict it without new
measurements of your own.

## The extraction problem

The negotiation step captures five fields from the patient's own words. They are captured
by the platform's variable-extraction config, one description per field, run by a small
model. The same input does not always produce the same capture.

Six identical runs of the reply **"next week in the morning please"** against version 38:

| runs | preference_from | preference_to | preference_after | preference_before | time_pref | outcome |
|---|---|---|---|---|---|---|
| 4 of 6 | `monday` | `friday` | `none` | `none` | `morning` | openings offered |
| 2 of 6 | `next week` | `next week` | `morning` | `morning` | `morning` | HTTP 409, conversation died |

Two separate faults in the failing runs: the literal phrase "next week" reached the date
fields, which the schedule cannot parse, and the word "morning" was also written into the
clock-time fields, where it does not belong.

A later run on version 41 produced a third variant: the reply **"after 3pm"** with no day
named put the literal string `after 3pm` into BOTH date fields.

Three rounds of tightening the field descriptions have moved the failure rate without
eliminating it. That is the signature of a problem that needs a different mechanism, not
better wording.

## What the schedule actually accepts

Measured directly against `/availability` on the live Mott gateway.

| phrase | result |
|---|---|
| `monday`, `next monday`, `mon`, `tuesday` | accepted, resolves to the next such weekday |
| `tomorrow`, `august 3`, `08/03/2026`, `2026-08-03` | accepted |
| `next week`, `this week`, `in 2 weeks`, `next month` | **rejected**, HTTP 409 |
| `day after tomorrow`, `in 3 days`, `this weekend` | **rejected**, HTTP 409 |

A range of two weekday words works: `from: monday, to: friday` returned 126 openings
across Monday to Friday. `time_pref: morning` narrows that to 24.

Optional fields must be strings. Sending JSON `null` returns HTTP 400
`field 'after' must be a string`. The platform substitutes an unfilled variable as a real
`null`, which strips the quotes out of the request body. The literal word `none` is
accepted and ignored, so it is the current sentinel for "not specified".

## The deployment gap behind all of this

The gateway ALREADY contains a deterministic resolver that handles every rejected phrase
above, including the Chinese equivalents. It is in `resolve_relative_date`, and
`/availability` already runs both `from` and `to` through it.

It is not running on Mott. The two services are on different task definitions:
CVC on 34, Mott on 18. Every resolver-only phrase 409s on Mott and would resolve on CVC.

## The display problem

`/availability` returns times as pre-formatted strings with no human-readable variant:

```json
{"start": "07/27/2026 11:30 am", "end": "07/27/2026 11:45 am",
 "doctor_id": "859017632", "store_id": "711", "store_name": "MS"}
```

Patients therefore receive `07/27/2026 11:30 am` rather than a weekday they would
recognise, a first name in raw capitals as the practice system stores it, and an internal
location code.

This CANNOT be fixed in a prompt. The platform substitutes an interpolated variable
directly into the message and the model never gets a chance to reformat it. That has been
proven three separate times across three versions. Any fix has to change what the gateway
returns, or add a field alongside it.

A wrong date is not only ugly, it is unverifiable by the patient: nobody reads
`08/03/2026 11:00 am` and notices it is the wrong week.
