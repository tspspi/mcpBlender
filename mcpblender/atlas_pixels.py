"""Independent RGBA8 PNG core/gutter preservation witness for atlas workers."""
import hashlib
from . import image_comparison as images

METHOD='RGBA8_CORE_AND_CLAMPED_GUTTER_V1'


def decode(payload):
    if len(payload)<25 or payload[24]!=8:raise ValueError('Atlas pixel verification requires PNG8')
    return images.decode_png(payload,color_space='LINEAR',premultiply=False)


def tile(source,sw,sh,packed,aw,ah,rect,gutter):
    x,y,w,h=rect
    if (sw,sh)!=(w,h) or min(x-gutter,y-gutter)<0 or x+w+gutter>aw or y+h+gutter>ah:raise ValueError('Atlas pixel verification bounds differ from tile')
    if len(source)!=sw*sh*4 or len(packed)!=aw*ah*4:raise ValueError('Invalid atlas verification pixel buffer')
    checked=0
    for row in range(-gutter,sh+gutter):
        sy=min(sh-1,max(0,row));py=y+row
        for col in range(-gutter,sw+gutter):
            sx=min(sw-1,max(0,col));si=(sy*sw+sx)*4;pi=(py*aw+x+col)*4
            if any(source[si+c]!=packed[pi+c] for c in range(4)):raise ValueError(f'Atlas changes source RGBA8 pixels at tile pixel ({col}, {row})')
            checked+=1
    return {'source_core_pixels':sw*sh,'gutter_pixels':checked-sw*sh,'checked_channels':checked*4,'max_channel_error':0}


def verify(payload,layout,entries,kind,read_source,progress=lambda v:None):
    aw,ah,packed=decode(payload)
    if (aw,ah)!=(layout['width'],layout['height']):raise ValueError('Atlas pixel verification dimensions changed')
    result=[]
    for row in layout['tiles']:
        progress({'phase':'verifying atlas RGBA8 tile and gutter','map':kind,'entry':row['id']})
        entry=entries[row['id']];relative='textures/'+kind.lower()+'.png';data=read_source(entry,relative)
        expected=next(v['sha256'] for v in entry['files'] if v['path']==relative)
        actual=hashlib.sha256(data).hexdigest()
        if actual!=expected:raise ValueError('Atlas pixel source file changed after planning')
        sw,sh,source=decode(data)
        # UV/layout rectangles use a bottom-left origin; decoded PNG scanlines
        # use top-left. Source PNGs are also top-first, so reverse the rectangle
        # origin once, without reversing either image's pixel rows.
        x,y,w,h=row['pixel_rect'];png_rect=[x,ah-y-h,w,h]
        result.append({'id':row['id'],'source_png_sha256':actual}|tile(source,sw,sh,packed,aw,ah,png_rect,layout['gutter']))
    return {'method':METHOD,'map':kind,'atlas_png_sha256':hashlib.sha256(payload).hexdigest(),'tiles':result}
