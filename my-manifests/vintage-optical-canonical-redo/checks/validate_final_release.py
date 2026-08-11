#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path

def why(x): print(f'WHY: {x}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dest',required=True); ap.add_argument('--old',required=True); a=ap.parse_args(); d=Path(a.dest); old=Path(a.old); fail=[]
    for f in ['onepager.pdf','onepager.html','scores.json','data/fresh_review.md','runlog.md','README.md']:
        if not (d/f).is_file(): fail.append(f'new packet missing {f}')
    log=(d/'runlog.md').read_text() if (d/'runlog.md').exists() else ''
    for token in ['Public route collection','Canonical evidence pack','Manual-band scoring','GPT-5.6 Sol','Chrome assembly','Fresh process/release review','Visual QA: PASS','READY_INTERNAL','Highest true state']:
        if token.lower() not in log.lower(): fail.append(f'closed runlog missing {token}')
    if 'RUN_IDS_PENDING_FINAL_CLOSE' in log: fail.append('runlog still has pending placeholder')
    rev=(d/'data/fresh_review.md').read_text() if (d/'data/fresh_review.md').exists() else ''
    if 'Verdict: READY_INTERNAL' not in rev: fail.append('fresh review not READY_INTERNAL')
    for name in ['onepager.pdf','onepager.html','scores.json','intake.md','runlog.md']:
        if (old/name).exists(): fail.append(f'old noncanonical artifact still active: {name}')
        if not (old/'superseded-noncanonical-onepager'/name).exists(): fail.append(f'quarantine missing {name}')
    if not (old/'SUPERSEDED.md').exists(): fail.append('old packet lacks SUPERSEDED notice')
    if not (old/'competitive-growth-analysis-full.pdf').exists(): fail.append('protected full report missing')
    if fail:
        for x in fail: why(x)
        return 1
    print('PASS: corrected packet is closed and the prior noncanonical one-pager is quarantined while the full report remains')
    return 0
if __name__=='__main__': sys.exit(main())
