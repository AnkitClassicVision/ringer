# Request contract

`POST /availability` ultimately invokes `appt availability`. Its CLI-backed whitelist is `store`, `from`, `to`, `doctor`, `min_minutes`, `slot_minutes`, `after`, and `before`. The gateway additionally consumes the control fields `time_pref`, `first_available`, and `callID` before strict whitelist validation. Unknown remaining fields fail the request. `date_conflict` and `either_days` are internal-only signals; caller-supplied values are discarded.

| Request field | Contract |
|---|---|
| `from` | Start of the date search. It may be an `MM/DD/YYYY` date or text accepted by `resolve_relative_date`. If it cannot be resolved, the clamp returns without rewriting either date. If raw-text authority resolves a date, this caller value is overwritten. |
| `to` | End of the search. It is resolved through `resolve_relative_date` only after `from` resolves. Missing, invalid, or earlier than `from` becomes the same day as `from`. A range longer than 14 calendar days inclusive is capped to `from + 13 days`. Raw-text authority overwrites it along with `from`. |
| `after` | Explicit lower clock-time bound passed as `--after`, except `""` and case-insensitive `"none"`, which mean absent and are removed. In the LLM-intent v2 source, an explicit non-`none` `after` outranks `time_pref`, so no band-derived `--after`/`--before` is added. The raw-text-authority v2 source lacks that guard and can apply both. |
| `before` | Explicit upper clock-time bound passed as `--before`, except `""` and case-insensitive `"none"`, which mean absent and are removed. Unlike `after`, it does not suppress `time_pref`; a band and explicit `before` may both constrain the query. |
| `time_pref` | Lowercased and consumed by the gateway. Recognized bands become CLI time bounds; unknown/empty values add no bound. In LLM-intent v2: `morning` = before noon, `afternoon` = after noon, `evening` = after 4:00 pm, and `late` = after 3:00 pm. Raw-text-authority v2 honors only `morning`, `afternoon`, and `evening`. |
| `slot_minutes` | Passed unchanged as `--slot-minutes`; it requests the appointment-slot duration. It must be a string or integer under generic validation. |
| `first_available` | Truthy only for stringified, case-insensitive `1`, `true`, or `yes`. It bypasses raw-text authority and replaces `from`/`to` with tomorrow through six days after tomorrow, in Eastern clinic time, then returns from the clamp. It is consumed and never sent to the CLI. Any other value behaves as false. |
| `callID` | Consumed on every availability call. When raw dates are enabled, tenant is `mott`, it is nonempty, and `first_available` is false, it is used to fetch the Bland conversation. It never reaches the CLI. A valid fetch ID must match `[A-Za-z0-9-]{8,64}` and contain at least eight alphanumerics. |

The actual endpoint also accepts `store` (forwarded as `--store`), `min_minutes` (forwarded as `--min-minutes`), and syntactically `doctor`. However, availability forces the configured doctor for the selected store and discards a caller-supplied doctor when a configured mapping exists. Empty values are skipped; values must be strings or integers, must not begin with `-`, and must fit the gateway length limit.

Precedence, highest first:

1. A truthy `first_available` wins over both conversation authority and caller `from`/`to`.
2. Otherwise, an engaged raw-text authority result overwrites only `from` and `to` (or produces internal conflict/either-day routing signals in LLM-intent v2).
3. `after`, `before`, `time_pref`, `slot_minutes`, `store`, and `min_minutes` survive date authority. `callID` and `first_available` are consumed. In LLM-intent v2 specifically, explicit `after` suppresses the `time_pref` band.
4. If authority fetch/parsing yields no usable date or errors, caller `from`/`to` remain the fallback inputs and undergo normal resolution/clamping.

# Raw-text authority

Authority engages only when all four gates pass: `ECP_RAW_TEXT_DATES` is enabled, tenant is `mott`, `callID` is nonempty, and `first_available` is not truthy. `_fetch_conversation` tries the Bland SMS-conversation URL first and the pathway-chat URL second, using the Bland API key and accepting `messages` or `chat_history` from the returned payload.

