#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path

def replace_once(path,old,new):
    text=path.read_text()
    if text.count(old)!=1: raise SystemExit(f'WHY: {path} expected one match, found {text.count(old)}')
    path.write_text(text.replace(old,new),encoding='utf-8')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--backup',required=True); a=ap.parse_args(); r=Path(a.report); b=Path(a.backup)
    if b.exists(): raise SystemExit(f'WHY: backup exists: {b}')
    rels=['intake.md','data/fresh_review.md','data/research_notes.md','data/competitor_set.json']; b.mkdir(parents=True)
    for rel in rels:
        src=r/rel; dst=b/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    comp=r/'data/competitor_set.json'; data=json.loads(comp.read_text()); data['project_room_status']='inventory_review_required'; comp.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    replace_once(r/'intake.md','Project Room status: EMPTY / UNROOMED\nExternal readiness: NOT CLIENT-READY / NOT PROSPECT-READY / NOT FOR EXTERNAL USE','Project Room initial state: pre-inventory\nProject Room current state: inventory_review_required; source inventory staged; human review pending\nExternal use: NOT FOR EXTERNAL USE pending human approval')
    replace_once(r/'data/research_notes.md','Applied `report_visibility: internal_only_unroomed_draft` because Project Room preflight was blocked and room status is EMPTY / UNROOMED.','Applied `report_visibility: internal_only_unroomed_draft` during the initial pre-inventory run. The current Project Room state is `inventory_review_required`; source inventory is staged and human review remains pending.')
    replace_once(r/'data/fresh_review.md','Unsupported review counts, complete-supply claims, route-window demographics, dollar forecasts, clinical-quality claims, and client-ready language are not presented as facts.','Unsupported review counts, complete-supply claims, route-window demographics, dollar forecasts, clinical-quality claims, and external-use-ready language are not presented as facts.')
    replace_once(r/'data/fresh_review.md','This is not client-ready. Project Room is empty/unroomed, and the packet remains internal-only and not for external use. external actions: none.','At the time of this historical review, the source inventory had not yet been staged. The current Project Room state is inventory_review_required, and the packet remains internal-only and not for external use. External actions: none.')
    print('PASS: stale current-room labels replaced with initial/current state distinction; no score or rendered artifact changed')
if __name__=='__main__': main()
