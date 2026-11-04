"""Opt-in matched camera/native versus delivered GLB card, via typed MCP only."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_CARD_COMPARISON_FIXTURE'),reason='Retained fitted-card delivery opt-in required')
def test_matched_native_delivered_card_images(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    fixture=Path(os.environ['MCPBLENDER_CARD_COMPARISON_FIXTURE']);proof=json.loads((fixture/'proof.json').read_text())
    bundle=next(p for p in fixture.iterdir() if p.is_dir() and (p/'source.blend').is_file())
    shutil.copy2(bundle/'source.blend',library/'source.blend');shutil.copy2(next(fixture.glob('*.glb')),library/'card.glb')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+300
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                    assert state['state'] not in {'failed','cancelled','interrupted'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline,('Still live; do not replay',queued['operation_id'])
            await client.call_tool('open_blend',{'path':'source.blend'})
            imported=(await client.call_tool('import_asset',{'path':'card.glb'})).data
            scene=(await client.call_tool('get_scene_info',{'limit':1000})).data
            source=proof['cluster']['object'];baked=[o['name'] for o in scene['objects'] if o['name'] in imported['objects'] and o['type']=='MESH']
            assert len(baked)==1
            async def visible(name,value):
                current=await tool(client,'inspect_render_visibility',name=name)
                await tool(client,'configure_render_visibility',name=name,expected_visibility=current['visibility_sha256'],hide_render=not value)
            for obj in scene['objects']:
                if obj['type'] in {'MESH','LIGHT'}:await visible(obj['name'],obj['name']==source)
            env=await tool(client,'inspect_environment')
            await tool(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5},film_transparent=True)
            fit=proof['fit'];assert fit['view']=='TOP'
            vertices=fit['vertices_m'];low=[min(v[a] for v in vertices) for a in range(3)];high=[max(v[a] for v in vertices) for a in range(3)]
            unit=scene['unit_scale'];centre=[(lo+hi)/2/unit for lo,hi in zip(low,high)];span=max(high[a]-low[a] for a in (0,1));location=centre[:];location[2]+=(fit['source_depth_m']+span*2+1)/unit
            camera=await tool(client,'configure_camera',name='ComparisonCamera',location=location,target=centre,projection='ORTHO',ortho_scale=span*1.1/unit)
            await tool(client,'configure_render',resolution_x=512,resolution_y=512,samples=16)
            await operation('render_still',path='native.png',camera='ComparisonCamera',engine='CYCLES',width=512,height=512)
            await visible(source,False);await visible(baked[0],True)
            await operation('render_still',path='card.png',camera='ComparisonCamera',engine='CYCLES',width=512,height=512)
            camera_after=(await client.call_tool('get_object_info',{'name':'ComparisonCamera'})).data
            assert camera_after['matrix_world']==camera['matrix_world']
            result=await operation('compare_png_images',reference='native.png',candidate='card.png',scales=[1,2,4,8])
            assert 'recovery' not in result and result['width']==512 and result['height']==512
            assert result['levels'][0]['reference_mask_pixels']>0 and result['levels'][0]['candidate_mask_pixels']>0
            assert (await operation('compare_png_images',reference='native.png',candidate='native.png',scales=[1,2,4,8]))['passed']
            if directory:=os.environ.get('MCPBLENDER_CARD_COMPARISON_EVIDENCE'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True)
                for name in ('native.png','card.png'):shutil.copy2(library/name,out/name)
                (out/'comparison.json').write_text(json.dumps({'comparison':result,'camera':camera,'unit_scale':unit,'frame':scene['frame'],'source':source,'candidate':baked[0],
                    'protocol':'Same TOP orthographic camera/frame, 512px Cycles16 samples, white world strength0.5 and transparent film, all other mesh/light objects render-hidden. Original native thin shader versus delivered FRONT_PBR GLB; optical/material losses intentionally measured, not removed.'},indent=2))
    asyncio.run(run())