`resolve_from_conversation` considers only dictionary messages whose `sender` or `role` uppercases to `USER`. If every retained user message has `created_at`, it chooses the maximum timestamp; otherwise it chooses the last retained message. It reads `message`, falling back to `content`, and truncates to 2,000 characters. It parses only that latest user turn with `extract_date_from_text`.

In raw-text-authority v2, one resolved date becomes identical `from` and `to`; no result returns `(None, None)`. In LLM-intent v2, a deterministic `("range", start, end)` becomes the two endpoints; ordinary resolved dates still become same-day endpoints. The LLM-intent source also supports deterministic conflict/either signals elsewhere in the parser. When the initial fetch has no messages or no latest user text, it waits 1.2 seconds and refetches once to address observed Bland commit lag. It does not retry merely because a present user message has no parseable date.

Crucially, authority does not merge caller dates with conversation dates. A successful resolution assigns both `body["from"]` and `body["to"]`; time constraints and slot length remain untouched.

# LLM intent

The LLM is downstream of the fetched conversation and downstream of the deterministic parser, not a general conversation planner.

- In `shadow` mode, it runs in a daemon thread only to log agreement; it cannot alter the patient result.
- In `authoritative` mode, it is called synchronously only when the latest user text exists and deterministic `raw_from` is `None`. A deterministic result always wins.
- The model contract allows exactly compact JSON with one key: `{"phrase":"patient's date words or empty"}`. It must retain the operative date words/qualifiers, may expand shorthand/drop filler, ignore negated/busy/historical/address dates, honor the last self-correction, and return an empty phrase for no date request.
- It is explicitly forbidden to calculate or emit calendar dates. This keeps date arithmetic and ambiguity handling in deterministic `extract_date_from_text`, using clinic-time `today`; the model only repairs/extracts language. After JSON validation and length/digit guards, the deterministic parser converts the phrase into `none`, `date`, `range`, `ambiguous`, or `either`. Although downstream code contains an `asap` branch, the shown `llm_interpret_intent` return mapping does not emit `asap`; ASAP text is parsed as a deterministic range.

Thus “the LLM resolved the intent” does not mean the model invented a date. It returned patient date words, and gateway code produced the dates.

# Logging

Core date-source meanings:

- `date_source=raw`: conversation fetch succeeded and the deterministic raw-text parser produced a usable date/range that overwrote `from`/`to`. This is the clearest positive authority signal.
- `date_source=fallback`: authority was entered far enough to evaluate a fetched conversation, but no usable raw date was produced; caller `from`/`to` remain in force. In LLM-intent v2 this can also follow an LLM `none`/error result.
- `date_source=error_fallback`: authority raised an exception; caller date fields remain the fallback. LLM-intent v2 appends `reason=<ExceptionClass>`.

The LLM-intent v2 diagnostic sequence makes engagement observable before a final source decision:

- `raw_gate flag=<...> tenant=<...> call_id_len=<...> first_req=<...>` shows whether the four authority prerequisites are present. A nonzero `call_id_len`, true flag, `tenant=mott`, and `first_req=False` indicate the gate should enter.
- `raw_fetch msgs=N|none` and possible `raw_refetch msgs=N|none` show fetch activity and lag retry.
- `raw_fetch_err attempt=N type=... code=...` identifies fetch failures.
- `raw_resolve from=...` shows the deterministic resolution.
- `llm_intent=<intent|error> det=<class> agree=<bool>` shows shadow scoring or an authoritative fallback consult.
- Additional LLM-intent-v2 outcomes are `date_source=llm`, `llm_either`, `llm_conflict`, `either`, and `conflict`.

An operator should not infer “authority disabled” from the absence of `date_source=raw` alone. Use `raw_gate` plus `raw_fetch`/`raw_resolve`: `fallback` means the authority pathway engaged but did not replace the dates; `error_fallback` means it engaged and failed. The simpler raw-text-authority v2 only logs the three core `date_source` values and silently produces no date-source line when the gate prerequisites fail or a fetch returns no messages, so absence there is ambiguous.

