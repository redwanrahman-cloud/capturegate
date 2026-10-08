import argparse
import html
import json
from pathlib import Path
import cv2
from vision import inspect, fixture

def build(output):
    output.mkdir(parents=True,exist_ok=True)
    records=[]; cards=[]
    for kind in ['clean','blur','clipped','glare','missing','blank']:
        image=fixture(kind); result=inspect(image); records.append({'fixture':kind,**result})
        if not cv2.imwrite(str(output/f'{kind}.png'),image): raise RuntimeError('Image write failed')
        cards.append(f'<article><h2>{kind}</h2><img alt="Synthetic {kind} document" src="{kind}.png"><pre>{html.escape(json.dumps(result,indent=2))}</pre></article>')
    (output/'results.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CaptureGate synthetic baseline</title><style>body{font:16px system-ui;background:#eff3f8;color:#193148;padding:30px}main{max-width:1100px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{background:white;border-radius:12px;padding:20px}img{width:100%}pre{white-space:pre-wrap;font-size:13px}p{line-height:1.6}</style><main><h1>CaptureGate</h1><p>Retake before OCR. Synthetic feasibility baseline using OpenCV 5.</p><p>Review-ready means only these heuristics did not flag this fixture. No OCR, document authenticity, real-photo accuracy, or AWS execution is demonstrated.</p><div class="grid">'''+''.join(cards)+'</div></main></html>'
    (output/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(records,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=Path('demo'))
    args=parser.parse_args(); build(args.output)
