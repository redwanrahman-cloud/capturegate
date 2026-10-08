"""Shared local/Lambda request dispatcher. No persistence or external calls."""
import os
os.environ.setdefault('OPENCV_IO_MAX_IMAGE_PIXELS', '16000000')
import base64
import hashlib
import json
import time
from pathlib import Path
import cv2
import numpy as np
from vision import inspect, fixture, POLICY
from rectify import align_page
from recovery import proposals
from public_guard import consume
from judge_auth import authorize

ROOT = Path(__file__).resolve().parent
MAX_FILE = 4_000_000
MAX_BODY = 5_400_000
ASSETS = {'/': ('index.html','text/html; charset=utf-8'), '/app.js': ('app.js','text/javascript; charset=utf-8'), '/style.css': ('style.css','text/css; charset=utf-8')}

def image_result(image, region=None, crop_corners=None, sharpen=False):
    started = time.perf_counter()
    result = inspect(image,region)
    result['image_size']=[image.shape[1],image.shape[0]]
    annotated = image.copy()
    if 'polygon' in result:
        cv2.polylines(annotated,[np.array(result['polygon'],dtype=np.int32)],True,(0,160,255),3)
    elif 'box' in result:
        x,y,w,h=result['box'];cv2.rectangle(annotated,(x,y),(x+w-1,y+h-1),(0,160,255),3)
    # Bound the response independently of the accepted input dimensions.
    height,width=annotated.shape[:2]
    scale=min(1.0,1280/max(height,width))
    if scale<1:
        annotated=cv2.resize(annotated,(max(1,round(width*scale)),max(1,round(height*scale))),interpolation=cv2.INTER_AREA)
    ok, encoded=cv2.imencode('.jpg',annotated,[cv2.IMWRITE_JPEG_QUALITY,80])
    if not ok: raise ValueError('Unable to generate preview')
    result['preview']='data:image/jpeg;base64,'+base64.b64encode(encoded).decode()
    if 'polygon' in result:
        aligned, alignment = align_page(image, result['polygon'])
        ok, crop = cv2.imencode('.jpg', aligned, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if ok:
            result['document_preview'] = 'data:image/jpeg;base64,' + base64.b64encode(crop).decode()
            result['alignment'] = alignment
    result['recovery']=proposals(image,result,crop_corners,sharpen)
    result['policy']=POLICY
    result['processing_ms'] = round((time.perf_counter()-started)*1000, 2)
    action={'retake':'request_retake','review_ready':'request_human_review','needs_selection':'request_document_area'}[result['decision']]
    result['trace']=[{'step':'locate_page','outcome':result.get('detection','not_found')}, {'step':'quality_checks','reasons':result['reasons']}, {'step':'next_action','action':action}]
    return result

def analyze(payload):
    if not isinstance(payload,dict) or set(payload)-{'image','fixture','region','crop_corners','sharpen'}: raise ValueError('Expected image or fixture request')
    if 'crop_corners' in payload and payload['crop_corners'] is None:raise ValueError('Select four finite corners in boundary order')
    if not isinstance(payload.get('sharpen',False),bool):raise ValueError('Sharpen must be true or false')
    if ('image' in payload)==('fixture' in payload):raise ValueError('Provide exactly one image or fixture')
    if 'fixture' in payload:
        if not isinstance(payload['fixture'],str):raise ValueError('Invalid fixture')
        image=fixture(payload['fixture']); result=image_result(image,payload.get('region'),payload.get('crop_corners'),payload.get('sharpen',False)); result['source']='synthetic'
    else:
        value=payload['image']
        if not isinstance(value,str) or len(value)>5_333_336:raise ValueError('Maximum image size is 4 MB')
        try: raw=base64.b64decode(value,validate=True)
        except Exception as exc:raise ValueError('Invalid image encoding') from exc
        if not raw or len(raw)>MAX_FILE:raise ValueError('Maximum image size is 4 MB')
        if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):raise ValueError('Only PNG and JPEG are supported')
        try:image=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
        except cv2.error as exc:raise ValueError('Image cannot be decoded or exceeds pixel limit') from exc
        result=image_result(image,payload.get('region'),payload.get('crop_corners'),payload.get('sharpen',False));result['source']='user_supplied';result['input_sha256']=hashlib.sha256(raw).hexdigest()
    return result

def dispatch(method,path,body=b''):
    headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; img-src 'self' data: blob:; connect-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}
    if method=='GET' and path in ASSETS:
        file,mime=ASSETS[path];headers['Content-Type']=mime;return 200,headers,(ROOT/'web'/file).read_bytes()
    headers['Content-Type']='application/json; charset=utf-8'
    if method=='GET' and path=='/api/health':return 200,headers,json.dumps({'status':'ok','opencv':cv2.__version__,'policy':POLICY}).encode()
    if method!='POST' or path!='/api/analyze':return 404,headers,b'{"error":"Not found"}'
    if len(body)>MAX_BODY:return 413,headers,b'{"error":"Request too large"}'
    try:
        result=analyze(json.loads(body));return 200,headers,json.dumps(result,allow_nan=False).encode()
    except (ValueError,TypeError,UnicodeDecodeError) as exc:
        return 400,headers,json.dumps({'error':str(exc)}).encode()

def handler(event,context):
    """Lambda Function URL v2 adapter. Template requires IAM authorization."""
    if not isinstance(event,dict):
        return {'statusCode':400,'body':'{"error":"Invalid event"}'}
    denied=authorize(event)
    if denied:
        status,message=denied
        headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
        if status==401:headers['WWW-Authenticate']='Basic realm="CaptureGate judges", charset="UTF-8"'
        return {'statusCode':status,'headers':headers,'body':json.dumps({'error':message}),'isBase64Encoded':False}
    request_context=event.get('requestContext') or {}
    http=request_context.get('http') if isinstance(request_context,dict) else None
    method=http.get('method','GET') if isinstance(http,dict) else 'GET'
    body=event.get('body') or ''
    if not isinstance(body,str) or len(body)>MAX_BODY*2:
        return {'statusCode':413,'body':'{"error":"Request too large"}'}
    try: raw=base64.b64decode(body,validate=True) if event.get('isBase64Encoded') else body.encode()
    except ValueError:return {'statusCode':400,'body':'{"error":"Invalid body encoding"}'}
    path=event.get('rawPath','/')
    if not isinstance(method,str) or not isinstance(path,str):
        return {'statusCode':400,'body':'{"error":"Invalid request route"}'}
    if method=='POST' and path=='/api/analyze':
        denied=consume()
        if denied:
            status,message=denied
            return {'statusCode':status,'headers':{'Content-Type':'application/json','Cache-Control':'no-store'},'body':json.dumps({'error':message}),'isBase64Encoded':False}
    status,headers,data=dispatch(method,path,raw)
    return {'statusCode':status,'headers':headers,'body':data.decode(),'isBase64Encoded':False}
