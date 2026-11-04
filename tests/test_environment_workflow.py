"""Code-disabled environment lighting, macro material comparisons and HDRI rotation."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def rgba(path):
    return subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True,check=True,timeout=30).stdout


def test_sky_leaf_transmission_bark_and_packed_hdri(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    # Synthetic input media is prepared outside MCP; all scene edits below use typed tools.
    fixture=root/'hdri.py';fixture.write_text('import bpy\ni=bpy.data.images.new("Input",width=32,height=16,float_buffer=True)\ni.pixels.foreach_set([v for y in range(16) for x in range(32) for v in ((4.,.1,.1,1.) if x<16 else (.1,.1,4.,1.))])\ni.filepath_raw='+repr(str(library/'environment.exr'))+'\ni.file_format="OPEN_EXR"\ni.save()\n')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(fixture)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    evidence=Path(os.environ['MCPBLENDER_ENVIRONMENT_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_ENVIRONMENT_EVIDENCE_DIR') else None
    if evidence:evidence.mkdir(parents=True,exist_ok=True)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            assert (await client.call_tool('bridge_status')).data['bridge']['pid']>0
            await client.call_tool('get_scene_info')
            async def environment(settings,**kw):
                current=await tool(client,'inspect_environment')
                return await tool(client,'configure_environment',expected_environment=current['environment_sha256'],settings=settings,**kw)
            async def render(name,camera,width=384,height=384):
                queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':name,'camera':camera,'width':width,'height':height,'engine':'CYCLES'}})).data
                deadline=time.monotonic()+600
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(v in str(exc) for v in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    if evidence:
                        with (evidence/'render-operations.jsonl').open('a') as f:f.write(json.dumps({'path':name,'operation':state})+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            vis=await tool(client,'inspect_render_visibility',name='Cube')
            await tool(client,'configure_render_visibility',name='Cube',expected_visibility=vis['visibility_sha256'],hide_render=True)
            await tool(client,'configure_light',name='Light',type='POINT',energy=0)
            await tool(client,'configure_render',samples=32,resolution_x=384,resolution_y=384)
            state=await environment({'mode':'SKY','strength':.3,'sun_elevation_degrees':35,'sun_rotation_degrees':225},film_transparent=True)
            assert state['managed_unchanged']
            sky_state=state
            leafplan=await tool(client,'plan_leaf_template')
            leaf=await tool(client,'create_leaf_template',name='LookLeaf',expected_leaf=leafplan['leaf_sha256'])
            material=leaf['mesh']['materials'][0]
            mat=await tool(client,'inspect_botanical_surface',material=material)
            await wait(client,'configure_botanical_surface',material=material,expected_material=mat['material_sha256'],settings={'profile':'OAK_LEAF'})
            await tool(client,'configure_camera',name='LeafView',location=[0,.06,.5],target=[0,.06,0],projection='ORTHO',ortho_scale=.18)
            await render('leaf-front.png','LeafView')
            await tool(client,'configure_camera',name='LeafView',location=[0,.06,-.5],target=[0,.06,0])
            await render('leaf-back-transmission.png','LeafView')
            optics=await tool(client,'inspect_foliage_material',material=material)
            opaque=await tool(client,'configure_foliage_material',material=material,expected_material=optics['material_sha256'],translucent_mix=0)
            await render('leaf-back-opaque.png','LeafView')
            await tool(client,'configure_foliage_material',material=material,expected_material=opaque['material_sha256'],translucent_mix=optics['settings']['translucent_mix'])
            treeplan=await wait(client,'plan_botanical_tree')
            tree=await wait(client,'create_botanical_tree',collection='BarkStudy',expected_model=treeplan['model_sha256'],location=[2,0,0])
            bark=tree['geometry']['bark_material'];info=await tool(client,'inspect_botanical_surface',material=bark)
            await wait(client,'configure_botanical_surface',material=bark,expected_material=info['material_sha256'],settings={'profile':'OAK_BARK'})
            await tool(client,'configure_camera',name='BarkView',location=[2,-2,1],target=[2,0,1],projection='ORTHO',ortho_scale=1.4)
            await render('bark-default.png','BarkView')
            info=await tool(client,'inspect_botanical_surface',material=bark)
            await wait(client,'configure_botanical_surface',material=bark,expected_material=info['material_sha256'],settings={'profile':'OAK_BARK','cross_scale':80,'length_scale':8,'bump_distance':.004,'bump_strength':.35})
            await render('bark-finer.png','BarkView')
            await client.call_tool('save_blend',{'path':'macro-studies.blend'})
            # The HDRI is visible to the camera and supplies its own light; no scene lights.
            await environment({'mode':'HDRI','image_path':'environment.exr'},film_transparent=False)
            await tool(client,'configure_camera',name='EnvironmentView',location=[0,-2,0],target=[0,0,0],projection='PERSP',lens=50)
            await render('hdri-0.png','EnvironmentView',192,96)
            state=await environment({'mode':'HDRI','image_path':'environment.exr','rotation_degrees':180})
            await render('hdri-180.png','EnvironmentView',192,96)
            (library/'environment.exr').unlink()
            await client.call_tool('save_blend',{'path':'packed-world.blend'})
            await client.call_tool('open_blend',{'path':'packed-world.blend'})
            state=await tool(client,'inspect_environment');assert state['managed_unchanged'] and state['settings']['is_float']
            await render('hdri-restored.png','EnvironmentView',192,96)
            (library/'environment-proof.json').write_text(json.dumps({'sky':sky_state,'hdri':state,'leaf_optics':optics,'source_tree':tree},indent=2))
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence and (root/'blender.log').exists():shutil.copy2(root/'blender.log',evidence/'blender.log')
    front=rgba(library/'leaf-front.png');transmitted=rgba(library/'leaf-back-transmission.png');opaque=rgba(library/'leaf-back-opaque.png')
    selected=[i for i in range(0,len(transmitted),4) if transmitted[i+3]>250 and opaque[i+3]>250]
    assert len(selected)>5000
    green_a=sum(transmitted[i+1] for i in selected)/len(selected);green_b=sum(opaque[i+1] for i in selected)/len(selected)
    assert green_a>green_b+2,(green_a,green_b)
    bark_a=rgba(library/'bark-default.png');bark_b=rgba(library/'bark-finer.png')
    bark_pixels=[i for i in range(0,len(bark_a),4) if bark_a[i+3]>250 and bark_b[i+3]>250]
    assert len(bark_pixels)>5000
    bark_difference=sum(abs(bark_a[i+c]-bark_b[i+c]) for i in bark_pixels for c in range(3))/(len(bark_pixels)*3)
    assert bark_difference>1
    a=rgba(library/'hdri-0.png');b=rgba(library/'hdri-180.png');c=rgba(library/'hdri-restored.png')
    assert (a[0]-a[2])*(b[0]-b[2])< -1000,(a[:4],b[:4])
    assert b==c
    if evidence:(evidence/'pixel-proof.json').write_text(json.dumps({'opaque_leaf_pixels':len(selected),'back_green_with_transmission':green_a,'back_green_without_transmission':green_b,'bark_mean_rgb_difference':bark_difference,'world_rotation_pixels':[list(a[:4]),list(b[:4])]},indent=2))


def test_retained_dense_canopy_sky_lighting(assets_live):
    """Optional targeted review on a retained large asset, without rebuilding it."""
    import pytest
    source=os.environ.get('MCPBLENDER_ENVIRONMENT_CANOPY_SOURCE')
    if not source:pytest.skip('Set MCPBLENDER_ENVIRONMENT_CANOPY_SOURCE to a retained Canopy3.blend')
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source-canopy.blend')
    evidence=Path(os.environ['MCPBLENDER_ENVIRONMENT_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_ENVIRONMENT_EVIDENCE_DIR') else None
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
                deadline=time.monotonic()+600
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    if evidence:
                        evidence.mkdir(parents=True,exist_ok=True)
                        with (evidence/'canopy-operations.jsonl').open('a') as f:f.write(json.dumps({'command':command,'operation':state})+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':'source-canopy.blend'})
            original=await operation('inspect_botanical_tree',collection='Canopy3');assert original['valid']
            scene=(await client.call_tool('get_scene_info')).data
            for obj in scene['objects']:
                if obj['type']=='LIGHT':
                    name=obj['name'];kind='SUN' if name.endswith('_Sun') else 'POINT' if name=='Light' else 'AREA'
                    await tool(client,'configure_light',name=name,type=kind,energy=0)
            await tool(client,'configure_render',samples=16,resolution_x=320,resolution_y=320)
            objects=[original['mesh_assets']['wood']['name'],original['foliage']['roles']['po']['name'],original['foliage']['roles']['so']['name']]
            await operation('frame_objects',name='Canopy3_Camera',objects=objects,view='FRONT',margin=1.15)
            state=await tool(client,'inspect_environment')
            state=await tool(client,'configure_environment',expected_environment=state['environment_sha256'],settings={'mode':'SKY','strength':.3,'sun_elevation_degrees':35,'sun_rotation_degrees':0},film_transparent=False)
            assert all(s['energy']==0 for s in state['sun_lights'])
            await operation('render_still',path='Canopy3-sky.png',camera='Canopy3_Camera',width=320,height=320,engine='CYCLES')
            pipeline=await tool(client,'inspect_render_pipeline')
            await tool(client,'configure_color_management',expected_settings=pipeline['settings_sha256'],exposure=-2)
            await operation('render_still',path='Canopy3-sky-backlit-minus2.png',camera='Canopy3_Camera',width=320,height=320,engine='CYCLES')
            current_env=await tool(client,'inspect_environment')
            state=await tool(client,'configure_environment',expected_environment=current_env['environment_sha256'],settings={'mode':'SKY','strength':.3,'sun_elevation_degrees':35,'sun_rotation_degrees':180})
            await operation('render_still',path='Canopy3-sky-frontlit-minus2.png',camera='Canopy3_Camera',width=320,height=320,engine='CYCLES')
            current=await operation('inspect_botanical_tree',collection='Canopy3')
            assert current['valid'] and current['tree_sha256']==original['tree_sha256']
            await client.call_tool('save_blend',{'path':'sky-canopy.blend'})
            (library/'canopy-environment-proof.json').write_text(json.dumps({'environment':state,'tree_sha256':current['tree_sha256']},indent=2))
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'canopy-library',dirs_exist_ok=True)
