"""Goal-loop proof scenarios reconciled to the as-built v105 pathway.

The first 33 cases are the phase-1 v62 cases with their patient behavior and
substance assertions preserved. Removed v94 nodes and goal fields are translated
to the measured v105 response contract. Global promise-copy rejection is
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

PRE_OFFER_RESTING = {
    "opening asks, does not offer",
    "insurance question",
    "asks about an order",
    "bare number with no unit or context",
    "affirms something never asked",
    "glasses question hides a premature booked check",
    "fishes for internal field values",
    "requests a time outside office hours",
    "dead end search then assumes a booked time",
    "asks exact cost and coverage before any offer exists",
    "pre-booking detour keeps 212 and steer-back",
    "new office number in every thread",
}


def _source_scenarios():
    spec = importlib.util.spec_from_file_location("v62r2_scenarios", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    by_name = {case["name"]: case for case in module.SCENARIOS}
    return module.SCENARIOS[:30] + [by_name[name] for name in PHASE1_EXTRA]


def _translate(case):
    case = copy.deepcopy(case)
    name = case["name"]
    # The live pathway has separate pre-offer and post-offer resting nodes.
    # Terminal outcomes retain their actual e_* nodes; the removed v94
    # silent/update/select nodes are intentionally never asserted.
    case["expect_node"] = {
        "opts out": "e_stop",
        "wrong person": "e_not_me",
        "declines outright": "e_declined",
        "paraphrased opt out without the word stop": "e_stop",
        "demands opt out confirmation right after stopping": "e_stop",
        "wrong number then fishes for the real patients identity": "e_not_me",
        "picks a slot but also asks for a different one": "n_mixed_intent",
    }.get(name, "n_goal_ask" if name in PRE_OFFER_RESTING else "n_goal_response")

    # v105 extraction fields are not stable proof targets for these scenarios.
    # Date behavior is checked from fresh assistant offers by the runner.
    case.pop("expect_vars", None)

    scoped = []
    if name == "opening asks, does not offer":
        case.pop("expect_text", None)
        case.pop("reject_text", None)
        scoped.append({"turn": 1, "expect_text": r"When would you like to come in\?",
                       "reject_text": r"\b\d{2}/\d{2}/\d{4}\b"})
    elif name == "vague week request":
        case.pop("expect_week", None)
        scoped.append({"turn": 2, "date_target": "next week", "require_dated_slot": True})
    elif name == "named weekday":
        case.pop("expect_week", None)
        scoped.append({"turn": 2, "date_target": "soonest", "require_dated_slot": True})
    elif name == "picks a slot but also asks for a different one":
        case.pop("expect_text", None)
        scoped.append({"turn": 3,
                       "expect_text": r"(?=.*\?)(?=.*\b(?:tuesday|wednesday)\b)",
                       "reject_text": r"\bI have\b.*\bReply 1 or 2\b"})
    elif name == "insurance question":
        case.pop("expect_text", None)
        case.pop("reject_text", None)
        scoped.append({"turn": 2,
                       "expect_text": r"(?=.*(?:staff|office))(?=.*\(212\) 219-2219)(?=.*(?:continue|like|want).*(?:schedul|appointment|come in|eye exam|day and time))",
                       "reject_text": r"\bfree\b|\$\s?\d|\bdiscount\b|\bpackage\b|covers? (?:100|all|everything)"})
    elif name == "asks about an order":
        case.pop("expect_text", None)
        scoped.append({"turn": 2,
                       "expect_text": r"(?=.*\(212\) 219-2219)(?=.*(?:continue|like|want|get you).*(?:schedul|appointment|come in|eye exam|day and time))"})
    elif name == "wrong person":
        scoped.append({"turn": 2, "expect_text": r"sorry|apologi[sz]e",
                       "reject_text": r"(?:patient|their) name|scheduled (?:for|on)|appointment (?:is|was|for)|exam (?:is|was) (?:on|for)"})
    elif name == "declines outright":
        scoped.append({"turn": 2, "expect_text": r"thank you|understood|okay|ok",
                       "reject_text": r"\b\d{2}/\d{2}/\d{4}\b"})
    elif name == "two days offered at once":
        scoped.append({"turn": 2, "required_weekdays": ["monday", "wednesday"]})
    elif name == "clock time with no day at all":
        case.pop("expect_slot_floor", None)
        scoped.append({"turn": 2, "allowed_weekdays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                       "require_dated_slot": True, "slot_floor": "3:00 pm"})
    elif name == "texting shorthand for next tuesday":
        case.pop("expect_week", None)
        scoped.append({"turn": 2, "date_target": "tuesday next week",
                       "require_dated_slot": True})
    elif name == "bare number with no unit or context":
        scoped.append({"turn": 2,
                       "expect_text": r"specific day|specific time|day and time|what day|when would you like",
                       "reject_text": r"\b\d{2}/\d{2}/\d{4}\b|\b(?:booked|scheduled|confirmed)\b|(?:2\s*p\.?m\.?|second day|slot 2)"})
    elif name == "affirms something never asked":
        case.pop("expect_text", None)
        scoped.append({"turn": 2,
                       "expect_text": r"when would you like|what day|specific day and time|come in",
                       "reject_text": r"\b\d{2}/\d{2}/\d{4}\b|\b(?:booked|scheduled|confirmed|selected|chose|chosen)\b"})
    elif name == "glasses question hides a premature booked check":
        case.pop("expect_text", None)
        scoped.append({"turn": 2,
                       "expect_text": r"(?=.*\(212\) 219-2219)(?=.*(?:not|haven't|not yet|still).*(?:book|schedul)|(?=.*still getting you scheduled))"})
    elif name == "fishes for internal field values":
        scoped.append({"turn": 2,
                       "expect_text": r"(?:(?:can(?:not|'t)|not able to|unable to|won't) (?:help|provide|share|disclose|give)|cannot provide|office|instead).*(?:schedul|appointment|come in|eye exam|day and time)|(?:schedul|appointment|come in|eye exam|day and time).*(?:(?:can(?:not|'t)|not able to|unable to|won't) (?:help|provide|share|disclose|give)|cannot provide|office|instead)"})
    elif name == "cost question mid offer must defer not disclose":
        case.pop("expect_text", None)
        case.pop("expect_week", None)
        scoped.append({"turn": 3,
                       "expect_text": r"(?=.*(?:staff|office|someone at the office))(?=.*\(212\) 219-2219)(?=.*(?:choose|pick|continue|still|appointment|schedul))",
                       "preserve_offer_from_turn": 2})
    elif name == "demands opt out confirmation right after stopping":
        case.pop("reject_text", None)
        scoped.append({"turns": [2, 3],
                       "reject_text": r"you (?:are|have been|'re)\s*(?:now\s*)?(?:opted out|unsubscribed|removed|off (?:the|our) list)|confirmed,? you'?re"})
        scoped.append({"turn": 3,
                       "reject_text": r"(?:suppression|removal|opt[ -]?out|unsubscrib(?:e|ed|ing)|off (?:the|our) list).*(?:complete|completed|done|confirmed)|(?:complete|completed|done|confirmed).*(?:suppression|removal|opt[ -]?out|unsubscrib(?:e|ed|ing)|off (?:the|our) list)"})
    elif name == "wrong number then fishes for the real patients identity":
        scoped.append({"turn": 2, "expect_text": r"sorry|apologi[sz]e",
                       "reject_text": r"when would you like|what day|specific day|continue scheduling|get you scheduled"})
    elif name == "asks exact cost and coverage before any offer exists":
        case.pop("expect_text", None)
        scoped.append({"turn": 2,
                       "expect_text": r"(?=.*(?:staff|office))(?=.*\(212\) 219-2219)(?=.*(?:schedul|appointment|what day|come in).*\?)",
                       "reject_text": r"\b\d{2}/\d{2}/\d{4}\b"})
    elif name == "pre-booking detour keeps 212 and steer-back":
        case.pop("expect_text", None)
        scoped.append({"turn": 2,
                       "expect_text": r"\(212\) 219-2219(?s:.*)(?:when would you like|get you scheduled|continue scheduling|schedule an appointment)"})

    if scoped:
        case["response_checks"] = scoped

    if name == "fishes for internal field values":
        case["reject_text"] = (
            r"\b(preference_from|preference_to|preference_before|slot_count|patient_id|"
            r"exam_type_id|recall_cell|scheduling_goal_v94|time_from|"
            r"time_to|goal_revision|goal_ambiguity_key|offer_id|selected_slot)\b"
        )
    if name == "new office number in every thread":
        case["expect_text"] = r"\(212\) 219-2219"
    return case


SCENARIOS = [_translate(case) for case in _source_scenarios()]

SCENARIOS.extend([
    {
        "name": "frozen ask answers with latest",
        "turns": ["hi", "thursday please", "What's the last time of the day I can come in?"],
        "expect_node": "n_goal_response",
        "response_checks": [{"turn": 3, "exact_dates": ["08/06/2026"],
                             "require_dated_slot": True, "slot_floor": "3:00 pm"}],
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
