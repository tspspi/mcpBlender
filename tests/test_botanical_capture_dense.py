"""Opt-in retained full-density native canopy capture qualification."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_capture_workflow import drain_captures
from mcpblender.card_views import DIRECTIONS

source=Path(os.environ['MCPBLENDER_TREE_CAPTURE_SOURCE']) if os.environ.get('MCPBLENDER_TREE_CAPTURE_SOURCE') else None
pytestmark=pytestmark+[pytest.mark.skipif(source is None or not source.is_file(),reason='Set MCPBLENDER_TREE_CAPTURE_SOURCE to retained Canopy3.blend')]


def test_full_density_tree_capture_and_live_editing(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True);shutil.copy2(source,library/'native-tree.blend')
    evidence=Path(os.environ['MCPBLENDER_TREE_CAPTURE_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_TREE_CAPTURE_EVIDENCE_DIR') else None
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+3600
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    if evidence:
                        evidence.mkdir(parents=True,exist_ok=True);(evidence/'dense-progress.json').write_text(json.dumps(state,indent=2))
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':'native-tree.blend'})
            before=await operation('inspect_botanical_tree',collection='Canopy3')
            moments=os.environ.get('MCPBLENDER_TREE_CAPTURE_NORMAL_MOMENTS')=='1'
            args={'collection':'Canopy3','views':list(DIRECTIONS),'resolution':512,'samples':8,'material_fields':True,'normal_moments':moments}
            plan=await operation('inspect_botanical_view_capture',**args)
            assert plan['leaf_instances']==88704 and plan['expanded_render_triangles']>17000000
            queued=(await client.call_tool('capture_botanical_views',{'params':args|{'directory':'dense-bundle','expected_capture':plan['capture_sha256']}})).data
            deadline=time.monotonic()+3600;edited=False
            while True:
                state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                if evidence:(evidence/'dense-progress.json').write_text(json.dumps(state,indent=2))
                assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                if not edited and state.get('progress',{}).get('render_job_id'):
                    assert state.get('storage',{}).get('free_bytes',0)>0,state
                    await operation('create_primitive',name='EditDuringTreeCapture',location=[100,100,100]);edited=True
                if state['state']=='succeeded':proof=state['result'];break
                assert time.monotonic()<deadline
            assert edited
            assert len(proof['outputs'])==20 and proof['botanical_capture']['capture_sha256']==plan['capture_sha256']
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
            verified=await operation('validate_render_job',directory='dense-bundle');assert verified['valid']
            if evidence:shutil.copytree(library/'dense-bundle',evidence/'dense-bundle',dirs_exist_ok=True)
            material_data=await operation('inspect_botanical_capture_data',directory='dense-bundle',material_inputs=True,views=['FRONT','BACK_LEFT'])
            if evidence:(evidence/'dense-material-inputs.json').write_text(json.dumps(material_data,indent=2))
            for view in material_data['views']:
                if moments:assert view['material_inputs']['normal_moments']['input_moments_valid'],view['material_inputs']['normal_moments']
                fields=view['material_inputs'];assert fields['covered_with_surface_weight']>0 and fields['covered_without_surface_weight']==0
                assert fields['normalized_inputs']['thin_weight']['max'][0]>.219
                assert fields['normalized_inputs']['thin_mode']['max'][0]>.999
                assert fields['normalized_inputs']['alpha']['min'][0]>.999
            if baseline:=os.environ.get('MCPBLENDER_TREE_CAPTURE_BASELINE'):
                from mcpblender.image_comparison import decode_png
                for row in verified['outputs']:
                    if row['format']=='PNG':assert decode_png((Path(baseline)/row['file']).read_bytes(),color_space='LINEAR',premultiply=False)==decode_png((library/'dense-bundle'/row['file']).read_bytes(),color_space='LINEAR',premultiply=False)
            if evidence:(evidence/'dense-material-inputs.json').write_text(json.dumps(material_data,indent=2))
            # Independently reopen the retained snapshot and check native shared
            # data, rather than trusting the planner's instance-count report.
            snapshot=library/'dense-bundle/source.blend'
            code="import bpy\nbpy.ops.wm.open_mainfile(filepath="+repr(str(snapshot))+",use_scripts=False)\nassert len(bpy.data.scenes)==1\nassert bpy.data.objects.get('EditDuringTreeCapture') is None\nassert any(len(m.vertices)==88704 for m in bpy.data.meshes)\nassert sum(len(m.vertices) for m in bpy.data.meshes)<500000\nassert any(n.bl_idname=='GeometryNodeInstanceOnPoints' for g in bpy.data.node_groups for n in g.nodes)\nassert not any(n.bl_idname=='GeometryNodeRealizeInstances' for g in bpy.data.node_groups for n in g.nodes)\n"
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python-expr',code],capture_output=True,text=True,timeout=45)
            assert probe.returncode==0,probe.stdout+probe.stderr
            from mcpblender.image_comparison import decode_png
            masks=[]
            for row in verified['outputs']:
                if row['format']!='PNG':continue
                width,height,pixels=decode_png((library/'dense-bundle'/row['file']).read_bytes())
                indices=[i for i in range(width*height) if pixels[4*i+3]>.5]
                assert indices
                low=[min(i%width for i in indices),min(i//width for i in indices)]
                high=[max(i%width for i in indices),max(i//width for i in indices)]
                assert min(low)>0 and high[0]<width-1 and high[1]<height-1
                masks.append({'camera':row['camera'],'covered_pixels':len(indices),'bounds_min':low,'bounds_max':high})
            if evidence:
                (evidence/'dense-proof.json').write_text(json.dumps({'plan':plan,'validation':verified,'live_editing':edited,'png_masks':masks,'native_shared_reopen':True},indent=2))
                shutil.copytree(library/'dense-bundle',evidence/'dense-bundle',dirs_exist_ok=True)
    try:asyncio.run(run())
    finally:
        if evidence:
            evidence.mkdir(parents=True,exist_ok=True)
            for file in ('blender.log','bridge/broker.log'):
                if (root/file).exists():shutil.copy2(root/file,evidence/Path(file).name)
