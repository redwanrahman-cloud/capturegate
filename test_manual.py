import base64
import json
import unittest
import cv2
import numpy as np
from service import analyze, dispatch
from vision import fixture, inspect
from recovery import proposals, sharpen_edges
from rectify import manual_boundary

class ManualBorderTests(unittest.TestCase):
    corners=[[.15,.15],[.85,.15],[.85,.85],[.15,.85]]

    def test_manual_crop_uses_original_pixels_and_remains_bounded(self):
        image=fixture('clean');before=image.copy()
        recovery=proposals(image,inspect(image),self.corners)
        self.assertEqual(recovery['geometry']['method'],'manual_perspective_crop')
        self.assertEqual(recovery['geometry']['normalized_corners'],self.corners)
        self.assertTrue(recovery['geometry']['human_selected'])
        self.assertFalse(recovery['geometry']['whole_page_verified'])
        self.assertTrue(recovery['crop_applied'])
        self.assertEqual(recovery['variants'][0]['size'],[447,335])
        self.assertEqual(recovery['uncropped_variants'][0]['size'],[640,480])
        np.testing.assert_array_equal(image,before)

    def test_original_failures_and_trace_are_not_overridden_by_human_crop(self):
        for name in ['blur','clipped','glare','inner_table','missing']:
            plain=analyze({'fixture':name})
            manual=analyze({'fixture':name,'crop_corners':self.corners,'sharpen':True})
            self.assertEqual(manual['decision'],plain['decision'])
            self.assertEqual(manual['reasons'],plain['reasons'])
            self.assertEqual(manual['trace'],plain['trace'])
            self.assertTrue(manual['recovery']['human_acceptance_required'])

    def test_strict_corner_validation(self):
        for value in [None,[],[[0,0]]*4,[[0,0],[1,1],[1,0],[0,1]],
                      [[0,0],[1,0],[.3,.2],[0,1]],[[0,0],[1,0],[1,1],[0,-.1]],
                      [[False,0],[1,0],[1,1],[0,1]],[[0,0],[1,0],[1,float('nan')],[0,1]],
                      [[0,0],[1,0],[1,float('inf')],[0,1]],
                      [['0',0],[1,0],[1,1],[0,1]],[[0,0],[.001,0],[.001,.001],[0,.001]]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):manual_boundary(fixture(),value)

    def test_invalid_api_crop_and_sharpen_returns_400(self):
        for patch in [{'crop_corners':None},{'crop_corners':[[0,0]]*4},{'sharpen':1},{'sharpen':'yes'}]:
            status,_,body=dispatch('POST','/api/analyze',json.dumps({'fixture':'clean',**patch}).encode())
            self.assertEqual(status,400)
            self.assertIn('error',json.loads(body))

    def test_full_frame_corners_are_valid_inclusive_bounds(self):
        result=analyze({'fixture':'clean','crop_corners':[[0,0],[1,0],[1,1],[0,1]]})
        self.assertEqual(result['recovery']['variants'][0]['size'],[639,479])

    def test_sharpening_is_bounded_repeatable_and_does_not_modify_original(self):
        image=fixture('blur');before=image.copy();sharpened=sharpen_edges(image)
        self.assertEqual(sharpened.dtype,np.uint8)
        self.assertEqual(sharpened.shape,image.shape)
        self.assertGreater(float(np.abs(sharpened.astype(float)-image).mean()),0)
        self.assertLess(float(np.abs(sharpened.astype(float)-image).mean()),3)
        np.testing.assert_array_equal(sharpen_edges(image),sharpened)
        np.testing.assert_array_equal(image,before)

    def test_sharpen_toggle_leaves_original_comparison_unchanged(self):
        plain=analyze({'fixture':'clean'})['recovery']
        sharp=analyze({'fixture':'clean','sharpen':True})['recovery']
        self.assertFalse(plain['sharpened']);self.assertTrue(sharp['sharpened'])
        self.assertEqual(plain['original_image'],sharp['original_image'])
        self.assertNotEqual(plain['variants'][0]['image'],sharp['variants'][0]['image'])
        for group in ['variants','uncropped_variants']:
            for variant in sharp[group]:
                img=cv2.imdecode(np.frombuffer(base64.b64decode(variant['image'].split(',')[1]),np.uint8),cv2.IMREAD_COLOR)
                self.assertEqual(variant['size'],[img.shape[1],img.shape[0]])
                self.assertLessEqual(max(img.shape[:2]),1200)

if __name__=='__main__':unittest.main()
