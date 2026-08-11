# Runtime-dead goal loop, round 2

## Root cause

The original `n_goal_update` was a patient-facing `Default` node with `userWait: true`, only `newTemperature` in `modelOptions`, and a scheduling prompt containing the opening and conversational instructions. Its `n_goal_update -> n_availability` edge was `edge-n_goal_update-n_availability-accepted-scheduling-update-1-through-8-including-every-usable-clarified`, whose label was descriptive prose rather than a condition matching a `responsePathways` entry. Bland therefore rendered the node prompt and yielded for another patient message. It never had an executable same-turn transition into `n_availability`, which explains both observed outcomes: the date follow-up question and the latest-slot promise paraphrase without a webhook call.

## Violated v92 convention

In v92, `n_identity` and `n_appt_check` are silent processors: `text` is empty, `modelOptions.skipUserResponse` is `true`, `retryAttempts` is `0`, and every `responsePathways` condition has a byte-shaped condition edge such as `count == 1` or `appt_count == 0`. The old `n_goal_update` had none of those auto-advance guarantees.

## Repair

- `n_goal_update` is now explicitly silent, has empty `text`, `userWait: false`, `skipUserResponse: true`, and `retryAttempts: 0`.
- Its pathway `goal_update_v94 != "" -> n_availability` is encoded by executable edge `edge-n_goal_update-n_availability-goal-update-v94`.
- `n_appt_check` now routes the unbooked entry to patient-facing `n_goal_response`, which owns the literal opening. Booked and failed checks still defer through `e_close`.
- The validator now enforces silence/no-wait/auto-advance for processor nodes and producer coverage for every prompt/text/body placeholder.

## Offline proof

- Regenerated graph: 13 nodes, 41 edges.
- Validator: `PASS: 249 assertions`.
- Fixtures: conformant green; A through E red on their locked target gates.
- Placeholder audit: 53 references, 0 unproduced before repair, 0 unproduced after repair; no placeholder substitutions were needed.
- Banned patient-facing promise phrases: 0.
