"""Adoption source paths, read-only discovery and portable witness claims."""
import asyncio
import copy
from fastmcp import Client
import pytest
from mcpblender import vegetation_adoption as schema,botany
from mcpblender.config import Config
from mcpblender.server import build_server,State
from mcpblender.vegetation_bake_contracts import Adoption


def document():
    record={'format':schema.FORMAT,'preparation_sha256':'a'*64,'bake_sha256':'b'*64,'bundle_manifest_sha256':'c'*64,'geometry_sha256':'d'*64,'uv_map':'BakeUV','uv_witness':{'LeafUV':'e'*64,'BakeUV':'f'*64},
        'maps':[{'map':'NORMAL','sha256':'a'*64,'bytes':1024,'width':32,'height':32,'color_space':'Non-Color'}],'rgba8_base_bytes':4096,'material_adapters':[],'front_pbr_accepted':False,'portable_optical_equivalence':False}
    record['adoption_sha256']=botany.digest(record);return record


def test_witness_claims():
    assert schema.validate(document())==4096
    for field in ('budget','uv','loss','optical','map'):
        r=copy.deepcopy(document())
        if field=='budget':r['rgba8_base_bytes']=0
        elif field=='uv':r['uv_witness']={}
        elif field=='loss':r['material_adapters']=[{'kind':'loss'}]
        elif field=='optical':r['portable_optical_equivalence']=True
        else:r['maps'][0]['map']='THICKNESS'
        r['adoption_sha256']=botany.digest({k:v for k,v in r.items() if k!='adoption_sha256'})
        with pytest.raises(ValueError):schema.validate(r)


def test_paths_and_policy(tmp_path):
    values={'lod_collection':'Lods','bake_collection':'Bake','entries':[{'asset':'leaf-0','directory':'bundle'}]}
    with pytest.raises(ValueError):Adoption.model_validate(values|{'entries':values['entries']*2})
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    with pytest.raises(ValueError,match='library_root'):state.prepare('inspect_vegetation_bake_adoption',values|{'entries':[{'asset':'leaf-0','directory':'../outside'}]})
    assert State.input_paths('adopt_vegetation_bakes',values)==['bundle']
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()};assert 'inspect_vegetation_bake_adoption' in names and 'adopt_vegetation_bakes' not in names
    asyncio.run(run())


def test_exported_uv_binding(tmp_path,monkeypatch):
    import json
    record=document();rows=[[0,0],[1,0],[0,1]]
    record['uv_witness']={'LeafUV':schema.uv_digest(rows),'BakeUV':schema.uv_digest(rows)}
    record['adoption_sha256']=botany.digest({k:v for k,v in record.items() if k!='adoption_sha256'})
    asset=tmp_path/'leaf-0';asset.mkdir();path=asset/'manifest.json'
    path.write_text(json.dumps({'source':{'uv_maps':['LeafUV','BakeUV']},'witness':{'uvs':[rows,rows]}}))
    doc={'meshes':[{'primitives':[{'material':0}]}],'materials':[{'normalTexture':{'index':0,'texCoord':1}}]}
    monkeypatch.setattr('mcpblender.lod_files.read_glb',lambda path:(doc,b''))
    schema.verify(tmp_path,{'leaf-0':record},['leaf-0'])
    doc['materials'][0]['normalTexture']['texCoord']=0
    with pytest.raises(ValueError,match='adopted UV channel'):schema.verify(tmp_path,{'leaf-0':record},['leaf-0'])
    doc['materials'][0]['normalTexture']['texCoord']=1
    d=json.loads(path.read_text());d['witness']['uvs'][1][0]=[.1,.1];path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='UVs differ'):schema.verify(tmp_path,{'leaf-0':record},['leaf-0'])
