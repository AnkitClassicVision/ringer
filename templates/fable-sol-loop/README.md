# Fable to Sol OAuth Loop

## What it is

This Blueprint is a four-round, single-purpose Ringer workflow. Fable maps the consequential decisions, Sol Ultra builds inside explicit ownership, an objective validator decides whether Fable review is required, and Sol closes reviewed findings or records a generated review skip. All four manifests share one run name so Ringside presents one evolving job.

## Use it when

Use this kit for a bounded repository feature where product intent, architecture, security/privacy, public API, data contract, or other user-visible decisions should stay with Fable while implementation and empirical proof belong to Sol. It is especially useful after the operator has prepared a clean disposable Git snapshot so the live checkout remains untouched.

Skip it for a tiny reversible edit, an unbounded product-discovery session, a task that needs interactive mid-round clarification, or any job that cannot be expressed with narrow owned paths and executable local verification.

## Locked four-round shape

1. `fable-map` uses `claude-lean` with model `fable`, reads staged copies only, and writes `decision-packet.json`.
2. `sol-build` uses Codex with model `gpt-5.6-sol` and ultra reasoning, edits only the declared owned paths, and writes `status.json` plus `notes.md`.
3. `fable-review` uses the same Fable OAuth lane only when the round-two validator sets `review_required=true`; it writes `review.json`.
4. `sol-close` uses the same Sol OAuth lane, closes Fable findings or consumes the generated skip notice, reruns verification, and writes `receipt.json`.

Rounds 1 and 3 have no repository writable roots. Rounds 2 and 4 receive only the resolved owned paths. Every task sets `full_access=false`. OAuth failure means `STOP_NO_API_FALLBACK`; there is no direct provider, key-based, alternate-provider, or local-model fallback.

The current Ringer manifest schema has no per-task attempts field. Its task runner fixes `max_attempts = 2`, and the focused suite asserts that implementation before accepting generated manifests. The kit does not add an ignored manifest property that would imply control Ringer does not expose.

## HOLD and QUESTION are controlled outputs

A structurally complete Sol `HOLD` exits its validator with status 0. That makes the boundary visible without retry pressure. Sol completes all safe remaining work, records evidence and tradeoffs, and routes the unknown to Fable or the explicit approval owner. Sol never asks Ankit directly and never accepts its own work.

Only Fable rounds may emit a QUESTION. The JSON packet carries one question, why it is needed now, the consequence of a wrong answer, at least two options with exactly one default, and the effect of waiting. Hermes relays it between rounds. A clean run needs zero questions and one launch approval; the worst case is one question per Fable round.

## Objective review gate

`validate_sol_status.py` computes the boolean. Review is required for any HOLD, material deviation or out-of-owned-path change, touch of a Fable-owned path selector, or unclean verification. A clean READY generates `skip-notice.json`; a skip is never silent or authored by Sol.

The status validator also re-executes every READY verification command, compares `diff_summary.paths_touched` with git porcelain, and rejects ownership violations. Verification commands must exactly match the Fable decision packet, use a named verifier family, and cannot grant mutation, external, deployment, scheduling, package-install, or source-control authority. Re-execution requires local util-linux `unshare` plus Bubblewrap (`bwrap`): `unshare` supplies an empty network namespace, and Bubblewrap supplies a temporary copy-on-write repository overlay with user-data locations hidden. The validator fails closed rather than execute with host networking or without the filesystem sandbox.

## Generator

Run `new_run.py` with a lowercase project slug, an explicit clean Git checkout or operator-approved clean disposable Git snapshot, one or more repo-relative owned paths, one curated UTF-8 brief, and an output directory outside the source repo. The path passed as `--source-repo` must itself have clean Git state. The generator writes the four filled manifests, inlined and staged prompts, validators, input metadata, and per-round `sources/` scaffolding. It never copies an arbitrary repository or searches for secrets.

The generator rejects every dirty source repository and has no bypass or operator-attestation flag. Never pass a dirty live checkout directly as `--source-repo`. First copy the intended source state into an operator-approved disposable Git snapshot, make that snapshot clean, and confirm `git status --porcelain=v1 --untracked-files=all` is empty there before generation.

Before launching the four-round wave, run the existing `probe` kit once against each logged-in OAuth lane. A failed preflight is a stop condition, not permission to substitute a route.

## Source transitions

Read `prompts/source-packet-layout.md`. Round outputs are copied into the next round's `sources/` directory after their validators pass. Absolute cross-round paths are intentionally absent because Fable safe mode reads only staged task-local copies.

## Proof

From the Ringer repository root:

```bash
python3 -m unittest discover -s templates/fable-sol-loop/tests -p 'test_kit.py' -v
```

The focused suite executes the generator, parses and lints every generated manifest with the current `ringer.py` functions, exercises all packet shapes and invalid fixtures, proves HOLD exits 0, checks both review-gate outcomes, and reruns receipt verification.
