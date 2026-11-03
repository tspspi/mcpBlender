"""Structured procedural assembly realization and existing GLB delivery pipeline."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_assemblies import create,place
from test_shaders import png
from mcpblender.lod_files import glb_report


def test_textured_building_instances_realization_export_and_reopen(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    png(library/'realize-brick.png',lambda x,y:(160,100,60) if y%4 else (210,200,190))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'apply_material_preset',material='RealizeBrick',preset='TEXTURED_PBR',base_color_texture='realize-brick.png')
            graph=await tool(client,'create_geometry_preset',group='RealizeBuildingRecipe',settings={'type':'BUILDING','floors':2,'wall_material':'RealizeBrick'})
            await tool(client,'create_primitive',name='RealizeSource')
            await tool(client,'attach_geometry_nodes',name='RealizeSource',group=graph['group'])
            asset=await create(client,['RealizeSource'],'RealizeBuildingAsset')
            await place(client,'RealizeBuildingAsset','RealizeOne',10)
            await place(client,'RealizeBuildingAsset','RealizeTwo',20)
            source=(await tool(client,'inspect_asset_instance',name='RealizeOne'))['instance_sha256']
            args={'instances':['RealizeOne','RealizeTwo']}
            plan=await tool(client,'inspect_asset_realization',**args)
            assert plan['total_leaves']==2 and plan['triangles']>100
            page=await tool(client,'inspect_asset_realization',**args,leaf_limit=1)
            assert len(page['leaves'])==1 and page['next_leaf_offset']==1 and page['source_sha256']==plan['source_sha256']
            job=(await client.call_tool('realize_asset_instances',{'params':args|{'collection':'FrozenBuildings','expected_source':plan['source_sha256']}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded' and 'storage' in done['progress'],done
            frozen=done['result'];assert len(frozen['objects'])==2 and frozen['static_snapshot']
            assert (await tool(client,'inspect_asset_instance',name='RealizeOne'))['instance_sha256']==source
            for record in frozen['leaves']:
                mesh=await tool(client,'inspect_mesh',name=record['object'],sample_limit=0)
                assert mesh['triangles']==record['mesh']['triangles'] and mesh['uv_layers']
                assert mesh['world_bounds']==record['mesh']['bounds'] and not mesh['modifiers']
            await tool(client,'export_objects_glb',objects=frozen['objects'],path='frozen-buildings.glb',animations=False)
            decoded=glb_report(library/'frozen-buildings.glb')
            assert decoded['triangles']==plan['triangles'] and decoded['images']==1 and decoded['embedded_dependencies']
            for key in ('min','max'):
                native=plan['world_bounds'];expected=([native['min'][0],native['min'][2],-native['max'][1]] if key=='min' else [native['max'][0],native['max'][2],-native['min'][1]])
                assert decoded['position_bounds'][key]==pytest.approx(expected,abs=1e-5)
            scene=(await client.call_tool('get_scene_info')).data;old={o['name'] for o in scene['objects']}
            await client.call_tool('import_asset',{'path':'frozen-buildings.glb'})
            added=[o['name'] for o in (await client.call_tool('get_scene_info')).data['objects'] if o['name'] not in old and o['type']=='MESH']
            assert len(added)==2
            restored=[await tool(client,'inspect_mesh',name=n,sample_limit=0) for n in added]
            assert sum(m['triangles'] for m in restored)==plan['triangles']
            for key,fn in (('min',min),('max',max)):
                assert [fn(m['world_bounds'][key][a] for m in restored) for a in range(3)]==pytest.approx(plan['world_bounds'][key],abs=1e-5)
            await client.call_tool('set_object_transform',{'name':'RealizeOne','location':[11,0,0]})
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('realize_asset_instances',{'params':args|{'collection':'RefusedFrozen','expected_source':plan['source_sha256']},'wait':True})
            await client.call_tool('save_blend',{'path':'realized-buildings.blend'})
            await client.call_tool('open_blend',{'path':'realized-buildings.blend'})
            assert (await tool(client,'inspect_mesh',name=frozen['objects'][0],sample_limit=0))['world_bounds']==frozen['leaves'][0]['mesh']['bounds']
            if evidence:=os.environ.get('MCPBLENDER_REALIZATION_EVIDENCE_DIR'):
                out=Path(evidence);out.mkdir(parents=True,exist_ok=True)
                for name in ('frozen-buildings.glb','realized-buildings.blend'):shutil.copy2(library/name,out/name)
                (out/'realization-proof.json').write_text(json.dumps({'plan':plan,'result':frozen,'decoded':decoded},indent=2))
    asyncio.run(run())
