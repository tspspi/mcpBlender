"""Policy-bearing source witnesses retain the original preparation binding."""
import copy
import json
import hashlib
import pytest
from mcpblender import texture_files as files,vegetation_adoption as adoption,botany
from mcpblender.texture_quality_contracts import Quality
from mcpblender.uv_quality import analyze
from test_texture_quality import square
from test_vegetation_adoption_contracts import document


def fixture():
    policy=Quality(width=64,height=64,min_texels_per_meter=32,padding_pixels=1,mip_levels=1).model_dump()
    triangles,edges=square(.125,.875);report=analyze(triangles,edges,1,policy)|{'scene_unit_scale':1.0}
    original={'objects':[{'name':'Prepared','role':'target','geometry':'a'*64}],'uv_map':'BakeUV','frame':1,'subframe':0.}
    source=files.bake_fingerprint(original);content=copy.deepcopy(original);content['objects'][0]['texture_quality']=report
    saved={'source':files.bake_fingerprint(content),'source_inspection':content,'texture_quality':report}
    job={'quality':policy,'width':64,'height':64,'margin':1}
    return original,source,saved,job


def test_original_hash_compatibility_and_policy_roundtrip():
    original,source,saved,job=fixture()
    assert source==hashlib.sha256(json.dumps(original,sort_keys=True,allow_nan=False).encode()).hexdigest()
    assert files.quality_binding(saved,job,source)==(saved['source'],saved['texture_quality'])
    assert saved['source']!=source
    assert 'texture_quality' in saved['source_inspection']['objects'][0]
    assert files.quality_binding({}, {}, source)==(source,None)
    assert files.validate_quality_report(saved['texture_quality'])==job['quality']


def test_missing_mismatched_and_failed_quality_witnesses():
    _,source,saved,job=fixture()
    for kind in ('missing','base','report','policy','size','margin','passed','coverage','level','density','padding'):
        s,j=copy.deepcopy(saved),copy.deepcopy(job)
        if kind=='missing':s.pop('source_inspection')
        elif kind=='base':s['source_inspection']['objects'][0]['geometry']='b'*64
        elif kind=='report':s['texture_quality']=copy.deepcopy(s['texture_quality']);s['texture_quality']['triangles']=12
        elif kind=='policy':j['quality']['max_spacing_tests']+=1
        elif kind=='size':j['width']=128
        elif kind=='margin':j['margin']=2
        elif kind=='passed':s['texture_quality']['passed']=False
        elif kind=='coverage':s['texture_quality']['levels'][0]['coverage']['minimum_covered_pixels']=0
        elif kind=='level':s['texture_quality']['levels'].pop()
        elif kind=='density':s['texture_quality']['minimum_directional_texels_per_meter']=0
        elif kind=='padding':s['texture_quality']['levels'][1]['edge_margin_pixels']=0
        with pytest.raises(ValueError):files.quality_binding(s,j,source)


def test_portable_quality_report_and_required_delivery():
    _,source,saved,_=fixture();r=document();r['maps'][0].update(width=64,height=64);r['rgba8_base_bytes']=64*64*4
    r.update(texture_quality=saved['texture_quality'],preparation_bake_sha256=source)
    r['adoption_sha256']=botany.digest({k:v for k,v in r.items() if k!='adoption_sha256'})
    assert adoption.validate(r)==16384
    args=({'wood':r},['wood'],['NORMAL'],64,1048576,1048576)
    assert adoption.delivery(*args,require_quality=True)['complete']
    assert adoption.delivery(*args,require_quality=True,scene_unit_scale=1)['complete']
    changed=adoption.delivery(*args,require_quality=True,scene_unit_scale=.01)
    assert not changed['complete'] and changed['quality_scene_unit_gaps']==['wood']
    old=document()
    assert adoption.delivery({'wood':old},['wood'],['NORMAL'],32,1048576,1048576)['complete']
    report=adoption.delivery({'wood':old},['wood'],['NORMAL'],32,1048576,1048576,require_quality=True)
    assert not report['complete'] and report['assets_without_quality_reports']==['wood']
    r['maps'][0]['width']=32;r['rgba8_base_bytes']=8192;r['adoption_sha256']=botany.digest({k:v for k,v in r.items() if k!='adoption_sha256'})
    with pytest.raises(ValueError,match='dimensions'):adoption.validate(r)
