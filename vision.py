"""Synthetic feasibility baseline; not validated for real document capture."""
import cv2
import numpy as np
POLICY = 'capturegate-v0.9-manual-borders'

def inspect(image, region=None):
    if not cv2.__version__.startswith('5.'):
        raise RuntimeError('OpenCV 5 is required')
    if not isinstance(image,np.ndarray) or image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError('Expected a decoded BGR image')
    h, w = image.shape[:2]
    if min(h, w) < 100 or max(h, w) > 4000:
        raise ValueError('Dimensions must be 100–4000 pixels')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    manual = region is not None
    if manual:
        if not isinstance(region,list) or len(region)!=4 or any(type(n) is not int for n in region):
            raise ValueError('Document area must contain four integer coordinates')
        x,y,rw,rh=region
        if x<0 or y<0 or rw<50 or rh<50 or x+rw>w or y+rh>h:
            raise ValueError('Document area must stay inside the photo and be at least 50 pixels wide and high')
        area=rw*rh/(h*w)
        clipped=False
    else:
        boundary_diagnostics={}
        polygon = locate_page(gray,boundary_diagnostics)
        if polygon is not None:
            mask=np.zeros_like(gray)
            cv2.fillConvexPoly(mask,polygon,255)
            interior=cv2.erode(mask,np.ones((21,21),np.uint8))>0
            detail=cv2.Laplacian(gray,cv2.CV_64F)[interior]
            sharpness=float(detail.var())
            glare_fraction=float(np.mean(gray[interior]>=250))
            reasons=[]
            if sharpness<80:reasons.append('blur_or_no_detail')
            if glare_fraction>.08:reasons.append('bright_region_possible_glare')
            x,y,rw,rh=cv2.boundingRect(polygon)
            return {'decision':'retake' if reasons else 'review_ready','reasons':reasons,
                    'sharpness':round(sharpness,3),'bright_fraction':round(glare_fraction,4),
                    'document_fraction':round(cv2.contourArea(polygon)/(h*w),4),
                    'box':[x,y,rw,rh],'polygon':polygon.tolist(),'opencv':cv2.__version__,
                    'detection':'automatic_page_edges','framing_assessment':'heuristic_only'}
        if boundary_diagnostics.get('unsupported_candidates',0):
            # Never let the bright-blob fallback promote a rejected inner
            # rectangle. No polygon means no misleading aligned export.
            return {'decision':'retake','reasons':['document_boundary_uncertain'],
                    'detection':'uncertain','framing_assessment':'heuristic_only',
                    'boundary_check':'insufficient_paper_background_separation',
                    'opencv':cv2.__version__}
        located=locate(gray)
        if located is None:
            return {'decision':'retake','reasons':['document_not_found'],'opencv':cv2.__version__}
        x,y,rw,rh,area,fill=located
        clipped=x<=2 or y<=2 or x+rw>=w-2 or y+rh>=h-2
        # A border-touching irregular bright blob can include hands/tables.
        # It is not evidence that the document itself was cut off.
        if fill<.80:
            return {'decision':'retake','reasons':['document_boundary_uncertain'],'candidate_box':[x,y,rw,rh],
                    'detection':'uncertain','opencv':cv2.__version__}
    roi = gray[y+10:y+rh-10, x+10:x+rw-10]
    if roi.size == 0:
        raise ValueError('Document region too small')
    sharpness = float(cv2.Laplacian(roi, cv2.CV_64F).var())
    glare_fraction = float(np.mean(roi >= 250))
    reasons = []
    if clipped: reasons.append('edge_clipped')
    if sharpness < 80: reasons.append('blur_or_no_detail')
    if glare_fraction > .08: reasons.append('bright_region_possible_glare')
    return {'decision':'retake' if reasons else 'review_ready', 'reasons':reasons,
            'sharpness':round(sharpness,3),'bright_fraction':round(glare_fraction,4),
            'document_fraction':round(area,4),'box':[x,y,rw,rh],'opencv':cv2.__version__,
            'detection':'user_marked' if manual else 'automatic',
            'framing_assessment':'human_review_required' if manual else 'heuristic_only'}

