# Pathway V65

## Changes

- Added weekday names to both English and Chinese standard and nearest-slot offers, including offer-node context.
- Added `n_date_conflict` to ask patients to choose between two disagreeing dates while preserving `preference_from` and `day_part` extraction.
- Added availability conflict response mappings and routed detected conflicts to the clarification node before slot-count routing.

## Verify

- Nodes: 42
- Edges: 113
