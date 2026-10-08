"""Bounded perspective alignment for detected pages; never changes the verdict."""
import cv2
import numpy as np


def manual_boundary(image, corners):
    """Validate ordered normalized user corners without silently repairing them."""
    if not isinstance(corners, list) or len(corners) != 4 or any(
        not isinstance(p, list) or len(p) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v)
            for v in p) for p in corners):
        raise ValueError('Select four finite corners in boundary order')
    points = np.asarray(corners, dtype=np.float64)
    if np.any(points < 0) or np.any(points > 1):
        raise ValueError('Keep all crop corners inside the original photo')
    h, w = image.shape[:2]
    pixels = (points * [w-1, h-1]).astype(np.float32)
    edges = np.roll(pixels, -1, axis=0) - pixels
    if (not cv2.isContourConvex(pixels.reshape(4, 1, 2)) or
        cv2.contourArea(pixels) < 100 or np.min(np.linalg.norm(edges, axis=1)) < 10):
        raise ValueError('Use an uncrossed four-corner border with edges at least 10 pixels long')
    return pixels


def align_page(image, polygon, max_side=1600):
    points = np.asarray(polygon, dtype=np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError('Expected four finite page corners')
    h, w = image.shape[:2]
    if np.any(points < 0) or np.any(points[:, 0] >= w) or np.any(points[:, 1] >= h):
        raise ValueError('Page corners must stay inside the photo')
    center = points.mean(axis=0)
    points = points[np.argsort(np.arctan2(points[:, 1]-center[1], points[:, 0]-center[0]))]
    points = np.roll(points, -int(np.argmin(points.sum(axis=1))), axis=0)
    if not cv2.isContourConvex(points.reshape(4, 1, 2)) or cv2.contourArea(points) < 100:
        raise ValueError('Page corners must form a non-degenerate convex boundary')
    tl, tr, br, bl = points
    width = max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl))
    height = max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr))
    scale = min(1., max_side/max(width, height))
    out_w, out_h = max(2, round(width*scale)), max(2, round(height*scale))
    target = np.array([[0, 0], [out_w-1, 0], [out_w-1, out_h-1], [0, out_h-1]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(points, target)
    aligned = cv2.warpPerspective(image, transform, (out_w, out_h), flags=cv2.INTER_LINEAR)
    return aligned, {'size': [out_w, out_h], 'source_corners': points.tolist(),
                     'transform': transform.tolist(), 'method': 'opencv_perspective_alignment',
                     'note': 'Geometric alignment only; inspect against the original before use.'}
