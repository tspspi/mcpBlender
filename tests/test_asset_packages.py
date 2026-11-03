"""Python-disabled textured batch packaging with proxies and validated LODs."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_assemblies import create,place
from test_proxies import generate
from test_shaders import png
from mcpblender.package_files import validate


def test_textured_batch_proxy_lod_bundle_and_reimport(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    png(library/'package-brick.png',lambda x,y:(160,100,60) if y%4 else (210,205,200))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'apply_material_preset',material='PackageBrick',preset='TEXTURED_PBR',base_color_texture='package-brick.png')
            graph=await tool(client,'create_geometry_preset',group='PackageBuildingRecipe',settings={'type':'BUILDING','floors':2,'wall_material':'PackageBrick'})
            await tool(client,'create_primitive',name='PackageBuildingSource')
            await tool(client,'attach_geometry_nodes',name='PackageBuildingSource',group=graph['group'])
            await create(client,['PackageBuildingSource'],'PackageBuildingPrototype')
            placed=await place(client,'PackageBuildingPrototype','PackageBuilding',10)
            await generate(client,'PackageBuildingCollision',objects=['PackageBuilding'],method='CONVEX_HULL')
            await tool(client,'create_primitive',name='PackageSphere',kind='UV_SPHERE',location=[30,0,2])
            await tool(client,'assign_material',objects=['PackageSphere'],material='PackageBrick')
            visibility=await tool(client,'inspect_render_visibility',name='PackageSphere')
            await tool(client,'configure_render_visibility',name='PackageSphere',expected_visibility=visibility['visibility_sha256'],visible_shadow=False)
            await generate(client,'PackageSphereShadow',objects=['PackageSphere'],purpose='SHADOW',method='DECIMATE',triangle_budget=150,max_relative_error=.2)
            source=await tool(client,'inspect_lod_source',name='PackageSphere')
            lod=(await client.call_tool('generate_lod_chain',{'params':{'name':'PackageSphere','chain':'PackageSphereLOD','expected_source':source['source_sha256'],'levels':[{'triangle_budget':250},{'triangle_budget':120}],'max_relative_error':.3,'error_samples':64},'wait':True})).data
            assets=[{'id':'building','objects':['PackageBuilding'],'collision_proxies':['PackageBuildingCollision']},
                    {'id':'prop','objects':['PackageSphere'],'shadow_proxies':['PackageSphereShadow'],'lods':[{'chain':'PackageSphereLOD','animations':False}]}]
            plan=await tool(client,'inspect_asset_package',assets=assets);assert plan['can_export'],plan
            assert plan['estimated_bytes']>16*1024**2 and len(plan['assets'])==2
            job=(await client.call_tool('export_asset_package',{'params':{'assets':assets,'directory':'asset-package','expected_source':plan['source_sha256']}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded' and done['progress']['storage']['free_bytes']>0,done
            assert done['progress']['storage']['estimated_output_bytes']==plan['estimated_bytes']
            result=done['result'];assert result['valid'] and result['assets']==2 and len(result['members'])==4
            assert validate(library/'asset-package')['valid']
            assert (await tool(client,'validate_asset_package',directory='asset-package'))['valid']
            assert (await tool(client,'inspect_asset_package',assets=assets))['source_sha256']==plan['source_sha256']
            package=library/'asset-package';document=json.loads((package/'manifest.json').read_text())
            assert len(document['assets'][1]['lods'])==1
            collision=next(m for m in document['assets'][0]['members'] if m['role']=='COLLISION')
            assert collision['proxy_method']=='CONVEX_HULL' and collision['proxy_nodes'][0]['suggested_collision_shape']=='CONVEX_HULL'
            assert collision['proxy_nodes'][0]['node']==collision['scene']['mesh_nodes'][0]['name']
            assert str(root) not in (package/'manifest.json').read_text()
            assert all(member['scene']['images']==1 for member in result['members'] if member['role']!='COLLISION')
            primary=next(m for m in result['members'] if m['asset']=='building' and m['role']=='PRIMARY')
            scene=(await client.call_tool('get_scene_info')).data;old={o['name'] for o in scene['objects']}
            await client.call_tool('import_asset',{'path':'asset-package/building/primary.glb'})
            added=[o['name'] for o in (await client.call_tool('get_scene_info')).data['objects'] if o['type']=='MESH' and o['name'] not in old]
            assert len(added)==1
            mesh=await tool(client,'inspect_mesh',name=added[0],sample_limit=0)
            assert mesh['triangles']==primary['scene']['triangles'] and mesh['uv_layers']
            for key in ('min','max'):assert mesh['world_bounds'][key]==pytest.approx(placed['world_bounds'][key],abs=1e-5)
            # Hash, inventory and binary-independent dependency proof failures.
            glb=package/'prop/shadow_00.glb';data=glb.read_bytes();glb.write_bytes(data[:-1]+bytes([data[-1]^1]))
            with pytest.raises(ToolError,match='hash'):await tool(client,'validate_asset_package',directory='asset-package')
            glb.write_bytes(data)
            (package/'unexpected.txt').write_text('extra')
            with pytest.raises(ToolError,match='undeclared'):await tool(client,'validate_asset_package',directory='asset-package')
            (package/'unexpected.txt').unlink()
            # Stale associations cannot silently package colliders for another asset.
            wrong=[{'id':'wrong','objects':['PackageSphere'],'collision_proxies':['PackageBuildingCollision']}]
            with pytest.raises(ToolError,match='association'):await tool(client,'inspect_asset_package',assets=wrong)
            await client.call_tool('save_blend',{'path':'asset-package-source.blend'})
            if evidence:=os.environ.get('MCPBLENDER_PACKAGE_EVIDENCE_DIR'):
                out=Path(evidence);out.mkdir(parents=True,exist_ok=True);shutil.copytree(package,out/'asset-package',dirs_exist_ok=True)
                shutil.copy2(library/'asset-package-source.blend',out/'asset-package-source.blend')
                (out/'package-proof.json').write_text(json.dumps({'plan':plan,'result':result},indent=2))
    asyncio.run(run())


def test_animated_skin_lod_package_and_future_clip_guard(assets_live):
    from test_skin_lods import make_skin,generate as generate_skin
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_skin(client,'PackageSkin','PackageRig',x=50)
            await generate_skin(client,'PackageSkin','PackageSkinLOD')
            assets=[{'id':'animated','objects':['PackageSkin'],'lods':[{'chain':'PackageSkinLOD'}]}]
            first=await tool(client,'inspect_asset_package',assets=assets);assert first['can_export']
            # A future/inactive clip changes delivery even when the current mesh
            # pose is unchanged; its fingerprint must participate in the guard.
            await tool(client,'create_animation_clip',name='PackageRig',clip='PackageIdle',activate=False,tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[0,0,0]}]}])
            current=await tool(client,'inspect_asset_package',assets=assets);assert current['source_sha256']!=first['source_sha256']
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('export_asset_package',{'params':{'assets':assets,'directory':'stale-animation-package','expected_source':first['source_sha256']},'wait':True})
            done=(await client.call_tool('export_asset_package',{'params':{'assets':assets,'directory':'animated-package','expected_source':current['source_sha256']},'wait':True})).data
            assert done['valid'] and validate(root/'library/animated-package')['valid']
            document=json.loads((root/'library/animated-package/animated/lod_00/manifest.json').read_text())
            assert document['animation_sha256']==current['assets'][0]['lods'][0]['export_profile']['animation_sha256']
            assert len(document['levels'])==3 and all(len(level['skin']['clips'])==2 for level in document['levels'])
            if evidence:=os.environ.get('MCPBLENDER_PACKAGE_EVIDENCE_DIR'):
                shutil.copytree(root/'library/animated-package',Path(evidence)/'animated-package',dirs_exist_ok=True)
    asyncio.run(run())


def test_timeline_baked_morph_lod_package(assets_live):
    import math
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            vertices=[[.3*math.cos(i*2*math.pi/16),.3*math.sin(i*2*math.pi/16),z/8] for z in range(17) for i in range(16)]
            faces=[[z*16+i,z*16+(i+1)%16,(z+1)*16+(i+1)%16,(z+1)*16+i] for z in range(16) for i in range(16)]+[list(range(15,-1,-1)),list(range(256,272))]
            await tool(client,'create_mesh',name='PackageMorph',vertices=vertices,faces=faces)
            await tool(client,'generate_uv',name='PackageMorph')
            await tool(client,'create_shape_key',name='PackageMorph',key='Lift',vertices=[{'vertex':i,'value':[0,0,z*.15]} for i,(x,y,z) in enumerate(vertices)])
            await tool(client,'create_morph_clip',name='PackageMorph',clip='PackageMorphMotion',tracks=[{'key':'Lift','keyframes':[{'frame':1,'value':0},{'frame':5,'value':1},{'frame':9,'value':0}]}])
            before=await tool(client,'inspect_lod_source',name='PackageMorph',deformation='MORPH')
            await client.call_tool('generate_lod_chain',{'params':{'name':'PackageMorph','deformation':'MORPH','chain':'PackageMorphLOD','expected_source':before['source_sha256'],'levels':[{'triangle_budget':250},{'triangle_budget':120}],'pose_frames':[1,5,9]},'wait':True})
            assets=[{'id':'morph','objects':['PackageMorph'],'lods':[{'chain':'PackageMorphLOD','timeline_clips':[{'name':'Breathe','frame_start':1,'frame_end':9}]}]}]
            planned=await tool(client,'inspect_asset_package',assets=assets);assert planned['can_export']
            result=(await client.call_tool('export_asset_package',{'params':{'assets':assets,'directory':'morph-package','expected_source':planned['source_sha256']},'wait':True})).data
            assert result['valid'] and validate(root/'library/morph-package')['valid']
            manifest=json.loads((root/'library/morph-package/morph/lod_00/manifest.json').read_text())
            assert manifest['animation_sha256']==planned['assets'][0]['lods'][0]['export_profile']['animation_sha256']
            if evidence:=os.environ.get('MCPBLENDER_PACKAGE_EVIDENCE_DIR'):
                shutil.copytree(root/'library/morph-package',Path(evidence)/'morph-package',dirs_exist_ok=True)
    asyncio.run(run())
