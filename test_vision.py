import unittest
import numpy as np
import cv2
from vision import fixture, inspect

class VisionTests(unittest.TestCase):
    @staticmethod
    def table_page(clipped=False, rotate=False, scale=1):
        image=np.full((800,700,3),45,dtype=np.uint8)
        cv2.rectangle(image,(70,0 if clipped else 50),(630,799 if clipped else 750),(220,220,220),-1)
        cv2.rectangle(image,(120,310),(580,530),(25,25,25),3)
        for y in [380,450]:cv2.line(image,(120,y),(580,y),(25,25,25),2)
        for y in [360,430,500]:cv2.putText(image,'TABLE TEXT',(160,y),cv2.FONT_HERSHEY_SIMPLEX,.8,(25,25,25),2)
        cv2.putText(image,'WHOLE PAGE TITLE',(120,150),cv2.FONT_HERSHEY_SIMPLEX,.8,(25,25,25),2)
        if rotate:image=cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE)
        if scale!=1:image=cv2.resize(image,None,fx=scale,fy=scale)
        return image
    def test_inner_table_on_clipped_paper_is_not_a_page(self):
        for rotate in [False,True]:
            for scale in [.75,1,2]:
                with self.subTest(rotate=rotate,scale=scale):
                    result=inspect(self.table_page(True,rotate,scale))
                    self.assertEqual(result['decision'],'retake')
                    self.assertIn('document_boundary_uncertain',result['reasons'])
                    self.assertNotIn('polygon',result)
    def test_framed_page_with_table_keeps_title_and_margins(self):
        for rotate in [False,True]:
            result=inspect(self.table_page(False,rotate))
            self.assertEqual(result['decision'],'review_ready')
            self.assertGreater(result['document_fraction'],.65)
    def test_one_unsupported_side_requests_retake(self):
        image=self.table_page(False)
        # Same paper-tone background below the sheet: bottom border ink must
        # not substitute for a visible paper/background transition.
        image[746:]=(220,220,220)
        cv2.line(image,(70,749),(630,749),(25,25,25),3)
        result=inspect(image)
        self.assertEqual(result['decision'],'retake')
        self.assertNotIn('polygon',result)
    def test_small_low_contrast_page_does_not_become_tabletop(self):
        image=np.full((1080,1920,3),160,dtype=np.uint8)
        page=np.array([[740,180],[1180,200],[1230,820],[700,810]],np.int32)
        cv2.fillConvexPoly(image,page,(185,185,185))
        for y in range(280,720,45):cv2.putText(image,'TEST PAGE',(790,y),cv2.FONT_HERSHEY_SIMPLEX,.75,(30,30,30),2)
        result=inspect(image)
        self.assertEqual(result['detection'],'automatic_page_edges')
        self.assertEqual(result['decision'],'review_ready')
        self.assertLess(result['document_fraction'],.2)
        self.assertGreater(result['document_fraction'],.1)
    def test_clean_control(self): self.assertEqual(inspect(fixture())['decision'],'review_ready')
    def test_inner_table_generated_example(self):
        result=inspect(fixture('inner_table'))
        self.assertEqual(result['decision'],'retake')
        self.assertEqual(result['reasons'],['document_boundary_uncertain'])
        self.assertNotIn('polygon',result)
    def test_blur(self): self.assertIn('blur_or_no_detail',inspect(fixture('blur'))['reasons'])
    def test_clipped(self): self.assertIn('edge_clipped',inspect(fixture('clipped'))['reasons'])
    def test_glare(self): self.assertIn('bright_region_possible_glare',inspect(fixture('glare'))['reasons'])
    def test_missing(self): self.assertEqual(inspect(fixture('missing'))['reasons'],['document_not_found'])
    def test_blank(self): self.assertIn('blur_or_no_detail',inspect(fixture('blank'))['reasons'])
    def test_repeatability_and_immutability(self):
        a=fixture(); before=a.copy(); self.assertEqual(inspect(a),inspect(a));np.testing.assert_array_equal(a,before)
    def test_bad_input(self):
        for image in [None,np.zeros((20,20,3),dtype=np.uint8),np.zeros((120,120),dtype=np.uint8)]:
            with self.assertRaises(ValueError):inspect(image)
    def test_merged_background_is_uncertain_not_clipped(self):
        image=np.full((480,640,3),40,dtype=np.uint8)
        cv2.rectangle(image,(0,10),(639,80),(220,220,220),-1)
        cv2.rectangle(image,(300,75),(315,110),(220,220,220),-1)
        cv2.rectangle(image,(250,100),(350,420),(220,220,220),-1)
        result=inspect(image)
        self.assertEqual(result['decision'],'retake')
        self.assertNotIn('edge_clipped',result['reasons'])
    def test_skewed_page_on_busy_background(self):
        image=np.full((800,700,3),55,dtype=np.uint8)
        cv2.rectangle(image,(0,0),(699,110),(230,230,230),-1)
        polygon=np.array([[150,170],[540,190],[580,720],[100,700]],np.int32)
        cv2.fillConvexPoly(image,polygon,(220,220,220))
        for y in range(250,650,40):cv2.putText(image,'FICTIONAL TEXT',(180,y),cv2.FONT_HERSHEY_SIMPLEX,.55,(30,30,30),2)
        result=inspect(image)
        self.assertEqual(result['decision'],'review_ready')
        self.assertEqual(result['detection'],'automatic_page_edges')
        self.assertIn('polygon',result)
        self.assertNotIn('edge_clipped',result['reasons'])
    def test_blank_skewed_page_still_requests_retake(self):
        image=np.full((800,700,3),40,dtype=np.uint8)
        cv2.fillConvexPoly(image,np.array([[150,170],[540,190],[580,720],[100,700]],np.int32),(220,220,220))
        self.assertIn('blur_or_no_detail',inspect(image)['reasons'])
    def test_manual_region_checks_quality_and_defers_framing(self):
        result=inspect(fixture(),[90,50,460,380])
        self.assertEqual(result['decision'],'review_ready')
        self.assertEqual(result['framing_assessment'],'human_review_required')
        self.assertEqual(result['detection'],'user_marked')
        self.assertIn('blur_or_no_detail',inspect(fixture('blur'),[90,50,460,380])['reasons'])
    def test_manual_region_bounds_and_types(self):
        for region in [[-1,0,100,100],[0,0,641,100],[0,0,49,100],[0,0,100,100.5],[False,0,100,100],[0,0,100],{}]:
            with self.assertRaises(ValueError):inspect(fixture(),region)

if __name__=='__main__': unittest.main()
