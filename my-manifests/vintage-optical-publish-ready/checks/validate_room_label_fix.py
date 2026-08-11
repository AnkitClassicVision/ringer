#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); a=ap.parse_args(); r=Path(a.report); fail=[]
    comp=json.loads((r/'data/competitor_set.json').read_text())
    if comp.get('project_room_status')!='inventory_review_required': fail.append('competitor_set project_room_status stale')
    intake=(r/'intake.md').read_text(); fresh=(r/'data/fresh_review.md').read_text(); research=(r/'data/research_notes.md').read_text()
    for name,text in [('intake',intake),('fresh_review',fresh),('research_notes',research)]:
        if 'inventory_review_required' not in text: fail.append(f'{name} missing current room state')
    for banned in ['EMPTY / UNROOMED','empty/unroomed','NOT CLIENT-READY','NOT PROSPECT-READY','not client-ready','client-ready language']:
        if banned in intake or banned in fresh or banned in research: fail.append(f'stale/banned phrase remains: {banned}')
    if 'External actions: none.' not in fresh: fail.append('fresh review external action boundary missing')
    if fail: [why(x) for x in fail]; return 1
    print('PASS: competitor data and historical notes distinguish initial state from current inventory_review_required with no stale external-readiness labels')
    return 0
if __name__=='__main__': sys.exit(main())
