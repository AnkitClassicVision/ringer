#!/usr/bin/env python3
import json, pathlib

CHECK = ("python3 -m pytest -q test_llm_intent.py && "
         "python3 /mnt/d_drive/repos/mott/gw-temporal-check/check_gateway_datefix.py "
         "--original /home/ankit114/repos/ringer/my-manifests/mott-date-arch/impl-src/bland_gateway.py "
         "--candidate bland_gateway.py 2>&1 | tail -1 | grep -q 'CHECK PASSED' && "
         "python3 -c \"s=open('bland_gateway.py').read(); "
         "assert 'ECP_LLM_INTENT' in s and 'def llm_interpret_intent' in s and "
         "'us.anthropic.claude-haiku-4-5-20251001-v1:0' in s, 'shape tokens missing'; print('shape OK')\"")

SPEC = r"""You are adding an LLM INTENT TIER (Bedrock Claude Haiku) to an SMS booking gateway.
BOUNDARY: write only inside your task directory; no network, no AWS calls, no MCP, no git.
You own: ./bland_gateway.py, ./test_llm_intent.py, ./eval_llm_intent.py, ./report.md.

STEP 1. Copy /mnt/d_drive/repos/cvc-booking-gateway/container/bland_gateway.py to ./bland_gateway.py.
It already contains: a deterministic free-text parser extract_date_from_text (returns a date
string, a ('conflict', d1, d2, descA, descB) tuple, a ('range', d1, d2) tuple, or None),
resolve_from_conversation(messages) -> (from,to) using the LATEST USER message,
_fetch_conversation(call_id) transcript pull with one retry, and a raw-text wiring block in
clamp_availability_range gated by _RAW_TEXT_DATES and tenant mott. boto3 is imported at module
top inside try/except (may be None). time, json, re, datetime, timedelta are available.

DESIGN (implement exactly):

A. CONFIG, next to the other _env_bool flags:
   _LLM_INTENT = os.environ.get("ECP_LLM_INTENT", "off").strip().lower()  # off|shadow|authoritative
   _LLM_MODEL_ID = os.environ.get("ECP_LLM_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
   _BEDROCK_CLIENT = None  # lazy singleton

B. def _bedrock():  lazy-create boto3.client('bedrock-runtime', region_name='us-east-1',
   config=botocore.config.Config(connect_timeout=1, read_timeout=3, retries={'max_attempts': 0}))
   inside try/except returning None when boto3/botocore unavailable. Import botocore.config
   lazily inside the function. Cache in _BEDROCK_CLIENT.

C. def llm_interpret_intent(user_text, today) -> dict | None:
   - today is a datetime; build header: f"Today is {today.strftime('%A')} {today.strftime('%m/%d/%Y')} (America/New_York clinic time)."
   - PROMPT (single user message, temperature 0, maxTokens 160) teaching the contract:
     * You extract appointment-date intent from ONE patient SMS for an optometry scheduler.
     * Output ONLY compact JSON: {"intent":"date|range|ambiguous|asap|none","date":"MM/DD/YYYY or empty","date2":"MM/DD/YYYY or empty","optionA":"short phrase or empty","optionB":"short phrase or empty"}
     * RULES (mirror the deterministic rails):
       - A day mentioned only as busy/unavailable/history/address is context, never the request ("I'm busy today, how about next week Wednesday?" -> the Wednesday of next week).
       - Negated days are rejected ("anything but Friday" -> not Friday; if nothing else named -> none).
       - "next <weekday>" said BEFORE that weekday in the current week is AMBIGUOUS between the imminent one and next week's: intent=ambiguous, date=imminent, date2=week after, optionA/optionB name them like "this coming Friday the 31st" / "next week Friday the 7th". Same for "next weekend" (Saturdays).
       - "<weekday> next week" is NOT ambiguous (always next calendar week, Monday-anchored).
       - asap / as soon as possible / next available / earliest / soonest / first opening -> intent=asap (no dates needed).
       - Explicit month+day (with or without ordinal), today/tomorrow/day after tomorrow, bare weekday (next future occurrence), "next week" (Monday of next week) -> intent=date with the resolved MM/DD/YYYY.
       - A stated span ("Aug 5 to Aug 8", "this weekend" Sat-Sun) -> intent=range with date/date2.
       - Two cues that agree -> date. Two that disagree (weekday vs explicit date mismatch) -> ambiguous with both.
       - Slot picks ("1","2"), yes/no, questions, greetings -> none.
     * Never invent availability. Never use a past date.
   - Call _bedrock().converse(modelId=_LLM_MODEL_ID, ...). ANY exception -> return None.
   - Parse the reply text: strip markdown code fences if present, json.loads; on failure return None.
   - VALIDATE deterministically (code, not trust): intent in the enum; for date/range/ambiguous the
     date fields parse as %m/%d/%Y, are >= today.date(), and <= today+120 days; range needs date < date2;
     ambiguous needs two distinct dates and both option strings non-empty (if empty, SYNTHESIZE them in
     code as f"{weekday} the {day}{suffix}" using our own strftime, never the model's words for the date).
     Any violation -> None.

D. WIRING in clamp_availability_range's raw block. After the existing deterministic
   resolve_from_conversation result (including its retry refetch):
   - Determine latest_user_text the same way resolve_from_conversation picks its message (factor a
     tiny helper _latest_user_text(msgs) and reuse it in both places).
   - If _LLM_INTENT != "off" and tenant mott and latest_user_text:
       verdict = llm_interpret_intent(latest_user_text, _eastern_today())
       det = the deterministic outcome classified as one of date/range/conflict/none for comparison
       agree = (verdict is not None) and (
           (verdict["intent"]=="date" and det is a date == verdict date) or
           (verdict["intent"]=="ambiguous" and det is conflict) or
           (verdict["intent"] in ("range","asap") and det is range) or
           (verdict["intent"]=="none" and det is None))
       log.info("llm_intent=%s det=%s agree=%s", verdict["intent"] if verdict else "error",
                det_class, agree)   # NEVER log message text or dates
   - shadow mode: nothing else changes.
   - authoritative mode PRECEDENCE (conservative): the deterministic result, when it exists, WINS.
     The LLM verdict is applied ONLY when the deterministic outcome was None:
       date -> body["from"]=body["to"]=verdict date; log date_source=llm
       range -> from/to = date/date2; log date_source=llm
       asap -> from = tomorrow, to = tomorrow+6 (compute in code); log date_source=llm
       ambiguous -> body["date_conflict"] = ("conflict", date, date2, optionA, optionB); log date_source=llm_conflict
       none -> nothing.
   - Everything stays inside the existing try/except fail-open.

E. ./test_llm_intent.py (pytest; import the module with capability_registry stubbed exactly as the
   existing tests do; set env ECP_DATE_ORDINAL_FALLBACK=1, ECP_RAW_TEXT_DATES=1, ECP_TENANT_ID=mott,
   ECP_LLM_INTENT=authoritative BEFORE import; freeze _eastern_today to datetime(2026,7,29,12,0,0)).
   Stub the LLM by monkeypatching module.llm_interpret_intent or _bedrock; tests:
   1. fenced-JSON parse: llm_interpret_intent internals - simulate converse returning
      '```json\n{"intent":"date","date":"08/07/2026","date2":"","optionA":"","optionB":""}\n```'
      via a fake client object -> dict with intent date.
   2. validation: past date -> None; bad enum -> None; ambiguous with one date -> None.
   3. precedence: stub deterministic path via _fetch_conversation returning a transcript whose
      latest USER message the deterministic parser CANNOT read ("hoping for something soonish"),
      and stub llm to return date 08/07 -> body from/to become 08/07, log path date_source=llm.
   4. deterministic wins: transcript "july 31st" (deterministic resolves) + llm stub returning a
      DIFFERENT date -> body keeps 07/31, llm only logged.
   5. ambiguous fill: deterministic None + llm ambiguous(07/31, 08/07) -> body["date_conflict"] tuple.
   6. fail-open: llm raises -> behavior identical to llm absent.
   7. off mode: ECP_LLM_INTENT=off fresh import -> llm function never called (counter stub).
   Run: python3 -m pytest -q test_llm_intent.py (must pass).

F. ./eval_llm_intent.py - the REAL exam harness (run later with AWS creds, not by you):
   loads CORPUS from /mnt/d_drive/repos/mott/gw-temporal-check/gen_golden.py (sys.path append),
   iterates CORPUS['raw_text'] items, maps expected -> expected intent class
   (date-string -> date+exact date match; 'conflict' -> ambiguous; 'range' -> range/asap; None -> none),
   calls llm_interpret_intent with today=datetime(2026,7,27,12,0,0) (the corpus freeze), prints a
   per-case PASS/FAIL table and final score "LLM exam: X/Y". Guard: if _bedrock() is None or
   env RUN_REAL!='1', print SKIPPED and exit 0.

VERIFY (exactly how you are graded): """ + json.dumps(CHECK) + r"""

./report.md: '# LLM Intent Tier', '## Design' (5 bullets), '## Precedence table',
'## Verify' (paste pytest + gate lines), '## Residual risks'. Under 400 words."""

manifest = {
    "run_name": "mott-llm-intent",
    "workdir": "/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work",
    "max_parallel": 1,
    "tasks": [{
        "key": "llm-intent-tier",
        "engine": "codex",
        "task_type": "code-fix",
        "timeout_s": 2700,
        "expect_files": ["bland_gateway.py", "test_llm_intent.py", "eval_llm_intent.py", "report.md"],
        "verified": ("Bedrock Haiku intent tier: strict-JSON contract with deterministic validation, "
                     "conservative precedence (deterministic wins, LLM fills gaps), shadow/authoritative/"
                     "off modes, fail-open, unit-tested with stubs, resolver gate untouched, plus a "
                     "real-exam harness for the 155-phrase corpus."),
        "check": CHECK,
        "spec": SPEC,
    }],
}
out = pathlib.Path("/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/manifest.json")
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
