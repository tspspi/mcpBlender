"""Alternative moment candidates through public MCP, with Python disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_MOMENT_CANOPY_SOURCE'),reason='Retained native moment capture required')
def test_structured_canopy_candidate_search_lifecycle(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copytree(os.environ['MCPBLENDER_MOMENT_CANOPY_SOURCE'],library/'canopy-input')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            source={'directory':'canopy-input','view':'FRONT','settings':{'geometry_mode':'MOMENT_FACETS','max_moment_candidates':64}}
            with pytest.raises(ToolError,match='candidate budget exhausted'):
                await wait(client,'inspect_botanical_depth_source',**(source|{'settings':source['settings']|{'max_moment_candidates':1}}))
            plan=await wait(client,'inspect_botanical_depth_source',**source)
            assert plan['geometry']['candidate_attempts']>plan['geometry']['moment_tiles']>0
            assert plan['geometry']['max_component_residual']<=1e-5
            alternative=source|{'settings':source['settings']|{'max_moment_candidates':63}}
            other=await wait(client,'inspect_botanical_depth_source',**alternative)
            assert plan['geometry']['vertices_sha256']==other['geometry']['vertices_sha256']
            assert plan['plan_sha256']!=other['plan_sha256']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**alternative,collection='CanopyMoment',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            made=await wait(client,'create_botanical_depth_asset',**source,collection='CanopyMoment',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            assert made['valid'] and made['shader_recipe']=='CAPTURED_INPUT_PBR_V3_GEOMETRIC_MOMENTS'
            await client.call_tool('save_blend',{'path':'canopy-moment.blend'})
            await client.call_tool('open_blend',{'path':'canopy-moment.blend'})
            shutil.rmtree(library/'canopy-input')
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='CanopyMoment')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256']
            removed=await wait(client,'remove_botanical_depth_asset',collection='CanopyMoment',expected_asset=reopened['asset_sha256'])
            assert removed['private_datablocks']==11
            return {'plan':plan,'created':made,'reopened':reopened,'removed':removed}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_CANDIDATE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        (out/'structured-proof.json').write_text(json.dumps(proof,indent=2))
        shutil.copy2(library/'canopy-moment.blend',out/'canopy-moment.blend')
