"""Atlas core/gutter checks include RGB hidden under zero alpha and bind metadata."""
from array import array
import copy
import hashlib
import pytest
from mcpblender import atlas_pixels as api
from mcpblender.texture_files import validate_atlas_pixels
from test_image_comparison import png


def test_rgba8_core_gutter_and_retained_witness():
    rgba=[255,0,0,255,0,200,100,0,30,40,50,128,90,80,70,255]
    source=png(2,2,rgba,filter=4);sha=hashlib.sha256(source).hexdigest()
    # An independently constructed 2x2 tile with one clamped border pixel.
    out=[]
    for y in (0,0,1,1):
        for x in (0,0,1,1):out.extend(rgba[(y*2+x)*4:(y*2+x+1)*4])
    packed=png(4,4,out,filter=1);files=[{'path':'textures/alpha.png','sha256':sha}]
    entries={'a':{'id':'a','files':files}};layout={'width':4,'height':4,'gutter':1,'maps':['ALPHA'],'tiles':[{'id':'a','pixel_rect':[1,1,2,2]}]}
    proof=api.verify(packed,layout,entries,'ALPHA',lambda entry,path:source)
    assert proof['tiles'][0]['source_core_pixels']==4 and proof['tiles'][0]['gutter_pixels']==12
    record={};saved={'atlas':{'layout':layout,'inputs':list(entries.values()),'pixel_copy_method':api.METHOD},'pixel_copy_proof':[proof],
                     'files':[{'path':'textures/alpha.png','sha256':hashlib.sha256(packed).hexdigest()}]}
    with pytest.raises(ValueError,match='not sealed'):validate_atlas_pixels(record,saved)
    validate_atlas_pixels(record,saved,seal=True);assert validate_atlas_pixels(record,saved)==[proof]
    bad=copy.deepcopy(saved);bad['pixel_copy_proof'][0]['tiles'][0]['gutter_pixels']=0
    with pytest.raises(ValueError):validate_atlas_pixels(record,bad)
    bad=copy.deepcopy(saved);bad['pixel_copy_proof'][0]['tiles'][0]['source_png_sha256']='0'*64
    with pytest.raises(ValueError):validate_atlas_pixels(record,bad)
    bad=copy.deepcopy(saved);bad['pixel_copy_proof'][0]['tiles'][0]['extra']='edit'
    with pytest.raises(ValueError,match='witness changed'):validate_atlas_pixels(record,bad)
    assert validate_atlas_pixels({}, {'atlas':{'layout':layout}}) is None # Historical bundles.
    # Alter transparent green in a core pixel: premultiplied comparisons alone
    # would miss this colour-padding corruption, but byte-level copy rejects it.
    bad=out[:];bad[(1*4+2)*4+1]=201
    with pytest.raises(ValueError,match='changes source'):api.verify(png(4,4,bad),layout,entries,'ALPHA',lambda e,p:source)
    bad=out[:];bad[0]=0
    with pytest.raises(ValueError,match='changes source'):api.verify(png(4,4,bad),layout,entries,'ALPHA',lambda e,p:source)
    with pytest.raises(ValueError,match='source file changed'):api.verify(packed,layout,entries,'ALPHA',lambda e,p:packed)


def test_png_top_rows_and_uv_bottom_origin_are_distinct():
    rgba=[255,0,0,255,0,200,100,0,30,40,50,128,90,80,70,255]
    source=png(2,2,rgba);sha=hashlib.sha256(source).hexdigest()
    # Tile lower-left (1,1) in a 4x6 atlas is top-left (1,3) in PNG rows.
    out=[0]*(4*6*4)
    for row,sy in enumerate((0,0,1,1),start=2):
        for col,sx in enumerate((0,0,1,1)):
            out[(row*4+col)*4:(row*4+col+1)*4]=rgba[(sy*2+sx)*4:(sy*2+sx+1)*4]
    entries={'a':{'id':'a','files':[{'path':'textures/alpha.png','sha256':sha}]}}
    layout={'width':4,'height':6,'gutter':1,'tiles':[{'id':'a','pixel_rect':[1,1,2,2]}]}
    assert api.verify(png(4,6,out),layout,entries,'ALPHA',lambda e,p:source)['tiles'][0]['gutter_pixels']==12
