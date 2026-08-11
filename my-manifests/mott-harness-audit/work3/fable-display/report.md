# Display Formatting Design

## Summary

- Add new display fields (`start_display`, `store_display`, `name_first_display`) **alongside** the existing raw fields on `/availability` and `/patient-search`; never change the raw fields, because `n_verify_1/2` and `n_book_1/2` round-trip them verbatim into `/conflict-check` and `/sign`, and a second practice (CVC) consumes the same endpoint.
- Display strings are formatted **server-side in the gateway** from the wall-clock values it already holds, using the per-store IANA timezone from store config (store `711` → `America/New_York`); the "Z"-suffixed timestamps on the related endpoint are mislabelled clinic-local and must never be parsed as UTC.
- The pathway consumes this with three added `responseData` mappings on `n_search`, one remapped path on `n_identity`, and a two-variable template edit on `n_offer`; deploy gateway first, pathway version after.

## Findings

### Finding: Patients receive raw machine dates because `/availability` has no human-readable variant

Evidence: Measured response shape `{"start": "07/27/2026 11:30 am", "end": "07/27/2026 11:45 am", "doctor_id": "859017632", "store_id": "711", "store_name": "MS"}`; `n_search` maps `$.result.slots[0].start` → `slot_1_start`; `n_offer` template interpolates `{{slot_1_start}}` directly. Prompt-side reformatting was proven impossible three times (MEASURED-EVIDENCE.md; pathway-design-rules.md "You cannot reformat an interpolated variable").
Impact: A patient reads `07/27/2026 11:30 am`, and a wrong-week date is unverifiable — nobody notices `08/03/2026` is not the week they asked for, so they miss the appointment.
Fix: Gateway adds `start_display` to every slot object. Format: `<Weekday>, <Month> <D> at <h:mm> <am|pm>`, with `, <YYYY>` inserted after the day only when the slot's year differs from the clinic-local current year. Worked examples (today is Sat 2026-07-25): same-week slot `"start": "07/27/2026 11:30 am"` → `"start_display": "Monday, July 27 at 11:30 am"`; further-out slot `"start": "08/03/2026 11:00 am"` → `"start_display": "Monday, August 3 at 11:00 am"`; cross-year slot `"start": "01/05/2027 9:00 am"` → `"start_display": "Tuesday, January 5, 2027 at 9:00 am"`. The time-of-day text must equal the raw field's time portion verbatim (see timezone finding). Pathway: `n_search` adds mappings `$.result.slots[0].start_display` → `slot_1_display` and `$.result.slots[1].start_display` → `slot_2_display`; `n_offer` template becomes "Great news, I have {{slot_1_display}} or {{slot_2_display}} at {{store_display}}. Reply 1 or 2 to take one, or tell me another day or time."
Priority: P0
Confidence: high

### Finding: Patient first name is interpolated in raw capitals from `name_first`

Evidence: `n_identity` maps `$.result.patients[0].name_first` → `patient_first`; `n_ask` and `n_reask` prompts interpolate `{{patient_first}}` ("Hi {{patient_first}}, this is Mott Optical…").
Impact: The very first message greets a lapsed patient as "Hi MARY-JANE" — it reads as spam, and first-message credibility decides whether they reply at all.
Fix: Gateway adds `name_first_display` to each patient object in `/patient-search`. Normalisation rules, applied only when the stored value contains **no lowercase letter** (a mixed-case value like `DeShawn` is human-entered — pass it through unchanged):
1. Lowercase with locale/Unicode awareness, then capitalise the first letter of each run after start, space, hyphen, and apostrophe: `MARY` → `Mary`; `MARY-JANE` → `Mary-Jane`; `D'ANGELO` → `D'Angelo`; `JOSÉ` → `José`. Naive `title()` fails the next two cases:
2. `MC` + ≥2 letters → `Mc` + capital: `MCKENNA` → `McKenna`. Do **not** apply the analogous rule to `MAC` (`MACY` → `Macy`, not `MacY`); Mac-detection miscapitalises more real names than it fixes.
3. Single letters stay capitals (`J` → `J`); strings with no cased letters (Chinese characters) pass through unchanged.
Pathway: change the existing `n_identity` mapping for `patient_first` to `$.result.patients[0].name_first_display` — no template edit needed, `n_ask`/`n_reask` keep `{{patient_first}}`.
Priority: P0
Confidence: high

