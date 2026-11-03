"""Explicit parameter provenance, optical separation and read-only discovery."""
import asyncio
import copy
import pytest
from fastmcp import Client
from mcpblender import vegetation_materials as v,botany
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.vegetation_material_contracts import Inspect
from mcpblender.vegetation_lod_contracts import Export


def document():
    values={'Base Color':[.2,.5,.1,1],'Roughness':.65,'Metallic':0,'Alpha':1,'Normal':None,'Emission Color':[0,0,0,1],'Emission Strength':0,'IOR':1.5,'Transmission Weight':0}
    material={'name':'Leaf','model':'MANAGED_THIN_FOLIAGE','source_sha256':'a'*64,'double_sided':True,'alpha':{'mode':'OPAQUE','cutoff':None,'factor':1},
       'transmission':{'model':'ARTISTIC_DIFFUSE_BACKLIGHT','weight':.22,'color_linear_rgba':[.2,.4,.1,1],'thickness_m':None},
       'source_base_colors':{'front':[.2,.5,.1,1],'back':[.3,.6,.1,1]},'maps':{m:None for m in v.MAPS},'detail':{'profile':'OAK_LEAF','uv_map':'LeafUV'},
       'front_inputs':{key:{'source':'GEOMETRY_NORMAL' if key=='Normal' else 'UNLINKED','value':value} for key,value in values.items()},'delivery':'NATIVE_PARAMETERS','portable_optical_equivalence':False}
    return v.finish([material],{'leaf-0':['Leaf']},source_uv={'leaf-0':['LeafUV']})


def test_material_contract_claims_and_bindings():
    source=document();assert v.validate(source)['materials']==1 and source['missing_detail_uv']=={'leaf-0':[]}
    for patch in ('thickness','alpha','maps','dimension','equivalence','source_uv'):
        d=copy.deepcopy(source);m=d['materials'][0]
        if patch=='thickness':m['transmission']['thickness_m']=.001
        elif patch=='alpha':m['alpha']['mode']='MASK'
        elif patch=='maps':m['maps']['NORMAL']='not-baked.png'
        elif patch=='dimension':m['front_inputs']['Base Color']['value']=[1,0,0]
        elif patch=='equivalence':m['portable_optical_equivalence']=True
        else:d['source_uv']['leaf-0']=[]
        d['materials_sha256']=botany.digest(d['materials']);d['contract_sha256']=botany.digest({k:v for k,v in d.items() if k!='contract_sha256'})
        with pytest.raises(ValueError):v.validate(d)
    with pytest.raises(ValueError):Inspect(materials=['a'],collection='Tree')
    with pytest.raises(ValueError):Export(lod_collection='Lods',expected_lods='a'*64,directory='out',material_mode='PARAMETERS')


def test_material_inspection_is_readonly(tmp_path):
    config=Config();config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False;config.stdio.library_root=str(tmp_path)
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:assert 'inspect_vegetation_materials' in {t.name for t in await client.list_tools()}
    asyncio.run(run())
