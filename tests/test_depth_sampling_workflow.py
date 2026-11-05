"""Capture denser input and author a declared output grid without Python tools."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_structured_denser_capture_output_grid_and_persistence(assets_live):
    root,path=assets_live;library=root/'library'
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='SamplingTree',recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='SamplingTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='SamplingTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='SamplingTree')
            for resolution in (32,128):
                args={'collection':'SamplingTree','views':['FRONT'],'resolution':resolution,'samples':32,'material_fields':True,'normal_moments':True}
                plan=await wait(client,'inspect_botanical_view_capture',**args)
                await wait(client,'capture_botanical_views',**args,directory=f'sampling-{resolution}',expected_capture=plan['capture_sha256'])
            assert (await wait(client,'inspect_botanical_tree',collection='SamplingTree'))['tree_sha256']==before['tree_sha256']
            source={'directory':'sampling-128','view':'FRONT','settings':{'output_resolution':32,'tile_pixels':4}}
            plan=await wait(client,'inspect_botanical_depth_source',**source)
            sampling=plan['geometry']['output_sampling']
            assert sampling['capture_texels_per_output_pixel']==4
            assert sampling['base_tile_output_pixels']==4 and sampling['base_tile_capture_pixels']==16
            assert plan['width']==plan['height']==128 and plan['decoded_texture_bytes']==128*128*96
            # The same world grid can be requested explicitly in capture pixels.
            manual=await wait(client,'inspect_botanical_depth_source',directory='sampling-128',view='FRONT',settings={'tile_pixels':16})
            assert manual['geometry']['vertices_sha256']==plan['geometry']['vertices_sha256']
            assert manual['geometry']['uv_sha256']==plan['geometry']['uv_sha256']
            assert manual['plan_sha256']!=plan['plan_sha256']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',directory='sampling-128',view='FRONT',settings={'tile_pixels':16},collection='SamplingProxy',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            with pytest.raises(ToolError,match='ratio'):
                await wait(client,'inspect_botanical_depth_source',directory='sampling-128',view='FRONT',settings={'output_resolution':48})
            with pytest.raises(ToolError,match='texture budget'):
                await wait(client,'inspect_botanical_depth_source',directory='sampling-128',view='FRONT',settings={'output_resolution':32,'max_texture_bytes':32768})
            made=await wait(client,'create_botanical_depth_asset',**source,collection='SamplingProxy',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            assert made['valid'] and made['plan']['geometry']['output_sampling']==sampling
            await client.call_tool('save_blend',{'path':'sampling-proxy.blend'})
            await client.call_tool('open_blend',{'path':'sampling-proxy.blend'})
            if destination:=os.environ.get('MCPBLENDER_SAMPLING_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                for resolution in (32,128):shutil.copytree(library/f'sampling-{resolution}',out/f'capture-{resolution}',dirs_exist_ok=True)
                shutil.copy2(library/'sampling-proxy.blend',out/'sampling-proxy.blend')
            shutil.rmtree(library/'sampling-128')
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='SamplingProxy')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256']
            removed=await wait(client,'remove_botanical_depth_asset',collection='SamplingProxy',expected_asset=reopened['asset_sha256'])
            assert removed['private_datablocks']==11
            return {'plan':plan,'created':made,'reopened':reopened,'removed':removed}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_SAMPLING_EVIDENCE'):
        (Path(destination)/'structured-proof.json').write_text(json.dumps(proof,indent=2))