### Finding: Patients are shown the internal location code, hard-coded and mismatched

Evidence: `n_offer` template hard-codes "at MK2" (Chinese form: "（地点：MK2）"), while the measured `/availability` slot carries `"store_id": "711", "store_name": "MS"` — a different code for the same conversation. Neither is a place a patient can find.
Impact: A patient told "at MK2" cannot tell where to go, and the hard-coded code silently diverges from the store the search actually ran against.
Fix: Gateway adds `store_display` (the human place name from store config) to each slot object. Pathway: `n_search` adds mapping `$.result.slots[0].store_display` → `store_display`; `n_offer` template replaces the hard-coded "MK2" with `{{store_display}}` in both language forms.
Priority: P1
Confidence: high

### Finding: Display formatting must not parse gateway timestamps as UTC

Evidence: Raw `start` values carry no offset (`07/27/2026 11:30 am`); the `n_offer` prompt states times are "America/New_York clinic local time"; the brief records that a related endpoint returns clinic-local times mislabelled with a UTC "Z" suffix.
Impact: An implementer who parses a Z-suffixed value as UTC and converts to Eastern shifts every displayed time by 4–5 hours; patients arrive hours late while the message looks perfectly formatted.
Fix: Format `start_display` from the same wall-clock value that produces `start`, treating it as clinic-local by definition. The weekday needs only the date already present. The per-store IANA zone (`store_id` `711` → `America/New_York`, from gateway store config — the only per-clinic, DST-correct source) is used solely to compute "current year" for the year-suffix rule and for any future true-instant inputs. Enforce with the test below: the time text in `start_display` must equal the raw `start` time portion byte-for-byte.
Priority: P1
Confidence: medium

### Finding: The Chinese offer message would embed an English date phrase

Evidence: `n_offer` Chinese template "好消息，我这里有 {{slot_1_start}} 或 {{slot_2_start}}…" interpolates the same variables as the English one.
Impact: A Chinese-speaking patient gets "Monday, July 27 at 11:30 am" mid-sentence in a Chinese message, defeating the weekday-recognition point of the fix.
Fix: Gateway also emits `start_display_zh` per slot (example: `7月27日（周一）上午11:30`); `n_search` maps `$.result.slots[0].start_display_zh` → `slot_1_display_zh` (and slot 2); the Chinese template uses those variables.
Priority: P2
Confidence: medium

## Clean

- The booking loop is closed and must stay closed: `n_verify_1`/`n_verify_2` and `n_book_1`/`n_book_2` send `{{slot_1_start}}`/`{{slot_1_end}}` (and slot 2) back to `/conflict-check` and `/sign` exactly as `/availability` emitted them. Keeping raw fields byte-identical means this design touches nothing on the write path.
- `n_confirm`, `n_negotiate`, `n_office`, `n_faq` interpolate no slot or name variables; no changes needed there.

**Backward compatibility argument.** Additive fields, not changed fields. (1) CVC extracts values by named JSONPath (`$.result.slots[0].start` etc.) — the same mechanism as `n_search` — so unknown sibling keys are ignored; every existing key keeps its exact format, so CVC's offers, conflict-checks and bookings are byte-identical before and after. (2) Mott's own write path round-trips `start`/`end` into `/sign`; changing `start` in place would require the gateway to parse "Monday, July 27 at 11:30 am" in booking bodies — a breaking change for both practices at once. (3) Rollout is order-safe in one direction only: deploy the gateway first (old pathways ignore the new keys), then publish pathway v42; publishing v42 first would interpolate unfilled `{{slot_1_display}}` variables (the platform substitutes unfilled variables as real nulls). Note the deployment gap already measured: Mott runs task definition 18 vs CVC's 34 — this change must actually reach Mott's task definition.

