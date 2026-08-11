# Runtime-dead goal-loop diagnosis

## Observed failure

The live Bland v97 chat routed every input, including the first `hi`, to `e_close`. The terminal emitted the literal `{{close_text}}`.

## Root cause and exact mechanism

`n_identity` remained the sole `isStart: true` node and retained v92's silent webhook settings, but the graph edges no longer encoded the webhook conditions that Bland uses for routing. In v92, the success edge `edge-n_identity-n_appt_check-count-1` is labeled and described with the executable condition `count == 1`. The draft replaced that with `edge-n_identity-n_appt_check-identity-succeeds-uniquely`, whose label was the prose `identity succeeds uniquely`. The failure edge to the shared terminal was likewise collapsed to prose. Bland could not match the successful identity response to the success edge, so it selected the terminal branch `n_identity -> e_close` instead of advancing to `n_appt_check`.

The same violated convention existed one node later: v92 uses `appt_count == 0` on `n_appt_check -> n_ask` and `appt_count >= 1` on `n_appt_check -> e_defer`; the draft used prose labels on `n_appt_check -> n_goal_update` and `n_appt_check -> e_close`. The repair restores one edge per `responsePathways` condition, with labels/descriptions in v92's exact `variable operator value` encoding. The intended entry is now `n_identity (count == 1) -> n_appt_check (appt_count == 0) -> n_goal_update`; `appt_count >= 1` routes to the literal office-deferral terminal.

`e_close.data.text` was independently invalid. It contained `{{close_text}}`, but no extraction, webhook `responseData`, or production `request_data` field named `close_text` existed. Bland therefore rendered the token literally. Because the 13-node contraction has one terminal, its runtime text is now the literal v92 `e_defer` copy; it no longer depends on an unproduced mode variable.

## Placeholder repair

Nine unique unproduced variables were found: four in patient-facing prompt/text (`date_candidate_1_en`, `date_candidate_2_en`, `selected_slot_day_name`, `close_text`) and five in webhook bodies (`user_verbatim`, `time_pref`, `selection_update`, `suppression_reason`, `conversation_id`). Gateway display fields now have `responseData` producers. Unsupported redundant inputs were removed, suppression uses literal safe metadata, `callID` supplies idempotency scope, and terminal copy is literal.

The validator now ports v91 assertion `[20]` producer accounting and applies it to every `prompt`, `text`, and webhook `body`. It also asserts v92 entry start/silent flags and exact correspondence between entry `responsePathways` and condition-encoded edges.