def boundary_support(gray, points):
    """Fraction of samples showing lighter paper inside each candidate edge.

    Sample away from the contour ink, using medians across several offsets.
    A printed box surrounded by the same paper is not a supported page edge.
    This deliberately abstains for indistinguishable paper/background; it is
    not a semantic guarantee that a rectangle is a whole document.
    """
    center=points.mean(axis=0)
    support=[]
    for i in range(4):
        a=points[i].astype(float);b=points[(i+1)%4].astype(float)
        normal=np.array([-(b-a)[1],(b-a)[0]])
        normal/=np.linalg.norm(normal)
        if np.dot(normal,center-(a+b)/2)<0:normal=-normal
        edge=a+(b-a)*np.linspace(.15,.85,40)[:,None]
        offsets=np.array([5,9,14,20])[:,None,None]
        def sample(sign):
            xy=np.rint(edge[None,:,:]+sign*offsets*normal).astype(int)
            xy[:,:,0]=np.clip(xy[:,:,0],0,gray.shape[1]-1)
            xy[:,:,1]=np.clip(xy[:,:,1],0,gray.shape[0]-1)
            return np.median(gray[xy[:,:,1],xy[:,:,0]],axis=0)
        difference=sample(1).astype(float)-sample(-1).astype(float)
        support.append(float(np.mean(difference>=8)))
    return support

def locate_page(gray, diagnostics=None):
    """Find a closed convex page boundary, excluding image-frame contours.

    Multiple edge thresholds improve lighting tolerance. Candidates must have
    plausible angles, area and lighter-paper support along all four sides.
    Internal ink rectangles with paper continuing outside are not accepted.
    This remains a geometric heuristic, not a trained document detector.
    """
    h,w=gray.shape
    scale=min(1.,900/max(h,w))
    small=cv2.resize(gray,(round(w*scale),round(h*scale))) if scale<1 else gray
    smooth=cv2.GaussianBlur(small,(5,5),0)
    candidates=[]
    for low,high in [(10,30),(20,60),(30,90),(50,150),(75,200)]:
        edges=cv2.Canny(smooth,low,high)
        edges=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for contour in sorted(contours,key=cv2.contourArea,reverse=True)[:40]:
            quad=cv2.approxPolyDP(contour,.025*cv2.arcLength(contour,True),True)
            if len(quad)!=4 or not cv2.isContourConvex(quad):continue
            points=quad.reshape(4,2)
            area=cv2.contourArea(quad)/small.size
            if not .04<=area<=.95:continue
            if np.any(points[:,0]<=3) or np.any(points[:,1]<=3) or np.any(points[:,0]>=small.shape[1]-4) or np.any(points[:,1]>=small.shape[0]-4):continue
            vectors=points.astype(float)
            cosines=[]
            for i in range(4):
                a=vectors[(i-1)%4]-vectors[i];b=vectors[(i+1)%4]-vectors[i]
                cosines.append(abs(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))))
            if max(cosines)>.55:continue
            mask=np.zeros_like(small);cv2.fillConvexPoly(mask,points,255)
            if float(np.median(small[mask>0]))<120:continue
            if min(boundary_support(small,points))<.60:
                if diagnostics is not None:
                    diagnostics['unsupported_candidates']=diagnostics.get('unsupported_candidates',0)+1
                continue
            candidates.append((area*(1-max(cosines)),points))
    if not candidates:return None
    return np.rint(max(candidates,key=lambda row:row[0])[1]/scale).astype(np.int32)

def locate(gray):
    h,w=gray.shape
    mask = cv2.inRange(gray, 120, 255)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    x, y, rw, rh = cv2.boundingRect(contour)
    area = cv2.contourArea(contour) / (h*w)
    if area < .20:
        return None
    return x,y,rw,rh,area,cv2.contourArea(contour)/(rw*rh)

def fixture(kind='clean'):
    image = np.full((480,640,3),40,dtype=np.uint8)
    cv2.rectangle(image,(90,50),(550,430),(220,220,220),-1)
    for i in range(9):
        cv2.putText(image,f'SYNTHETIC LINE {i+1}',(115,95+i*35),cv2.FONT_HERSHEY_SIMPLEX,.6,(30,30,30),2)
    if kind == 'blur': image=cv2.GaussianBlur(image,(25,25),8)
    elif kind == 'clipped': image=image[:,110:]
    elif kind == 'glare': cv2.rectangle(image,(230,120),(440,330),(255,255,255),-1)
    elif kind == 'missing': image[:]=40
    elif kind == 'blank': cv2.rectangle(image,(90,50),(550,430),(220,220,220),-1)
    elif kind == 'inner_table':
        image[:]=40
        cv2.rectangle(image,(90,0),(550,479),(220,220,220),-1)
        cv2.rectangle(image,(125,140),(515,320),(25,25,25),3)
        for y in [200,260]:cv2.line(image,(125,y),(515,y),(25,25,25),2)
        for y in [180,240,300]:cv2.putText(image,'FICTIONAL TABLE',(150,y),cv2.FONT_HERSHEY_SIMPLEX,.6,(25,25,25),2)
        cv2.putText(image,'PAGE TITLE',(145,80),cv2.FONT_HERSHEY_SIMPLEX,.7,(25,25,25),2)
    elif kind != 'clean': raise ValueError('Unknown fixture')
    return image
