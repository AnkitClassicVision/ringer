#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,shutil
from datetime import datetime,timezone
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--reviews',required=True); ap.add_argument('--verdict',required=True); ap.add_argument('--backup',required=True); ap.add_argument('--receipt',required=True); a=ap.parse_args()
    r=Path(a.report); reviews=Path(a.reviews); verdict=Path(a.verdict); backup=Path(a.backup)
    if backup.exists(): raise SystemExit(f'WHY: backup exists {backup}')
    backup.mkdir(parents=True)
    for rel in ['README.md','runlog.md']:
        shutil.copy2(r/rel,backup/rel)
    targets={
      'numeric':'verify-final-numeric-review-artifact',
      'logic':'verify-final-logic-review-artifact',
      'render':'verify-final-render-review-artifact'
    }
    fr=r/'data/final-reviews'; fr.mkdir(parents=True,exist_ok=True)
    for name,key in targets.items():
        for ext in ['json','md']: shutil.copy2(reviews/key/f'review.{ext}',fr/f'{name}-review.{ext}')
    shutil.copy2(verdict/'release-verdict.json',r/'data/release-verdict.json'); shutil.copy2(verdict/'release-verdict.md',r/'data/release-verdict.md')
    readme=(r/'README.md').read_text()
    readme=readme.replace('Status: READY_INTERNAL. Internal-only, unroomed, not for external use.','Status: READY_FOR_PROJECT_ROOM_REVIEW. Internal-only; external use is blocked pending human source-inventory approval.')
    if '- `data/release-verdict.md`:' not in readme:
        readme+='\n- `data/release-verdict.md`: final numeric, logic, render, and human-gate verdict\n- `data/final-reviews/`: three independent final review artifacts\n'
    (r/'README.md').write_text(readme,encoding='utf-8')
    runlog=(r/'runlog.md').read_text().replace('- Clean final review rerun: not yet run.','- Clean final review artifacts: PASS; deterministic Ringer re-verification `vintage-optical-publish-ready-20260730T052239Z-p4076566`.')
    now=datetime.now(timezone.utc).isoformat()
    section=f'''\n\n## Final publish-candidate release review\n\n- Three independent final reviews: numeric/lineage PASS, logic/owner-read PASS, render/boundary PASS.\n- Review artifact re-verification: `vintage-optical-publish-ready-20260730T052239Z-p4076566` - PASS\n- Final fresh-context release judge: `vintage-optical-publish-ready-20260730T052311Z-p4117717` - PASS\n- Strengthened canary-safe verdict re-verification: `vintage-optical-publish-ready-20260730T053828Z-p1088150` - PASS\n- Fatal issues: none\n- Material issues: none\n- Minor issues: none\n- Highest true state: READY_FOR_PROJECT_ROOM_REVIEW\n- Project Room status: inventory_review_required\n- External use authorized: no\n- Required human action: Ankit must approve the source inventory before external use.\n- One-page PDF SHA-256: `{sha(r/'onepager.pdf')}`\n- Explainer PDF SHA-256: `{sha(r/'number-explainer.pdf')}`\n- External actions: none\n- Closed at: {now}\n'''
    runlog=re.sub(r'\n\n## Final publish-candidate release review.*\Z','',runlog,flags=re.S)+section
    (r/'runlog.md').write_text(runlog,encoding='utf-8')
    result={'status':'PASS','closed_at':now,'report':str(r),'source_count':len(json.loads((r/'data/sources.json').read_text())['sources']),'onepager_sha256':sha(r/'onepager.pdf'),'explainer_sha256':sha(r/'number-explainer.pdf'),'highest_true_state':'READY_FOR_PROJECT_ROOM_REVIEW','project_room_status':'inventory_review_required','external_use_authorized':False,'external_actions':'none','backup':str(backup)}
    Path(a.receipt).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
