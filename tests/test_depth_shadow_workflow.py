"""Python-disabled MCP authoring of receiver-dependent depth-shadow layers."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_paired_shadow_batch_guards_budgets_and_packed_reopen(assets_live):
    root,path=assets_live;library=root/'library'
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='ShadowTree',recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='ShadowTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='ShadowTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='ShadowTree')
            capture={'collection':'ShadowTree','views':['FRONT','BACK','SIDE'],'resolution':128,'samples':32,'material_fields':True}
            cap=await wait(client,'inspect_botanical_view_capture',**capture)
            await wait(client,'capture_botanical_views',**capture,directory='shadow-input',expected_capture=cap['capture_sha256'])
            assert (await wait(client,'inspect_botanical_tree',collection='ShadowTree'))['tree_sha256']==before['tree_sha256']
            settings={'geometry_mode':'ADAPTIVE_NORMAL','max_slope':64,'output_resolution':32}
            layer={'view':'BACK','render_role':'SHADOW_ONLY','settings':settings,'shadow_mask':{'receiver_view':'FRONT'}}
            source={'directory':'shadow-input','view':'BACK','render_role':'SHADOW_ONLY','settings':settings,'shadow_mask':{'receiver_view':'FRONT'}}
            masked=await wait(client,'inspect_botanical_depth_source',**source)
            unmasked=await wait(client,'inspect_botanical_depth_source',**(source|{'shadow_mask':None}))
            assert masked['geometry']==unmasked['geometry']
            assert masked['maps'][0]['float32_sha256']!=unmasked['maps'][0]['float32_sha256']
            assert masked['maps'][1:]==unmasked['maps'][1:]
            mask=masked['shadow_mask']
            assert mask['unknown_policy']=='EXCLUDE' and mask['unknown_covered_pixels']>0
            assert mask['decoded_source_pixels']==2*128*128
            assert 0<mask['retained_alpha_mass']<mask['original_alpha_mass']
            with pytest.raises(ToolError,match='opposed'):
                await wait(client,'inspect_botanical_depth_source',**(source|{'shadow_mask':{'receiver_view':'SIDE'}}))
            args={'directory':'shadow-input','prefix':'ShadowStack','layers':[{'view':'FRONT','settings':settings},layer]}
            plan=await wait(client,'inspect_botanical_depth_layers',**args)
            assert plan['totals']['pixels']==3*128*128
            assert plan['totals']['decoded_texture_bytes']==2*128*128*96
            assert plan['layers'][1]['source_plan_sha256']==masked['plan_sha256']
            with pytest.raises(ToolError,match='pixel budget'):
                await wait(client,'inspect_botanical_depth_layers',**args,limits={'max_total_pixels':2*128*128})
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_layers',**(args|{'layers':[args['layers'][0],layer|{'shadow_mask':{'receiver_view':'FRONT','minimum_span_m':.01}}]}),expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            made=await wait(client,'create_botanical_depth_layers',**args,expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            assert made['created_count']==2 and all(v['valid'] for v in made['assets'])
            assert (await wait(client,'inspect_botanical_tree',collection='ShadowTree'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'shadow-stack.blend'})
            await client.call_tool('open_blend',{'path':'shadow-stack.blend'})
            if destination:=os.environ.get('MCPBLENDER_SHADOW_MCP_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'shadow-input',out/'capture',dirs_exist_ok=True)
                shutil.copy2(library/'shadow-stack.blend',out/'shadow-stack.blend')
            shutil.rmtree(library/'shadow-input')
            # Tree edit guards include native pointers and expire across reopen.
            # Compare portable content across reopen, then guard the removal span.
            after_open=await wait(client,'inspect_botanical_tree',collection='ShadowTree')
            for key in ('model_sha256','members','foliage','root_world_matrix','scene_unit_scale','geometry','metrics'):
                assert after_open[key]==before[key],key
            assert after_open['valid']
            reopened=[]
            for asset in made['assets']:
                state=await wait(client,'inspect_botanical_depth_asset',collection=asset['collection'])
                assert state['valid'] and state['asset_sha256']==asset['asset_sha256']
                reopened.append(state)
                removed=await wait(client,'remove_botanical_depth_asset',collection=state['collection'],expected_asset=state['asset_sha256'])
                assert removed['private_datablocks']==11
            assert (await wait(client,'inspect_botanical_tree',collection='ShadowTree'))['tree_sha256']==after_open['tree_sha256']
            return {'plan':plan,'created':made,'reopened':reopened}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_SHADOW_MCP_EVIDENCE'):
        (Path(destination)/'structured-proof.json').write_text(json.dumps(proof,indent=2))
