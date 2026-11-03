"""Structured fitted leaf/cluster targets through bake, reopen and GLB delivery."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.skin_glb import Document,point
from test_asset_editing import assets_live,client_for,tool,pytestmark


@pytest.mark.parametrize('scene_unit_scale',[1,.01])
def test_fitted_leaf_and_cluster_bake_delivery(assets_live,scene_unit_scale):
    root,path=assets_live
    leaf_dir='fitted-leaf-'+str(scene_unit_scale);cluster_dir='fitted-cluster-'+str(scene_unit_scale)
    library=root/'library';library.mkdir(exist_ok=True)
    setup=root/'units.py'
    setup.write_text('import bpy\nbpy.context.scene.unit_settings.scale_length='+repr(scene_unit_scale)+'\nbpy.ops.wm.save_as_mainfile(filepath='+repr(str(library/'units.blend'))+')\n')
    prepared=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(setup)],capture_output=True,text=True,timeout=60)
    assert prepared.returncode==0,prepared.stdout+prepared.stderr
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'units.blend'})
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            shape=await tool(client,'plan_leaf_template')
            await tool(client,'create_leaf_template',name='FitLeaf',expected_leaf=shape['leaf_sha256'])
            with pytest.raises(ToolError,match='FRONT_PBR'):await tool(client,'inspect_foliage_card',sources=['FitLeaf'])
            args={'sources':['FitLeaf'],'thin_foliage_mode':'FRONT_PBR','padding':.025}
            before=await tool(client,'inspect_botanical_surface',material='FitLeaf_Surface')
            rect=await tool(client,'inspect_foliage_card',**args,outline='RECTANGLE')
            plan=await tool(client,'inspect_foliage_card',**args)
            assert 'recovery' not in plan # Inspection must not trigger a mutation checkpoint.
            assert plan['card_area_m2']<rect['card_area_m2']*.85
            assert plan['triangles']>2 and plan['projection']['area_amplification']<rect['projection']['area_amplification']
            created=await tool(client,'create_foliage_card',**args,name='FitCard',expected_card=plan['card_sha256'])
            bake=created['bake_parameters']|{'directory':leaf_dir,'width':128,'height':128,'samples':8,'margin':2,
                  'min_projection_coverage':created['suggested_min_projection_coverage']}
            result=(await client.call_tool('bake_textures',{'params':bake,'wait':True})).data
            assert result['live_scene_unchanged'] and result['projection']['fraction']>.5
            assert (await tool(client,'inspect_botanical_surface',material='FitLeaf_Surface'))['material_sha256']==before['material_sha256']
            # Two differently placed leaves form a mesh cluster without hand-fitting.
            await tool(client,'duplicate_object',name='FitLeaf',new_name='FitLeafSecond')
            await client.call_tool('set_object_transform',{'name':'FitLeafSecond','location':[v/scene_unit_scale for v in (.04,.04,.01)],'rotation_euler':[0,0,.7]})
            cluster_args={'sources':['FitLeaf','FitLeafSecond'],'thin_foliage_mode':'FRONT_PBR','outline':'RECTANGLE'}
            cluster=await tool(client,'inspect_foliage_card',**cluster_args)
            target=await tool(client,'create_foliage_card',**cluster_args,name='ClusterCard',expected_card=cluster['card_sha256'])
            assert target['card']['triangles']==2 and target['bake_inspection']['complete']
            cluster_bake=(await client.call_tool('bake_textures',{'params':target['bake_parameters']|{'directory':cluster_dir,'width':96,'height':96,'samples':4,'margin':1,'min_projection_coverage':target['suggested_min_projection_coverage']},'wait':True})).data
            assert cluster_bake['live_scene_unchanged'] and cluster_bake['projection']['fraction']>.2
            await client.call_tool('open_blend',{'path':cluster_dir+'/asset.blend'})
            assert (await tool(client,'validate_texture_bake',directory=cluster_dir))['validated']
            # The worker bundle is self-contained: reopen, validate and export it.
            await client.call_tool('open_blend',{'path':leaf_dir+'/asset.blend'})
            checked=await tool(client,'validate_texture_bake',directory=leaf_dir);assert checked['validated']
            await tool(client,'export_objects_glb',objects=['FitCard'],path=leaf_dir+'.glb')
            raw=Document(library/(leaf_dir+'.glb'),morphs=True)
            world=raw.world(None,0)[raw.mesh_node];points=[point(world,p) for _,_,p,_,_ in raw.vertices()]
            assert max(p[2] for p in points)-min(p[2] for p in points)>.1
            await tool(client,'configure_render',resolution_x=256,resolution_y=256,samples=8)
            await tool(client,'setup_preview_stage',objects=['FitCard'],prefix='FitView',strength=.35)
            preview=leaf_dir+'-preview.png'
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':preview,'camera':'FitView_Camera','engine':'CYCLES','width':256,'height':256}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            if directory:=os.environ.get('MCPBLENDER_CARD_EVIDENCE_DIR'):
                out=Path(directory)/('metres' if scene_unit_scale==1 else 'centimetres');out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/leaf_dir,out/'fitted-leaf',dirs_exist_ok=True)
                shutil.copytree(library/cluster_dir,out/'fitted-cluster',dirs_exist_ok=True)
                shutil.copy2(library/(leaf_dir+'.glb'),out/'fitted-leaf.glb');shutil.copy2(library/preview,out/'fitted-preview.png')
                (out/'proof.json').write_text(json.dumps({'plan':plan,'rectangle':rect,'created':created,'bake':result,'cluster':target},indent=2))
    asyncio.run(run())
