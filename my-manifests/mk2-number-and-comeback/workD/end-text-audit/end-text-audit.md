# End Call patient-text audit

Scope: all 11 nodes whose `type` is `End Call` in pathway version 87. This is a static audit of the exported JSON and incident packet. "Ambiguous reachability" below means a Webhook `responsePathways` condition can route directly to the End node without proving the underlying gateway outcome. It does not mean that any earlier ambiguous read somewhere in a potentially long conversation permanently taints every later End node; a later explicit success can establish a new known state.

## Ranked defects and safe rewording direction

1. **Critical: `e_booking_failed`**. It states a definite negative after `/sign` returns a response that can mean the write outcome is unknown. Reword toward uncertainty: say the booking could not be verified, do not say it failed or did not happen, and ask the patient to call so the office can check before another booking is attempted.
2. **Major: `e_safe_failure`**. It says scheduling could not be accessed and no appointment was booked after negative-form `ok != true` branches. Reword toward the bounded fact that scheduling could not be verified or completed in this conversation, without making an unqualified claim about appointment state; direct the patient to the office to confirm.

`e_stop` and `e_not_me` are reachable on ambiguous suppression-write responses, but their texts do not claim that suppression succeeded or failed. They are therefore not text defects under the stated rule.

## `e_safe_identity`

Outcome: `identity_failed`

Verbatim text:

> I couldn't safely continue this scheduling request. Please call MK2 Optical at (212) 219-2219.

Claims:

- `I couldn't safely continue this scheduling request.`: `definite_negative`
- `Please call MK2 Optical at (212) 219-2219.`: `neutral`

Ambiguous gateway reachability: **No**. The direct routes are missing request inputs or explicit patient-search counts of zero or at least two. `n_identity` sends `ok != true` to `e_safe_failure`, not here.

Defect: **None**. The negative statement is supported by the explicit condition on every inbound edge to this node.

## `e_safe_failure`

Outcome: `gateway_failed`

Verbatim text:

> I couldn't access scheduling right now and no appointment was booked. Please call MK2 Optical at (212) 219-2219.

Claims:

- `I couldn't access scheduling right now`: `definite_negative`
- `no appointment was booked.`: `definite_negative`
- `Please call MK2 Optical at (212) 219-2219.`: `neutral`

Ambiguous gateway reachability: **Yes**.

- `n_identity -> e_safe_failure on ok != true`
- `n_verify_1 -> e_safe_failure on ok != true`
- `n_verify_2 -> e_safe_failure on ok != true`

Each branch can catch a non-2xx response, timeout, malformed body, or missing `$.ok`. The pathway knows that the lookup or conflict check did not report success, not the full external state.

Defect: **Major**. The unqualified statement `no appointment was booked` exceeds what the ambiguous response itself proves, even though these three calls are reads and `/sign` has not been invoked on these routes.

## `e_booking_failed`

Outcome: `booking_failed`

Verbatim text:

> I couldn't confirm that booking. Please call MK2 Optical at (212) 219-2219 so they can check it for you.

Claims:

- `I couldn't confirm that booking.`: `definite_negative`
- `Please call MK2 Optical at (212) 219-2219 so they can check it for you.`: `neutral`

Ambiguous gateway reachability: **Yes**.

- `n_book_1 -> e_booking_failed on book_success != true`
- `n_book_2 -> e_booking_failed on book_success != true`

Both negative-form routes can catch a non-2xx response, timeout, malformed body, or missing `$.success`. A `/sign` write may commit even when the pathway does not receive success.

Defect: **Critical**. The measured incident followed this route on HTTP 502 while the appointment existed in the EMR, proving the patient-facing negative can be false.

## `e_booked`

Outcome: `booked`

Verbatim text:

> Thank you. We look forward to seeing you.

Claims:

- `Thank you.`: `neutral`
- `We look forward to seeing you.`: `definite_positive`

Ambiguous gateway reachability: **No**. `e_booked` follows `n_confirm`, which is entered from `/sign` only on `book_success == true`; its other inbound route is silence after that confirmed-success state.

Defect: **None**. The implied positive appointment state has an explicit success predicate.

## `e_defer`

Outcome: `deferred_after_booking`

