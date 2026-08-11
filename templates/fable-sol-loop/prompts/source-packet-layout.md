# Source packet staging

All round inputs are explicit read-only copies under that round's task directory. Never point a Fable prompt at an absolute path or another round's live task directory.

## Round 1: fable-map

- `sources/brief.md`: the explicitly curated brief copied by `new_run.py`.
- `sources/answers.md`: the operator's verbatim answer when a prior Fable QUESTION is being resumed; otherwise the generated no-answer marker.
- Optional curated repo excerpts. Do not stage secrets, credential files, arbitrary home-directory content, or an automatic repository copy.

## Round 2: sol-build

- `sources/decision-packet.json`: validated copy of round 1 output.
- Optional convention files or repo excerpts selected by the operator.

Sol reads the explicitly named repository checkout directly because its manifest has narrowly bounded writable roots. The path passed to the generator as `--source-repo` must already have clean Git state. Never pass a dirty live checkout directly. First copy the intended source state into an operator-approved disposable Git snapshot, make that snapshot clean, and confirm Git porcelain is empty there before generation.

## Round 3: fable-review

- `sources/decision-packet.json`: validated round 1 packet.
- `sources/status.json` and `sources/notes.md`: validated round 2 artifacts.
- `sources/answers.md`: the operator's verbatim answer when a prior round-3 QUESTION is being resumed; otherwise the generated no-answer marker.
- `sources/changed/`: curated changed-file copies or diff excerpts needed to assess material findings.

Run round 3 only when `status.json.review_required` is true. The evidence cited by every finding must exist beneath `sources/`.

## Round 4: sol-close

- `sources/decision-packet.json` and `sources/status.json`.
- Exactly one of `sources/review.json` or `sources/skip-notice.json`.

The skip notice comes only from `validate_sol_status.py` when every objective gate rule is false. It is never hand-written approval.

## QUESTION transport

Workers are headless. A valid Fable QUESTION ends its round successfully. Hermes asks the single question, then stages the verbatim answer in the emitting Fable round's `sources/answers.md` and reruns that round when the answer changes its output. Sol never asks Ankit directly.
