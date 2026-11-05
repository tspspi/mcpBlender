"""Alternative moment candidates through public MCP, with Python disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark


async def completed(client,queued):
    deadline=time.monotonic()+900
    while True:
        operation=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':30})).data
        if destination:=os.environ.get('MCPBLENDER_CANDIDATE_EVIDENCE'):
            out=Path(destination);out.mkdir(parents=True,exist_ok=True)
            (out/'operation-progress.json').write_text(json.dumps(operation,indent=2))
        if operation['state'] in {'failed','succeeded','cancelled','interrupted'}:return operation
        assert time.monotonic()<deadline,operation


async def wait(client,command,**params):
    queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
    operation=await completed(client,queued)
    if operation['state']!='succeeded':raise ToolError(operation.get('error') or str(operation))
    return operation['result']


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_MOMENT_CANOPY_SOURCE'),reason='Retained native moment capture required')
@pytest.mark.parametrize('slope',[16,64])
def test_structured_canopy_candidate_search_lifecycle(assets_live,slope):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copytree(os.environ['MCPBLENDER_MOMENT_CANOPY_SOURCE'],library/'canopy-input')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            source={'directory':'canopy-input','view':'FRONT','settings':{'geometry_mode':'MOMENT_FACETS','max_moment_candidates':64,'max_slope':slope}}
            with pytest.raises(ToolError,match='candidate budget exhausted'):
                await wait(client,'inspect_botanical_depth_source',**(source|{'settings':source['settings']|{'max_moment_candidates':1}}))
            plan=await wait(client,'inspect_botanical_depth_source',**source)
            assert plan['geometry']['candidate_attempts']>plan['geometry']['moment_tiles']>0
            assert plan['geometry']['max_component_residual']<=1e-5
            assert plan['geometry']['options']['max_slope']==slope
            assert plan['geometry']['direction_cap_method']=='mcpblender-normal-direction-cap-v1'
            alternative=source|{'settings':source['settings']|{'max_moment_candidates':63}}
            other=await wait(client,'inspect_botanical_depth_source',**alternative)
            assert plan['geometry']['vertices_sha256']==other['geometry']['vertices_sha256']
            assert plan['plan_sha256']!=other['plan_sha256']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**alternative,collection='CanopyMoment',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            made=await wait(client,'create_botanical_depth_asset',**source,collection='CanopyMoment',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            assert made['valid'] and made['shader_recipe']=='CAPTURED_INPUT_PBR_V3_GEOMETRIC_MOMENTS'
            await client.call_tool('save_blend',{'path':f'canopy-moment-{slope}.blend'})
            await client.call_tool('open_blend',{'path':f'canopy-moment-{slope}.blend'})
            shutil.rmtree(library/'canopy-input')
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='CanopyMoment')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256']
            removed=await wait(client,'remove_botanical_depth_asset',collection='CanopyMoment',expected_asset=reopened['asset_sha256'])
            assert removed['private_datablocks']==11
            return {'plan':plan,'created':made,'reopened':reopened,'removed':removed}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_CANDIDATE_EVIDENCE'):
        out=Path(destination)/str(slope);out.mkdir(parents=True,exist_ok=True)
        (out/'structured-proof.json').write_text(json.dumps(proof,indent=2))
        shutil.copy2(library/f'canopy-moment-{slope}.blend',out/'canopy-moment.blend')


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_MOMENT_DENSE_SOURCE'),reason='Retained dense native moment capture required')
def test_structured_direction_cap_refusal_progress_and_storage(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    source=Path(os.environ['MCPBLENDER_MOMENT_DENSE_SOURCE'])
    size=sum(p.stat().st_size for p in source.rglob('*') if p.is_file())
    assert shutil.disk_usage(library).free>size+2*1024**3
    shutil.copytree(source,library/'dense-input')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            queued=(await client.call_tool('submit_operation',{'command':'inspect_botanical_depth_source',
                'params':{'directory':'dense-input','view':'FRONT','settings':{'geometry_mode':'MOMENT_FACETS','max_moment_candidates':64}}})).data
            operation=await completed(client,queued)
            assert operation['state']=='failed' and 'DirectionCapError' in operation['error'],operation
            progress=operation['progress'];diag=progress['direction_cap']
            assert progress['phase']=='moment facet direction-cap refusal'
            assert diag['max_slope']==16 and diag['verdict']=='RULED_OUT'
            assert diag['next_not_ruled_out_max_slope']==32
            assert progress['storage']['free_bytes']>0
            decoded=json.loads(operation['error'].split('Moment facet direction cap ruled out: ',1)[1])
            assert decoded['direction_cap']==diag and decoded['pixel_rect']==progress['pixel_rect']
            return operation
    operation=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_CANDIDATE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        (out/'dense-refusal.json').write_text(json.dumps(operation,indent=2))
    shutil.rmtree(library/'dense-input')
