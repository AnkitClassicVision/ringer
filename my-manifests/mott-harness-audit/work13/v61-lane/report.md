# v61 Panel Rulings Implemented

## Summary

- Corrected week-only extraction guidance on all eight nodes that carry `preference_to`.
- Tightened `clock time with no day at all` to require the deterministic late-band node.
- Extended the candidate gate and redproof to cover the missing week-end-field rule.

## Ruling 1

Final `preference_to` description:

> The last day the patient will accept, in exactly the same forms as preference_from. If they named one day, repeat it here unchanged, INCLUDING any next week qualifier. If they used texting shorthand, expand it to the same full accepted weekday written in preference_from; never pass abbreviations such as tues, nxt or wk through verbatim. If they gave a span, put the later day. If they asked for next week in general with no day, put friday next week. When the patient names a week qualifier but no weekday, preference_from is the week phrase alone and preference_to is friday followed by that same full week qualifier, giving the pair next week through friday next week. A part of day such as morning or afternoon is NOT a weekday and does not change this week-only range. If they named no day and no week at all, put friday. Bare weekdays with no week qualifier stay bare. Never put a clock time here. This field must NEVER be left blank: whenever preference_from is unclear, write unclear here too.

The existing `preference_from` start rule remains byte-identical. The model passes supported phrases through and does not compute calendar dates.

## Ruling 2

```diff
-     'expect_node': ['n_offer', 'n_offer_2'],
+     'expect_node': 'n_offer_3',
```

`expect_slot_floor: '3pm'` and every other scenario field remain unchanged. The scenario inventory remains 30.

## Gate And Redproof Extensions

The temporal invariant now requires every `preference_to` extractor to state that a week qualifier without a weekday ends at Friday with the same full qualifier, including `next week` through `friday next week`.

Redproof adds the mutation `delete preference_to week_end friday_next end_field rule`. The extended gate catches it, and the run reports `mutations_caught=11`. The gate passes `v61_graph.json` and still fails `source/v56_graph.json`.

## Assumptions

- The panel rulings and supplied gateway receipt are authoritative.
- The accepted scheduler grammar remains phrase-based, with no model-side date arithmetic.
- No live API, booking, minting, commit, or external write was required or performed.
