"""Frozen procedural regression set, expressly NOT independent photo evidence."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from vision import fixture,inspect

def run():
    records=[]
    for scale in [.75,1,1.25]:
        for kind in ['clean','blur','clipped','glare','blank','missing']:
            image=cv2.resize(fixture(kind),None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
            for brightness in [0,10]:
                image2=cv2.add(image,np.full_like(image,brightness));result=inspect(image2)
                expected='review_ready' if kind=='clean' else 'retake'
                records.append({'case':f'{kind}-{scale}-{brightness}','expected':expected,'actual':result['decision'],'reasons':result['reasons'],'passed':expected==result['decision']})
    document={'kind':'procedural_regression_not_real_photo_accuracy','opencv':cv2.__version__,'cases':records,'passed':sum(r['passed'] for r in records),'total':len(records)}
    output=Path('evidence');output.mkdir(exist_ok=True)
    text=json.dumps(document,indent=2)+'\n';(output/'procedural-results.json').write_text(text,encoding='utf-8')
    (output/'procedural-results.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'\n',encoding='utf-8')
    print(f"Procedural regression: {document['passed']}/{document['total']} (not real-photo accuracy)")
    return document
if __name__=='__main__':run()