Verbatim text:

> For that you'll have to contact the MK2 Optical office at (212) 219-2219

Claims:

- `For that you'll have to contact the MK2 Optical office at (212) 219-2219`: `neutral`

Ambiguous gateway reachability: **No**. Its direct webhook route is `n_appt_check -> e_defer on appt_count >= 1`; other routes come from `n_confirm` after reported booking success.

Defect: **None**. The text is an office-contact direction, not a definite gateway outcome.

## `e_office`

Outcome: `office`

Verbatim text:

> Please call MK2 Optical at (212) 219-2219.

Claims:

- `Please call MK2 Optical at (212) 219-2219.`: `neutral`

Ambiguous gateway reachability: **No**. The only explicit inbound edge is `n_office -> e_office on office direction delivered`; no Webhook response pathway targets this End node.

Defect: **None**. The text contains no system-outcome assertion.

## `e_declined`

Outcome: `declined`

Verbatim text:

> Ok, thank you for letting us know. If you need anything, call the office at (212) 219-2219.

Claims:

- `Ok, thank you for letting us know.`: `definite_positive`
- `If you need anything, call the office at (212) 219-2219.`: `neutral`

Ambiguous gateway reachability: **No**. Every explicit inbound edge is a conversational decline or giving-up route. No Webhook response pathway targets this End node.

Defect: **None**. The positive claim acknowledges patient communication and does not assert a gateway or appointment outcome.

## `e_stop`

Outcome: `stopped`

Verbatim text:

> Understood. If you would like to be taken off our list, please call MK2 Optical at (212) 219-2219 and the office can take care of it.

Claims:

- `Understood.`: `neutral`
- `If you would like to be taken off our list, please call MK2 Optical at (212) 219-2219 and the office can take care of it.`: `neutral`

Ambiguous gateway reachability: **Yes**.

- `n_suppress_stop -> e_stop on suppression_ok != true`

The negative-form branch can catch a non-2xx response, timeout, malformed body, or missing `$.ok`, leaving the suppression-write outcome unknown.

Defect: **None**. The text does not tell the patient that suppression succeeded or failed.

## `e_not_me`

Outcome: `wrong_person`

Verbatim text:

> Sorry about that. If you would like to be taken off our list, please call MK2 Optical at (212) 219-2219 and the office can take care of it.

Claims:

- `Sorry about that.`: `neutral`
- `If you would like to be taken off our list, please call MK2 Optical at (212) 219-2219 and the office can take care of it.`: `neutral`

Ambiguous gateway reachability: **Yes**.

- `n_suppress_not_me -> e_not_me on suppression_ok != true`

The negative-form branch can catch a non-2xx response, timeout, malformed body, or missing `$.ok`, leaving the suppression-write outcome unknown.

Defect: **None**. The text neither confirms nor denies that suppression was recorded.

## `e_existing`

Outcome: `existing_appointment`

Verbatim text:

> Please call MK2 Optical at (212) 219-2219 and the office can help with that appointment.

Claims:

- `Please call MK2 Optical at (212) 219-2219`: `neutral`
- `the office can help with that appointment.`: `definite_positive`

Ambiguous gateway reachability: **No**. This global End node is selected when the patient says an appointment made outside this conversation needs cancellation or movement. No explicit edge or Webhook response pathway targets it.

Defect: **None**. The appointment reference follows a patient-intent route, not an ambiguous gateway response.

## `e_timeout`

Outcome: `no_reply`

Verbatim text:

> Closing this conversation.

Claims:

- `Closing this conversation.`: `neutral`

Ambiguous gateway reachability: **No**. Its explicit inbound edges are 72-hour silence routes from conversational nodes. No Webhook response pathway targets it.

Defect: **None**. It states only the pathway's current conversational action.

## Static-analysis limits

The export shows response conditions and graph edges but not Bland AI's exact runtime treatment of transport failures, missing extracted values, or ordered-condition fallthrough. The audit therefore treats negative-form conditions such as `ok != true`, `book_success != true`, and `suppression_ok != true` as ambiguity-catching, as required by the task and corroborated by the measured 502 incident. No live API, webhook, gateway, or network endpoint was called.
