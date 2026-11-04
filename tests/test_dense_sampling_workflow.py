"""Full-density typed multigrid planning, cached creation and fixed-view review."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


def portable(state):return {k:v for k,v in state.items() if k not in {'tree_sha256','operation_id','recovery'}}


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_SAMPLING_DENSE_SOURCE'),reason='Requires retained Canopy3.blend')
def test_dense_multigrid_native_creation_and_views(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(os.environ['MCPBLENDER_SAMPLING_DENSE_SOURCE'],library/'source.blend')
    evidence=Path(os.environ['MCPBLENDER_SAMPLING_DENSE_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_SAMPLING_DENSE_EVIDENCE_DIR') else None
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            assert (await client.call_tool('bridge_status')).data['bridge']['pid']>0
            async def operation(command,**params):
                op=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+3600
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':op['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(t in str(exc) for t in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    if evidence:
                        evidence.mkdir(parents=True,exist_ok=True)
                        (evidence/'latest-operation.json').write_text(json.dumps({'command':command,'operation':state},indent=2))
                        with (evidence/'operations.jsonl').open('a') as f:f.write(json.dumps({'command':command,'operation':state})+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':'source.blend'})
            original=await operation('inspect_botanical_tree',collection='Canopy3');assert original['valid'] and original['foliage']['metrics']['leaves']==88704
            assert original['scene_unit_scale']==1
            args={'collection':'Canopy3','levels':[{'leaf_budget':70000,'radial_sides':8,'min_branch_radius_m':0},{'leaf_budget':60000,'radial_sides':8,'min_branch_radius_m':0}],
                  'resolution':64,'margin':1.5,'max_projected_triangles':180000000}
            # New total work admission includes all three grids; original default
            # must refuse this workload, not silently increase its policy.
            with pytest.raises(ToolError,match='budget'):
                await client.call_tool('inspect_botanical_lod_source',{
                    'params':args|{'max_projected_triangles':60000000},'wait':True})
            plan=await operation('inspect_botanical_lod_source',**args)
            assert plan['valid'] and plan['sampling_method']=='AREA_PRIORITY_MULTIGRID_V2' and len(plan['quality_grids'])==3
            assert plan['mask_payload_estimated_bytes']<1024**2 and plan['projected_triangles']<=180000000
            created=await operation('create_botanical_lods',**args,lod_collection='SamplingLods',display_offset_m=[20,0,0],expected_plan=plan['plan_sha256'])
            assert created['valid'] and [l['leaves'] for l in created['levels']]==[88704,70000,60000]
            assert all(l['wood_validation_quality'] for l in created['levels'])
            assert created['levels'][0]['wood_quality_frame']['FRONT']['frame_min_m'][1]==0
            scene=(await client.call_tool('get_scene_info')).data
            for o in scene['objects']:
                if o['type']=='LIGHT':
                    name=o['name'];kind='SUN' if name.endswith('_Sun') else 'POINT' if name=='Light' else 'AREA'
                    await tool(client,'configure_light',name=name,type=kind,energy=0)
            env=await tool(client,'inspect_environment')
            await tool(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'SKY','strength':.3,'sun_rotation_degrees':180})
            pipeline=await tool(client,'inspect_render_pipeline')
            await tool(client,'configure_color_management',expected_settings=pipeline['settings_sha256'],exposure=-2)
            await tool(client,'configure_render',samples=8,resolution_x=320,resolution_y=320)
            await tool(client,'configure_camera',name='SamplingView',location=[20,-25,7.5],target=[20,0,7.5],projection='ORTHO',ortho_scale=18)
            hidden=[*[v['object'] for v in original['members']],*[original['foliage']['roles'][k]['name'] for k in ('po','so')]]
            if any(o['name']=='Cube' for o in scene['objects']):hidden.append('Cube')
            visibility={}
            for name in dict.fromkeys(hidden):
                state=await tool(client,'inspect_render_visibility',name=name)
                visibility[name]=state['visibility']['hide_render']
                await tool(client,'configure_render_visibility',name=name,expected_visibility=state['visibility_sha256'],hide_render=True)
            current=created;fits={}
            for view in ('FRONT','ISOMETRIC'):
                current=await tool(client,'activate_botanical_lod',lod_collection='SamplingLods',expected_lods=current['lods_sha256'],level=0)
                fits[view]=await operation('frame_objects',name='SamplingView',objects=created['levels'][0]['objects'],view=view,margin=1.15)
                assert fits[view]['fully_in_frame']
                for number in range(3):
                    current=await tool(client,'activate_botanical_lod',lod_collection='SamplingLods',expected_lods=current['lods_sha256'],level=number)
                    await operation('render_still',path=f'{view.lower()}-{number}.png',camera='SamplingView',width=320,height=320,engine='CYCLES')
            for name,hide_render in visibility.items():
                state=await tool(client,'inspect_render_visibility',name=name)
                await tool(client,'configure_render_visibility',name=name,expected_visibility=state['visibility_sha256'],hide_render=hide_render)
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==original['tree_sha256']
            await client.call_tool('save_blend',{'path':'multigrid-lods.blend'})
            await client.call_tool('open_blend',{'path':'multigrid-lods.blend'})
            restored=await operation('inspect_botanical_lods',lod_collection='SamplingLods');assert restored['valid']
            source=await operation('inspect_botanical_tree',collection='Canopy3');assert portable(source)==portable(original)
            (library/'sampling-proof.json').write_text(json.dumps({'plan':plan,'created':created,'restored':restored,'source':original,'fits':fits},indent=2))
            await operation('remove_botanical_lods',lod_collection='SamplingLods',expected_lods=restored['lods_sha256'])
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==source['tree_sha256']
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence and (root/'blender.log').exists():shutil.copy2(root/'blender.log',evidence/'blender.log')
