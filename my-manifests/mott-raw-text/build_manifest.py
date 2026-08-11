#!/usr/bin/env python3
import json, pathlib

CHECK = ("python3 /mnt/d_drive/repos/mott/gw-temporal-check/check_gateway_datefix.py "
         "--original /home/ankit114/repos/ringer/my-manifests/mott-date-arch/impl-src/bland_gateway.py "
         "--candidate bland_gateway.py && python3 -m pytest -q test_raw_wiring.py")

SPEC = r"""You are adding a RAW-TEXT DATE AUTHORITY to an SMS booking gateway. BOUNDARY: write only inside your task directory; no git, no network, no MCP, no skills. You own exactly three output files: ./bland_gateway.py, ./test_raw_wiring.py, ./report.md.

STEP 1. Copy /mnt/d_drive/repos/cvc-booking-gateway/container/bland_gateway.py to ./bland_gateway.py. It already contains an ordinal fallback and a compound normalizer inside resolve_relative_date (lines ~616-628), module constants _ORDINAL_MONTHS and _ordinal_suffix (~line 476), _WEEKDAYS (~line 468), _env_bool (~line 141), _DATE_ORDINAL_FALLBACK (~line 159), TENANT_ID (~line 52), and clamp_availability_range (~line 632).

WHY. The small extraction model sometimes DESTROYS the date ('Tomorrow july 28th' -> it extracts 'thursday', month dropped). Measured across 1,890 live probes; no prompt wording fixes it without breaking other phrases. The fix: the gateway fetches the patient's RAW message (the webhook carries the conversation id as callID; the transcript is fetchable server-side) and parses the patient's own words deterministically. The model extraction becomes a fallback only.

ADD 1 - flag, next to _DATE_ORDINAL_FALLBACK:
    _RAW_TEXT_DATES = _env_bool("ECP_RAW_TEXT_DATES", False)

ADD 2 - free-text parser (module level, after the compound-normalizer section of resolve_relative_date, i.e. after the function ends). Signature EXACTLY:
    def extract_date_from_text(text) -> str | None:
Deterministic; uses _eastern_today() for 'today' (tests freeze it). Pipeline:
  a. Normalize: str(text or ''), lowercase, collapse whitespace. Expand texting shorthand tokens word-by-word BEFORE parsing: nxt->next, wk->week, wks->weeks, tmrw/tmr->tomorrow, 2day->today, 2moro/2morrow->tomorrow.
  b. EXPLICIT MONTH+DAY WINS. Find ALL matches of: (month name from _ORDINAL_MONTHS) + space + day 1-31 + optional valid ordinal suffix + optional 4-digit year. Use finditer over the normalized text with punctuation (commas etc) stripped around tokens. If any matches: take the LAST one (a later date in the same message is a correction: 'july 28, no wait, august 3' -> august 3). Validate ordinal suffix with _ordinal_suffix (reject 'july 11st'). Resolve by calling resolve_relative_date on 'month day[ year]' WITHOUT the suffix. Return it.
  c. CHINESE explicit: regex (\d{1,2})月(\d{1,2})[号日] anywhere -> resolve via resolve_relative_date('{m}/{d}'). This outranks relative words too ('明天7月28号' -> 07/28).
  d. Whole-string try: resolve_relative_date(normalized_text) - catches clean single phrases including Chinese ('下周三').
  e. TOKEN-WINDOW SCAN: split into tokens; for window sizes 4,3,2,1 (largest first), slide left-to-right, join window with spaces, SKIP windows that are purely digits (r'^\d+$' - slot picks like '1' must never resolve), call resolve_relative_date(window); first hit wins. This catches 'can you do tomorrow?', 'how about this thursday', 'day after tomorrow maybe', 'I'm free wed or thurs' (wed wins, leftmost), 'tuesday next week', 'in 2 weeks'.
  f. BARE DAY-OF-MONTH: if still nothing, regex \b(?:the\s+)?(\d{1,2})(st|nd|rd|th)\b with valid suffix and 1-31: next occurrence of that day-of-month (today's month if day >= today.day else next month; handle month rollover and short months by advancing to the next month that has that day). 'any openings on the 28th?' at Mon 07/27 -> 07/28/2026.
  g. Nothing found -> return None. NEVER guess.

ADD 3 - conversation helper (module level). Signature EXACTLY:
    def resolve_from_conversation(messages) -> tuple:
messages is a list of dicts. A user message is one whose sender/role value (any of keys 'sender','role') upper()=='USER'. Its text is under 'message' or 'content'. Take ONLY the LATEST user message; run extract_date_from_text on it; if a date d -> return (d, d); else return (None, None). Do not mine older messages.

ADD 4 - fetch seam (module level):
    def _fetch_conversation(call_id) -> list | None:
Uses urllib.request with header Authorization: os.environ.get('ECP_BLAND_API_KEY',''), User-Agent 'mott-gateway'. Try GET https://api.bland.ai/v1/sms/conversations/{call_id} then https://api.bland.ai/v1/pathway/chat/{call_id}, timeout 2 seconds each. Parse JSON; the payload is under 'data' (fallback: whole object); messages under 'messages' (SMS shape: sender/message) or 'chat_history' (chat shape: role/content). Return the list, or None on any error/no messages. Must never raise.

ADD 5 - wiring inside clamp_availability_range, as the FIRST statements of the function body:
    call_id = str(body.pop("callID", "") or "").strip()
    if _RAW_TEXT_DATES and TENANT_ID != "cvc" and call_id:
        try:
            msgs = _fetch_conversation(call_id)
            if msgs:
                raw_from, raw_to = resolve_from_conversation(msgs)
                if raw_from:
                    body["from"], body["to"] = raw_from, raw_to
                    log.info("date_source=raw")
                else:
                    log.info("date_source=fallback")
        except Exception:
            log.info("date_source=error_fallback")
The callID pop is UNCONDITIONAL (outside the if) so an unknown field can never reach the CLI arg builder even with the flag off. Never log message bodies or phone numbers here; only those fixed source codes.

HARD RULES: change nothing else. resolve_relative_date itself is untouched. No new third-party imports (urllib/json/os/re/datetime only). All new behavior is inert unless ECP_RAW_TEXT_DATES is on AND tenant is not cvc, except the harmless callID pop.

./test_raw_wiring.py - executable pytest proof of the wiring (import ./bland_gateway.py as a module with capability_registry stubbed exactly like this:
    import types, sys
    stub = types.ModuleType('capability_registry'); stub.QueryError = type('QE',(Exception,),{})
    stub.load_manifest = lambda *a, **k: {}; stub.prepare_query = lambda *a, **k: {}; stub.render_query_result = lambda *a, **k: {}
    sys.modules['capability_registry'] = stub
and os.environ ECP_DATE_ORDINAL_FALLBACK=1, ECP_RAW_TEXT_DATES=1, ECP_TENANT_ID=mott set BEFORE import; freeze mod._eastern_today to datetime(2026,7,27,12,0,0)). Tests:
  1. raw override: stub mod._fetch_conversation to return a Kenneth-style transcript (USER 'Tomorrow july 28th'); clamp_availability_range({'store':'711','from':'thursday','to':'thursday','callID':'x'}) ends with from==to=='07/28/2026' and no 'callID' key.
  2. fail-open: stub seam to raise RuntimeError; same body -> from/to resolve as plain 'thursday' would (the model fallback), no exception, no 'callID' key.
  3. flag off: reimport module fresh with ECP_RAW_TEXT_DATES=0 under a different module name; stub seam with a counter; clamp -> seam never called, callID still popped.
  4. cvc tenant: fresh import with ECP_TENANT_ID=cvc and flag on -> seam never called.
  5. no-date latest message: seam returns transcript ending USER '1' -> falls back to model values.
Run the tests yourself: python3 -m pytest -q test_raw_wiring.py must pass.

VERIFY - run exactly this; it is how you are graded:
    python3 /mnt/d_drive/repos/mott/gw-temporal-check/check_gateway_datefix.py --original /home/ankit114/repos/ringer/my-manifests/mott-date-arch/impl-src/bland_gateway.py --candidate ./bland_gateway.py && python3 -m pytest -q test_raw_wiring.py
The check runs ~190 frozen-clock phrases including 32 raw-text sentences (explicit-wins, corrections, Chinese, bare '28th', slot-pick '1' -> None) plus zero-drift, tenant-guard, and shape sections. Iterate until CHECK PASSED and pytest green.

./report.md: '# Raw-Text Date Authority', '## Summary' (3 bullets max), '## Parser Pipeline' (the a-g order you implemented), '## Verify' (paste the CHECK PASSED line and pytest tail), '## Risks' (anything you saw). Under 400 words."""

manifest = {
    "run_name": "mott-date-architecture",
    "workdir": "/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work",
    "max_parallel": 1,
    "tasks": [
        {
            "key": "raw-text-authority",
            "engine": "codex",
            "task_type": "code-fix",
            "timeout_s": 2700,
            "expect_files": ["bland_gateway.py", "test_raw_wiring.py", "report.md"],
            "verified": ("Raw-text authority: deterministic free-text parser resolves 32 real patient "
                         "sentences (explicit-wins, corrections, Chinese, bare day-of-month; slot picks "
                         "stay None), conversation helper takes latest USER message only, wiring is "
                         "flag-gated + tenant-guarded + fail-open with callID always popped, and all "
                         "prior zero-drift/ordinal/compound/CVC-inert sections stay green."),
            "check": CHECK,
            "spec": SPEC,
        }
    ],
}

out = pathlib.Path("/home/ankit114/repos/ringer/my-manifests/mott-raw-text/manifest.json")
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
