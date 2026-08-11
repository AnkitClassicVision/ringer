#!/usr/bin/env python3
import json, pathlib

CHECK = ("python3 -m pytest -q test_llm_intent.py && "
         "python3 /mnt/d_drive/repos/mott/gw-temporal-check/check_gateway_datefix.py "
         "--original /home/ankit114/repos/ringer/my-manifests/mott-date-arch/impl-src/bland_gateway.py "
         "--candidate bland_gateway.py 2>&1 | tail -1 | grep -q 'CHECK PASSED' && "
         "python3 -c \"s=open('bland_gateway.py').read(); "
         "assert 'phrase' in s and 'def llm_interpret_intent' in s, 'shape'; print('shape OK')\"")

SPEC = r"""ROUND 2 of the LLM intent tier. A real Bedrock exam (48 phrases) proved the round-1
contract wrong in a precise way; you are fixing exactly that. BOUNDARY: write only inside your
task directory; no network, no AWS, no MCP, no git. Own: ./bland_gateway.py, ./test_llm_intent.py,
./eval_llm_intent.py, ./report.md.

STEP 1. Copy the round-1 artifacts from
/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work/llm-intent-tier/
(bland_gateway.py, test_llm_intent.py, eval_llm_intent.py) into your directory.

THE EXAM FINDING (ground truth, 2026-07-29): Haiku classifies INTENT superbly (negation,
busy-context, corrections, asap all correct) but computes CALENDAR DATES wrong exactly like
every other model - measured off-by-one weekday math on 10+ cases:
  'friday would be good' -> it answered 08/01/2026 (a Saturday; Friday was 07/31)
  'tuesday next week' -> 08/05 (a Wednesday; correct 08/04)
  'next monday works' -> 08/04 (a Tuesday; correct 08/03)
  'how about this thursday' -> wrongly flagged ambiguous (only "next <weekday>" is ambiguous)
  'can we do next weekend?' -> contract error (ambiguous with empty dates failed validation)
The deterministic resolver in this same file is 100% correct on 153 phrases. CONCLUSION:
no model may ever emit a calendar date. The LLM's only job is choosing WHICH WORDS are the
request.

THE NEW CONTRACT - rewrite llm_interpret_intent(user_text, today) so the model returns ONLY:
    {"phrase": "<the patient's operative date words, minimally normalized>"}
  - phrase is the date request expressed in the patient's own words, with ONLY these
    normalizations allowed: expand texting shorthand (tues nxt wk -> tuesday next week),
    drop filler ("how about", "can I do", "works for me"), keep qualifiers intact
    ("wednesday next week" stays exactly that, "next friday" stays "next friday"),
    keep month+day as said ("august 3", "july 28th"), keep relative words as said
    ("tomorrow", "as soon as possible", "this weekend", "next weekend").
  - Negated / busy / historical / address-context dates are NOT the request: "I'm busy today,
    how about next week Wednesday?" -> phrase "wednesday next week". "no not friday, monday
    works" -> "monday". "I cannot do July 28; Wednesday is better" -> "wednesday".
  - A correction takes the LAST stated request: "july 28, no wait, august 3" -> "august 3".
  - Chinese passes through as said ("下周三" -> "下周三").
  - If the message contains no date request at all (slot picks "1"/"2", yes/no, questions,
    greetings): phrase "".
  PROMPT: keep it tight; give 6-8 few-shot pairs covering exactly the cases above. maxTokens 60,
  temperature 0. Include today's weekday+date line for context ONLY (the model never outputs dates).

PARSING/VALIDATION: strip code fences, json.loads, phrase = str(...)[:80].strip(); reject if it
contains any digit-heavy garbage beyond 12 tokens; empty phrase -> {"intent":"none"}.
Then DERIVE everything deterministically IN CODE:
    outcome = extract_date_from_text(phrase)   # the existing deterministic parser
    - outcome None -> {"intent":"none"}
    - date string -> {"intent":"date","date":outcome}
    - ('range', a, b) -> {"intent":"range","date":a,"date2":b}
    - ('conflict', a, b, descA, descB) -> {"intent":"ambiguous","date":a,"date2":b,
       "optionA":descA,"optionB":descB}
  Keep the function's return shape identical to round 1 so the wiring, precedence
  (deterministic-first, LLM fills only when deterministic was None), shadow/authoritative
  modes, logging, and fail-open ALL stay byte-identical. Do not touch the wiring block except
  where the verdict is built.

TESTS - update test_llm_intent.py to the new contract:
  1. fake client returns fenced {"phrase":"wednesday next week"} -> intent date, date computed
     by the resolver (freeze _eastern_today to 2026-07-29: expect 08/05/2026).
  2. {"phrase":"next friday"} -> intent ambiguous with BOTH dates from the parser conflict.
  3. {"phrase":"as soon as possible"} -> intent range/asap (parser range tomorrow..+6).
  4. {"phrase":""} -> none.
  5. garbage reply / exception -> None (fail-open) - keep the round-1 tests for precedence,
     off mode, deterministic-wins; adjust stubs to the new shape.
  All tests stub the Bedrock client; python3 -m pytest -q test_llm_intent.py must pass.

EXAM HARNESS - eval_llm_intent.py stays, but the grading maps through the SAME derivation:
it should now compare the DERIVED intent/dates (which use the deterministic parser) against
CORPUS['raw_text'] expectations. Keep RUN_REAL guard.

VERIFY (exactly how you are graded): """ + json.dumps(CHECK) + r"""

./report.md: '# LLM Intent Tier v2 - phrase contract', '## Why' (the exam finding, 3 bullets),
'## Contract', '## Verify' (paste pytest + gate lines). Under 300 words."""

manifest = {
    "run_name": "mott-llm-intent",
    "workdir": "/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2",
    "max_parallel": 1,
    "tasks": [{
        "key": "llm-intent-v2",
        "engine": "codex",
        "task_type": "code-fix",
        "timeout_s": 2400,
        "expect_files": ["bland_gateway.py", "test_llm_intent.py", "eval_llm_intent.py", "report.md"],
        "verified": ("Phrase-only LLM contract: the model never emits dates; the deterministic "
                     "parser derives date/range/ambiguous/none from the extracted phrase; wiring, "
                     "precedence, modes and fail-open unchanged; unit tests and resolver gate green."),
        "check": CHECK,
        "spec": SPEC,
    }],
}
out = pathlib.Path("/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/manifest_v2.json")
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
