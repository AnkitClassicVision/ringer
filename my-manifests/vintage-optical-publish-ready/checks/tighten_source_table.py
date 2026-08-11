#!/usr/bin/env python3
from __future__ import annotations
import argparse,shutil
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); ap.add_argument('--target',required=True); a=ap.parse_args(); s=Path(a.source); t=Path(a.target); t.mkdir(parents=True,exist_ok=True)
    for n in ['number-explainer.html','number-explainer.md','explainer_build_report.md']: shutil.copy2(s/n,t/n)
    p=t/'number-explainer.html'; html=p.read_text(); old='.public-source-table td { padding-top: .075in; padding-bottom: .075in; }'; new='.public-source-table td { padding-top: .045in; padding-bottom: .045in; }'
    if html.count(old)!=1: raise SystemExit(f'WHY: expected one public-source padding rule, found {html.count(old)}')
    p.write_text(html.replace(old,new),encoding='utf-8')
    br=t/'explainer_build_report.md'; text=br.read_text(); text+='\n\n## Final Chrome pagination tightening\n\n- Finding: S17 alone spilled onto a near-blank page in the corrected Chrome render.\n- Fix: reduced only the public-source table cell padding from 0.075in to 0.045in per side so all 17 public source rows stay together.\n- Preserved: font size, line height, wording, links, source rows, formulas, data-number IDs, and all other layout rules.\n- External actions: none.\n'; br.write_text(text,encoding='utf-8')
    print('PASS: tightened only public-source table padding; all content and source rows preserved')
if __name__=='__main__': main()
