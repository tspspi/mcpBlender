"""A multi-view authoring pipeline through MCP, with arbitrary code disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


def test_structured_depth_layer_batch(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='LayerSource',recipe=recipe,expected_model=model['model_sha256'])
            foliage={'shoots_per_bud':2,'attachment_nodes':4};layout=await wait(client,'plan_botanical_foliage',collection='LayerSource',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='LayerSource',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            capture={'collection':'LayerSource','views':['FRONT','TOP'],'resolution':32,'samples':2,'material_fields':True}
            planned=await wait(client,'inspect_botanical_view_capture',**capture)
            await wait(client,'capture_botanical_views',**capture,directory='layer-input',expected_capture=planned['capture_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='LayerSource')
            args={'directory':'layer-input','prefix':'Layers','layers':[{'view':'FRONT','render_role':'CAMERA_ONLY'},{'view':'TOP','render_role':'DIFFUSE_SHADOW','settings':{'geometry_mode':'ADAPTIVE_NORMAL'}}]}
            plan=await wait(client,'inspect_botanical_depth_layers',**args)
            assert len(plan['layers'])==2 and plan['totals']['pixels']==2*32*32 and plan['totals']['decoded_texture_bytes']==2*32*32*96
            with pytest.raises(ToolError,match='budget'):
                await wait(client,'inspect_botanical_depth_layers',**args,limits={'max_total_texture_bytes':1024})
            changed=args|{'layers':[args['layers'][0],args['layers'][1]|{'render_role':'SHADOW_ONLY'}]}
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_layers',**changed,expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            with pytest.raises(ToolError,match='accept_approximate_optics'):
                await wait(client,'create_botanical_depth_layers',**args,expected_plan=plan['plan_sha256'])
            queued=(await client.call_tool('create_botanical_depth_layers',{'params':args|{'expected_plan':plan['plan_sha256'],'accept_approximate_optics':True}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':60})).data
            assert done['state']=='succeeded',done
            storage=done['progress']['storage']
            assert storage['free_bytes']>0 and storage['enough_space']
            assert storage['estimate_kind']=='packed_depth_layers_checkpoint_heuristic'
            assert storage['estimated_output_bytes']==2*plan['totals']['decoded_texture_bytes']+2*16*1024**2
            made=done['result']
            assert made['created_count']==2 and made['totals']==plan['totals']
            assert (await wait(client,'inspect_botanical_tree',collection='LayerSource'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'depth-layers.blend'});await client.call_tool('open_blend',{'path':'depth-layers.blend'})
            shutil.rmtree(root/'library/layer-input')
            reopened=[]
            for asset in made['assets']:
                state=await wait(client,'inspect_botanical_depth_asset',collection=asset['collection']);assert state['valid'] and state['asset_sha256']==asset['asset_sha256'] and state['render_role']==asset['render_role'];reopened.append(state)
                removed=await wait(client,'remove_botanical_depth_asset',collection=state['collection'],expected_asset=state['asset_sha256']);assert removed['private_datablocks']==11
            after=await wait(client,'inspect_botanical_tree',collection='LayerSource')
            for key in ('model_sha256','members','recipe','metrics','geometry','root_world_matrix','scene_unit_scale'):assert after[key]==before[key],key
            return {'plan':plan,'created':made,'reopened':reopened,'operation':done}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_DEPTH_LAYERS_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True);(out/'mcp-proof.json').write_text(json.dumps(proof,indent=2));shutil.copy2(root/'library/depth-layers.blend',out/'small-layers.blend')
