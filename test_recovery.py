import base64
import unittest
import cv2
import numpy as np
from vision import fixture,inspect
from recovery import proposals
from service import analyze
from page_crop import visible_page_crop

class RecoveryTests(unittest.TestCase):
    def test_complete_page_is_cropped_to_supported_edges(self):
        r=analyze({'fixture':'clean'})['recovery']
        self.assertTrue(r['crop_applied'])
        self.assertEqual(r['geometry']['method'],'perspective_alignment')
        self.assertLess(r['variants'][0]['size'][0],640)
        self.assertEqual(r['uncropped_variants'][0]['size'],[640,480])
        self.assertFalse(r['geometry']['whole_page_verified'])
    def test_undo_sources_preserve_full_frame_and_all_styles(self):
        original=fixture('clean');r=proposals(original,inspect(original))
        for v in r['uncropped_variants']:
            decoded=cv2.imdecode(np.frombuffer(base64.b64decode(v['image'].split(',')[1]),np.uint8),cv2.IMREAD_COLOR)
            self.assertEqual(decoded.shape,original.shape)
        natural=cv2.imdecode(np.frombuffer(base64.b64decode(r['uncropped_variants'][0]['image'].split(',')[1]),np.uint8),cv2.IMREAD_COLOR)
        self.assertLess(float(np.abs(natural.astype(float)-original).mean()),3)
    def test_visible_slanted_edge_crops_textured_background_not_inner_table(self):
        rng=np.random.default_rng(17)
        gray=np.clip(rng.normal(100,25,(600,420)),0,255).astype(np.uint8)
        paper=np.array([[0,0],[419,0],[419,430],[0,470]],np.int32)
        cv2.fillConvexPoly(gray,paper,205)
        cv2.rectangle(gray,(65,110),(350,280),25,3)
        for y in [150,190,230]:cv2.putText(gray,'TEST LINE',(80,y),cv2.FONT_HERSHEY_SIMPLEX,.5,25,1)
        for turns in range(4):
            rotated=np.rot90(gray,turns).copy()
            found=visible_page_crop(rotated)
            self.assertIsNotNone(found)
            corners,meta=found
            self.assertTrue(meta['may_be_partial'])
            self.assertFalse(meta['whole_page_verified'])
            mask=np.zeros_like(rotated);cv2.fillConvexPoly(mask,np.rint(corners).astype(np.int32),255)
            wanted=np.rot90(np.where(cv2.fillConvexPoly(np.zeros_like(gray),paper,255)>0,1,0),turns)
            self.assertGreater(float((mask[wanted>0]>0).mean()),.97)
            self.assertLess(cv2.contourArea(corners)/rotated.size,.85)
    def test_partial_edge_does_not_crop_uniform_ink_band_or_blank_frame(self):
        gray=np.full((600,420),205,np.uint8)
        cv2.rectangle(gray,(0,0),(60,599),30,-1)
        cv2.rectangle(gray,(100,150),(350,300),30,3)
        self.assertIsNone(visible_page_crop(gray))
        self.assertIsNone(visible_page_crop(np.full((600,420),205,np.uint8)))
    def test_all_variants_are_bounded_decodable(self):
        result=analyze({'fixture':'clean'})
        recovery=result['recovery']
        self.assertTrue(recovery['available'])
        self.assertEqual([v['id'] for v in recovery['variants']],['natural','contrast','bw'])
        for v in recovery['variants']:
            img=cv2.imdecode(np.frombuffer(base64.b64decode(v['image'].split(',')[1]),np.uint8),cv2.IMREAD_COLOR)
            self.assertLessEqual(max(img.shape[:2]),1200)
            self.assertEqual(v['size'],[img.shape[1],img.shape[0]])
    def test_missing_page_does_not_offer_recovery(self):
        self.assertFalse(analyze({'fixture':'missing'})['recovery']['available'])
    def test_crop_does_not_promote_clipped_page(self):
        result=analyze({'fixture':'clipped'})
        self.assertEqual(result['decision'],'retake')
        self.assertIn('edge_clipped',result['reasons'])
        self.assertTrue(result['recovery']['available'])
        self.assertTrue(result['recovery']['human_acceptance_required'])
        self.assertFalse(result['recovery']['geometry']['whole_page_verified'])
    def test_inner_table_never_becomes_the_recovery_crop(self):
        result=analyze({'fixture':'inner_table'})
        self.assertEqual(result['decision'],'retake')
        self.assertNotIn('document_preview',result)
        recovery=result['recovery']
        self.assertEqual(recovery['geometry']['method'],'tentative_outer_bright_region_crop')
        x,y,w,h=recovery['geometry']['source_box']
        self.assertEqual(y,0)
        self.assertEqual(h,480)
        self.assertGreater(w,400)
    def test_recovery_is_repeatable_and_does_not_mutate_original(self):
        image=fixture('glare');before=image.copy();result=inspect(image)
        self.assertEqual(proposals(image,result),proposals(image,result))
        np.testing.assert_array_equal(image,before)
        self.assertIn('bright_region_possible_glare',result['reasons'])
    def test_enhancement_does_not_hide_blur_or_change_action(self):
        result=analyze({'fixture':'blur'})
        self.assertEqual(result['decision'],'retake')
        self.assertEqual(result['trace'][-1]['action'],'request_retake')
        self.assertIn('blur_or_no_detail',result['reasons'])
        self.assertTrue(result['recovery']['automatic_decision_unchanged'])

if __name__=='__main__':unittest.main()
