#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
import fitz
from PIL import Image,ImageDraw

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def render(html,pdf):
    cmd=['/usr/bin/google-chrome','--headless=new','--no-sandbox','--disable-gpu','--allow-file-access-from-files','--no-pdf-header-footer',f'--print-to-pdf={pdf}',html.resolve().as_uri()]
    r=subprocess.run(cmd,text=True,capture_output=True)
    if r.returncode: raise SystemExit(f'WHY: Chrome render failed: {r.stderr[-2000:]}')
def sheet(images,path):
    thumbs=[]
    for i,img in enumerate(images):
        t=img.copy(); t.thumbnail((510,660)); c=Image.new('RGB',(540,700),'white'); c.paste(t,((540-t.width)//2,24)); ImageDraw.Draw(c).text((12,8),f'Page {i+1}',fill='black'); thumbs.append(c)
    s=Image.new('RGB',(1080,((len(thumbs)+1)//2)*700),(225,225,225))
    for i,img in enumerate(thumbs): s.paste(img,((i%2)*540,(i//2)*700))
    s.save(path)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--stage',required=True); ap.add_argument('--backup',required=True); ap.add_argument('--receipt',required=True); ap.add_argument('--fix-run',required=True); a=ap.parse_args()
    report=Path(a.report); stage=Path(a.stage); backup=Path(a.backup)
    if backup.exists(): raise SystemExit(f'WHY: backup exists: {backup}')
    backup.mkdir(parents=True)
    mapping={'scores.json':'scores.json','sources.json':'data/sources.json','market_inputs.json':'data/market_inputs.json','evidence.md':'data/evidence.md','research_notes.md':'data/research_notes.md','scoring_notes.md':'data/scoring_notes.md','number-explainer.md':'number-explainer.md','number-explainer.html':'number-explainer.html','README.md':'README.md','runlog.md':'runlog.md'}
    for srcname,rel in mapping.items():
        old=report/rel
        if old.exists(): dst=backup/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(old,dst)
        dst=report/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(stage/srcname,dst)
    for rel in ['number-explainer.pdf','number-explainer-qa-contact-sheet.png','data/number-explainer-text.txt']:
        old=report/rel
        if old.exists(): dst=backup/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(old,dst)
    for p in report.glob('number-explainer-page-*.png'):
        dst=backup/p.name; shutil.copy2(p,dst); p.unlink()
    render(report/'number-explainer.html',report/'number-explainer.pdf')
    doc=fitz.open(report/'number-explainer.pdf'); images=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False); img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples); img.save(report/f'number-explainer-page-{i+1}.png'); images.append(img)
    (report/'data/number-explainer-text.txt').write_text(''.join(p.get_text() for p in doc),encoding='utf-8'); sheet(images,report/'number-explainer-qa-contact-sheet.png')
    exp_hash=sha(report/'number-explainer.pdf'); one_hash=sha(report/'onepager.pdf')
    runlog=(report/'runlog.md').read_text(); runlog=re.sub(r'Explainer PDF SHA-256: `[^`]+`',f'Explainer PDF SHA-256: `{exp_hash}`',runlog)
    section=f'''\n\n## Historical population lineage correction\n\n- Fresh-review finding: the historical 17,557 value lacked its own registered source ID, and one nested Project Room status was stale.\n- Correction: S18 now registers the frozen official 2024-vintage PEP file; S17 remains the current 2025 authority; both Project Room status fields now say inventory_review_required.\n- Correction run: `{a.fix_run}` - PASS\n- Source count: 25\n- Score impact: none\n- One-page PDF SHA-256: `{one_hash}`\n- Explainer PDF SHA-256: `{exp_hash}`\n- Post-S18 visual QA: PENDING\n- External use: blocked pending human Project Room source-inventory approval.\n- External actions: none.\n'''
    runlog=re.sub(r'\n\n## Historical population lineage correction.*\Z','',runlog,flags=re.S)+section; (report/'runlog.md').write_text(runlog,encoding='utf-8')
    result={'integrated_at':datetime.now(timezone.utc).isoformat(),'status':'PASS','backup':str(backup),'onepager_pages':1,'explainer_pages':len(doc),'source_count':25,'onepager_sha256':one_hash,'explainer_sha256':exp_hash,'project_room':'inventory_review_required','external_actions':'none'}
    Path(a.receipt).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
