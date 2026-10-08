import unittest
import cv2
import numpy as np
from rectify import align_page
from service import analyze


class AlignmentTests(unittest.TestCase):
    def test_corner_order_and_input_preservation(self):
        image = np.zeros((240, 320, 3), dtype=np.uint8)
        for x, y, color in [(40,40,(0,0,255)),(280,40,(0,255,0)),(280,200,(255,0,0)),(40,200,(255,255,255))]:
            cv2.circle(image, (x,y), 20, color, -1)
        before = image.copy()
        for polygon in [[[280,200],[40,40],[40,200],[280,40]], [[40,200],[280,200],[280,40],[40,40]]]:
            aligned, meta = align_page(image, polygon)
            self.assertEqual(meta['size'], [240,160])
            np.testing.assert_array_equal(aligned[5,5], [0,0,255])
            np.testing.assert_array_equal(aligned[5,-6], [0,255,0])
            np.testing.assert_array_equal(aligned[-6,-6], [255,0,0])
        np.testing.assert_array_equal(image, before)

    def test_bounded_output(self):
        aligned, _ = align_page(np.zeros((2000,2500,3),np.uint8), [[20,20],[2480,30],[2470,1980],[30,1970]])
        self.assertLessEqual(max(aligned.shape[:2]), 1600)

    def test_invalid_geometry(self):
        image = np.zeros((200,200,3), np.uint8)
        for polygon in [[[0,0]]*4, [[0,0],[200,0],[199,199],[0,199]], [[0,0],[1,0],[2,0],[3,0]]]:
            with self.assertRaises(ValueError):
                align_page(image, polygon)

    def test_crop_does_not_change_quality_verdict(self):
        clean = analyze({'fixture':'clean'})
        self.assertEqual(clean['decision'], 'review_ready')
        self.assertTrue(clean['document_preview'].startswith('data:image/jpeg;base64,'))
        self.assertGreater(clean['processing_ms'], 0)
        missing = analyze({'fixture':'missing'})
        self.assertEqual(missing['decision'], 'retake')
        self.assertNotIn('document_preview', missing)
