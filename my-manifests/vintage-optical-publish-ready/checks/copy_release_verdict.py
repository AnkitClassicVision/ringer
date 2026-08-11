#!/usr/bin/env python3
from __future__ import annotations
import argparse,shutil
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source-dir',required=True); a=ap.parse_args(); s=Path(a.source_dir)
    for n in ['release-verdict.json','release-verdict.md']:
        if not (s/n).is_file(): raise SystemExit(f'WHY: missing {s/n}')
        shutil.copy2(s/n,Path(n))
    print('PASS: copied completed release verdict for corrected checker re-verification')
if __name__=='__main__': main()
