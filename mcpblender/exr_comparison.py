"""Bounded scene-linear float RGBA comparisons; no display transform or bpy."""
from array import array
import math
from . import exr_scanline,image_comparison as images


def prefix(value):
    if not isinstance(value,str) or len(value.encode('utf-8'))>256 or any(ord(c)<32 for c in value):raise ValueError('Invalid EXR pass prefix')
    return value


def decode(path,pass_prefix,alpha_mode,max_pixels,*,cancelled,progress):
    prefix(pass_prefix)
    if alpha_mode not in ('PREMULTIPLIED','STRAIGHT'):raise ValueError('Invalid EXR alpha interpretation')
    names=[(pass_prefix+'.' if pass_prefix else '')+c for c in 'RGBA']
    result=exr_scanline.decode(path,names,max_pixels=max_pixels,cancelled=cancelled,progress=progress)
    w,h=result['width'],result['height']
    if tuple(result['data_window'])!=(0,0,w-1,h-1):raise ValueError('EXR comparison requires zero-origin full-frame data windows')
    channels=[result['channels'][key] for key in names];pixels=array('f')
    for i in range(w*h):
        if i%4096==0:cancelled();progress({'phase':'interpreting comparison EXR RGBA','completed':i,'total':w*h})
        values=[row[i] for row in channels];alpha=values[3]
        if not all(math.isfinite(v) for v in values) or not 0<=alpha<=1:raise ValueError('Comparison EXR requires finite RGB and normalized alpha; no clamping')
        pixels.extend([*(v*alpha if alpha_mode=='STRAIGHT' else v for v in values[:3]),alpha])
    return w,h,pixels,result['sha256']


def compare(reference,candidate,*,reference_pass,candidate_pass,reference_alpha_mode='PREMULTIPLIED',candidate_alpha_mode='PREMULTIPLIED',
            max_pixels=1024**2,scales=(1,2,4),alpha_threshold=.5,policy=None,cancelled=lambda:None,progress=lambda v:None):
    policy=images._options(scales,alpha_threshold,policy,hdr=True)
    w,h,a,ref_sha=decode(reference,reference_pass,reference_alpha_mode,max_pixels,cancelled=cancelled,progress=progress)
    cw,ch,b,cand_sha=decode(candidate,candidate_pass,candidate_alpha_mode,max_pixels,cancelled=cancelled,progress=progress)
    if (w,h)!=(cw,ch):raise ValueError('Comparison images require identical dimensions; no automatic registration/resizing')
    levels,failures=images._evaluate(a,b,w,h,scales,alpha_threshold,policy,cancelled,progress,phase='comparing filtered scene-linear EXR images')
    return {'method':'PREMULTIPLIED_BOX_EXR_V1','color_space':'LINEAR_REC709','reference_pass':reference_pass,'candidate_pass':candidate_pass,
            'reference_alpha_mode':reference_alpha_mode,'candidate_alpha_mode':candidate_alpha_mode,'max_pixels':max_pixels,
            'alpha_threshold':alpha_threshold,'policy':policy,'reference_sha256':ref_sha,'candidate_sha256':cand_sha,
            'width':w,'height':h,'levels':levels,'passed':not failures,'failures':failures,
            'scope':'Float32 RGBA NONE/ZIPS/ZIP scanline EXR only, bounded single/multipart zero-origin full frames. Selected pass prefixes and alpha interpretation are explicit. Scene-linear RGB is treated as linear Rec709 for luminance; no OCIO/display/primaries conversion or file-header color-space inference. Finite HDR and negative RGB are preserved; alpha must be in [0,1]. Straight data is premultiplied once before box filtering; premultiplied data is retained. Relative luminance is unavailable for nonpositive shared reference luminance. No automatic alignment or matched-camera, lighting, optical, shadow, angular or runtime certification.'}
