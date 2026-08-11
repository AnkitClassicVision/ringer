# New scenarios for the Mott Optical booking pathway (v39_graph.json).
# Focus: ambiguous, mixed or awkward patient replies that the existing
# pathway_harness.py SCENARIOS list does not cover. Same format as that
# list: each entry is checked by matching pathway_harness.run_scenario.
#
# No scenario here ends on n_confirm or e_booked; several are expected to
# be genuinely ambiguous and may legitimately fail when run.

NEW_SCENARIOS = [
    {"name": "picks a slot but also asks for a different one",
     "turns": ["hi", "can I come tuesday?", "yes 2 works but do you have anything wednesday instead?"],
     "expect_node": "n_offer",
     "expect_text": r"which|mean|clarify",
     "why": "the offer prompt requires asking which they meant when a reply both selects an "
            "opening and asks for a different time; silently booking slot 2 here would write an "
            "appointment the patient never clearly consented to."},

    {"name": "repeats the day already being offered",
     "turns": ["hi", "can I come tuesday?", "tuesday works"],
     "expect_node": "n_offer",
     "why": "'tuesday works' repeats the day already on offer without picking slot 1, 2 or a "
            "specific time; misreading it as a request for a different day would trigger a "
            "pointless re-search, and misreading it as a pick would book without a chosen time"},

    {"name": "clock time with no day at all",
     "turns": ["hi", "after 3pm works for me"],
     "expect_node": "n_offer",
     "expect_vars": {"preference_from": "monday", "preference_to": "friday",
                      "preference_after": "3pm"},
     "why": "a bare clock time with no day named must still populate the required monday to "
            "friday default window and carry the 3pm floor through, not leave the search "
            "fields blank because no weekday was ever spoken"},

    {"name": "two days offered at once",
     "turns": ["hi", "monday or wednesday works, whichever you have open"],
     "expect_node": "n_offer",
     "expect_vars": {"preference_from": "monday", "preference_to": "wednesday"},
     "why": "naming two candidate days in one reply must be captured as a monday-to-wednesday "
            "span for the search, not silently collapsed to only one of the two days named"},

    {"name": "bare number with no unit or context",
     "turns": ["hi", "2"],
     "expect_node": "n_ask",
     "why": "a lone digit with no am/pm, weekday or date word is not an answer about timing; "
            "guessing it means 2pm, the 2nd of the month, or slot 2 before any offer exists "
            "would search or route on an invented meaning nobody actually said"},

    {"name": "switches to Chinese mid negotiation",
     "turns": ["hi", "can I come tuesday?", "其实周三比较方便"],
     "expect_node": "n_offer",
     "expect_text": r"[一-鿿]",
     "why": "the patient switches languages mid-thread while asking for a different day; the "
            "negotiate and offer steps must reply in Chinese from that turn on, not keep "
            "answering in English because the conversation opened in English"},

    {"name": "first substantive reply is entirely in Chinese",
     "turns": ["hi", "我想约下周二上午"],
     "expect_node": "n_offer",
     "expect_text": r"[一-鿿]",
     "why": "the very first patient reply arrives in Chinese with no prior English turn from "
            "them; the offer step must respond in Chinese immediately rather than defaulting "
            "to English because no earlier message 'established' the language"},

    {"name": "texting shorthand for next tuesday",
     "turns": ["hi", "tues nxt wk"],
     "expect_node": "n_offer",
     "expect_vars": {"preference_from": "tuesday", "preference_to": "tuesday"},
     "why": "clipped texting shorthand for 'Tuesday next week' names one exact day; failing "
            "to parse it must not fall back to the blank-default monday-friday span, which "
            "would erase the specific day the patient actually asked for"},

    {"name": "changes mind twice in one negotiation",
     "turns": ["hi", "can I come tuesday?", "actually wednesday instead",
               "no, let's stick with tuesday after all"],
     "expect_node": "n_offer",
     "why": "two consecutive reversals in one thread must still resolve to a fresh search for "
            "the last-stated day, tuesday; getting stuck offering wednesday, or erroring out "
            "from the flip-flopping, would strand a patient who was just thinking out loud"},

    {"name": "affirms something never asked",
     "turns": ["hi", "yes that's fine"],
     "expect_node": "n_ask",
     "expect_text": r"when would you like|what day|come in",
     "why": "'yes that's fine' answers no question this pathway has posed and names no timing "
            "at all; treating it as consent to book, or as picking an opening that was never "
            "offered, would move the conversation forward on nothing the patient actually said"},
]
