# V63 Prompt Fix

## Summary

- Added compound-date priority and no-weekday-derivation rules to `preference_from`.
- Added matching compound-date propagation to `preference_to`.
- Updated the builder output to `v63_graph.json`.

## The Changes

> If the patient said both a relative word like tomorrow and a month and day like july 28th, write ONLY the month and day. The month and day is more specific. Drop the relative word. For example, tomorrow july 28th becomes july 28th, and tuesday july 28 becomes july 28.

> Never derive a weekday from a relative word: if they said tomorrow, write tomorrow, never tuesday. Never derive a weekday from a date: if they said july 28th, write july 28th, never tuesday. If they said day after tomorrow, write day after tomorrow, never a weekday.

The `preference_to` description now repeats the month and day selected from a compound phrase.

## Graph Diff

V63 matches V62 at 41 nodes and 111 edges. The graph's only leaf-value differences are the propagated `preference_from` and `preference_to` extraction descriptions.
