"""Large seeded canopy studies through MCP; opt-in visual qualification fixture."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark

pytestmark=pytestmark+[pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_CANOPY')!='1',reason='Set MCPBLENDER_TEST_CANOPY=1 for the three-seed dense canopy/render fixture')]


def test_three_seed_dense_canopy_presets_and_multiview_delivery(assets_live):
    root,path=assets_live;library=root/'library'
    evidence=Path(os.environ['MCPBLENDER_CANOPY_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_CANOPY_EVIDENCE_DIR') else None
    if evidence:evidence.mkdir(parents=True,exist_ok=True)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            bridge=(await client.call_tool('bridge_status')).data;assert bridge['bridge']['pid']>0
            if evidence:(evidence/'bridge.json').write_text(json.dumps(bridge,indent=2))
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+3600
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(v in str(exc) for v in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    trace={'command':command,'operation_id':queued['operation_id'],'state':state['state'],'progress':state.get('progress'),'storage':state.get('storage'),'error':state.get('error')}
                    if evidence:
                        (evidence/'latest-operation.json').write_text(json.dumps(trace,indent=2))
                        with (evidence/'operations.jsonl').open('a') as f:f.write(json.dumps(trace)+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            vis=await tool(client,'inspect_render_visibility',name='Cube')
            await tool(client,'configure_render_visibility',name='Cube',expected_visibility=vis['visibility_sha256'],hide_render=True)
            await tool(client,'configure_light',name='Light',type='POINT',energy=0)
            await tool(client,'configure_render',samples=8,resolution_x=320,resolution_y=320)
            proof={}
            for seed in (1,2,3):
                plan=await operation('plan_botanical_asset_preset',seed=seed)
                assert 80000<plan['foliage_metrics']['leaves']<=100000
                assert plan['triangles']['stored_with_shared_templates']*100<plan['triangles']['expanded_with_leaves']
                assert plan['lod_mask_estimates']['64']<256*1024**2<plan['lod_mask_estimates']['128']
                name=f'Canopy{seed}';state=await operation('create_botanical_asset_preset',seed=seed,collection=name,expected_preset=plan['preset_sha256'])
                assert state['valid'] and state['asset_preset']['creation_plan_sha256']==plan['preset_sha256']
                assert state['model_sha256']==plan['model_sha256'] and state['foliage']['compact_sha256']==plan['foliage_sha256']
                assert state['foliage']['metrics']['prototypes']==3
                objects=[state['mesh_assets']['wood']['name'],state['foliage']['roles']['po']['name'],state['foliage']['roles']['so']['name']]
                stage=await operation('setup_preview_stage',objects=objects,prefix=name,view='FRONT',projection='ORTHO',margin=1.15)
                bounds=stage['asset_world_bounds'];assert abs(bounds['min'][2])<1e-6 and 14<=bounds['max'][2]<16
                fits={}
                for view in ('FRONT','BACK','RIGHT','ISOMETRIC'):
                    fits[view]=await operation('frame_objects',name=name+'_Camera',objects=objects,view=view,margin=1.15)
                    assert fits[view]['fully_in_frame']
                    await operation('render_still',path=f'{name}-{view.lower()}.png',camera=name+'_Camera',width=320,height=320,engine='CYCLES')
                for light in stage['lights']:await tool(client,'configure_light',name=light['name'],type='AREA',energy=0)
                await tool(client,'configure_light',name=name+'_Sun',type='SUN',energy=3,location=[0,20,20],target=[0,0,8])
                await operation('frame_objects',name=name+'_Camera',objects=objects,view='FRONT',margin=1.15)
                await operation('render_still',path=f'{name}-backlit.png',camera=name+'_Camera',width=320,height=320,engine='CYCLES')
                await tool(client,'configure_light',name=name+'_Sun',type='SUN',energy=0)
                for light in stage['lights']:
                    await tool(client,'configure_light',name=light['name'],type='AREA',energy=light['energy'],color=light['color'],size=light['size'],location=light['location'],target=stage['asset_center'])
                await client.call_tool('save_blend',{'path':name+'.blend'})
                current=await operation('inspect_botanical_tree',collection=name);assert current['valid']
                proof[str(seed)]={'plan':plan,'stage':stage,'fits':fits,'tree_sha256':current['tree_sha256'],'blend':name+'.blend'}
                (library/'canopy-proof.json').write_text(json.dumps(proof,indent=2))
                print('CANOPY',seed,plan['foliage_metrics']['leaves'],bounds,flush=True)
                await operation('remove_botanical_tree',collection=name,expected_tree=current['tree_sha256'])
                for light in stage['lights']:await tool(client,'configure_light',name=light['name'],type='AREA',energy=0)
            # Independent save/reopen readback after the initial master was removed.
            await client.call_tool('open_blend',{'path':'Canopy3.blend'})
            restored=await operation('inspect_botanical_tree',collection='Canopy3')
            assert restored['valid'] and restored['model_sha256']==proof['3']['plan']['model_sha256']
            assert restored['asset_preset']['creation_plan_sha256']==proof['3']['plan']['preset_sha256']
            assert len({v['plan']['model_sha256'] for v in proof.values()})==3
            if evidence:(evidence/'canopy-proof.json').write_text(json.dumps(proof,indent=2))
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence:
            for file in ('blender.log','bridge/broker.log'):
                source=root/file
                if source.exists():shutil.copy2(source,evidence/source.name)
