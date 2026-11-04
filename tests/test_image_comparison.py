"""Independent PNG filters/precision, alpha invariants and informative gates."""
import struct
import zlib
import pytest
from mcpblender import image_comparison as api


def png(w,h,values,*,depth=8,channels=4,filter=0,extra=()):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    bpp=channels*(depth//8);stride=w*bpp;previous=bytes(stride);rows=[]
    raw=bytes(values) if depth==8 else struct.pack('>'+str(len(values))+'H',*values)
    for y in range(h):
        row=raw[y*stride:(y+1)*stride];out=[]
        for x,value in enumerate(row):
            a=row[x-bpp] if x>=bpp else 0;b=previous[x];c=previous[x-bpp] if x>=bpp else 0
            p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
            predictor=[0,a,b,(a+b)//2,a if pa<=pb and pa<=pc else b if pb<=pc else c][filter]
            out.append((value-predictor)&255)
        rows.append(bytes([filter,*out]));previous=row
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,depth,6 if channels==4 else 2,0,0,0))+b''.join(chunk(k,d) for k,d in extra)+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')


@pytest.mark.parametrize('depth',[8,16])
@pytest.mark.parametrize('filter',range(5))
def test_decode_filters_precision_and_explicit_srgb(depth,filter):
    maximum=2**depth-1;values=[maximum,maximum//2,0,maximum,0,maximum,maximum//4,maximum//2]*2
    image=png(2,2,values,depth=depth,filter=filter)
    w,h,pixels=api.decode_png(image,color_space='LINEAR');assert (w,h)==(2,2)
    alpha=values[7]/maximum
    assert list(pixels[:8])==pytest.approx([1,values[1]/maximum,0,1,0,alpha,values[6]/maximum*alpha,alpha])
    _,_,srgb=api.decode_png(image)
    encoded=values[1]/maximum;expected=((encoded+.055)/1.055)**2.4
    assert srgb[1]==pytest.approx(expected)
    assert api.compare(image,image)['passed']


def test_transparent_rgb_invariance_empty_references_and_real_rejection():
    a=png(2,2,[255,0,0,255,0,255,0,0]*2);b=png(2,2,[255,0,0,255,255,0,255,0]*2)
    result=api.compare(a,b);assert result['passed']
    assert all(r['premultiplied_rgb_rmse']==0 and r['soft_alpha_iou']==1 for r in result['levels'])
    blank=png(2,2,[0,0,0,0]*4);assert not api.compare(blank,blank,policy={k:None for k in result['policy']})['passed']
    lost=api.compare(a,blank);base=lost['levels'][0]
    assert not lost['passed'] and base['missing_fraction']==1 and base['mask_iou']==0 and base['alpha_mae']==.5
    # Equal whole-image alpha area does not imply matching silhouette.
    shifted=png(2,2,[0,0,0,0,255,0,0,255]*2);moved=api.compare(a,shifted)
    assert not moved['passed'] and moved['levels'][0]['alpha_area_relative_bias']==0 and moved['levels'][0]['mask_iou']==0
    assert moved['levels'][1]['soft_alpha_iou']==1 # Explicit box-filter equivalence only.
    dark=png(2,2,[0,0,0,255,0,0,0,0]*2);colour=api.compare(a,dark)
    assert colour['levels'][0]['mask_iou']==1 and not colour['passed']


def test_partial_filter_blocks_and_subthreshold_masks_never_invent_perfect_overlap():
    rgba=[255,255,255,64]*9;image=png(3,3,rgba)
    result=api.compare(image,image,policy={'min_mask_iou':None})
    assert result['passed'] and result['levels'][1]['width']==2 and result['levels'][2]['width']==1
    assert all(r['mask_iou'] is None and not r['hard_mask_informative'] for r in result['levels'])
    assert not api.compare(image,image)['passed'] # Default base hard-mask gate unavailable.


def test_admission_crc_budgets_profiles_and_cancellation():
    good=png(1,1,[0,0,0,255])
    with pytest.raises(ValueError,match='CRC'):api.decode_png(good[:-1]+b'X')
    with pytest.raises(ValueError,match='ICC'):api.decode_png(png(1,1,[0,0,0,255],extra=[(b'iCCP',b'unsupported')]))
    with pytest.raises(ValueError,match='identical dimensions'):api.compare(good,png(2,1,[0,0,0,255]*2))
    for kwargs in ({'scales':[True]},{'scales':[2]},{'alpha_threshold':0},{'policy':{'unknown':1}}):
        with pytest.raises(ValueError):api.compare(good,good,**kwargs)
    def stop():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):api.compare(good,good,cancelled=stop)


def test_rgb_opaque_inputs_and_predecode_size_admission():
    image=png(2,1,[65535,0,0,0,65535,32767],depth=16,channels=3,filter=3)
    w,h,pixels=api.decode_png(image,color_space='LINEAR')
    assert (w,h)==(2,1) and list(pixels)==pytest.approx([1,0,0,1,0,1,32767/65535,1])
    assert api.compare(image,image)['passed']
    oversized=bytearray(png(1,1,[0,0,0,255]));struct.pack_into('>I',oversized,16,5000)
    with pytest.raises(ValueError,match='4 megapixels'):api.decode_png(oversized)
