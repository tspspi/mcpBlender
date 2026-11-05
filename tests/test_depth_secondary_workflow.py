"""Camera-excluded paired-depth roles through Python-disabled MCP batch tools."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_masked_secondary_roles_batch_and_portable_lifecycle(assets_live):
    root,path=assets_live;library=root/'library'
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='SecondaryTree',recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='SecondaryTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='SecondaryTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='SecondaryTree')
            capture={'collection':'SecondaryTree','views':['FRONT','BACK'],'resolution':32,'samples':8,'material_fields':True}
            plan=await wait(client,'inspect_botanical_view_capture',**capture)
            await wait(client,'capture_botanical_views',**capture,directory='secondary-input',expected_capture=plan['capture_sha256'])
            settings={'output_resolution':8,'geometry_mode':'ADAPTIVE_NORMAL','max_slope':64}
            source={'directory':'secondary-input','view':'BACK','shadow_mask':{'receiver_view':'FRONT'},'settings':settings}
            plans={}
            for role in ('SHADOW_ONLY','DIFFUSE_SHADOW','SECONDARY'):
                plans[role]=await wait(client,'inspect_botanical_depth_source',**source,render_role=role)
                assert not plans[role]['ray_visibility']['visible_camera'] and plans[role]['optical_equivalence'] is False
            assert len({p['plan_sha256'] for p in plans.values()})==3
            assert all(p['geometry']==plans['SHADOW_ONLY']['geometry'] and p['maps']==plans['SHADOW_ONLY']['maps'] and p['shadow_mask']==plans['SHADOW_ONLY']['shadow_mask'] for p in plans.values())
            layers=[{'view':'FRONT','render_role':'DIFFUSE_SHADOW','shadow_mask':{'receiver_view':'BACK'},'settings':settings},
                    {'view':'BACK','render_role':'SECONDARY','shadow_mask':{'receiver_view':'FRONT'},'settings':settings}]
            args={'directory':'secondary-input','prefix':'SecondaryLayers','layers':layers}
            batch=await wait(client,'inspect_botanical_depth_layers',**args)
            assert batch['totals']['pixels']==4*32*32 and batch['totals']['decoded_texture_bytes']==2*32*32*96
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_layers',**(args|{'layers':[layers[0]|{'render_role':'SECONDARY'},layers[1]]}),expected_plan=batch['plan_sha256'],accept_approximate_optics=True)
            made=await wait(client,'create_botanical_depth_layers',**args,expected_plan=batch['plan_sha256'],accept_approximate_optics=True)
            assert (await wait(client,'inspect_botanical_tree',collection='SecondaryTree'))['tree_sha256']==before['tree_sha256']
            for asset in made['assets']:
                expected=next(row['ray_visibility'] for row in batch['layers'] if row['view']==asset['collection'].removeprefix('SecondaryLayers-'))
                assert asset['valid'] and asset['ray_visibility']==expected
                assert asset['ray_visibility']['visible_diffuse'] and asset['ray_visibility']['visible_shadow'] and not asset['ray_visibility']['visible_camera']
            await client.call_tool('save_blend',{'path':'secondary-layers.blend'})
            await client.call_tool('open_blend',{'path':'secondary-layers.blend'})
            if destination:=os.environ.get('MCPBLENDER_SECONDARY_MCP_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'secondary-input',out/'capture',dirs_exist_ok=True)
                shutil.copy2(library/'secondary-layers.blend',out/'secondary-layers.blend')
            shutil.rmtree(library/'secondary-input');reopened=[]
            for asset in made['assets']:
                state=await wait(client,'inspect_botanical_depth_asset',collection=asset['collection'])
                assert state['valid'] and state['asset_sha256']==asset['asset_sha256'] and not state['source_files_required']
                assert state['render_role']==asset['render_role'] and state['ray_visibility']==asset['ray_visibility'];reopened.append(state)
                removed=await wait(client,'remove_botanical_depth_asset',collection=state['collection'],expected_asset=state['asset_sha256'])
                assert removed['private_datablocks']==11
            after=await wait(client,'inspect_botanical_tree',collection='SecondaryTree')
            for key in ('model_sha256','members','foliage','root_world_matrix','geometry','metrics'):assert after[key]==before[key]
            assert after['valid']
            return {'plans':plans,'batch':batch,'created':made,'reopened':reopened}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_SECONDARY_MCP_EVIDENCE'):
        (Path(destination)/'structured-proof.json').write_text(json.dumps(proof,indent=2))
