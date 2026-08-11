#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
import fitz
from PIL import Image,ImageOps,ImageDraw

def sha(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--build',required=True); ap.add_argument('--dest',required=True); ap.add_argument('--logo',required=True); ap.add_argument('--receipt',required=True); a=ap.parse_args()
    b=Path(a.build); d=Path(a.dest); d.mkdir(parents=True,exist_ok=True); (d/'assets').mkdir(exist_ok=True)
    for name in ['number-explainer.html','number-explainer.md']: shutil.copy2(b/name,d/name)
    shutil.copy2(a.logo,d/'assets/mybcat-logo.png')
    pdf=d/'number-explainer.pdf'; url=(d/'number-explainer.html').resolve().as_uri()
    cmd=['/usr/bin/google-chrome','--headless=new','--no-sandbox','--disable-gpu','--allow-file-access-from-files','--no-pdf-header-footer',f'--print-to-pdf={pdf}',url]
    subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    doc=fitz.open(pdf); (d/'explainer-text.txt').write_text(''.join(p.get_text() for p in doc),encoding='utf-8')
    thumbs=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False); img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        page=d/f'explainer-page-{i+1}.png'; img.save(page); thumb=img.copy(); thumb.thumbnail((510,660)); canvas=Image.new('RGB',(540,700),'white'); canvas.paste(thumb,((540-thumb.width)//2,24)); ImageDraw.Draw(canvas).text((12,8),f'Page {i+1}',fill='black'); thumbs.append(canvas)
    cols=2; rows=(len(thumbs)+1)//2; sheet=Image.new('RGB',(cols*540,rows*700),(225,225,225))
    for i,img in enumerate(thumbs): sheet.paste(img,((i%cols)*540,(i//cols)*700))
    sheet.save(d/'explainer-qa-contact-sheet.png')
    result={'dest':str(d),'pdf_sha256':sha(pdf),'pdf_bytes':pdf.stat().st_size,'pages':len(doc)}
    Path(a.receipt).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
