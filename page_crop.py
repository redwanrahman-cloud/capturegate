"""Best-effort visible paper edge crop; photo-frame edges are not page edges.

Used only for review proposals when closed-page detection abstains. Long lines
must separate smooth lighter paper from textured darker surroundings. A crop
touching the photo frame is explicitly partial and never changes the verdict.
"""
import cv2
import numpy as np


def clip_side(points, normal, offset):
    output=[]
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        da,db=float(a@normal-offset),float(b@normal-offset)
        if da>=0:output.append(a)
        if (da>=0)!=(db>=0):output.append(a+(b-a)*(da/(da-db)))
    return np.asarray(output,dtype=np.float32)


def visible_page_crop(gray, diagnostics=None):
    h,w=gray.shape
    scale=min(1.,900/max(h,w))
    g=cv2.resize(gray,(round(w*scale),round(h*scale)),interpolation=cv2.INTER_AREA) if scale<1 else gray
    sh,sw=g.shape
    smooth=cv2.GaussianBlur(g,(5,5),0)
    line_groups=[]
    for low,high in [(20,60),(35,100),(60,140)]:
        edges=cv2.Canny(smooth,low,high)
        lines=cv2.HoughLinesP(edges,1,np.pi/720,threshold=55,
                             minLineLength=round(min(sh,sw)*.45),maxLineGap=round(min(sh,sw)*.12))
        if lines is not None:line_groups.append(lines.reshape(-1,4))
    if not line_groups:return None
    lines=np.concatenate(line_groups)
    # Local texture, not edge magnitude: printed bands can also be darker than
    # white paper, but smooth ink is not evidence of a textured desk boundary.
    f=g.astype(np.float32)
    variance=np.maximum(0,cv2.blur(f*f,(9,9))-cv2.blur(f,(9,9))**2)
    texture=np.sqrt(variance)
    frame=np.array([[0,0],[sw-1,0],[sw-1,sh-1],[0,sh-1]],np.float32)
    candidates=[]
    for raw in lines.reshape(-1,4):
        a,b=raw[:2].astype(float),raw[2:].astype(float)
        tangent=b-a;length=np.linalg.norm(tangent)
        tangent/=length
        if length/(sw*abs(tangent[0])+sh*abs(tangent[1]))<.55:continue
        normal=np.array([-tangent[1],tangent[0]])
        if max(abs(normal))<.90:continue
        samples=a+(b-a)*np.linspace(.12,.88,48)[:,None]
        for direction in [1,-1]:
            inward=normal*direction
            def sample(sign,source):
                xy=np.rint(samples[None,:,:]+sign*np.array([7,13,21])[:,None,None]*inward).astype(int)
                valid=(xy[:,:,0]>=0)&(xy[:,:,0]<sw)&(xy[:,:,1]>=0)&(xy[:,:,1]<sh)
                xy[:,:,0]=np.clip(xy[:,:,0],0,sw-1);xy[:,:,1]=np.clip(xy[:,:,1],0,sh-1)
                return np.median(source[xy[:,:,1],xy[:,:,0]],axis=0),valid.all(axis=0)
            inside,vi=sample(1,f);outside,vo=sample(-1,f)
            ti,_=sample(1,texture);to,_=sample(-1,texture)
            valid=vi&vo
            if valid.mean()<.75:continue
            light=(inside-outside>=8)&(inside>=110)
            rough=to>=np.maximum(ti*1.5,ti+3)
            support=float(np.mean(light[valid]))
            texture_support=float(np.mean(rough[valid]))
            if diagnostics is not None:
                diagnostics.append({'line':raw.tolist(),'direction':direction,'light':round(support,3),'texture':round(texture_support,3)})
            if support<.60:continue
            # A tiny outward allowance avoids cutting through the edge itself.
            polygon=clip_side(frame,inward,float(a@inward)-2)
            if len(polygon)!=4:continue
            fraction=cv2.contourArea(polygon)/(sw*sh)
            if not .45<=fraction<=.97:continue
            mask=np.zeros_like(g);cv2.fillConvexPoly(mask,np.rint(polygon).astype(np.int32),255)
            inside_median=float(np.median(g[mask>0]))
            outside_median=float(np.median(g[mask==0]))
            inside_texture=float(np.median(texture[mask>0]))
            outside_texture=float(np.median(texture[mask==0]))
            if diagnostics is not None:
                diagnostics.append({'candidate_line':raw.tolist(),'fraction':round(fraction,3),'inside':round(inside_median,2),'outside':round(outside_median,2),'inside_texture':round(inside_texture,2),'outside_texture':round(outside_texture,2)})
            if inside_median<120 or inside_median-outside_median<15:continue
            if outside_texture<max(inside_texture*1.5,inside_texture+3):continue
            # Prefer the outermost eligible edge, not a tighter printed border.
            score=fraction
            candidates.append((score,polygon,support,texture_support))
    if not candidates:return None
    _,polygon,support,texture_support=max(candidates,key=lambda row:row[0])
    polygon=polygon/scale
    polygon[:,0]=np.clip(polygon[:,0],0,w-1);polygon[:,1]=np.clip(polygon[:,1],0,h-1)
    return polygon,{'method':'visible_edge_partial_alignment','may_be_partial':True,
                    'photo_frame_used_for_missing_edges':True,'whole_page_verified':False,
                    'light_support':round(support,3),'texture_support':round(texture_support,3)}
