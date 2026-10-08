"""Loopback-only end-to-end HTTP checks using generated fictional pages.

Runs a temporary server on an OS-assigned port. No AWS or external traffic.
This checks software plumbing, not real-camera accuracy.
"""
import base64
import hashlib
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

import cv2
import numpy as np
from server import Handler
from service import MAX_BODY
from vision import fixture, POLICY
import test_vision


class HttpWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def call(self, method='GET', path='/api/health', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def analyze(self, payload):
        status, headers, body = self.call('POST', '/api/analyze', json.dumps(payload).encode(), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        return json.loads(body)

    def test_actual_assets_and_security_headers(self):
        for path, mime in [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/style.css', 'text/css')]:
            status, headers, body = self.call(path=path)
            self.assertEqual(status, 200)
            self.assertTrue(body)
            self.assertIn(mime, headers['Content-Type'])
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertIn(b'RETAKE REQUIRED', self.call(path='/')[2])
        self.assertIn(b'function canExport()', self.call(path='/app.js')[2])

    def test_health_reports_current_runtime_and_policy(self):
        status, _, body = self.call()
        self.assertEqual(status, 200)
        health = json.loads(body)
        self.assertTrue(health['opencv'].startswith('5.'))
        self.assertEqual(health['policy'], POLICY)

    def test_six_generated_http_decisions_and_traces(self):
        for name in ['clean', 'blur', 'clipped', 'glare', 'blank', 'missing']:
            with self.subTest(name=name):
                result = self.analyze({'fixture': name})
                self.assertEqual(result['decision'], 'review_ready' if name == 'clean' else 'retake')
                self.assertEqual(result['source'], 'synthetic')
                self.assertEqual(result['trace'][-1]['action'], 'request_human_review' if name == 'clean' else 'request_retake')

    def test_actual_png_and_jpeg_bytes_use_photo_path(self):
        for name in ['clean', 'blur', 'clipped', 'glare', 'blank', 'missing']:
            for extension in ['.png', '.jpg']:
                with self.subTest(name=name, format=extension):
                    ok, encoded = cv2.imencode(extension, fixture(name))
                    self.assertTrue(ok)
                    raw = encoded.tobytes()
                    result = self.analyze({'image': base64.b64encode(raw).decode()})
                    self.assertEqual(result['decision'], 'review_ready' if name == 'clean' else 'retake')
                    self.assertEqual(result['source'], 'user_supplied')
                    self.assertEqual(result['input_sha256'], hashlib.sha256(raw).hexdigest())
                    preview = cv2.imdecode(np.frombuffer(base64.b64decode(result['preview'].split(',')[1]), dtype=np.uint8), cv2.IMREAD_COLOR)
                    self.assertIsNotNone(preview)
                    self.assertLessEqual(max(preview.shape[:2]), 1280)
                    if name == 'clean':
                        self.assertIn('document_preview', result)
                        crop = cv2.imdecode(np.frombuffer(base64.b64decode(result['document_preview'].split(',')[1]), dtype=np.uint8), cv2.IMREAD_COLOR)
                        self.assertIsNotNone(crop)
                        self.assertLessEqual(max(crop.shape[:2]), 1600)

    def test_inner_table_cannot_create_aligned_export_over_http(self):
        for clipped in [False,True]:
            for rotated in [False,True]:
                for extension in ['.jpg','.png']:
                    with self.subTest(clipped=clipped,rotated=rotated,format=extension):
                        ok,encoded=cv2.imencode(extension,test_vision.VisionTests.table_page(clipped,rotated))
                        self.assertTrue(ok)
                        result=self.analyze({'image':base64.b64encode(encoded).decode()})
                        self.assertEqual(result['decision'],'retake' if clipped else 'review_ready')
                        if clipped:
                            self.assertEqual(result['reasons'],['document_boundary_uncertain'])
                            self.assertNotIn('polygon',result)
                            self.assertNotIn('document_preview',result)
                            self.assertNotIn('alignment',result)
                            self.assertEqual(result['trace'][-1]['action'],'request_retake')
                        else:
                            self.assertIn('document_preview',result)
                            self.assertGreater(result['document_fraction'],.65)

    def test_manual_crop_and_sharpen_over_http_keep_original_failure(self):
        result=self.analyze({'fixture':'inner_table','crop_corners':[[.1,.1],[.9,.1],[.9,.9],[.1,.9]],'sharpen':True})
        self.assertEqual(result['decision'],'retake')
        self.assertTrue(result['recovery']['sharpened'])
        self.assertEqual(result['recovery']['geometry']['method'],'manual_perspective_crop')
        self.assertFalse(result['recovery']['geometry']['whole_page_verified'])
        status,_,_=self.call('POST','/api/analyze',b'{"fixture":"clean","crop_corners":[[0,0],[1,1],[1,0],[0,1]]}',{'Content-Type':'application/json'})
        self.assertEqual(status,400)

    def test_malformed_input_returns_bounded_errors_and_recovers(self):
        for raw in [b'not json', b'[]', b'{"image":"!!!"}', b'{"fixture":"unknown"}', b'{"image":""}', b'{"fixture":"clean","unexpected":1}']:
            status, _, body = self.call('POST', '/api/analyze', raw, {'Content-Type': 'application/json'})
            self.assertEqual(status, 400)
            self.assertIn('error', json.loads(body))
            self.assertLess(len(body), 1000)
        self.assertEqual(self.analyze({'fixture': 'clean'})['decision'], 'review_ready')

    def test_origin_and_host_are_rejected_without_widening_access(self):
        for headers in [{'Host': 'attacker.example'}, {'Origin': 'https://attacker.example'}, {'Origin': 'null'}]:
            self.assertEqual(self.call(headers=headers)[0], 403)
        for origin in [f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}']:
            self.assertEqual(self.call(headers={'Origin': origin})[0], 200)

    def test_wrong_media_type_and_oversize_declarations_rejected(self):
        for value in [str(MAX_BODY + 1), '-1', 'invalid']:
            self.assertEqual(self.call('POST', '/api/analyze', b'', {'Content-Type': 'application/json', 'Content-Length': value})[0], 413)
        for _ in range(5):
            self.assertEqual(self.call('POST', '/api/analyze', b'{}', {'Content-Type': 'text/plain'})[0], 415)
            self.assertEqual(self.call('POST', '/api/analyze', b'{}')[0], 415)

    def test_static_allowlist_does_not_expose_code_or_private_paths(self):
        for path in ['/vision.py', '/STATUS.json', '/.env', '/../README.md', '/%2e%2e/README.md', '/api/unknown']:
            self.assertEqual(self.call(path=path)[0], 404)

    def test_out_of_bounds_decoded_dimensions_rejected(self):
        for shape in [(99, 100, 3), (100, 4001, 3)]:
            ok, encoded = cv2.imencode('.png', np.zeros(shape, dtype=np.uint8))
            self.assertTrue(ok)
            status, _, body = self.call('POST', '/api/analyze', json.dumps({'image': base64.b64encode(encoded).decode()}).encode(), {'Content-Type': 'application/json'})
            self.assertEqual(status, 400)
            self.assertIn('Dimensions', json.loads(body)['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
