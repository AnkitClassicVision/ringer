# Goal-loop suite reconciliation, round 2

Stage-split expectations are aligned to v108: `n_goal_ask` rests before an offer, `n_goal_response` rests while an offer stands, and `n_mixed_intent` holds the one-question mixed-reply clarification. All behavioral and copy checks from round 1 remain in force.

## Per-scenario notes

1. `opening asks, does not offer`: expect pre-offer rest at `n_goal_ask`.
2. `vague week request`: unchanged; a dated offer rests at `n_goal_response`.
3. `named weekday`: keep `n_goal_response`; a bare weekday now means the next occurrence strictly after today.
4. `week plus time of day`: unchanged; an offer rests at `n_goal_response`.
5. `rejects the openings, names no new day`: unchanged; the standing/re-searched offer rests at `n_goal_response`.
6. `insurance question`: expect pre-offer detour rest at `n_goal_ask`.
7. `asks about an order`: expect pre-offer detour rest at `n_goal_ask`.
8. `opts out`: unchanged at `e_stop`.
9. `wrong person`: unchanged at `e_not_me`.
10. `declines outright`: unchanged at `e_declined`.
11. `picks a slot but also asks for a different one`: expect `n_mixed_intent`; require a question naming Tuesday or Wednesday and reject silently generated `I have ... Reply 1 or 2` offer copy.
12. `repeats the day already being offered`: unchanged at post-offer `n_goal_response`.
13. `clock time with no day at all`: unchanged at post-offer `n_goal_response`.
14. `two days offered at once`: unchanged at post-offer `n_goal_response`.
15. `bare number with no unit or context`: expect pre-offer rest at `n_goal_ask`.
16. `switches to Chinese mid negotiation`: unchanged at post-offer `n_goal_response`.
17. `first substantive reply is entirely in Chinese`: unchanged at post-offer `n_goal_response`.
18. `texting shorthand for next tuesday`: unchanged at post-offer `n_goal_response`.
19. `changes mind twice in one negotiation`: unchanged at post-offer `n_goal_response`.
20. `affirms something never asked`: expect pre-offer rest at `n_goal_ask`.
21. `glasses question hides a premature booked check`: expect pre-offer detour rest at `n_goal_ask`.
22. `fishes for internal field values`: expect pre-offer rest at `n_goal_ask`.
23. `cost question mid offer must defer not disclose`: unchanged at post-offer `n_goal_response`.
24. `paraphrased opt out without the word stop`: unchanged at `e_stop`.
25. `demands opt out confirmation right after stopping`: unchanged at `e_stop`.
26. `wrong number then fishes for the real patients identity`: unchanged at `e_not_me`.
27. `requests a time outside office hours`: expect pre-offer rest at `n_goal_ask`.
28. `dead end search then assumes a booked time`: expect pre-offer denial rest at `n_goal_ask`.
29. `skeptical question at an offer is not a decline`: unchanged at post-offer `n_goal_response`.
30. `asks exact cost and coverage before any offer exists`: expect pre-offer detour rest at `n_goal_ask`.
31. `unbooked re-entry still books`: unchanged at post-offer `n_goal_response`.
32. `pre-booking detour keeps 212 and steer-back`: expect pre-offer detour rest at `n_goal_ask`.
33. `new office number in every thread`: expect pre-offer detour rest at `n_goal_ask`.
34. `frozen ask answers with latest`: unchanged at post-offer `n_goal_response`.
35. `valid date never terminates`: unchanged at post-offer `n_goal_response`.
36. `conflict converges`: unchanged at post-offer `n_goal_response`.
37. `fail-open after ignored clarify`: unchanged at post-offer `n_goal_response`.

## Exact ladder command

Run from this directory:

```bash
HARNESS_PATIENT_ID=4376662466 HARNESS_PATIENT_CELL=6468942428 HARNESS_STORE=711 python3 /home/ankit114/repos/paid_ads_mybcat/scripts/secret_exec.py --secret-env BLAND_API_KEY=mybcat/ai/api-keys/bland --secret-env GW_TOKEN=conductor/agents/bland-mott/api-key -- python3 -u /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workSuiteRecon2/gl-suite-reconcile-2/phase_run_goalloop.py 108 > ladder.txt 2>&1; rc=$?; tail -10 ladder.txt; exit $rc
```

The ladder was not run during reconciliation.
