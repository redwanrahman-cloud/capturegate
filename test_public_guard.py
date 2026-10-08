import os
import unittest
from unittest.mock import patch
from public_guard import consume
import service

class Client:
    def update_item(self,**kwargs):self.request=kwargs

class GuardTests(unittest.TestCase):
    def test_private_disabled(self):
        with patch.dict(os.environ,{},clear=True):self.assertIsNone(consume())
    def test_atomic_allowance_and_no_document_data(self):
        client=Client()
        with patch.dict(os.environ,{'CAPTUREGATE_ALLOWANCE_TABLE':'demo'},clear=True):self.assertIsNone(consume(client))
        self.assertEqual(client.request['Key'],{'id':{'S':'analysis'}})
        self.assertEqual(client.request['ExpressionAttributeValues'][':limit'],{'N':'1000'})
        self.assertIn('used < :limit',client.request['ConditionExpression'])
    def test_invalid_limit_fails_closed(self):
        for limit in ['0','1001','oops']:
            with patch.dict(os.environ,{'CAPTUREGATE_ALLOWANCE_TABLE':'demo','CAPTUREGATE_ANALYSIS_LIMIT':limit},clear=True):self.assertEqual(consume(Client())[0],503)
    def test_exhausted_allowance(self):
        class Denied(Exception):response={'Error':{'Code':'ConditionalCheckFailedException'}}
        class Exhausted:
            def update_item(self,**kwargs):raise Denied()
        with patch.dict(os.environ,{'CAPTUREGATE_ALLOWANCE_TABLE':'demo'},clear=True):self.assertEqual(consume(Exhausted())[0],429)
    def test_unavailable_fails_closed(self):
        class Offline:
            def update_item(self,**kwargs):raise RuntimeError('offline')
        with patch.dict(os.environ,{'CAPTUREGATE_ALLOWANCE_TABLE':'demo'},clear=True):self.assertEqual(consume(Offline())[0],503)
    def test_lambda_denial_never_dispatches(self):
        with patch.object(service,'consume',return_value=(429,'Paused')),patch.object(service,'dispatch') as dispatch:
            result=service.handler({'requestContext':{'http':{'method':'POST'}},'rawPath':'/api/analyze','body':'{}'},None)
            self.assertEqual(result['statusCode'],429);dispatch.assert_not_called()
