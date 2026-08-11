#!/usr/bin/env python3
from __future__ import annotations
import argparse,re,sys
from pathlib import Path

def why(x): print(f'WHY: {x}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--review',required=True); a=ap.parse_args(); t=Path(a.review).read_text(encoding='utf-8'); low=t.lower(); fail=[]
    for h in ['## Verdict','## Process conformance','## Fatal issues','## Material issues','## Minor issues','## Release boundary','## Evidence checked']:
        if h.lower() not in low: fail.append(f'missing heading {h}')
    if not re.search(r'(?mi)^verdict:\s*READY_INTERNAL\s*$',t): fail.append('verdict must be exact READY_INTERNAL')
    fatal=re.search(r'(?is)## Fatal issues\s*(.*?)(?=\n## |\Z)',t)
    material=re.search(r'(?is)## Material issues\s*(.*?)(?=\n## |\Z)',t)
    for name,m in [('fatal',fatal),('material',material)]:
        if not m: fail.append(f'{name} section unparseable')
        elif not re.search(r'(?i)\bnone\b|\bno issues\b',m.group(1)): fail.append(f'{name} section is not clear of issues')
    for token in ['manual directional bands','digital presence','fix card','project room','internal-only','one letter page','source ids','external actions: none']:
        if token not in low: fail.append(f'review missing {token}')
    if 'client-ready' in low and 'not client-ready' not in low: fail.append('review implies client readiness')
    if fail:
        for x in fail: why(x)
        return 1
    print('PASS: fresh review is READY_INTERNAL with no fatal/material issues and preserves the unroomed external-send boundary')
    return 0
if __name__=='__main__': sys.exit(main())
