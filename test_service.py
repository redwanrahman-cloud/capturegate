import base64
import json
import unittest
import cv2
from service import analyze,dispatch,handler,MAX_BODY
from vision import fixture

class ServiceTests(unittest.TestCase):
    def test_real_encoding_path(self):
        ok,data=cv2.imencode('.png',fixture());self.assertTrue(ok)
        result=analyze({'image':base64.b64encode(data).decode()})
        self.assertEqual(result['decision'],'review_ready');self.assertEqual(result['source'],'user_supplied')
        self.assertEqual(len(result['input_sha256']),64);self.assertTrue(result['preview'].startswith('data:image/jpeg;base64,'))
    def test_action_changes_with_visual_evidence(self):
        self.assertEqual(analyze({'fixture':'clean'})['trace'][-1]['action'],'request_human_review')
        self.assertEqual(analyze({'fixture':'blur'})['trace'][-1]['action'],'request_retake')
    def test_invalid_inputs(self):
        for payload in [[],{}, {'fixture':'unknown'},{'image':'!!!'}, {'image':'','fixture':'clean'}, {'image':base64.b64encode(b'<svg/>').decode()}, {'fixture':12}, {'fixture':'clean','secret':'x'}, {'image':base64.b64encode(b'\x89PNG\r\n\x1a\ninvalid').decode()}]:
            with self.assertRaises(ValueError):analyze(payload)
    def test_invalid_requests(self):
        for body in [b'not json',b'[]',b'{"fixture":null}',b'\xff']:
            self.assertEqual(dispatch('POST','/api/analyze',body)[0],400)
        self.assertEqual(dispatch('POST','/api/analyze',b'x'*(MAX_BODY+1))[0],413)
    def test_static_allowlist_and_headers(self):
        for path in ['/../vision.py','/vision.py','/.env']:
            self.assertEqual(dispatch('GET',path)[0],404)
        for path in ['/','/app.js','/style.css']:
            status,headers,body=dispatch('GET',path);self.assertEqual(status,200);self.assertTrue(body)
            self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
    def test_lambda_parity(self):
        raw=json.dumps({'fixture':'clipped'}).encode()
        response=handler({'requestContext':{'http':{'method':'POST'}},'rawPath':'/api/analyze','body':base64.b64encode(raw).decode(),'isBase64Encoded':True},None)
        self.assertEqual(response['statusCode'],200);self.assertIn('edge_clipped',json.loads(response['body'])['reasons'])
    def test_lambda_bad_body(self):
        self.assertEqual(handler({'body':'!','isBase64Encoded':True},None)['statusCode'],400)
    def test_wrong_dtype(self):
        from vision import inspect
        with self.assertRaises(ValueError):inspect(fixture().astype('float32'))
    def test_marked_region_contract(self):
        result=analyze({'fixture':'clean','region':[90,50,460,380]})
        self.assertEqual(result['image_size'],[640,480])
        self.assertEqual(result['framing_assessment'],'human_review_required')
        self.assertEqual(result['policy'],'capturegate-v0.9-manual-borders')
        self.assertEqual(dispatch('POST','/api/analyze',b'{"fixture":"clean","region":[0,0,9999,99]}')[0],400)

    def test_preview_size_is_bounded(self):
        from service import image_result
        image=cv2.resize(fixture(),(2000,2000))
        result=image_result(image)
        import numpy as np
        preview=cv2.imdecode(np.frombuffer(base64.b64decode(result['preview'].split(',')[1]),dtype=np.uint8),cv2.IMREAD_COLOR)
        self.assertLessEqual(max(preview.shape[:2]),1280)

    def test_lambda_malformed_routes(self):
        self.assertEqual(handler([],None)['statusCode'],400)
        self.assertEqual(handler({'rawPath':[]},None)['statusCode'],400)
        self.assertEqual(handler({'requestContext':{'http':{'method':[]}}},None)['statusCode'],400)
        self.assertEqual(handler({'rawPath':'/api/health','requestContext':None},None)['statusCode'],200)

if __name__=='__main__':unittest.main()
