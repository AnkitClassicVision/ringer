# GW44B live-path fix evidence

## Live failure reproduced and path traced

The handler-level resolution entry is `build_argv`.

1. `Handler.do_POST` parses JSON and copies it to `cli_body` (`fixed-bland_gateway.py:3070-3079`).
2. The handler calls `build_argv(self.path, cli_body)` (`fixed-bland_gateway.py:3137`).
3. For `/availability`, `build_argv` calls `clamp_availability_range` before constructing flags (`fixed-bland_gateway.py:2298-2307`).
4. With the Mott raw-text gate enabled, the clamp pre-normalizes `user_text` through `resolve_from_conversation` (`fixed-bland_gateway.py:1535-1605`). That calls `extract_date_from_text` (`fixed-bland_gateway.py:1396-1434`). This was the missed production path: its general scanner split the five-token week-of phrase and selected bare `monday`, even though the lower `resolve_relative_date` helper already had the correct qualified grammar.
5. The clamp then resolves final `from`/`to` values (`fixed-bland_gateway.py:1777-1808`). Before this fix, an unresolved `from` set `from_unresolved` and returned without replacing the raw value. `build_argv` deferred the signal but emitted the still-raw value as CLI `--from`, allowing the inner CLI to return 409.
6. After the CLI succeeds, the handler restores `from_unresolved` on the availability envelope and returns HTTP 200 (`fixed-bland_gateway.py:3153-3159`, `fixed-bland_gateway.py:3469-3474`). The generic 409 refusal is later at `fixed-bland_gateway.py:3490-3499`; unresolvable date text no longer reaches it.

## Change

- `extract_date_from_text` now recognizes the complete `<weekday> (of )?the week of <date-phrase>` before the general token scanner (`fixed-bland_gateway.py:1036-1050`). It delegates the intact phrase to `resolve_relative_date`, whose week-of rule precedes bare-weekday handling (`fixed-bland_gateway.py:759-790`).
- If either supplied `from` or `to` is unresolvable, `clamp_availability_range` replaces both with today through today + 13 days and retains the handler-only `from_unresolved` signal (`fixed-bland_gateway.py:1787-1802`). Missing/`none` values keep the same default window without the signal (`fixed-bland_gateway.py:1779-1785`).
- The production file diff is limited to those two resolution corrections and comments. The fixed file is installed in `gwtest/container/bland_gateway.py`.

## Tests on the handler entry

The new tests call `build_argv`, the exact resolution entry called by `Handler.do_POST`, with the raw Mott gate enabled for the week-of case. Coverage includes week-of, gibberish default window and signal, Monday next week, bare Thursday, in two weeks, datetime from/to, and missing-value default window (`gwtest/tests/test_bland_gateway.py:291-346`). The HTTP handler test also proves gibberish returns 200, the CLI receives `08/04/2026..08/17/2026`, raw gibberish is absent from argv, and the result carries `from_unresolved:true` (`gwtest/tests/test_bland_gateway.py:348-385`).

`proof_live_path.py` is standalone and invokes `build_argv` with Mott raw-text pre-normalization enabled. Frozen time is 2026-08-04.

Proof output tail:

```text
CASE=week-of-18th FROM=2026-08-17
CASE=gibberish UNRESOLVED=true
CASE=monday-next-week FROM=2026-08-10
```

Full-suite output tail, run from `./gwtest`:

```text
............................................. [ 52%]
........................................                                 [100%]
85 passed, 33 warnings, 27 subtests passed in 0.55s
```

The 33 warnings are the pre-existing Python date parsing deprecation warning at `container/bland_gateway.py:803`; there are no test failures.

## Gate state

This is an offline local artifact only. Deployment and a new live gate run are separately gated and were not performed.
