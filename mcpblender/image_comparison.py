"""Bounded PNG decoding and premultiplied multi-scale image comparisons (stdlib)."""
from array import array
import hashlib
import math
import struct
import zlib
from .package_files import image_info

MAX_PIXELS=4*1024**2
MAX_BYTES=64*1024**2


def decode_png(data,*,color_space='SRGB',cancelled=lambda:None,progress=lambda v:None):
    if color_space not in {'SRGB','LINEAR'}:raise ValueError('Unknown image comparison colour interpretation')
    if len(data)>MAX_BYTES or len(data)<33 or data[:16]!=b'\x89PNG\r\n\x1a\n\0\0\0\rIHDR':raise ValueError('Bounded ordinary PNG input required')
    w,h,depth,color,compression,filter_method,interlace=struct.unpack_from('>IIBBBBB',data,16)
    if not 1<=w<=4096 or not 1<=h<=4096 or w*h>MAX_PIXELS or depth not in (8,16) or color not in (2,6) or compression or filter_method or interlace:
        raise ValueError('Image comparison supports non-interlaced RGB/RGBA PNG8/16 up to 4 megapixels')
    cancelled();image_info(data,'image/png') # Complete CRC and bounded stream validation.
    offset=8;compressed=bytearray()
    while offset<len(data):
        size=struct.unpack_from('>I',data,offset)[0];kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+size];offset+=size+12
        if kind in {b'iCCP',b'cICP',b'acTL',b'tRNS'}:raise ValueError('Image comparison refuses ICC/CICP/animated PNG and colour-key transparency')
        if kind==b'IDAT':compressed.extend(payload)
    channels=4 if color==6 else 3;sample=depth//8;bpp=channels*sample;stride=w*bpp
    decoder=zlib.decompressobj();raw=decoder.decompress(compressed,(stride+1)*h+1)
    if len(raw)!=(stride+1)*h or not decoder.eof or decoder.unused_data:raise ValueError('Invalid bounded PNG pixel stream')
    del compressed
    output=array('f');previous=bytearray(stride);maximum=255 if depth==8 else 65535
    # Table avoids applying the sRGB transfer millions of times for PNG8.
    def transfer(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    table=[transfer(i/255) if color_space=='SRGB' else i/255 for i in range(256)] if depth==8 else None
    for y in range(h):
        if y%32==0:cancelled();progress({'phase':'decoding comparison PNG','completed':y,'total':h})
        start=y*(stride+1);kind=raw[start];row=bytearray(raw[start+1:start+1+stride])
        if kind not in range(5):raise ValueError('Invalid PNG row filter')
        if kind:
            for x in range(stride):
                a=row[x-bpp] if x>=bpp else 0;b=previous[x];c=previous[x-bpp] if x>=bpp else 0
                if kind==1:predict=a
                elif kind==2:predict=b
                elif kind==3:predict=(a+b)//2
                else:
                    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);predict=a if pa<=pb and pa<=pc else b if pb<=pc else c
                row[x]=(row[x]+predict)&255
        for x in range(w):
            start=x*bpp
            values=list(row[start:start+bpp]) if depth==8 else list(struct.unpack_from('>'+str(channels)+'H',row,start))
            rgb=[table[v] if table is not None else transfer(v/maximum) if color_space=='SRGB' else v/maximum for v in values[:3]]
            alpha=values[3]/maximum if channels==4 else 1.
            output.extend([*(v*alpha for v in rgb),alpha])
        previous=row
    cancelled();return w,h,output


def downsample(pixels,w,h,factor,cancelled=lambda:None):
    if factor==1:return pixels,w,h
    width=(w+factor-1)//factor;height=(h+factor-1)//factor;out=array('f')
    for y in range(0,h,factor):
        cancelled()
        for x in range(0,w,factor):
            sums=[0.,0.,0.,0.];count=0
            for yy in range(y,min(h,y+factor)):
                for xx in range(x,min(w,x+factor)):
                    i=(yy*w+xx)*4;count+=1
                    for c in range(4):sums[c]+=pixels[i+c]
            out.extend(v/count for v in sums)
    return out,width,height


