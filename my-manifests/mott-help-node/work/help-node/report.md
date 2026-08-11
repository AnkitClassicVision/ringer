# HELP Node

## Summary

- Added `n_help` as a global, auto-returning HELP/INFO response.
- The reply identifies Mott Optical, supplies the office number, includes STOP guidance, and follows the patient's language.
- Existing booking, suppression, offer, and confirmation paths remain unchanged.

## The Node

Global label: “The patient texts HELP, INFO, or a bare request for help or more information.”

Message: “This is Mott Optical's appointment scheduling assistant. For help, call (855) 750-6688. Reply STOP to opt out.”

## Additive Proof

I generated `v62_graph.json`, removed `n_help` in memory, and compared the remaining graph with the source `v61_graph.json`; they were identical. I also confirmed that only `n_book_1` and `n_book_2` can reach `n_confirm`, while `e_stop` and `e_not_me` remain reachable only through their existing suppression nodes.

## Assumptions

The pathway's global intent classifier treats HELP, INFO, and bare help/information requests as the new pathway-level response without replacing Twilio carrier behavior. Global auto-return resumes the prior booking node after the one-line response.
