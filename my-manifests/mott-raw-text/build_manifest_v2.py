#!/usr/bin/env python3
import json, pathlib

CHECK = ("python3 /mnt/d_drive/repos/mott/gw-temporal-check/check_gateway_datefix.py "
         "--original /home/ankit114/repos/ringer/my-manifests/mott-date-arch/impl-src/bland_gateway.py "
         "--candidate bland_gateway.py && python3 -m pytest -q test_raw_wiring.py")

SPEC = r"""ROUND 2 of the raw-text date authority. An adversarial review found real defects in round 1; you are fixing exactly those. BOUNDARY: write only inside your task directory; no git, no network, no MCP, no skills. You own ./bland_gateway.py, ./test_raw_wiring.py, ./report.md.

STEP 1. Copy the round-1 artifacts: /home/ankit114/repos/ringer/my-manifests/mott-raw-text/work/raw-text-authority/bland_gateway.py and /home/ankit114/repos/ringer/my-manifests/mott-raw-text/work/raw-text-authority/test_raw_wiring.py into your directory. Round 1 already passes the base corpus; you are ADDING intent/safety rules and hardening. Do not regress anything.

THE REVIEW FINDINGS (all reproduced RED against round 1):
  'I cannot do July 28; Wednesday is better' -> got 07/28, must be 07/29 (negated date won)
  'no not friday, monday works' -> got 07/31, must be 08/03
  'Not the 5th, the 8th' -> got 08/05, must be 08/08 (first-match instead of last)
  'Anything but Friday' -> got 07/31, must be None
  'June 5 is my birthday; I need next Tuesday' -> got 06/05/2027, must be 07/28 (incidental date won)
  'My insurance renewed June 5 years ago.' -> got 06/05/2027, must be None (history)
  'I paid on the 5th last time' -> got 08/05, must be None (history)
  'My address is May 5th Avenue, apartment 2.' -> got 05/05/2027, must be None (address)
  'My unit is 12/5 on Peachtree Road.' -> got 12/05, must be None (address)
  'Can you do tomorrow<emoji>' -> got None, must be 07/28 (attached emoji broke tokenizing)

FIX A - extract_date_from_text gets an intent layer. Deterministic, in this order:
  1. NORMALIZE: before tokenizing, replace every character that is not a letter, digit, whitespace, or one of / - : , ; . ? ! or a CJK character with a single space (this detaches emoji: 'tomorrow<emoji>' -> 'tomorrow '). Then lowercase, collapse whitespace, expand shorthand as in round 1.
  2. CLAUSE SPLIT: split the text into clauses on ; . ? ! and the standalone word ' but '. Track comma segments inside each clause.
  3. FIND all candidate date expressions as in round 1 (explicit month+day incl ordinal/year, Chinese explicit, resolver-recognized token windows, bare day-of-month) BUT record each expression's clause index and comma-segment index.
  4. KILL RULES, applied per expression:
     - NEGATION: if any negator appears earlier in the SAME comma-segment of the same clause, kill the expression. Negators: cannot, can not, cant, can't, wont, won't, dont, don't, not, no, never, except, anything but, rather than, instead of. So 'no not friday, monday works': friday killed (same segment), monday survives (next segment) -> 08/03. 'I cannot do July 28; Wednesday is better': july 28 killed, wednesday (next clause) survives -> 07/29. 'Anything but Friday' -> friday killed -> None. 'Not the 5th, the 8th' -> 5th killed, 8th survives -> 08/08.
     - HISTORY: if the expression's clause contains any of: ago, last time, renewed, paid, birthday, born, since, back in, history -> kill every expression in that clause. 'June 5 is my birthday' clause dies; 'I need next Tuesday' clause survives -> 07/28.
     - ADDRESS: if the expression's clause contains any of: avenue, ave, street, road, rd, blvd, boulevard, drive, apartment, apt, unit, suite, floor, zip -> kill every expression in that clause.
  5. PICK from survivors: explicit month+day survivors take priority and the LAST one wins (correction recency); bare day-of-month also LAST-wins; otherwise first surviving window hit as in round 1. No survivors -> None.

FIX B - positive tenant gate for the raw-text wiring in clamp_availability_range: replace the TENANT_ID != "cvc" condition ON THE RAW-TEXT BLOCK ONLY with TENANT_ID.strip().lower() == "mott". Do NOT touch the ordinal/compound conditions inside resolve_relative_date; they are deployed and proven.

FIX C - skip pointless fetches: in the wiring, before fetching, if str(body.get("first_available", "")).strip().lower() in ("1","true","yes") skip the whole raw-text block (the fetch result would be discarded).

FIX D - harden _fetch_conversation:
  - Require a nonempty os.environ.get("ECP_BLAND_API_KEY"); else return None immediately.
  - Strengthen the id guard: keep the existing fullmatch and ALSO require at least 8 alphanumeric characters in the id.
  - Refuse redirects: build a private urllib.request.OpenerDirector via build_opener with a HTTPRedirectHandler subclass whose redirect_request returns None (redirects then raise HTTPError and are swallowed by the existing except). Use that opener's open() for both requests so the Authorization header can never follow a redirect off-origin.
  - One total deadline: take time.monotonic() at entry; before the second URL attempt, if more than 2.5 seconds have elapsed, return None. Keep per-request timeout 2.
  - Cap the read: response.read(524288) (512 KB).
  - In resolve_from_conversation, truncate the chosen message text to its first 2000 characters before parsing, and pick the latest USER message by 'created_at' when every USER message has one (ISO strings sort correctly); otherwise keep last-in-list.

FIX E - tests. Extend ./test_raw_wiring.py, keeping the round-1 five green, adding:
  - missing API key: unset ECP_BLAND_API_KEY (monkeypatch os.environ) -> _fetch_conversation('a'*12) is None with no network attempt (stub the opener/urlopen to raise if called).
  - first_available skip: seam call-counter; clamp body with first_available='1' and callID -> seam not called, callID still popped.
  - tenant case variants: fresh imports with ECP_TENANT_ID=' MOTT ' -> raw block active; 'CVC' -> inactive; 'unknownclinic' -> inactive (positive gate).
  - created_at ordering: two USER messages with created_at out of list order -> the newer timestamp wins.
  - oversize message: a USER message of 12000 characters whose FIRST 100 chars contain 'july 28th' -> resolves 07/28/2026 and returns quickly.
Run: python3 -m pytest -q test_raw_wiring.py until green.

VERIFY - exactly this command grades you; the frozen corpus now contains all ten review sentences:
    python3 /mnt/d_drive/repos/mott/gw-temporal-check/check_gateway_datefix.py --original /home/ankit114/repos/ringer/my-manifests/mott-date-arch/impl-src/bland_gateway.py --candidate ./bland_gateway.py && python3 -m pytest -q test_raw_wiring.py
Iterate until CHECK PASSED and pytest green.

./report.md: '# Raw-Text Authority round 2', '## Fixed' (map each review finding to the rule that fixes it), '## Verify' (paste the CHECK PASSED line + pytest tail), '## Residual risks'. Under 400 words."""

manifest = {
    "run_name": "mott-date-architecture",
    "workdir": "/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2",
    "max_parallel": 1,
    "tasks": [
        {
            "key": "raw-text-authority-v2",
            "engine": "codex",
            "task_type": "code-fix",
            "timeout_s": 2700,
            "expect_files": ["bland_gateway.py", "test_raw_wiring.py", "report.md"],
            "verified": ("Round 2 closes the adversarial findings: negated/historical/address dates can "
                         "never steer the search, corrections last-win, emoji-attached dates parse, the "
                         "raw block is positively gated to tenant mott, fetches refuse redirects with one "
                         "2.5s deadline and size caps, and every prior corpus section stays green."),
            "check": CHECK,
            "spec": SPEC,
        }
    ],
}

out = pathlib.Path("/home/ankit114/repos/ringer/my-manifests/mott-raw-text/manifest_v2.json")
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