def measure(reference,candidate,w,h,threshold,cancelled):
    alpha_error=rgb_error=soft_intersection=soft_union=ref_area=cand_area=0.
    ref_count=cand_count=intersection=0;n=w*h
    for i in range(n):
        if i%16384==0:cancelled()
        j=i*4;a=reference[j+3];b=candidate[j+3]
        alpha_error+=abs(a-b);ref_area+=a;cand_area+=b
        soft_intersection+=min(a,b);soft_union+=max(a,b)
        ar=a>=threshold;br=b>=threshold;ref_count+=ar;cand_count+=br;intersection+=ar and br
        rgb_error+=sum((reference[j+c]-candidate[j+c])**2 for c in range(3))
    union=ref_count+cand_count-intersection
    return {'width':w,'height':h,'reference_alpha_area_pixels':ref_area,'candidate_alpha_area_pixels':cand_area,
            'reference_mask_pixels':ref_count,'candidate_mask_pixels':cand_count,'intersection_pixels':intersection,
            'mask_iou':intersection/union if union else None,'soft_alpha_iou':soft_intersection/soft_union if soft_union else None,
            'missing_fraction':(ref_count-intersection)/ref_count if ref_count else None,
            'excess_fraction':(cand_count-intersection)/ref_count if ref_count else None,
            'alpha_area_relative_bias':(cand_area-ref_area)/ref_area if ref_area else None,
            'alpha_mae':alpha_error/n,'premultiplied_rgb_rmse':math.sqrt(rgb_error/(n*3))}


def compare(reference,candidate,*,scales=(1,2,4),alpha_threshold=.5,color_space='SRGB',policy=None,
            cancelled=lambda:None,progress=lambda v:None):
    if not isinstance(scales,(list,tuple)) or not 1<=len(scales)<=5 or len(set(scales))!=len(scales) or any(type(s)!=int or s not in (1,2,4,8,16) for s in scales) or 1 not in scales:raise ValueError('Comparison scales must include 1 and distinct powers of two up to 16')
    if isinstance(alpha_threshold,bool) or not isinstance(alpha_threshold,(int,float)) or not math.isfinite(alpha_threshold) or not 0<alpha_threshold<=1:raise ValueError('Invalid comparison alpha threshold')
    defaults={'min_mask_iou':.8,'min_soft_alpha_iou':.8,'max_alpha_mae':.05,'max_premultiplied_rgb_rmse':.1}
    policy=defaults|(policy or {})
    if set(policy)!=set(defaults) or any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1) for v in policy.values()):raise ValueError('Invalid image comparison policy')
    w,h,a=decode_png(reference,color_space=color_space,cancelled=cancelled,progress=progress)
    cw,ch,b=decode_png(candidate,color_space=color_space,cancelled=cancelled,progress=progress)
    if (w,h)!=(cw,ch):raise ValueError('Comparison images require identical dimensions; no automatic registration/resizing')
    levels=[];failures=[]
    for scale in sorted(scales):
        cancelled();progress({'phase':'comparing filtered PNG images','scale':scale})
        aa,ww,hh=downsample(a,w,h,scale,cancelled);bb,_,_=downsample(b,w,h,scale,cancelled)
        row=measure(aa,bb,ww,hh,alpha_threshold,cancelled)|{'scale':scale};reasons=[]
        if row['reference_alpha_area_pixels']<=0:reasons.append('reference alpha is empty')
        for key,value in policy.items():
            if value is None:continue
            metric=key[4:];actual=row[metric]
            # Hard masks may disappear under filtering. Keep soft-alpha/colour
            # tests active and mark this hard test unavailable, never perfect.
            if key=='min_mask_iou' and scale!=1 and row['reference_mask_pixels']==0:continue
            if actual is None or key.startswith('min_') and actual<value or key.startswith('max_') and actual>value:reasons.append(key)
        row['hard_mask_informative']=row['reference_mask_pixels']>0;row['passed']=not reasons;row['failures']=reasons;levels.append(row)
        failures.extend(f'scale {scale}: {reason}' for reason in reasons)
    return {'method':'PREMULTIPLIED_BOX_PNG_V1','color_space':color_space,'alpha_threshold':alpha_threshold,'policy':policy,
            'reference_sha256':hashlib.sha256(reference).hexdigest(),'candidate_sha256':hashlib.sha256(candidate).hexdigest(),
            'width':w,'height':h,'levels':levels,'passed':not failures,'failures':failures,
            'scope':'Decoded straight PNG RGB interpreted explicitly as sRGB or linear, premultiplied before comparison/box filtering. Partial edge blocks use their actual pixel count. No registration, scene-radiance, matched-camera, optical/shadow, GPU-filtering or runtime quality certification; display transforms may already be baked into inputs.'}
