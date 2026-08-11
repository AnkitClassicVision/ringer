# v58 Builder

## Summary

- Preserves every week qualifier, including clipped shorthand, and maps vague next-week requests to the qualified Monday-through-Friday span.
- Maps explicit clock times with no other part-of-day wording at the approved 3pm boundary using only `morning`, `afternoon`, `late`, or `none`.
- Keeps the v57 graph structure, routing, prompts, bodies, and variable names unchanged.

## Changes

| Location | Old instruction | New instruction |
|---|---|---|
| Builder comment near `PREFERENCE_VARS` | Vague week becomes bare `monday..friday`. | Vague next week becomes `monday next week..friday next week`. |
| `preference_from` description | Clipped `tues nxt wk` must become bare `tuesday`; fallback wording was contradictory. | Every week qualifier is preserved; clipped variants become `tuesday next week`; vague next week becomes `monday next week`; unqualified weekdays stay bare. |
| `preference_to` description | Vague weeks ended at bare `friday`. | Vague next week ends at `friday next week`; unqualified weekdays stay bare. |
| `day_part` description | Five-token guidance, with vague clock handling and late after 4. | Four-token guidance: before noon is `morning`, noon to 2:59pm is `afternoon`, and 3pm or later is `late` when no other part-of-day wording is present. |
| Output path | `v57_graph.json` | `v58_graph.json` |

## Verified

- Ran `PYTHONDONTWRITEBYTECODE=1 python3 build_v58.py`: generated 40 nodes and 111 edges.
- Compared v58 with `source/v57_graph.json`: all 23 differences are existing `extractVars` description strings; node set, edges/routing, prompts, bodies, and variable names/types are unchanged.
- Verified confirmation is entered only from `n_book_1`/`n_book_2`; each book node only from its matching verify node; opt-out exits only from their suppression nodes.
- Ran a negative control proving the comparator rejects a non-description edge change.
- Verified required temporal/day-part guidance is present and forbidden stripping/stale text is absent from builder and JSON.

## Assumptions

- “Every clipped variant” is handled by expanding recognized weekday and week shorthand to the same full qualified form.
- No API, mint, commit, or live pathway run was needed or performed.