**Executable test** (staging gateway; fixture patients seeded with the names shown):

```python
import os, re, datetime, requests
GW = os.environ["GW_URL"]; H = {"Authorization": os.environ["GW_TOKEN"],
                                "Content-Type": "application/json"}

def test_availability_display():
    r = requests.post(f"{GW}/availability", headers=H, json={
        "store": "711", "from": "monday", "to": "friday",
        "after": "none", "before": "none", "time_pref": "none",
        "slot_minutes": "15"}).json()
    assert r["ok"] and r["result"]["count"] >= 1
    for s in r["result"]["slots"]:
        assert re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{1,2}:\d{2} [ap]m", s["start"])  # raw unchanged
        d = datetime.datetime.strptime(s["start"], "%m/%d/%Y %I:%M %p")
        assert s["start_display"].startswith(d.strftime("%A"))          # weekday matches date
        assert s["start_display"].endswith(s["start"].split(" ", 1)[1]) # wall time preserved, no UTC shift
        assert s["store_display"] and s["store_display"] not in ("MS", "MK2", s["store_id"])

def test_patient_name_display():
    cases = {"MARY": "Mary", "MARY-JANE": "Mary-Jane", "D'ANGELO": "D'Angelo",
             "MCKENNA": "McKenna", "MACY": "Macy", "JOSÉ": "José", "DeShawn": "DeShawn"}
    for raw, want in cases.items():
        r = requests.post(f"{GW}/patient-search", headers=H, json=FIXTURES[raw]).json()
        p = r["result"]["patients"][0]
        assert p["name_first"] == raw and p["name_first_display"] == want

def test_cvc_contract_unchanged():
    golden = load_recorded_cvc_response()          # recorded before the change
    now = requests.post(f"{GW}/availability", headers=H, json=golden["request"]).json()
    for i, slot in enumerate(golden["response"]["result"]["slots"]):
        for k, v in slot.items():                  # old keys: present and identical
            assert now["result"]["slots"][i][k] == v
```

## Assumptions

- The mislabelled-UTC endpoint's identity comes from the brief, not MEASURED-EVIDENCE.md; the design is safe either way because it never converts timezones.
- CVC's pathway extracts by named JSONPath and ignores unknown keys — same platform mechanism as `n_search`, but CVC's graph was not in the staged evidence; `test_cvc_contract_unchanged` is the proof.
- Gateway store config has (or can be given) a human display name and IANA timezone per `store_id`; the actual place name behind code `MS`/store `711` must come from the practice — "Mott Street" below is a placeholder.
- Patient first names are stored uniformly upper-case; the no-lowercase guard makes the normaliser a no-op if that assumption fails.

## Proposed Contract

`POST /availability` (additions marked; all existing fields byte-identical):

```json
{
  "ok": true,
  "result": {
    "count": 2,
    "time_pref_relaxed": false,
    "slots": [
      {
        "start": "07/27/2026 11:30 am",
        "end": "07/27/2026 11:45 am",
        "doctor_id": "859017632",
        "store_id": "711",
        "store_name": "MS",
        "start_display": "Monday, July 27 at 11:30 am",
        "start_display_zh": "7月27日（周一）上午11:30",
        "store_display": "Mott Street"
      },
      {
        "start": "08/03/2026 11:00 am",
        "end": "08/03/2026 11:15 am",
        "doctor_id": "859017632",
        "store_id": "711",
        "store_name": "MS",
        "start_display": "Monday, August 3 at 11:00 am",
        "start_display_zh": "8月3日（周一）上午11:00",
        "store_display": "Mott Street"
      }
    ]
  }
}
```

`POST /patient-search` (addition: `name_first_display`):

```json
{
  "ok": true,
  "result": {
    "count": 1,
    "exam_type_id": "comprehensive",
    "patients": [
      {
        "patient_id": "P-102938",
        "name_first": "MARY-JANE",
        "name_first_display": "Mary-Jane"
      }
    ]
  }
}
```