`time_pref_relaxed` is always present in the LLM-intent v2 availability envelope as `""` initially. If a recognized time band produces zero slots, the handler retries the same request without `time_pref`. If that unfiltered retry finds slots, those slots replace the empty result and `time_pref_relaxed` is set to the rejected band name. It means “no openings in the requested band, but openings exist outside it,” not that the original band matched. If the retry fails or remains empty, it stays `""`. Raw-text-authority v2 adds the field only on a successful relaxation, so its absence/empty behavior is less stale-safe.

# IMPLICATIONS FOR THE PATHWAY

To fully engage the semantics, an availability node body should contain at least:

```json
{
  "store": "<resolved store id or configured store name>",
  "from": "<pathway fallback date or relative-date text>",
  "to": "<pathway fallback end date or relative-date text>",
  "after": "<explicit clock time or none>",
  "before": "<explicit clock time or none>",
  "time_pref": "<morning|afternoon|evening|late or empty>",
  "slot_minutes": "<required appointment duration>",
  "first_available": "<1|true|yes only for an explicit soonest search; otherwise false/empty>",
  "callID": "<the current Bland conversation id>"
}
```

The `late` value is fully honored only by LLM-intent v2. Use literal `none` or empty values for unset `after`/`before`; those values are explicitly stripped. Do not send caller-generated `date_conflict` or `either_days`.

Absent-field effects:

| Absent field | Effect |
|---|---|
| `callID` | Raw-text authority cannot engage. No conversation fetch or LLM intent consult occurs; `from`/`to` are solely pathway-controlled. |
| `from` | If authority supplies a date, that date works normally. Otherwise `resolve_relative_date(None)` fails and the clamp returns; because `from` remains absent, the CLI search lacks a start boundary. Do not rely on an implicit gateway default. |
| `to` | With a resolvable `from`, it collapses to the same day. With no resolvable `from`, it is not independently processed. |
| `after` | No explicit lower-time bound. A recognized `time_pref` may supply a band bound. |
| `before` | No explicit upper-time bound. A recognized `time_pref` may supply one (`morning`). |
| `time_pref` | No band filtering and no time-preference relaxation retry/marker. Explicit `after`/`before` still apply. |
| `slot_minutes` | No `--slot-minutes` is sent; duration behavior falls to the CLI/provider default. The gateway does not synthesize one. |
| `first_available` | Treated as false: authority may engage and caller/conversation dates are used. |
| `store` | No store flag and no reliable forced-doctor lookup; behavior falls to downstream defaults and can defeat the intended Mott office/provider scoping. A production pathway should always send it. |

For reliable pathway routing, map `count`, slot fields, and `time_pref_relaxed` from the response. In the LLM-intent tier, also map/route `date_conflict` so ambiguous raw language asks the patient to clarify rather than searching. Route on the real `count`, not padded `slots` length: the envelope pads to at least two slot objects to clear stale Bland variables.

```json CITATIONS
[
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"call_id = str(body.pop(\"callID\", \"\") or \"\").strip()"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"and not first_requested"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"body[\"from\"], body[\"to\"] = raw_from, raw_to"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"log.info(\"date_source=raw\")"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"log.info(\"date_source=fallback\")"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"log.info(\"date_source=error_fallback\")"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py","quote":"body[\"to\"] = (start + timedelta(days=6)).strftime(\"%m/%d/%Y\")"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"Extract only the operative appointment-date WORDS from one patient message."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"Never calculate or output a calendar date. Ignore negated, busy, historical, and address dates."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"Output only compact JSON: {{\"phrase\":\"patient's date words or empty\"}}"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"and raw_from is None"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"\"morning\": [(\"--before\", \"12:00 pm\")],"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"\"late\": [(\"--after\", \"03:00 pm\")],"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"explicit_after = str(body.get(\"after\", \"\")).strip().lower() not in (\"\", \"none\")"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"relaxed[\"time_pref_relaxed\"] = pref"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/llm-intent-v2/bland_gateway.py","quote":"raise ValueError(f\"unknown field {key!r} for {path}\")"}
]
```
