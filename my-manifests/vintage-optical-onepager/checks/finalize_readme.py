#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys

OLD="""## One-pager status

Not generated yet. The canonical intake still requires two confirmations that should not be guessed:

1. `owner_intent`: `grow`, `hold`, or `tighten`
2. `existing_client_check`: whether Vintage Optical is already a MyBCAT client

Known fields are already available: practice name, website, full location, and `public_only` data mode.
"""
NEW="""## One-pager status

Generated and technically validated using the canonical GROW-lane process after Ankit confirmed `owner_intent: grow` and `existing_client_check: not an existing MyBCAT client`.

- Client artifact: `onepager.pdf` (exactly one US Letter page)
- Editable source: `onepager.html`
- Score record: `scores.json`
- Public evidence: `data/evidence.md` and `data/sources.json`
- QA render: `onepager-qa.png`
- Run receipt: `runlog.md`
- Client Opportunity: 66, Practice Competitiveness: 72, Room to Win: 44, Confidence C
- Final fresh-context review: READY, no fatal or material issues

The human delivery gate remains pending. No external delivery occurred.
"""

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--readme',required=True); args=ap.parse_args()
    p=Path(args.readme); t=p.read_text(encoding='utf-8',errors='replace')
    if OLD not in t:
        print('WHY: expected stale one-pager status block not found'); return 1
    p.write_text(t.replace(OLD,NEW),encoding='utf-8')
    print('PASS: README one-pager status updated')
    return 0

if __name__=='__main__': sys.exit(main())
