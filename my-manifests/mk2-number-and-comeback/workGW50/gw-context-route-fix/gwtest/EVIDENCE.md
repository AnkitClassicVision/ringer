# Evidence packet: Mott gateway `/patient-search` returns zero for ids that exist

All measurements below were taken directly against the live Mott booking gateway
(`https://mott-booking-gw.mail.mybcat.com`) on 2026-07-25, authenticated with the
approved Bland bearer. They are primary observations, not inferences.

## The contradiction

Patient id `675624166` **provably exists**. It was confirmed two independent ways:

1. Directly in EyeCloud via the vendor CLI: `appt patient-get --patient 675624166
   --data-source live` returned a record whose surname is two characters beginning
   `MA`. A second id, `4362694474`, also resolved, with a five-character surname
   beginning `PA`.
2. From the gateway itself. A name search returned that exact id in its result set,
   see the table below.

Yet every id-based query returns an empty result.

| Request body to `POST /patient-search` | HTTP | `ok` | `result.count` |
|---|---|---|---|
| `{"last": "MA"}` | 200 | true | **199** |
| `{"patient_id": "675624166"}` | 200 | true | **0** |
| `{"patient_id": "675624166", "profile": "contact"}` | 200 | true | **0** |
| `{"patient_id": "675624166", "store": "711"}` | 200 | true | **0** |
| `{"patient_id": 675624166}` (integer, not string) | 200 | true | **0** |
| `{"id": "675624166"}` | 200 | true | **0** |
| `{"name_last": "MA"}` | 200 | true | **0** |
| `{"last": "MA", "store": "711"}` | 400 | — | error: `unknown field 'store' for /patient-search` |

Critically: of the 199 records returned by the name search, **exactly one has
`patient_id` equal to `675624166`** — the same id the id-mode query reports zero for.
Same endpoint, same session, same underlying data.

## Shape of what the name search returns

- Record keys present: `dob`, `name_first`, `name_last`, `patient_id`.
- Record keys ABSENT: `phone_mobile`, `home_store`.
- `result.exam_type_id` is present at the envelope level.
- Returned id lengths across 199 records: 112 are 9 digits, 87 are 10 digits. The
  id being queried is 9 digits and numeric, so it is not an obvious format mismatch.

## Other live gateway state

- `GET /health` returns `ok=true` and **`test_mode=True`**.
- `POST /availability` with `{"store":"711","first_available":"1","slot_minutes":"15"}`
  returns `ok=true` with **129 slots** and a populated first start. The scheduler read
  path is healthy, so this is specific to patient resolution.
- Test mode demonstrably enforces write rules. A container log line reads:
  `refused 403: test mode: new-patient last name must start with MA`.

## The lead, which may or may not be correct

Container logs contain this line, returning HTTP 200 in 0 ms:

```
INFO patient-search short-circuit: no usable identity filters
INFO POST /patient-search -> 200 (0 ms)
```

A 0 ms response means no CLI subprocess was invoked. That log string appears in the
handler on the branch taken when `prepare_patient_search` yields a non-None "short"
value. If an id-pinned request were reaching the CLI, the response would take
hundreds of milliseconds, as the name search did (one observed name search took
1957 ms).

**Do not treat this as the answer.** Those specific log lines carry the user agent
`mott-patient-search-probe/1.0`, which is a different caller from the measurements in
the table above (user agent `mybcat-cli`). The branch is a hypothesis to confirm or
refute by reading and running the code, not an established fact.

## Why this matters

Two live Bland SMS pathways begin by resolving a patient from a trusted patient id.
While this returns zero, no recall conversation can start at all. This blocks the
campaign regardless of any pathway change.

## Scope warning

`container/bland_gateway.py` is shared code. The same container image serves a second
live client's booking lane. Any proposed change must state explicitly whether it
alters behavior for callers other than the id-pinned Mott recall path.
