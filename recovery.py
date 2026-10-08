"""Bounded, non-generative cleanup proposals; never promotes the verdict."""
import base64
import cv2
import numpy as np
from rectify import align_page, manual_boundary
from vision import locate, locate_page
from page_crop import visible_page_crop

MAX_SIDE=1200

def jpeg(image):
    ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,88])
    if not ok:raise ValueError('Unable to encode cleanup preview')
    return 'data:image/jpeg;base64,'+base64.b64encode(encoded).decode()

def sharpen_edges(image):
    """Mild luminance-only unsharp mask, no text reconstruction or upscaling."""
    lab=cv2.cvtColor(image,cv2.COLOR_BGR2LAB) if image.ndim==3 else None
    light=(lab[:,:,0] if lab is not None else image).astype(np.float32)
    detail=light-cv2.GaussianBlur(light,(0,0),.8)
    adjusted=np.clip(light+.5*np.clip(detail,-16,16),0,255).astype(np.uint8)
    if lab is None:return adjusted
    lab[:,:,0]=adjusted
    return cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)

def proposals(image,result,crop_corners=None,sharpen=False):
    h,w=image.shape[:2]
    manual=manual_boundary(image,crop_corners) if crop_corners is not None else None
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    attempts=[{'step':'multi_threshold_edges','outcome':result.get('detection','not_found')}]
    warnings=['Cleanup cannot recover missing text, undo severe blur or prove completeness. Compare every needed line with the original.']
    if manual is None and (float(gray.std())<4 or result.get('reasons')==['document_not_found']):
        return {'available':False,'attempts':attempts,'reason':'No usable page proposal; retake the photo.','warnings':warnings}
    base=image
    geometry={'method':'original_photo','whole_page_verified':False,'source_box':[0,0,w,h]}
    polygon=result.get('polygon')
    if polygon is None:
        # A second, illumination-normalized edge pass may find a page, but its
        # edges must still have support in the ORIGINAL pixels. Never certify
        # a contrast-created boundary or an internal printed box.
        from vision import boundary_support
        enhanced=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(gray)
        candidate=locate_page(enhanced)
        supported=candidate is not None and min(boundary_support(gray,candidate))>=.60
        attempts.append({'step':'illumination_normalized_edges','outcome':'supported_candidate' if supported else 'no_supported_candidate'})
        if supported:polygon=candidate.tolist()
    if polygon is not None:
        base,alignment=align_page(image,polygon,MAX_SIDE)
        geometry={'method':'perspective_alignment','source_corners':alignment['source_corners'],
                  'whole_page_verified':False,'boundary_support':'heuristic_only'}
        attempts.append({'step':'perspective_alignment','outcome':'proposal_created'})
    else:
        partial=visible_page_crop(gray)
        if partial is not None:
            corners,geometry=partial
            base,alignment=align_page(image,corners,MAX_SIDE)
            geometry['source_corners']=alignment['source_corners']
            attempts.append({'step':'visible_outer_edges','outcome':'partial_crop_proposed'})
            warnings.append('Some page edges are outside the photo. Auto crop follows the visible edge only; missing edges use the photo frame. Undo crop if anything needed is cut off.')
        # Only outer bright-object contours can propose a crop; never use the
        # rejected inner quadrilateral. Include a margin and preserve the
        # original for comparison. A crop may still be partial or a desk.
        located=locate(gray)
        if partial is None and located:
            x,y,rw,rh,area,fill=located
            if fill>=.80 and rw*rh/(w*h)<.95:
                margin=max(3,round(min(w,h)*.01))
                x0,y0=max(0,x-margin),max(0,y-margin)
                x1,y1=min(w,x+rw+margin),min(h,y+rh+margin)
                base=image[y0:y1,x0:x1]
                geometry={'method':'tentative_outer_bright_region_crop','source_box':[x0,y0,x1-x0,y1-y0],
                          'whole_page_verified':False,'may_be_partial':True}
        attempts.append({'step':'outer_region_crop','outcome':geometry['method']})
        warnings.append('Page boundary is uncertain. The proposal may contain background or omit content; acceptance is your judgment, not a passed whole-page check.')
    if manual is not None:
        base,alignment=align_page(image,manual,MAX_SIDE)
        geometry={'method':'manual_perspective_crop','source_corners':alignment['source_corners'],
                  'normalized_corners':crop_corners,'whole_page_verified':False,'human_selected':True}
        attempts.append({'step':'manual_border','outcome':'user_selected_crop_created'})
        warnings.append('These borders were selected by you, not verified by the detector. Check that the crop includes every needed line.')
    scale=min(1.,MAX_SIDE/max(base.shape[:2]))
    if scale<1:base=cv2.resize(base,(max(2,round(base.shape[1]*scale)),max(2,round(base.shape[0]*scale))),interpolation=cv2.INTER_AREA)
    else:base=base.copy()
    attempts.extend([{'step':'local_contrast','outcome':'proposal_created'}, {'step':'adaptive_black_white','outcome':'proposal_created'}])
    original_scale=min(1.,MAX_SIDE/max(h,w))
    original=cv2.resize(image,(max(2,round(w*original_scale)),max(2,round(h*original_scale))),interpolation=cv2.INTER_AREA) if original_scale<1 else image
    def versions(source):
        lab=cv2.cvtColor(source,cv2.COLOR_BGR2LAB)
        lab[:,:,0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(lab[:,:,0])
        color=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
        g=cv2.cvtColor(source,cv2.COLOR_BGR2GRAY)
        bw=cv2.adaptiveThreshold(g,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,15)
        return [{'id':key,'label':label,'image':jpeg(sharpen_edges(img) if sharpen else img),'size':[img.shape[1],img.shape[0]]}
                for key,label,img in [('natural','Natural color',source),('contrast','Contrast cleanup',color),('bw','Black & white',bw)]]
    cropped=geometry['method']!='original_photo'
    return {'available':True,'attempts':attempts,'geometry':geometry,'variants':versions(base),
            'uncropped_variants':versions(original),'crop_applied':cropped,'warnings':warnings,'original_image':jpeg(original),
            'sharpened':sharpen,'automatic_decision_unchanged':True,'human_acceptance_required':True,
            'note':'Three alternatives, not a guarantee of restored data. No generative fill, OCR or automatic external upload.'}
