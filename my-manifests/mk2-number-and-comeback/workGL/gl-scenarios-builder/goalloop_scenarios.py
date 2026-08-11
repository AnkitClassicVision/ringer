"""Goal-loop proof scenarios for the v94 pathway.

The first 33 cases are the phase-1 v62 cases with their patient behavior and
substance assertions preserved.  Only node names and persistent-goal variable
names are translated to the v94 contract.  Global promise-copy rejection is
performed by phase_run_goalloop.py because pathway_harness has no public hook
for a scenario module to extend its ALWAYS_REJECT list.
"""
import copy
import importlib.util


SOURCE = "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workB3/v62r2-lane/scenarios.py"
PHASE1_EXTRA = (
    "unbooked re-entry still books",
    "pre-booking detour keeps 212 and steer-back",
    "new office number in every thread",
)


def _source_scenarios():
    spec = importlib.util.spec_from_file_location("v62r2_scenarios", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    by_name = {case["name"]: case for case in module.SCENARIOS}
    return module.SCENARIOS[:30] + [by_name[name] for name in PHASE1_EXTRA]


SERVICE_CASES = {
    "insurance question",
    "asks about an order",
    "glasses question hides a premature booked check",
    "fishes for internal field values",
    "cost question mid offer must defer not disclose",
    "asks exact cost and coverage before any offer exists",
    "pre-booking detour keeps 212 and steer-back",
    "new office number in every thread",
}
TERMINAL_CASES = {
    "opts out",
    "wrong person",
    "declines outright",
    "paraphrased opt out without the word stop",
    "demands opt out confirmation right after stopping",
    "wrong number then fishes for the real patients identity",
}
OFFER_CASES = {
    "vague week request",
    "named weekday",
    "week plus time of day",
    "rejects the openings, names no new day",
    "repeats the day already being offered",
    "clock time with no day at all",
    "two days offered at once",
    "switches to Chinese mid negotiation",
    "first substantive reply is entirely in Chinese",
    "texting shorthand for next tuesday",
    "changes mind twice in one negotiation",
    "requests a time outside office hours",
    "dead end search then assumes a booked time",
    "skeptical question at an offer is not a decline",
    "unbooked re-entry still books",
}


def _translate(case):
    case = copy.deepcopy(case)
    name = case["name"]
    if name in SERVICE_CASES:
        case["expect_node"] = "n_service_guard"
    elif name in TERMINAL_CASES:
        case["expect_node"] = "e_close"
    elif name == "picks a slot but also asks for a different one":
        case["expect_node"] = "n_select"
    elif name in OFFER_CASES:
        case["expect_node"] = "n_goal_response"
    else:
        case["expect_node"] = "n_goal_update"

    if "expect_vars" in case:
        case["expect_vars"] = {
            {"preference_from": "goal_from", "preference_to": "goal_to"}.get(key, key): value
            for key, value in case["expect_vars"].items()
        }
    if name == "fishes for internal field values":
        case["reject_text"] = (
            r"\b(preference_from|preference_to|preference_before|slot_count|patient_id|"
            r"exam_type_id|recall_cell|scheduling_goal_v94|goal_from|goal_to|time_from|"
            r"time_to|goal_revision|goal_ambiguity_key|offer_id|selected_slot)\b"
        )
    return case


SCENARIOS = [_translate(case) for case in _source_scenarios()]

SCENARIOS.extend([
    {
        "name": "frozen ask answers with latest",
        "turns": ["hi", "thursday please", "What's the last time of the day I can come in?"],
        "expect_node": "n_goal_response",
        "expect_vars": {"goal_from": "thursday"},
        "expect_dated_slots": True,
        "expect_slot_floor": "3:00 pm",
        "why": "A latest-slot refinement must search and offer dated late-day slots, not freeze on the prior ask.",
    },
    {
        "name": "valid date never terminates",
        "turns": ["hi", "I'm out of town the next week how about the week after", "Tuesday the 18th"],
        "expect_node": "n_goal_response",
        "why": "A valid date after a range clarification must return to an offer, never a terminal.",
    },
    {
        "name": "conflict converges",
        "turns": ["hi", "How about next Friday the 17th", "Friday the 14th"],
        "expect_node": "n_goal_response",
        "expect_week": "08/14",
        "why": "A correction after conflicting weekday/date wording must converge on an 08/14 offer.",
    },
    {
        "name": "fail-open after ignored clarify",
        "turns": ["hi", "How about next Friday the 17th", "hmm whatever you think", "just pick something"],
        "expect_node": "n_goal_response",
        "why": "After one clarify and one re-ask, ambiguity must fail open to availability and an offer.",
    },
])
