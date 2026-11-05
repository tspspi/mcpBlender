"""Bounded paired-depth span selection, without surface-identity inference.

Opposed orthographic views share vertical coordinates and mirror horizontal
coordinates. First-hit depth is not a filtered surface-identity measurement.
"""
from array import array
import math
from . import capture_data,depth_tiles,botany

FORMAT='mcpblender-paired-depth-shadow-mask-v1'
MASK_ROLES=('SHADOW_ONLY','DIFFUSE_SHADOW','SECONDARY')


def options(value):
    if not isinstance(value,dict) or set(value)!={'receiver_view','minimum_span_m'}:raise ValueError('Invalid paired shadow mask options')
    from .card_views import DIRECTIONS
    if value['receiver_view'] not in DIRECTIONS:raise ValueError('Unknown shadow receiver view')
    span=value['minimum_span_m']
    if type(span) not in (int,float) or not math.isfinite(span) or not 0<=span<=1e6:raise ValueError('Invalid shadow minimum span')
    return value|{'minimum_span_m':float(span)}


def frame(layer,receiver,unit,width):
    """Validate a common pixel grid before reading or pairing any EXR samples."""
    if not math.isfinite(unit) or unit<=0:raise ValueError('Positive source units required for paired shadow mask')
    cl,al,_=capture_data.pose(layer['matrix_world'],unit=True)
    cr,ar,_=capture_data.pose(receiver['matrix_world'],unit=True)
    spans=[v['ortho_scale'] for v in (layer,receiver)]
    if any(not math.isfinite(s) or s<=0 for s in spans):raise ValueError('Invalid paired shadow camera span')
    for v in (layer,receiver):
        if not 0<v['clip_start']<v['clip_end'] or not all(math.isfinite(v[k]) for k in ('clip_start','clip_end')):raise ValueError('Invalid paired shadow clipping')
    # Bound alignment to 1e-4 source pixels. No resampling or nearest-grid guess.
    tol=1e-4/width
    if abs(spans[0]-spans[1])>spans[0]*tol or any(abs(al[a][k]-sign*ar[a][k])>tol for a,sign in ((0,-1),(1,1),(2,-1)) for k in range(3)):
        raise ValueError('Paired shadow views require opposed cameras, mirrored U, common V and equal span')
    delta=[a-b for a,b in zip(cr,cl)];baseline=capture_data.dot(delta,ar[2])
    if baseline<=0 or any(abs(capture_data.dot(delta,ar[a]))>spans[0]*tol for a in (0,1)):raise ValueError('Paired shadow cameras require a positive common-axis baseline')
    return baseline


def build(layer_data,receiver_data,layer,receiver,unit,settings,mask,*,cancelled=lambda:None,progress=lambda v:None):
    mask=options(mask);p=depth_tiles.options(settings);w=layer_data['width'];h=layer_data['height']
    if type(w) is not int or type(h) is not int or w!=h or not 1<=w<=1024 or w*h>p['max_pixels']:raise ValueError('Paired shadow pixel budget exceeded')
    if layer['view']==receiver['view'] or receiver['view']!=mask['receiver_view']:raise ValueError('Paired shadow receiver must be a different captured view')
    for d in (layer_data,receiver_data):
        if (d['width'],d['height'])!=(w,h) or tuple(d['data_window'])!=(0,0,w-1,h-1):raise ValueError('Paired shadow requires identical full-frame data windows')
        if any(len(d['channels'][key])!=w*h for key in ('TreeCapture.Combined.A','TreeCapture.Depth.Z')):raise ValueError('Paired shadow channel length mismatch')
    baseline=frame(layer,receiver,unit,w)
    la,ld=(layer_data['channels']['TreeCapture.'+k] for k in ('Combined.A','Depth.Z'))
    ra,rd=(receiver_data['channels']['TreeCapture.'+k] for k in ('Combined.A','Depth.Z'))
    pixels=array('f');known=kept=covered=0;mass=retained=0.;low=math.inf;high=-math.inf
    for i in range(w*h):
        if i%4096==0:cancelled();progress({'phase':'pairing opposed shadow depth samples','completed':i,'total':w*h})
        j=i//w*w+(w-1-i%w);a,b=la[i],ra[j]
        if any(not math.isfinite(v) or not -1e-6<=v<=1+1e-6 for v in (a,b)):raise ValueError('Invalid paired shadow coverage')
        active=a>p['alpha_threshold'];covered+=active
        valid=active and b>p['alpha_threshold'] and math.isfinite(ld[i]) and math.isfinite(rd[j]) and layer['clip_start']<=ld[i]<=layer['clip_end'] and receiver['clip_start']<=rd[j]<=receiver['clip_end']
        span=(baseline-ld[i]-rd[j])*unit if valid else 0.
        if valid:known+=1;low=min(low,span);high=max(high,span)
        keep=valid and span>mask['minimum_span_m'];kept+=keep;pixels.append(float(keep));mass+=a;retained+=a*keep
    report={'format':FORMAT,'options':mask,'layer_view':layer['view'],'width':w,'height':h,
            'receiver_pixel_mapping':'MIRROR_U_SAME_V','camera_baseline_m':baseline*unit,
            'source_pixel_width_m':layer['ortho_scale']/w*unit,'alpha_threshold':p['alpha_threshold'],
            'covered_pixels':covered,'known_pixels':known,'unknown_covered_pixels':covered-known,'retained_pixels':kept,
            'original_alpha_mass':mass,'retained_alpha_mass':retained,'measured_span_range_m':[low,high] if known else None,
            'unknown_policy':'EXCLUDE','comparison':'SPAN_STRICTLY_GREATER_THAN_MINIMUM','mask_float32_sha256':depth_tiles.floats_sha(pixels),
            'scope':'Receiver-dependent binary depth-span selection for camera-excluded shadow, diffuse/shadow or secondary layers. Multiply layer coverage once; do not alter geometry, normals or PBR inputs. First-hit samples and filtered coverage may describe different subpixel surfaces. Positive span does not prove distinct surface identity; no duplicate-removal, relighting, angular or shadow equivalence guarantee.'}
    report['mask_sha256']=botany.digest(report)
    return pixels,report
