#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
import fitz


def why(x): print(f'WHY: {x}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dest',required=True); a=ap.parse_args(); d=Path(a.dest); fail=[]
    req=['intake.md','data/evidence.md','data/sources.json','data/competitor_set.json','data/market_inputs.json','data/route_receipts.json','scores.json','onepager.html','onepager.pdf','onepager-qa.png','data/onepager-text.txt','runlog.md','README.md','assets/mybcat-logo.png']
    for f in req:
        if not (d/f).is_file() or (d/f).stat().st_size==0: fail.append(f'missing/empty {f}')
    if fail:
        for x in fail: why(x)
        return 1
    doc=fitz.open(d/'onepager.pdf')
    if len(doc)!=1: fail.append(f'PDF pages={len(doc)}, expected 1')
    page=doc[0]; rect=page.rect
    if abs(rect.width-612)>2 or abs(rect.height-792)>2: fail.append(f'PDF not Letter: {rect.width}x{rect.height}')
    text=page.get_text(); low=text.lower(); compact=re.sub(r'\s+','',text).lower(); sc=json.loads((d/'scores.json').read_text())['scores']
    for token in ['Vintage Optical','THE READ','INTERNAL-ONLY','UNROOMED','NOT FOR EXTERNAL USE','YOUR MARKET','YOUR COMPETITION','YOUR OPPORTUNITY','FIRST 30 DAYS','Confidence C']:
        if re.sub(r'\s+','',token).lower() not in compact: fail.append(f'PDF text missing {token}')
    for label,key in [('ROOM TO WIN','room_to_win_score'),('PRACTICE COMPETITIVENESS','practice_competitiveness_score'),('CLIENT OPPORTUNITY','client_opportunity_score'),('DIGITAL PRESENCE','digital_presence_score')]:
        if label.lower() not in low or str(sc[key]) not in text: fail.append(f'PDF missing visible {label} {sc[key]}')
    if 'competitive pressure index' in low or 'competition facing score' in low: fail.append('raw high-bad pressure visible in PDF')
    links=[x.get('uri') for x in page.get_links() if x.get('uri')]
    if len(set(links))<10: fail.append(f'only {len(set(links))} unique PDF links')
    ids=set(re.findall(r'\b(?:S|R)\d{2}\b',text))
    if len(ids)<8: fail.append(f'only {len(ids)} evidence IDs extract from PDF')
    if (d/'onepager.pdf').stat().st_size<40000: fail.append('PDF implausibly small')
    runlog=(d/'runlog.md').read_text()
    for token in ['manual public-only bands','Digital Presence','Fix Cards','Chrome 150','External actions: none']:
        if token.lower() not in runlog.lower(): fail.append(f'runlog missing {token}')
    preliminary='RUN_IDS_PENDING_FINAL_CLOSE' in runlog
    closed=all(token.lower() in runlog.lower() for token in ['Public route collection','Fresh process/release review','Visual QA: PASS','READY_INTERNAL','Highest true state'])
    if not preliminary and not closed: fail.append('runlog is neither preliminary-pending nor fully closed')
    if fail:
        for x in fail: why(x)
        return 1
    print(f'PASS: canonical packet rendered as one Letter page, {len(set(links))} PDF links, {len(ids)} evidence IDs, required scores and internal/unroomed boundary present')
    return 0
if __name__=='__main__': sys.exit(main())
