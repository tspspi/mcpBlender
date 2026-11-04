"""Opt-in retained full-density wind, native animation, rendered video and readback."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_WIND_CANOPY_SOURCE'),reason='Requires a retained Canopy3.blend')
def test_retained_dense_canopy_wind_animation(assets_live):
    source=os.environ.get('MCPBLENDER_WIND_CANOPY_SOURCE')
    if not source:pytest.skip('Set MCPBLENDER_WIND_CANOPY_SOURCE to a retained Canopy3.blend')
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source-canopy.blend')
    evidence=Path(os.environ['MCPBLENDER_WIND_CANOPY_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_WIND_CANOPY_EVIDENCE_DIR') else None
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
                deadline=time.monotonic()+1800
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(v in str(exc) for v in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    if evidence:
                        evidence.mkdir(parents=True,exist_ok=True)
                        with (evidence/'operations.jsonl').open('a') as f:f.write(json.dumps({'command':command,'operation':state})+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':'source-canopy.blend'})
            original=await operation('inspect_botanical_tree',collection='Canopy3');assert original['valid']
            args={'collection':'Canopy3','frame_start':1,'frame_end':13,'frame_step':1,'display_offset_m':[20,0,0],
                  'max_instances':original['foliage']['metrics']['leaves'],'wind':{'steady_mps':[3,1,0],'gust_mps':2,'bend_degrees_per_mps':1}}
            # Defaults deliberately refuse this larger population before allocation.
            with pytest.raises(ToolError,match='instance budget'):
                await tool(client,'inspect_botanical_wind_preview_source',**(args|{'max_instances':30000}))
            planned=await operation('inspect_botanical_wind_preview_source',**args)
            assert planned['leaf_instances']==88704 and planned['prototypes']==3
            created=await operation('create_botanical_wind_preview',**args,preview_collection='CanopyWind',expected_plan=planned['plan_sha256'])
            assert created['valid'] and len(created['verification']['checked_frames'])==25
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==original['tree_sha256']
            scene=(await client.call_tool('get_scene_info')).data
            for obj in scene['objects']:
                if obj['type']=='LIGHT':
                    name=obj['name'];kind='SUN' if name.endswith('_Sun') else 'POINT' if name=='Light' else 'AREA'
                    await tool(client,'configure_light',name=name,type=kind,energy=0)
            env=await tool(client,'inspect_environment')
            await tool(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'SKY','strength':.3,'sun_elevation_degrees':35,'sun_rotation_degrees':180},film_transparent=False)
            pipeline=await tool(client,'inspect_render_pipeline')
            await tool(client,'configure_color_management',expected_settings=pipeline['settings_sha256'],exposure=-2)
            await tool(client,'configure_render',samples=8,resolution_x=256,resolution_y=256)
            await tool(client,'configure_camera',name='WindView',location=[20,-25,7.5],target=[20,0,7.5],projection='ORTHO',ortho_scale=18)
            images=[]
            for frame in range(1,14):
                await client.call_tool('set_frame',{'frame':frame})
                name=f'wind-{frame:03}.png';images.append(name)
                await operation('render_still',path=name,camera='WindView',width=256,height=256,engine='CYCLES')
            assert len({(library/name).read_bytes() for name in images})==13
            await client.call_tool('save_blend',{'path':'canopy-wind.blend'})
            await client.call_tool('open_blend',{'path':'canopy-wind.blend'})
            restored=await operation('inspect_botanical_wind_preview',preview_collection='CanopyWind');assert restored['valid']
            source_after_reopen=await operation('inspect_botanical_tree',collection='Canopy3')
            assert portable_source(source_after_reopen)==portable_source(original)
            (library/'wind-proof.json').write_text(json.dumps({'plan':planned,'created':created,'restored':restored,'source_tree_sha256':original['tree_sha256'],'source_tree':original},indent=2))
            await operation('remove_botanical_wind_preview',preview_collection='CanopyWind',expected_preview=restored['preview_sha256'])
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==source_after_reopen['tree_sha256']
    try:
        asyncio.run(run())
        complete_evidence(library,root)
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence and (root/'blender.log').exists():shutil.copy2(root/'blender.log',evidence/'blender.log')


def portable_source(state):
    # Session guards include native addresses and intentionally change on reload.
    return {k:v for k,v in state.items() if k not in {'tree_sha256','recovery','operation_id'}}


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_WIND_CANOPY_SAVED'),reason='Requires retained wind evidence')
def test_retained_canopy_wind_saved_delivery(assets_live):
    root,path=assets_live;library=root/'library'
    shutil.copytree(os.environ['MCPBLENDER_WIND_CANOPY_SAVED'],library,dirs_exist_ok=True)
    proof=json.loads((library/'wind-proof.json').read_text())
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'canopy-wind.blend'})
            source=await tool(client,'inspect_botanical_tree',collection='Canopy3')
            assert portable_source(source)==portable_source(proof['source_tree'])
            preview=await tool(client,'inspect_botanical_wind_preview',preview_collection='CanopyWind');assert preview['valid']
            removed=await tool(client,'remove_botanical_wind_preview',preview_collection='CanopyWind',expected_preview=preview['preview_sha256'])
            assert removed['materials_preserved']
            after=await tool(client,'inspect_botanical_tree',collection='Canopy3')
            assert after['tree_sha256']==source['tree_sha256'] and after['valid']
            (library/'cleanup-proof.json').write_text(json.dumps({'source':source,'after':after,'removed':removed},indent=2))
    try:
        asyncio.run(run());complete_evidence(library,root)
    finally:
        if destination:=os.environ.get('MCPBLENDER_WIND_CANOPY_EVIDENCE_DIR'):
            shutil.copytree(library,Path(destination)/'library',dirs_exist_ok=True)


def complete_evidence(library,root):
    reader=root/'readback.py'
    reader.write_text('import sys\nsys.path.insert(0,'+repr(str(Path(__file__).resolve().parents[1]))+')\nROOT='+repr(str(library))+'\n'+NATIVE_READBACK)
    readback=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(reader)],capture_output=True,text=True,timeout=600)
    (library/'readback.log').write_text(readback.stdout+'\n'+readback.stderr)
    assert readback.returncode==0,readback.stdout+'\n'+readback.stderr
    decoded=[subprocess.run(['ffmpeg','-v','error','-i',str(library/f'wind-{i:03}.png'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=30).stdout for i in range(1,14)]
    assert all(len(v)==256*256*3 for v in decoded) and len(set(decoded))==13
    pairs=[{'frames':[1,i+1],'changed_rgb_pixels':sum(decoded[0][j:j+3]!=decoded[i][j:j+3] for j in range(0,len(decoded[0]),3)),
            'mean_absolute_rgb_difference':sum(abs(x-y) for x,y in zip(decoded[0],decoded[i]))/len(decoded[0])} for i in (6,12)]
    (library/'pixel-proof.json').write_text(json.dumps({'distinct_decoded_frames':13,'pairs':pairs},indent=2))
    subprocess.run(['ffmpeg','-y','-v','error','-framerate','24','-start_number','1','-i',str(library/'wind-%03d.png'),'-frames:v','13','-c:v','libx264','-pix_fmt','yuv420p',str(library/'canopy-wind.mp4')],check=True,capture_output=True,timeout=60)
    media=json.loads(subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(library/'canopy-wind.mp4')],check=True,capture_output=True,text=True,timeout=30).stdout)['streams'][0]
    assert (media['width'],media['height'],media['nb_read_frames'],media['r_frame_rate'])==(256,256,'13','24/1')
    (library/'video-proof.json').write_text(json.dumps(media,indent=2))



NATIVE_READBACK=r'''
import bpy,json,math,hashlib,array
from pathlib import Path
from mathutils import Vector
from mcpblender import foliage,wind
from mcpblender.blender import wind_preview as api,botanical_trees as trees,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
root=Path(ROOT);proof=json.loads((root/'wind-proof.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(root/'canopy-wind.blend'),load_ui=False,use_scripts=False)
col,owned,meta,state=api.inspect({'preview_collection':'CanopyWind'});assert state['valid']
document=json.loads(bpy.data.texts[state['semantic_text']].as_string())
model=document['model'];population=foliage.generate(model,document['foliage_recipe'])
plan=document['plan'];cfg=plan['source']['wind'];placement=plan['source']['placement']
helper=bpy.data.objects[state['roles']['leaves']];wood=bpy.data.objects[state['roles']['wood']]
# Read native shape-key coordinates before the instance-only Geometry Nodes output.
carrier=bpy.data.objects.new('Independent helper readback',helper.data);bpy.context.scene.collection.objects.link(carrier)
carrier.parent=helper.parent;carrier.matrix_basis=helper.matrix_basis.copy()
count=len(population['leaves']);assert count==88704 and len(helper.data.vertices)==count*3
assert len(helper.data.shape_keys.key_blocks)==len(plan['frames'])+1==14
assert len(state['prototype_objects'])==3
assert all(n.bl_idname!='GeometryNodeRealizeInstances' for m in helper.modifiers for n in m.node_group.nodes)
assert len({helper.data,*[bpy.data.objects[n].data for n in state['prototype_objects']]})==4
source=trees.inspect({'collection':'Canopy3'});assert source['valid']
portable=lambda d:{k:v for k,v in d.items() if k not in {'tree_sha256','recovery','operation_id'}}
assert portable(source)==portable(proof['source_tree'])
soil=[v.index for v in wood.data.vertices if abs(v.co.z)<1e-7 and wood.data.attributes['bot_branch_index'].data[v.index].value==0]
assert soil
result={'leaf_instances':count,'helper_vertices':count*3,'shape_keys':14,'frames':[],'max_center_error_m':0.,'max_helper_axis_error_degrees':0.,'source_guard':source['tree_sha256']}
endpoint=None;first=None
for frame in (1,7,7.5,13,20):
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));graph=bpy.context.evaluated_depsgraph_get()
    evaluated=carrier.evaluated_get(graph);mesh=evaluated.to_mesh()
    try:
        seconds=min(frame,13)/plan['fps'];pose=wind.solve(model,cfg,seconds,placement)
        maximum=0.;angle=0.
        for i,leaf in enumerate(population['leaves']):
            j=leaf['parent_branch_index'];desired=wind.leaf_local_pose(leaf,model['branches'][j],pose['branches'][j],cfg,seconds)
            center=mesh.vertices[i*3].co
            maximum=max(maximum,(center-Vector(desired['position_local_m'])).length*placement['scale'])
            for axis,index in ((0,1),(2,2)):
                actual=(mesh.vertices[i*3+index].co-center).normalized()
                expected=Vector([desired['rotation_local'][k][axis] for k in range(3)])
                angle=max(angle,math.degrees(actual.angle(expected,0.)))
        limit=plan['options']['max_key_error_m'] if frame in (1,7,13,20) else plan['options']['max_midpoint_error_m']
        assert maximum<=limit,(frame,maximum,limit)
        assert angle<plan['options']['max_orientation_error_degrees'],(frame,angle)
        coords=array.array('f',[0.])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',coords)
        signature=hashlib.sha256(coords.tobytes()).hexdigest()
        if frame==1:first=signature
        if frame==13:endpoint=signature;assert endpoint!=first
        if frame==20:assert signature==endpoint
        observed={}
        if frame in (1,13):
            prototypes={bpy.data.objects[n] for n in state['prototype_objects']};instances=0;used=set()
            for inst in graph.object_instances:
                if inst.is_instance and inst.parent and inst.parent.original==helper and inst.show_self:
                    instances+=1;assert inst.object.original in prototypes;used.add(inst.object.original.name)
            assert instances==count and len(used)==3
            observed={'native_instances':instances,'used_prototypes':sorted(used)}
        vertices=wood.evaluated_get(graph).data.vertices
        assert all((vertices[i].co-wood.data.vertices[i].co).length<1e-6 for i in soil)
        result['frames'].append({'frame':frame,'center_error_m':maximum,'axis_error_degrees':angle,'coordinate_sha256':signature,**observed})
        result['max_center_error_m']=max(result['max_center_error_m'],maximum)
        result['max_helper_axis_error_degrees']=max(result['max_helper_axis_error_degrees'],angle)
    finally:evaluated.to_mesh_clear()
bpy.data.objects.remove(carrier,do_unlink=True)
assert api.inspect({'preview_collection':'CanopyWind'})[-1]['valid']
assert trees.inspect({'collection':'Canopy3'})['tree_sha256']==source['tree_sha256']
(root/'native-readback.json').write_text(json.dumps(result,indent=2))
print('DENSE_CANOPY_WIND_READBACK_OK')
'''
