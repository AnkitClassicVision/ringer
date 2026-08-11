#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import fitz

def why(m): print(f'WHY: {m}')
def run(cmd):
    x=subprocess.run(cmd,text=True,capture_output=True)
    if x.returncode: print(x.stdout+x.stderr,end=''); raise SystemExit(x.returncode)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--receipt',required=True); ap.add_argument('--room',required=True); a=ap.parse_args(); r=Path(a.report); fail=[]
    req=['onepager.pdf','number-explainer.pdf','data/release-verdict.json','data/release-verdict.md','data/final-reviews/numeric-review.json','data/final-reviews/numeric-review.md','data/final-reviews/logic-review.json','data/final-reviews/logic-review.md','data/final-reviews/render-review.json','data/final-reviews/render-review.md','README.md','runlog.md']
    for f in req:
        if not (r/f).is_file() or (r/f).stat().st_size<100: fail.append(f'missing or undersized {f}')
    receipt=json.loads(Path(a.receipt).read_text()); room=json.loads(Path(a.room).read_text()); runlog=(r/'runlog.md').read_text(); readme=(r/'README.md').read_text()
    if receipt.get('highest_true_state')!='READY_FOR_PROJECT_ROOM_REVIEW' or receipt.get('external_use_authorized') is not False: fail.append('final receipt state invalid')
    if room.get('status')!='inventory_review_required' or room.get('last_reviewed_at') is not None: fail.append('Project Room human gate state invalid')
    if 'READY_FOR_PROJECT_ROOM_REVIEW' not in readme: fail.append('README state missing')
    for token in ['Highest true state: READY_FOR_PROJECT_ROOM_REVIEW','Fatal issues: none','Material issues: none','Minor issues: none','External use authorized: no','approve the source inventory']:
        if token.lower() not in runlog.lower(): fail.append(f'runlog missing {token}')
    if 'not yet run' in runlog.lower(): fail.append('stale not-yet-run marker remains')
    text_files=[p for p in r.rglob('*') if p.is_file() and p.suffix.lower() in {'.md','.json','.html','.txt'}]
    leaks=[]
    for p in text_files:
        try: text=p.read_text()
        except UnicodeDecodeError: continue
        if 'CANARY' in text: leaks.append(str(p.relative_to(r)))
    if leaks: fail.append(f'canary leaked in {leaks}')
    if len(json.loads((r/'data/sources.json').read_text())['sources'])!=25: fail.append('source count not 25')
    if len(fitz.open(r/'onepager.pdf'))!=1 or len(fitz.open(r/'number-explainer.pdf'))!=11: fail.append('page counts are not 1/11')
    reviews=[json.loads((r/f'data/final-reviews/{n}-review.json').read_text()) for n in ['numeric','logic','render']]
    if any(x.get('verdict')!='PASS' or x.get('fatal_issues') or x.get('material_issues') or x.get('minor_issues') for x in reviews): fail.append('one or more final reviews not clean PASS')
    if fail: [why(x) for x in fail]; return 1
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_release_verdict.py','--dir',str(r/'data')])
    run(['python3','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_integrated_s18.py','--report',str(r),'--receipt','/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/work-integrate-s18/integrate-s18-lineage-and-rerender/integration_receipt.json'])
    print('PASS: closed packet has clean final reviews, canary-safe release verdict, 1/11 Letter PDFs, 25-source lineage, READY_FOR_PROJECT_ROOM_REVIEW state, and blocked external use')
    return 0
if __name__=='__main__': sys.exit(main())
