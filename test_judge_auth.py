import base64
import hashlib
import unittest
from unittest.mock import patch
from judge_auth import authorize
import service

class JudgeAuthTests(unittest.TestCase):
    def setUp(self):
        self.env={'CAPTUREGATE_JUDGE_AUTH':'required','CAPTUREGATE_JUDGE_PASSWORD_SHA256':hashlib.sha256(b'test-only').hexdigest(),'CAPTUREGATE_JUDGE_EXPIRES':'2000000000'}
        self.event={'headers':{'authorization':'Basic '+base64.b64encode(b'judges:test-only').decode()},'requestContext':{'http':{'method':'GET'}},'rawPath':'/'}
    def test_valid(self):
        with patch.dict('os.environ',self.env,clear=True):self.assertIsNone(authorize(self.event,now=1))
    def test_missing(self):
        with patch.dict('os.environ',self.env,clear=True):self.assertEqual(authorize({},now=1)[0],401)
    def test_wrong_or_malformed(self):
        with patch.dict('os.environ',self.env,clear=True):
            for value in ['Basic !!!','Bearer xyz','Basic '+base64.b64encode(b'judges:wrong').decode(),'Basic '+base64.b64encode(b'other:test-only').decode()]:
                self.assertEqual(authorize({'headers':{'Authorization':value}},now=1)[0],401)
    def test_expired(self):
        with patch.dict('os.environ',self.env,clear=True):self.assertEqual(authorize(self.event,now=2000000000)[0],403)
    def test_bad_configuration(self):
        for key in ['CAPTUREGATE_JUDGE_PASSWORD_SHA256','CAPTUREGATE_JUDGE_EXPIRES']:
            env=dict(self.env);env[key]=''
            with patch.dict('os.environ',env,clear=True):self.assertEqual(authorize(self.event,now=1)[0],503)
    def test_unconfigured_gateway_fails_closed(self):
        with patch.dict('os.environ',{},clear=True):self.assertEqual(authorize({'requestContext':{'apiId':'test'}})[0],503)
    def test_existing_iam_compatible(self):
        with patch.dict('os.environ',{},clear=True):self.assertIsNone(authorize(self.event))
    def test_denied_analysis_never_runs_or_consumes(self):
        event={'requestContext':{'http':{'method':'POST'}},'rawPath':'/api/analyze','body':'invalid'}
        with patch.dict('os.environ',self.env,clear=True),patch('service.consume') as consume,patch('service.dispatch') as dispatch:
            response=service.handler(event,None)
            self.assertEqual(response['statusCode'],401)
            self.assertIn('WWW-Authenticate',response['headers'])
            consume.assert_not_called();dispatch.assert_not_called()
