# ROOT CAUSE
VERDICT: NOT-REPRODUCED

The supplied executed reproduction did not reproduce the deployed `08/06/2026` resolution: it reports `PIPELINE_RESOLVED=NONE`, so the executed evidence rules out forcing a phrase-picking, vocabulary, or combined verdict for that run. Resolver isolation nevertheless proves a vocabulary gap (`the following thursday` returns `NONE` while `thursday next week` returns `08/13/2026`), and code inspection shows that the raw-text picker also treats the leading corrective “No” as negation of the later weekday phrase. The file separately records `OBSERVED_DEPLOYED=08/06/2026`, but that observation is not the reproduced pipeline result.

# EVIDENCE

Literal lines from `repro.txt`:

```text
PIPELINE_PICKED=NOT-APPLICABLE
PIPELINE_RESOLVED=NONE
STAGE2(thursday)=08/06/2026
STAGE2(the following thursday)=NONE
STAGE2(thursday next week)=08/13/2026
OBSERVED_DEPLOYED=08/06/2026
```

# MECHANISM

In `/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/raw-text-authority-v2/bland_gateway_live.py`, `resolve_relative_date` begins at line 493. Its English weekday forms at lines 588-602 recognize `weekday after next`, `weekday next week`, and prefixes `this|next|on|coming`, but contain no pattern for `following <weekday>` or `the following <weekday>`. Consequently, resolver isolation returns `NONE` at Stage 2. Independently, `extract_date_from_text` defines `killed(start)` at lines 695-702 and treats any earlier `no` as negation; for `No the following Thursday`, the leading correction marker precedes every candidate window and kills it. The candidate window is passed to the resolver at lines 759-772. The conversation picker at lines 853-869 selects only the latest user message and returns no date when extraction fails. No Stage 1 LLM phrase-picking result was executed here (`LLM_PICKED=NOT-APPLICABLE`), so the prompt at `mott-llm-intent/work2/llm-intent-v2/bland_gateway.py:365-385` is not implicated by this reproduction.

# PROPOSED FIX

In `resolve_relative_date`, immediately before the existing English weekday patterns at line 588, add an anchored form equivalent to `rf"(?:the )?following ({weekday_pattern})"` and resolve it as `calendar_weekday(_WEEKDAYS[match.group(1)], 1)`. In `extract_date_from_text`, classify sentence-leading `no` followed by an affirmative replacement date as a correction boundary rather than a negator, while retaining adjacent date rejection such as `no friday works`; the smallest targeted behavior is to exclude only a leading discourse `no` before `the following <weekday>` from `killed(start)`. Do not change the LLM prompt based on this run because Stage 1 was not exercised; if that lane is later enabled, add a prompt example mapping `No the following Thursday` to `the following thursday` without calculating a date.

# CVC PORTABILITY

Re-apply the resolver vocabulary form and the narrowly scoped leading-correction rule to the CVC gateway only after confirming its weekday semantics and raw-text authority path match Mott. Port the new eval cases as a shared temporal contract, but preserve CVC-specific tenant flags and require a frozen-clock differential run before promotion.
