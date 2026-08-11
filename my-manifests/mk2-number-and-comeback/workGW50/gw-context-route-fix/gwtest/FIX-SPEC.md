# Gateway fix: `/patient-search` returns empty for patients that exist

Written for whoever lands this. **No file in `cvc-booking-gateway` was modified.**
That repo had uncommitted changes to `container/bland_gateway.py` at the time this
was written, so a patch would likely have conflicted with work not visible here.

## What is broken

`POST /patient-search` resolves patients by name but returns an empty result for
every query by `patient_id`, including ids that appear in its own name-search
results.

Measured live on 2026-07-25 against `mott-booking-gw.mail.mybcat.com`:

| Request body | HTTP | `ok` | `result.count` |
|---|---|---|---|
| `{"last": "MA"}` | 200 | true | **199** |
| `{"patient_id": "675624166"}` | 200 | true | **0** |
| `{"patient_id": "675624166", "profile": "contact"}` | 200 | true | **0** |
| `{"patient_id": "675624166", "store": "711"}` | 200 | true | **0** |
| `{"patient_id": 675624166}` (integer) | 200 | true | **0** |
| `{"id": "675624166"}` | 200 | true | **0** |

**One of those 199 name-search records carries `patient_id` equal to `675624166`.**
Same endpoint, same session, same data. The patient was independently confirmed
present in EyeCloud via `appt patient-get --patient 675624166 --data-source live`.

Ruled out by measurement, not assumption:

- **Not test mode.** An id that is *not* allowlisted returns `403 test mode:
  patient_id is not allowlisted`. We get `200 count=0`, so the id clears the gate.
- **Not the gateway being down.** `/availability` for store 711 returns 129 real
  slots with a populated first start.
- **Not missing data.** Both candidate ids resolve in EyeCloud directly.
- **Not an id-space mismatch.** The queried id matches a returned id exactly.

## Root cause

Three independent diagnoses converged, using three different methods.

**Part one — the direct read omits the live data-source selector.**
`build_patient_get_argv` produces:

```
[CLI, "appt", "patient-get", "--agent", "--reason", "bland-patient-get", "--patient", <id>]
```

There is no `--data-source`, so the CLI uses its default `auto` mode, described in
its own help as "live with local fallback". The local path opens a SQLCipher
database. A CGO-disabled build of that CLI fails there with
`verifying SQLCipher key: Binary was compiled with 'CGO_ENABLED=0'` — reproduced
directly while investigating. The invocation proven to work passes
`--data-source live` explicitly.

**Part two — the handler reports that failure as a success.**
On the pinned-id branch, a timeout, a nonzero exit, or a zero-exit response that
parses to nothing all reach `patient_get_envelope` and produce `HTTP 200` with
`result.count: 0`. A broken lookup and a genuine no-match are indistinguishable to
every caller.

Part two is the more serious defect. Part one is the current trigger; part two is
what makes any future trigger silent.

**Why the tests never caught it.** `tests/test_id_pinned_search.py` does two things
that guarantee it cannot. It injects a successful CLI result regardless of argv:

```python
self.get = Mock(return_value={"patient_id": "222", "name_first": "Target"})
```

and then asserts the argv **without** the live selector, encoding the bug as the
expected behaviour:

```python
[self.gateway.CLI, "appt", "patient-get", "--agent", "--reason",
 "bland-patient-get", "--patient", "222"]
```

It also reimplements the handler in a local `run_search` helper rather than going
through `Handler.do_POST`, so the real routing is never exercised.

## The change

1. **`build_patient_get_argv`** — add `--data-source live` to the argv.

2. **The pinned-id failure path** — stop mapping a failed direct read to
   `200 count=0`. Either return a distinct upstream error, or carry a signal on the
   envelope that lets a caller tell "lookup failed" from "no such patient".

## Blast radius, which is the part to think about

`container/bland_gateway.py` is shared. The same image serves a second client's
booking lane. Both diagnosis lanes flagged this independently and unprompted:

> "Changing patient-get fail-soft (200 empty) to hard errors, or altering
> prepare_patient_search/id routing, changes behavior for every tenant on this
> image, not only Mott recall."

Change 1 is low risk — it makes an existing invocation explicit about a source it
was already meant to read. Change 2 changes error semantics for every caller, so
anything downstream currently treating `count: 0` as "not found" will now see an
error it must handle.

There is no tenant branch in this handler today. If change 2 needs to be scoped to
one client, that scoping does not exist yet and would have to be built.

## Verification

`test_id_pinned_search_regression.py` in this directory drops into `tests/`. It is
written to fail against the current code and pass after the fix. Three groups:

- the argv selects the live data source
- a behaviour-faithful CLI fake, which answers only when `--data-source live` is
  present, resolves an existing patient through the pinned path
- a failed direct read is distinguishable from a genuine no-match

After landing, the live check is one call: `POST /patient-search` with
`{"patient_id": "675624166", "profile": "contact"}` should return `count: 1` with
`phone_mobile` and `home_store` populated.

## One more thing the recall lane needs

The working name search returns only `dob`, `name_first`, `name_last`,
`patient_id`. It does **not** return `phone_mobile` or `home_store`. The recall
pathway gates on the patient id, the mobile, the home store and an exam type all
being present, so restoring the id lookup without those fields still leaves it
exiting at the identity guard. Worth confirming the `profile=contact` payload
returns the full set.
