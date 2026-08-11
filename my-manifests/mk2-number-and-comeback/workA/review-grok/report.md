# v62 design review — patient experience & copy integrity

Scope: Ankit’s closing-number + post-booking deferral. Emphasis: what the patient reads on their phone; collisions with warmth/bilingual/NO_CLAIM; come-back under unmeasured Bland End Call behavior. Quotes from `./source/build_v61.py` / graph unless noted.

---

## 1. CHANGE LIST

Phone lock: `(212) 219-2219` replaces `(855) 750-6688` in all eleven carriers. Pre-booking `n_office` / `n_faq` keep answer-then-steer-back (`BACK`); only post-booking requests get the mandated deferral.

### The eleven number carriers

| Node | Current (v61) | Proposed v62 |
|---|---|---|
| **n_confirm** | TASK: confirm booked time with warmth (“Great, you're all set for…”); “If the patient then asks to change, cancel or move it, give them the office number **(855) 750-6688** and explain the office will take care of it.” (model-composed) | Keep time confirmation + warmth as sole positive-claim surface (NO_CLAIM monopoly). **End confirmation with mandated close, verbatim:** `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219`. Remove free-compose follow-up handoff; same-thread asks after success → deferral node, not paraphrase. ZH equivalent under `LANG_REPLY`. Retain “Never go back to searching, verifying or booking after this point”. |
| **n_office** | “Give the office number **(855) 750-6688**…” + `BACK` | Number → `(212) 219-2219`. Pre-booking behavior unchanged. **Must not** be post-book landing (today `n_confirm` → `n_office` on change-after-confirm re-opens the book loop). |
| **n_faq** | Insurance/cost deferral; office number **(855) 750-6688** + `BACK` | Number only. Keep `BACK` + `NO_PRICE` + `NO_CLAIM` + `LANG_REPLY`. Pre-booking only; do not use for post-book asks. |
| **e_safe_identity** | `I couldn't safely continue this scheduling request. Please call Mott Optical at (855) 750-6688.` | Same sentence, new number (or Ankit brand pick — §5). End Call. |
| **e_safe_failure** | `I couldn't access scheduling right now and no appointment was booked. Please call Mott Optical at (855) 750-6688.` | New number. Keep “no appointment was booked” (honest negative claim). |
| **e_booking_failed** | `I couldn't confirm that booking. Please call Mott Optical at (855) 750-6688 so they can check it for you.` | New number. Keep hedge (signer may have committed). |
| **e_office** | `Please call Mott Optical at (855) 750-6688.` | New number. |
| **e_declined** | `Ok, thank you for letting us know. If you need anything, call the office at (855) 750-6688.` | New number. Optional brand align. |
| **e_stop** | `Understood. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it.` | New number only. Do not promise suppression recorded. |
| **e_not_me** | `Sorry about that. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it.` | New number. Keep no-name / no-appointment leak. |
| **e_existing** | `Please call Mott Optical at (855) 750-6688 and the office can help with that appointment.` | New number. Pre-campaign existing-appt path only — do not overload as post-book deferral. |

### Close path and identity

| Node | Current | Proposed |
|---|---|---|
| **e_booked** | `Thank you. We look forward to seeing you.` | **Do not** put mandated “You're all set…” here. Gate invariant 5 fails `e_booked` on `you're all set` / `booked`. Patient already got close at end of **n_confirm**. Keep short non-claim thank-you for bare thanks/ok; no second number. |
| **n_identity** | Silent `/patient-search`; maps `ok`, `count`, `patient_first`, `patient_id`, `exam_type_id`. `isStart: true`. | No patient-visible copy. For come-back: extend mapping with booking-state field (§2); if already booked this campaign → End/Default that sends **only** the mandated deferral, never `n_ask`. |

### New / rewired post-book surfaces

| Node / edge | Why | Patient-visible |
|---|---|---|
| **New `e_post_book` (End Call)** | Same-thread ask after `n_confirm` success | Verbatim: `For that you'll have to contact the MK2 Optical office at (212) 219-2219` |
| **Rewire** `n_confirm` → `n_office` | `n_office`+`BACK` re-pitches after real booking — cold, contradictory, double-book risk | → `e_post_book` |
| **Optional `n_post_book` Default** | Discriminate thanks vs ask before End | thanks → `e_booked`; ask → deferral once, then end. Never search/verify/book. |

**Success SMS structure (phone view):**

1. `n_confirm` single bubble — avoid double “you're all set”:  
   `Great — your eye exam is {{time}} at MK2. You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219`  
   Mandated **ending** verbatim; warmth without repeating “all set” as opener *and* closer. One claim, one number.
2. Patient “thanks” → `Thank you. We look forward to seeing you.` (`e_booked`) — warm, no re-claim.
3. Patient any ask → **only** `For that you'll have to contact the MK2 Optical office at (212) 219-2219` — not `n_office` handoff+steer-back, not a second “you're all set”.

**Bilingual:** `LANG_REPLY` on Defaults. Fixed End Call strings in v61 are English-only. For ZH threads, prefer Default that can emit ZH then silent End; or accept EN fixed ends (current pattern). Number digits stay ASCII. ZH mandated lines need ops sign-off if required.

**NO_LEAK / NO_CLAIM:** Close/deferral must not mention `new_appt_id` or gateway fields. Pure deferral does not re-assert booking. Gate may allow “You're all set” on `n_confirm`’s mandated tail only — not on `e_booked`.

---

## 2. COME-BACK DESIGN

### Same thread (measured topology)

After `book_success == true` → `n_confirm` (`userWait` true). Edges today: confirmation delivered / 72h silence → `e_booked`; change requested → `n_office`.

**v62 reply classes at `n_confirm`:**
- ack / thanks / silence-timeout → `e_booked`
- any substantive ask → one deferral SMS → End
- never → `n_search` / verify / book / `n_office`+`BACK` / `n_faq`+`BACK`

Covers “later in the same thread” without End Call magic.

### Text-back into a finished thread (UNMEASURED)

Facts only:
- Outbound: Bland `/v1/sms/send` with `new_conversation: true`, `start_node_id`, `request_data` (`CONTEXT.md`).
- `n_identity` is sole `isStart: true`.
- `e_booked` is `End Call`.
- **Inbound SMS after End Call: unknown in `./source`.**

| Plausible behavior | Risk | Fail-safe |
|---|---|---|
| **P1. Re-enters at `isStart` (`n_identity`)** | count==1 → `n_ask` → second exam | Gateway campaign-booked flag; route to deferral End before `n_ask` |
| **P2. Inbound ignored / dead** | Patient texts, gets nothing | No double-book; close already gave the number |
| **P3. New conversation at start** | Same as P1 if identity resolves | Same gateway flag |
| **P4. Globals still match after End** | `n_office`/`n_faq` could steer back to booking | Do not rely on globals for post-book; if probes show globals live, narrow labels to pre-book only |

### Empirical probes (before trusting any mechanism)

1. **Post-End inbound:** Book test patient to `e_booked`; send “can I reschedule?”; capture session open, `start_node_id`, `request_data` survival, SMS sent.
2. **Global-after-End:** After `e_booked`, send `STOP` and “wrong number”; see if `e_stop`/`e_not_me` fire.
3. **new_conversation:** Inbound on original conversation id vs after fresh `/v1/sms/send` with `new_conversation: true`.
4. **Identity replay:** If P1/P3, confirm new booked field flips after `/sign` success.

### Gateway vs Bland-only

| Approach | Pros | Cons |
|---|---|---|
| **Extend `/patient-search`** with `campaign_booked` | Works under P1/P3; fail-closed at `isStart`; no End dependence | Second deploy; define campaign key |
| **Bland parked node** (never End) | Same-thread asks work | 72h `e_timeout` still ends; post-timeout unknown |
| **Bland global post-book deferral** | Elegant if globals survive End | Unmeasured; no booked-state without gateway |
| **Deferral only on close + hope patient calls** | Matches close | Does not satisfy “texting back gets deferral” |

**Recommendation: gateway extension + identity branch**, plus Bland same-thread rewire.

- `n_identity`: booked flag true → `e_post_book` and stop; else existing routes.
- Until gateway field ships, do not market come-back SMS as handled; close line degrades to P2 safely.
- Do not use pathway memory of “said thanks” as cross-conversation booked signal.

**Sequences:**

```
Bot (n_confirm): Great — your eye exam is <time> at MK2. You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219
Patient: thanks
Bot (e_booked): Thank you. We look forward to seeing you.
```

```
Bot (n_confirm): [same close]
Patient: can I come Wednesday instead?
Bot (e_post_book): For that you'll have to contact the MK2 Optical office at (212) 219-2219
```

```
# Come-back after End (P1 + gateway field)
Patient: hi, what time is my appointment?
Bot: For that you'll have to contact the MK2 Optical office at (212) 219-2219
```

Slightly cold for “what time?” but mandated; better than re-opening recall pitch. No second number, no steer-back, no re-claim.

---

## 3. SCENARIO ADDITIONS

| name | intent | expect |
|---|---|---|
| `post_book_close_mandated_tail` | Happy book through confirm | node ∈ {`n_confirm`,`e_booked`}; text has mandated close; reject old number |
| `post_book_extra_ask_same_thread` | After success: “can I reschedule to Friday?” | `e_post_book`; exact deferral; reject re-offer / re-search |
| `post_book_thanks_not_deferral` | After success: “thanks” | `e_booked`; `look forward`; reject deferral line |
| `post_book_faq_no_steer_back` | After success: insurance ask | deferral only; reject `BACK`-style re-ask |
| `text_back_after_close_already_booked` | Identity returns booked flag; “can I move it?” | deferral end; never `n_ask` opener |
| `text_back_after_close_not_booked` | count==1, not booked | still books (regression) |
| `pre_book_office_still_steers` | “are my glasses ready?” before book | `n_office`/`n_ask`; number **212**; booking goal alive |
| `pre_book_faq_number_and_back` | insurance pre-book | pre-book loop; new number; not sole post-book deferral |
| `no_two_numbers_one_thread` | full book + mid-way office ask | reject `855` entire thread |
| `stop_after_book_still_suppresses` | book then STOP | `e_stop`; new number; path unchanged |
| `wrong_person_unchanged` | NOT ME | `e_not_me`; no name leak |
| `chinese_post_book_deferral` | ZH book then ZH ask | ZH if Default path else documented EN end; `212`; no EN opener reinjection |
| `never_rebook_after_success_edge` | after confirm, “book tuesday instead” | deferral; never `n_book_*` |
| `e_existing_prebook_still_works` | move existing appt before campaign book | `e_existing`; new number |

Update existing cases that `expect_text: '855'` (e.g. order/glasses asks) → `212` or `office|staff|212`.

---

## 4. GATE AND REDPROOF ADDITIONS

### `check_candidate_gate.py`

1. **`old_number_absent`:** zero `855) 750-6688` / `855-750-6688` / `8557506688` in any `prompt` or `text`.
2. **`new_number_on_eleven`:** each of the eleven ids carries `(212) 219-2219`.
3. **`mandated_close_on_confirm`:** `n_confirm` includes verbatim `You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219`.
4. **`mandated_deferral_node`:** some End/Default (e.g. `e_post_book`) has verbatim `For that you'll have to contact the MK2 Optical office at (212) 219-2219`.
5. **`post_book_no_back`:** no edge `n_confirm` → `n_office` / `n_faq` / `n_search` / `n_negotiate` / `n_book_*`. Allowed: `e_booked`, deferral end, timeout.
6. **`no_rebook_after_confirm`:** `n_confirm` outbound ∩ `{n_search,n_verify_1,n_verify_2,n_book_1,n_book_2,n_gate_1,n_gate_2}` = ∅.
7. **NO_CLAIM adjust:** positive claim on `n_confirm` only; keep forbidding claim language on `e_booked`. Deferral “contact the office” is not a claim.
8. **`identity_booked_branch` (once gateway ships):** `n_identity` responseData includes new field; pathway to deferral when true. Until then skip/warn — do not pretend field exists in v61.
9. Keep scenario-inventory discipline as suite grows.

### `redproof_run.py` mutations

| mutation | proves |
|---|---|
| restore `(855) 750-6688` on any of the eleven | `old_number_absent` |
| strip mandated close from `n_confirm` | `mandated_close_on_confirm` |
| strip deferral from `e_post_book` | `mandated_deferral_node` |
| rewire `n_confirm` → `n_office` | `post_book_no_back` |
| add `n_confirm` → `n_search` | `no_rebook_after_confirm` |
| append “Your appointment is booked.” to `e_booked` | existing second-claim rule |
| remove booked-flag pathway from `n_identity` (when present) | `identity_booked_branch` |
| put old number only in `n_faq` | still caught (global zero-old) |

Clean candidate passes; each mutation fails.

---

## 5. REGRESSION RISKS

| Invariant | Risk | Mitigation |
|---|---|---|
| **NO_CLAIM** | Mandated “You're all set” is a claim; duplicating on `e_booked` breaks gate + trust; warmth+tail can double-phrase “all set” in one bubble | Close only on `n_confirm`; one bubble (§1); `e_booked` non-claim |
| **Never rebook after success** | `n_confirm` → `n_office`+`BACK` is a foot-gun; come-back at `n_identity` without flag restarts `n_ask` | Rewire edges; gateway flag; gate on edges; scenarios |
| **Bilingual** | EN End Call after ZH confirm is jarring; ZH invite must stay opener-only | Prefer Default for ZH deferral; never re-attach `ZH_INVITE` on close |
| **STOP / wrong-person** | Number swap OK; risk is post-book globals broader than STOP, or come-back skipping suppression | Probes §2; keep `n_suppress_*` before `e_stop`/`e_not_me` |
| **NO_PRICE / FAQ** | Post-book insurance must not invent coverage | Route post-book to deferral, not `n_faq` |
| **NO_LEAK** | Confirm edits might tempt appointment ids | Gate/prompt never |
| **Pre-book conversion** | Over-eager defer-everything kills `n_office`/`n_faq` steer-back | Deferral post-booking only; gate that `BACK` remains on those prompts |
| **Scenario drift** | Suite hard-codes `855` in ≥2 cases | Update with number change |

### Brand: Mott Optical vs MK2 Optical

- 26-style copy introduces **“Mott Optical”** (WORLD, OPENER_EN, safe ends).
- Booking geography: **“at the MK2 office”** / “at MK2”.
- Mandated v62 lines: **“MK2 Optical”**.

**One successful thread:** opener “this is **Mott Optical**” → offers “at **MK2**” → close “call **MK2 Optical**” = two practice names + nickname. Reads like a handoff.

**Ankit’s call — pick one public brand:**
- **A — Mott Optical everywhere:** change mandated lines (requires unlock).
- **B — MK2 Optical everywhere patient-facing:** opener + safe ends + WORLD → MK2 Optical.
- **C — hybrid gloss once:** “Mott Optical (MK2 office)” then one name — still avoid Mott opener + MK2 Optical close without gloss.

**Reviewer pick:** **B** if MK2 is store brand on mandated lines; else **A** if Mott is SMS-registered sender. Until decided, ship number + locked mandated strings; do not invent a third variant. Remaining Mott/MK2 mix is accepted debt only with Ankit sign-off.

---

## Decisions summary

1. Mandated **close** ends **`n_confirm`** (claim monopoly, one bubble); **`e_booked`** stays non-claim thank-you.
2. New **post-book deferral end**; cut **`n_confirm` → `n_office`**; never `BACK` after success.
3. **Gateway `campaign_booked` on `/patient-search`** + `n_identity` branch = only come-back that fail-closes under re-entry; Bland End inbound **unknown** until probes 1–4.
4. Gate: zero old number, verbatim mandated strings, no post-confirm book edges; redproof each rule.
5. Mott vs MK2 is a real PX bug — **Ankit chooses**; eng must not invent a third name.
