# ROOT CAUSE
VERDICT: NOT-REPRODUCED

The supplied executed artifact does not contain the described `MSGS=`, `PIPELINE_PICKED=`, `PIPELINE_RESOLVED=`, `STAGE2(...)`, or `LLM_PICKED=` results. Its only line is an import failure, and the named `messages.json` input is absent. Therefore the executed evidence does not reproduce a resolution of `08/06/2026`, so it would be dishonest to force a phrase-picking or vocabulary verdict. Static inspection does reveal a vocabulary gap that would cause `the following thursday` to fall through when passed directly to the resolver, but that code-reading cannot replace the missing run.

# EVIDENCE

The only literal line present in `repro.txt` is:

> `FETCH_FAILURE=ModuleNotFoundError: No module named 'capability_registry'`

There is no literal `PIPELINE_RESOLVED=` line or `STAGE2(` line to quote: `repro.txt` has exactly one line. The requested three-line evidentiary showing is therefore impossible from the supplied artifact without fabricating evidence.

# MECHANISM

In `mott-raw-text/work2/raw-text-authority-v2/bland_gateway_live.py`, lines 588-598 recognize `weekday after next`, `a week from weekday`, and `weekday next week`; lines 600-602 recognize a bare weekday after stripping only `this|next|on|coming`. They do not recognize `following weekday` or `the following weekday`. Thus `resolve_relative_date("the following thursday")` falls through instead of selecting the Thursday in the next calendar week. The raw-text scanner calls that resolver for token windows at lines 759-772, while the raw result silently replaces pathway `from`/`to` at lines 945-968. Separately, the LLM variant's prompt at `mott-llm-intent/work2/llm-intent-v2/bland_gateway.py` lines 369-385 explicitly says to keep qualifiers; no executed `LLM_PICKED=` result was supplied, so stage 1 is not implicated by evidence.

# PROPOSED FIX

Immediately after construction of `weekday_pattern` at line 588 and before the existing compound-weekday branches, add a full-match branch for `rf"(?:the )?following ({weekday_pattern})"` and return `emit(calendar_weekday(_WEEKDAYS[match.group(1)], 1))`. Keep `following` out of the generic prefix stripping at line 600 because `next_weekday(...)` can mean the imminent weekday in the current week, which is exactly the incident's wrong `08/06/2026` behavior. Add the new cases in `eval_cases.json` to the resolver/raw-text differential corpus. Do not change the LLM prompt unless a successful rerun shows it dropping `following`; if that happens, add the example `"No the following Thursday" -> {"phrase":"the following thursday"}` beside the correction examples.

# CVC PORTABILITY

Reapply the resolver branch to the CVC gateway only after confirming its weekday semantics also define `following weekday` as the named weekday in the next Monday-anchored calendar week. Port the resolver tests first, then test the CVC ingestion path separately because Mott's raw-text authority and tenant gate at lines 936-968 are Mott-specific. Do not copy the raw override behavior into CVC merely to share the vocabulary fix.
