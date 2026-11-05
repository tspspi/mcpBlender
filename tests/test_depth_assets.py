"""Structured depth assets with arbitrary execution absent and native capture input."""
import asyncio
import json
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


@pytest.mark.parametrize('geometry_mode',['FLAT','ADAPTIVE_NORMAL','MOMENT_FACETS'])
def test_structured_native_depth_asset_lifecycle(assets_live,geometry_mode):
    root,path=assets_live;source_name='DepthSource_'+geometry_mode;blend_name='depth-packed-'+geometry_mode.lower()+'.blend'
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            state=await wait(client,'create_botanical_tree',collection=source_name,recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            if geometry_mode=='MOMENT_FACETS':
                # Controlled supported distribution, authored through the public
                # shader surface. Arbitrary captured trees may refuse support.
                await wait(client,'configure_shader_graph',material=state['geometry']['bark_material'],replace=True,
                    nodes=[{'name':'Surface','type':'ShaderNodeBsdfPrincipled','inputs':[{'socket':'Base Color','value':[.2,.2,.2,1]}]},
                        {'name':'Normal','type':'ShaderNodeVectorMath','properties':{'operation':'ADD'},'inputs':[{'socket':0,'value':[0,-1,0]}]},
                        {'name':'Output','type':'ShaderNodeOutputMaterial'}],
                    links=[{'from_node':'Normal','from_socket':'Vector','to_node':'Surface','to_socket':'Normal'},
                        {'from_node':'Surface','from_socket':'BSDF','to_node':'Output','to_socket':'Surface'}])
            else:
                f={'shoots_per_bud':2,'attachment_nodes':4}
                layout=await wait(client,'plan_botanical_foliage',collection=source_name,foliage=f)
                state=await wait(client,'configure_botanical_foliage',collection=source_name,foliage=f,expected_tree=state['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            args={'collection':source_name,'views':['FRONT'],'resolution':32,'samples':2,'material_fields':True}
            if geometry_mode=='MOMENT_FACETS':args['normal_moments']=True
            plan=await wait(client,'inspect_botanical_view_capture',**args)
            await wait(client,'capture_botanical_views',**args,directory='depth-input',expected_capture=plan['capture_sha256'])
            source_before=await wait(client,'inspect_botanical_tree',collection=source_name)
            before=source_before['tree_sha256']
            role='SHADOW_ONLY' if geometry_mode=='FLAT' else 'DIFFUSE_SHADOW'
            source={'directory':'depth-input','view':'FRONT','render_role':role,'settings':{'max_triangles':2048,'geometry_mode':geometry_mode}}
            info=await wait(client,'inspect_botanical_depth_source',**source)
            assert info['geometry']['triangles']>0 and info['decoded_texture_bytes']==32*32*96 and len(info['maps'])==6
            assert info['root_matrix_world'][0][3]==4 and info['root_matrix_world'][1][3]==3
            assert info['optical_equivalence'] is False and info['render_role']==role
            assert info['ray_visibility']['visible_camera'] is False and info['ray_visibility']['visible_shadow'] is True
            assert info['ray_visibility']['visible_diffuse']==(role=='DIFFUSE_SHADOW')
            assert info['shader_recipe']==('CAPTURED_INPUT_PBR_V3_GEOMETRIC_MOMENTS' if geometry_mode=='MOMENT_FACETS' else 'CAPTURED_INPUT_PBR_V2_SIDED_NORMAL')
            if geometry_mode=='MOMENT_FACETS':
                assert info['geometry']['moment_tiles']>0 and info['geometry']['max_component_residual']<=1e-5
                assert info['material_transport']=={'use_bump_map_correction':True}
            assert info['geometry']['options']['geometry_mode']==geometry_mode
            if geometry_mode=='ADAPTIVE_NORMAL':assert info['geometry']['refinement_work']>0
            changed=source|{'settings':source['settings']|{'geometry_mode':'FLAT' if geometry_mode=='ADAPTIVE_NORMAL' else 'ADAPTIVE_NORMAL'}}
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**changed,collection='ChangedMode',expected_plan=info['plan_sha256'],accept_approximate_optics=True)
            with pytest.raises(ToolError,match='accept_approximate_optics'):
                await wait(client,'create_botanical_depth_asset',**source,collection='Approximate',expected_plan=info['plan_sha256'])
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**source,collection='Approximate',expected_plan='0'*64,accept_approximate_optics=True)
            with pytest.raises(ToolError,match='texture budget'):
                await wait(client,'inspect_botanical_depth_source',directory='depth-input',view='FRONT',settings={'max_texture_bytes':1024})
            made=await wait(client,'create_botanical_depth_asset',**source,collection='Approximate',expected_plan=info['plan_sha256'],accept_approximate_optics=True)
            assert made['render_role']==role and made['ray_visibility']==info['ray_visibility']
            assert made['valid'] and made['packed_images']==6 and made['triangles']==info['geometry']['triangles']
            assert made['source_files_required'] is False and made['shader_recipe']==info['shader_recipe']
            assert (await wait(client,'inspect_botanical_tree',collection=source_name))['tree_sha256']==before
            await client.call_tool('save_blend',{'path':blend_name})
            # Reopen native packed data and prove lifecycle no longer reads input.
            await client.call_tool('open_blend',{'path':blend_name})
            import shutil
            shutil.rmtree(root/'library/depth-input')
            source_after_open=await wait(client,'inspect_botanical_tree',collection=source_name)
            # Live tree guards include RNA addresses and change on file reopen.
            # Prove portable source state as well, then use the new live guard.
            for key in ('model_sha256','members','recipe','metrics','geometry','root_world_matrix','scene_unit_scale'):assert source_after_open[key]==source_before[key],key
            reopened_source=source_after_open['tree_sha256']
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='Approximate')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256']
            assert reopened['render_role']==role and reopened['ray_visibility']==info['ray_visibility']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'remove_botanical_depth_asset',collection='Approximate',expected_asset='0'*64)
            removed=await wait(client,'remove_botanical_depth_asset',collection='Approximate',expected_asset=reopened['asset_sha256'])
            assert removed['private_datablocks']==11
            assert (await wait(client,'inspect_botanical_tree',collection=source_name))['tree_sha256']==reopened_source
            return {'plan':info,'created':made,'reopened':reopened,'removed':removed}
    proof=asyncio.run(run())
    import os,shutil
    if evidence:=os.environ.get('MCPBLENDER_DEPTH_EVIDENCE_DIR'):
        destination=Path(evidence)/geometry_mode.lower();destination.mkdir(parents=True,exist_ok=True)
        (destination/'structured-proof.json').write_text(json.dumps(proof,indent=2))
        shutil.copy2(root/'library'/blend_name,destination/'small-packed.blend')
