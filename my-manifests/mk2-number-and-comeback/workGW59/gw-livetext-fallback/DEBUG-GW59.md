# GW59: live-text fallback for time authorities

## What changed

`clamp_availability_range` now evaluates each time authority against
`user_verbatim` first. When that authority produces no result and `user_text`
is non-empty and different, the same authority is evaluated once against
`user_text`. The authority implementations themselves remain single-copy.

The fallback covers meridiem, clock idioms, explicit time windows, day-parts
(including Chinese), and later/earlier relative offer floors. Date authority
behavior was not changed.

## Exact fallback rule

For each time authority:

1. Evaluate `user_verbatim` with all existing trigger and non-trigger guards.
2. If it finds a signal, keep that result and do not consult `user_text`.
3. If it finds no signal, evaluate a non-empty, different `user_text` using the
   same authority and guards.
4. Preserve the existing cross-authority order and explicit-extraction guards.

Meridiem uses an equivalent signal selector because its existing authority
removes an unsupported extractor suffix rather than returning an unchanged
result when evidence is absent.

## Known limitations

`user_text` or the production SMS history fetch can race one turn behind. In
that case the fallback can apply the previous turn's stated time preference.
That is the patient's last stated intent and is acceptable by the lane-59
design ruling. A valid current-turn `user_verbatim` signal always wins, which
limits the fallback to extraction misses or corruption for that authority.
