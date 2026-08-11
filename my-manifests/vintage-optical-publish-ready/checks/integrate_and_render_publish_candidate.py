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

def render_pdf(html,pdf):
    cmd=['/usr/bin/google-chrome','--headless=new','--no-sandbox','--disable-gpu','--allow-file-access-from-files','--no-pdf-header-footer',f'--print-to-pdf={pdf}',html.resolve().as_uri()]
    r=subprocess.run(cmd,text=True,capture_output=True)
    if r.returncode: raise SystemExit(f'WHY: Chrome render failed: {r.stderr[-2000:]}')

def render_pages(pdf,dest,prefix,scale=1.5):
    doc=fitz.open(pdf); images=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False); img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        path=dest/f'{prefix}-page-{i+1}.png'; img.save(path); images.append(img)
    return doc,images

def contact_sheet(images,path):
    thumbs=[]
    for i,img in enumerate(images):
        thumb=img.copy(); thumb.thumbnail((510,660)); canvas=Image.new('RGB',(540,700),'white'); canvas.paste(thumb,((540-thumb.width)//2,24)); ImageDraw.Draw(canvas).text((12,8),f'Page {i+1}',fill='black'); thumbs.append(canvas)
    cols=2; rows=(len(thumbs)+1)//2; sheet=Image.new('RGB',(cols*540,rows*700),(225,225,225))
    for i,img in enumerate(thumbs): sheet.paste(img,((i%cols)*540,(i//cols)*700))
    sheet.save(path)

def main():
    ap=argparse.ArgumentParser()
    for x in ['report','stage','explainer','refresh','backup','receipt','audit_run','refresh_run','stage_run','explainer_run']: ap.add_argument('--'+x.replace('_','-'),required=True)
    a=ap.parse_args(); report=Path(a.report); stage=Path(a.stage); expl=Path(a.explainer); refresh=Path(a.refresh); backup=Path(a.backup)
    if backup.exists(): raise SystemExit(f'WHY: backup path already exists: {backup}')
    backup.mkdir(parents=True)
    rels=['scores.json','data/market_inputs.json','data/sources.json','data/evidence.md','data/research_notes.md','data/scoring_notes.md','data/receipt_summary.json','onepager.html','onepager.pdf','onepager-qa.png','data/onepager-text.txt','README.md','runlog.md']
    for rel in rels:
        src=report/rel
        if src.exists():
            dst=backup/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    if (report/'data/source_receipts').exists(): shutil.copytree(report/'data/source_receipts',backup/'data/source_receipts')
    mapping={'updated-scores.json':'scores.json','updated-market_inputs.json':'data/market_inputs.json','updated-sources.json':'data/sources.json','updated-evidence.md':'data/evidence.md','updated-research_notes.md':'data/research_notes.md','updated-scoring_notes.md':'data/scoring_notes.md','updated-onepager.html':'onepager.html'}
    for srcname,rel in mapping.items():
        dst=report/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(stage/srcname,dst)
    shutil.copy2(expl/'number-explainer.md',report/'number-explainer.md'); shutil.copy2(expl/'number-explainer.html',report/'number-explainer.html')
    rr=report/'data/source_receipts'; rr.mkdir(exist_ok=True)
    shutil.copy2(refresh/'receipt_summary.json',report/'data/receipt_summary.json')
    for p in (refresh/'source_receipts').iterdir():
        if p.is_file(): shutil.copy2(p,rr/p.name)
    render_pdf(report/'onepager.html',report/'onepager.pdf')
    for stale in report.glob('onepager-page-*.png'):
        stale.unlink()
    one_doc,one_imgs=render_pages(report/'onepager.pdf',report,'onepager',1.5)
    if len(one_doc)!=1: raise SystemExit(f'WHY: onepager rendered {len(one_doc)} pages')
    one_imgs[0].save(report/'onepager-qa.png'); (report/'data/onepager-text.txt').write_text(''.join(p.get_text() for p in one_doc),encoding='utf-8')
    render_pdf(report/'number-explainer.html',report/'number-explainer.pdf')
    for stale in report.glob('number-explainer-page-*.png'):
        stale.unlink()
    exp_doc,exp_imgs=render_pages(report/'number-explainer.pdf',report,'number-explainer',1.25)
    (report/'data/number-explainer-text.txt').write_text(''.join(p.get_text() for p in exp_doc),encoding='utf-8'); contact_sheet(exp_imgs,report/'number-explainer-qa-contact-sheet.png')
    one_hash=sha(report/'onepager.pdf'); exp_hash=sha(report/'number-explainer.pdf')
    readme=(report/'README.md').read_text()
    marker='## Publish-candidate number package'
    block=f'''\n\n{marker}\n\nStatus: internal publish-candidate; Project Room inventory review required; not for external use.\n\n- `onepager.pdf`: current one-page summary using the official 2025 Morton population estimate\n- `number-explainer.pdf`: number-by-number source, formula, logic, and limitation guide\n- `data/source_receipts/`: frozen PEP population files, live route receipt, and source-audit extract\n- Scores are unchanged after the source refresh\n'''
    readme=re.sub(r'\n\n## Publish-candidate number package.*\Z','',readme,flags=re.S)+block
    readme=readme.replace('source registry, evidence','24-record source registry, evidence')
    (report/'README.md').write_text(readme,encoding='utf-8')
    runlog=(report/'runlog.md').read_text()
    runlog=runlog.replace('23-source registry','24-source registry')
    runlog=re.sub(r'PDF SHA-256: `[^`]+`',f'PDF SHA-256: `{one_hash}`',runlog)
    runlog=re.sub(r'Final PDF SHA-256: `[^`]+`',f'Final PDF SHA-256: `{one_hash}`',runlog)
    section=f'''\n\n## Publish-candidate number audit and explainer\n\n- Numeric/formula/source audit: `{a.audit_run}` - PASS\n- Current public receipt refresh: `{a.refresh_run}` - PASS\n- GPT-5.6 Sol staged report refresh: `{a.stage_run}` - PASS\n- GPT-5.6 Sol number explainer: `{a.explainer_run}` - PASS\n- Population authority: official PEP 2025 file, Morton village = 17,565; historical PEP 2024 file retains 17,557.\n- Live route refresh: R01 remains 4.07 minutes.\n- Score impact: none; all six core and three specialty scores are unchanged.\n- One-page PDF SHA-256: `{one_hash}`\n- Explainer PDF SHA-256: `{exp_hash}`\n- Publish-candidate visual QA: PENDING\n- Project Room: inventory_review_required. External use remains blocked.\n- External actions: none.\n'''
    runlog=re.sub(r'\n\n## Publish-candidate number audit and explainer.*\Z','',runlog,flags=re.S)+section
    (report/'runlog.md').write_text(runlog,encoding='utf-8')
    result={'integrated_at':datetime.now(timezone.utc).isoformat(),'backup':str(backup),'report':str(report),'onepager_pages':len(one_doc),'explainer_pages':len(exp_doc),'onepager_sha256':one_hash,'explainer_sha256':exp_hash,'status':'PASS','project_room':'inventory_review_required','external_actions':'none'}
    Path(a.receipt).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
