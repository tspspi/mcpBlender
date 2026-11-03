"""Physical GLB dimensions across structured static, LOD, batch and skin workflows."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from mcpblender.skin_glb import Document,point
from mcpblender.package_files import validate as validate_package
from mcpblender.lod_files import validate as validate_lod
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skin_lods import make_skin,generate as generate_skin


def test_centimetre_project_static_lod_package_and_skin(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    script=root/'prepare-units.py'
    script.write_text('import bpy\nbpy.context.scene.unit_settings.system="METRIC"\nbpy.context.scene.unit_settings.scale_length=.01\nbpy.ops.wm.save_as_mainfile(filepath='+repr(str(library/'centimetres.blend'))+')\n')
    prepared=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert prepared.returncode==0,prepared.stdout+prepared.stderr
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'centimetres.blend'})
            planned=await tool(client,'plan_leaf_template',leaf={'length':.1,'petiole':.004})
            leaf=await tool(client,'create_leaf_template',name='UnitLeaf',leaf=planned['recipe'],expected_leaf=planned['leaf_sha256'])
            unit=leaf['scene_unit_scale'];assert unit==pytest.approx(.01)
            out=await tool(client,'export_objects_glb',objects=['UnitLeaf'],path='leaf-cm.glb')
            assert out['unit_normalization']['applied']
            doc=Document(library/'leaf-cm.glb',morphs=True);world=doc.world(None,0)[doc.mesh_node]
            points=[point(world,p) for _,_,p,_,_ in doc.vertices()]
            assert max(max(v[a] for v in points)-min(v[a] for v in points) for a in range(3))==pytest.approx(.104,abs=1e-6)
            await tool(client,'create_primitive',name='UnitSphere',kind='UV_SPHERE',location=[3,0,1])
            source=await tool(client,'inspect_lod_source',name='UnitSphere')
            chain=(await client.call_tool('generate_lod_chain',{'params':{'name':'UnitSphere','chain':'UnitSphereLOD','expected_source':source['source_sha256'],'levels':[{'triangle_budget':150}]},'wait':True})).data
            lod=(await client.call_tool('export_lod_chain',{'params':{'chain':'UnitSphereLOD','expected_chain':chain['chain_sha256'],'directory':'cm-lods'},'wait':True})).data
            assert lod['valid'] and validate_lod(library/'cm-lods')['valid']
            manifest=json.loads((library/'cm-lods/manifest.json').read_text());assert manifest['scene_unit_scale']==unit
            assert manifest['levels'][0]['world_bounds_m']['max'][0]==pytest.approx(.04,abs=1e-6)
            manifest_path=library/'cm-lods/manifest.json';original=manifest_path.read_text()
            for bad in ([],[float('nan'),0,0],[0,0,0]):
                changed=json.loads(original);changed['levels'][0]['world_bounds_m']['max']=bad
                manifest_path.write_text(json.dumps(changed))
                with pytest.raises(ValueError,match='world bounds'):validate_lod(library/'cm-lods')
            manifest_path.write_text(original)
            assets=[{'id':'sphere','objects':['UnitSphere'],'lods':[{'chain':'UnitSphereLOD','animations':False}]}]
            plan=await tool(client,'inspect_asset_package',assets=assets);assert plan['can_export'],plan
            package=(await client.call_tool('export_asset_package',{'params':{'assets':assets,'expected_source':plan['source_sha256'],'directory':'cm-package'},'wait':True})).data
            assert package['valid'] and validate_package(library/'cm-package')['valid']
            report=package['members'][0]['scene'];assert report['world_bounds']['max'][0]==pytest.approx(.04,abs=1e-6)
            # A bone bend plus independent object translation must preserve clip timing
            # and scale root motion to metres in the actual file, not just its proof.
            await make_skin(client,'UnitSkin','UnitRig',x=10)
            await tool(client,'set_keyframes',name='UnitRig',data_path='location',keyframes=[{'frame':1,'value':[10,0,0]},{'frame':9,'value':[12,0,0]}])
            await client.call_tool('set_frame',{'frame':5})
            skin=await generate_skin(client,'UnitSkin','UnitSkinLOD')
            animation=await tool(client,'inspect_lod_export',chain='UnitSkinLOD')
            before=(await client.call_tool('get_object_info',{'name':'UnitRig'})).data
            result=(await client.call_tool('export_lod_chain',{'params':{'chain':'UnitSkinLOD','expected_chain':skin['chain_sha256'],'expected_animation':animation['animation_sha256'],'directory':'cm-skin'},'wait':True})).data
            assert result['valid'] and validate_lod(library/'cm-skin')['valid']
            raw=Document(library/'cm-skin/level_00.glb');clip=next(iter(raw.clips));times=raw.times(clip,3)
            start=raw.replay(clip,times[0],raw.representatives(8));end=raw.replay(clip,times[-1],raw.representatives(8))
            assert start['joints']['Base'][0][3]==pytest.approx(10*unit,abs=1e-6)
            assert end['joints']['Base'][0][3]==pytest.approx(12*unit,abs=1e-6)
            assert all(b[0]-a[0]==pytest.approx(2*unit,abs=1e-5) for a,b in zip(start['points'],end['points']))
            assert raw.report()['coordinate_space']=='METRES'
            after=(await client.call_tool('get_object_info',{'name':'UnitRig'})).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
            saved=await tool(client,'plan_leaf_template')
            probe=await tool(client,'create_leaf_template',name='FinalUnitsProbe',expected_leaf=saved['leaf_sha256']);assert probe['scene_unit_scale']==unit
            if target:=os.environ.get('MCPBLENDER_GLTF_UNIT_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True)
                for name in ('cm-lods','cm-package','cm-skin'):shutil.copytree(library/name,out/name,dirs_exist_ok=True)
                shutil.copy2(library/'leaf-cm.glb',out/'leaf-cm.glb')
                (out/'proof.json').write_text(json.dumps({'unit':unit,'leaf':leaf,'skin_start':start,'skin_end':end,'package':package},indent=2))
    asyncio.run(run())
