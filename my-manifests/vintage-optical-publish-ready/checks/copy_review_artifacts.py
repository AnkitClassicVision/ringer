#!/usr/bin/env python3
from __future__ import annotations
import argparse,shutil
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source-dir',required=True); a=ap.parse_args(); s=Path(a.source_dir)
    for n in ['review.json','review.md']:
        p=s/n
        if not p.is_file(): raise SystemExit(f'WHY: missing {p}')
        shutil.copy2(p,Path(n))
    print('PASS: copied completed review artifacts for deterministic checker re-verification')
if __name__=='__main__': main()
