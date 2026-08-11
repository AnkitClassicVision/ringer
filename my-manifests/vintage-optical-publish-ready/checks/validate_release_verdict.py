#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def why(m): print(f'WHY: {m}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir); fail=[]
    jp=d/'release-verdict.json'; mp=d/'release-verdict.md'
    if not jp.is_file() or not mp.is_file(): why('release verdict files missing'); return 1
    try: x=json.loads(jp.read_text())
    except Exception as e: why(f'invalid release-verdict.json: {e}'); return 1
    req={'verdict':'PASS','highest_true_state':'READY_FOR_PROJECT_ROOM_REVIEW','project_room_status':'inventory_review_required','external_use_authorized':False,'review_count':3,'all_review_verdicts':'PASS','external_actions':'none'}
    for k,v in req.items():
        if x.get(k)!=v: fail.append(f'{k}={x.get(k)!r} expected {v!r}')
    for k in ['fatal_issues','material_issues','minor_issues']:
        if x.get(k)!=[]: fail.append(f'{k} not empty')
    if x.get('onepager_pages')!=1 or x.get('explainer_pages')!=11: fail.append('final page counts must be 1 and 11')
    if x.get('source_count')!=25: fail.append('source_count must be 25')
    if x.get('score_changes_after_refresh') is not False: fail.append('score_changes_after_refresh must be false')
    if 'approve' not in str(x.get('user_action_required','')).lower() or 'source inventory' not in str(x.get('user_action_required','')).lower(): fail.append('user_action_required must request source-inventory approval')
    text=mp.read_text(); low=text.lower()
    for token in ['Verdict: PASS','Highest true state: READY_FOR_PROJECT_ROOM_REVIEW','External use authorized: no','No fatal, material, or minor issues','Source inventory approval']:
        if token.lower() not in low: fail.append(f'markdown missing {token}')
    if len(text)<2000: fail.append('release-verdict.md too short')
    if '—' in text: fail.append('em dash present')
    if 'CANARY' in text: fail.append('canary leaked into release verdict')
    if fail: [why(z) for z in fail]; return 1
    print('PASS: final release judge accepts technical/numeric/logic package, assigns READY_FOR_PROJECT_ROOM_REVIEW, and keeps external use blocked for human source-inventory approval')
    return 0
if __name__=='__main__': sys.exit(main())
