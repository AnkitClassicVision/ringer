# Round 4 debug record

## Exact `hi` to close mechanism

The derived graph kept `n_appt_check.data.responsePathways[1]` pointing to retired node
`n_ask` (`appt_count == 0 -> n_ask`), but emitted edge
`edge-n_appt_check-n_goal_response-derived-48` for
`appt_count == 0 -> n_goal_response`. After `n_identity` silently resolved the patient through
`edge-n_identity-n_appt_check-count-1`, the appointment webhook selected the missing `n_ask`
pathway. Bland could not follow that target in the 34-node graph and fell through to the close
behavior. The patient's `hi` was therefore never handled by the scheduling loop.

The violated v92 convention is that a silent webhook's `responsePathways` destination and its
custom edge destination/condition are the same existing node. The repair changes both executable
representations to `appt_count == 0 -> n_goal_response`; `appt_count >= 1 -> e_defer` remains the
booked guard, and `ok != true -> e_defer` is fail-safe. `n_identity` remains the sole `isStart`
node with `text: ""`, `skipUserResponse: true`, and its proven `count == 1 -> n_appt_check` pair.

## Respond-layer repair

`n_goal_search.responseData` is copied byte-for-byte from working `n_search`, including both
`slot_N_start` and `slot_N_day_name` producers. `n_goal_response` starts from working `n_offer`,
contains the exact protected two-slot template, the D4 paragraph, explicit MM/DD/YYYY preservation,
literal-template rendering, and one-message/no-promise-tail discipline. Two unsafe confirmation
uses of `slot_N_start` without `slot_N_day_name` were repaired in `n_gate_1` and `n_gate_2`.
