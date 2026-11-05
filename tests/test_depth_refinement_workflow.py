"""Depth-aware authoring through structured MCP, without code execution."""
import asyncio,json,os,shutil
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_depth_normal_refinement_guards_and_portable_maps(assets_live):
    root,path=assets_live;library=root/'library'
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='DepthTree',recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='DepthTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='DepthTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='DepthTree')
            capture={'collection':'DepthTree','views':['FRONT'],'resolution':32,'samples':8,'material_fields':True}
            cap=await wait(client,'inspect_botanical_view_capture',**capture)
            await wait(client,'capture_botanical_views',**capture,directory='depth-refine-input',expected_capture=cap['capture_sha256'])
            settings={'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','depth_tolerance_m':.05,'output_resolution':8,'max_slope':64}
            geo_settings=settings|{'plane_normal_source':'GEOMETRIC_AOV'}
            with pytest.raises(ToolError,match='recapture'):
                await wait(client,'inspect_botanical_depth_source',directory='depth-refine-input',view='FRONT',settings=geo_settings)
            capture['geometric_normals']=True
            cap=await wait(client,'inspect_botanical_view_capture',**capture)
            await wait(client,'capture_botanical_views',**capture,directory='depth-geometric-input',expected_capture=cap['capture_sha256'])
            args={'directory':'depth-geometric-input','view':'FRONT','settings':settings}
            plan=await wait(client,'inspect_botanical_depth_source',**args)
            report=plan['geometry'];depth=report['depth_residuals']
            assert report['format']=='mcpblender-adaptive-depth-normal-v1' and depth['measured_depth_pixels']>0
            assert depth['depth_tolerance_m']==.05 and depth['coverage_weighted_mae_m']<=depth['maximum_error_m']
            assert report['refinement_work']<=settings.get('max_refinement_work',8000000)
            legacy=await wait(client,'inspect_botanical_depth_source',**(args|{'settings':{'geometry_mode':'ADAPTIVE_NORMAL','output_resolution':8,'max_slope':64}}))
            assert plan['maps']==legacy['maps'] and 'depth_tolerance_m' not in legacy['geometry']['options']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**(args|{'settings':settings|{'depth_tolerance_m':.1}}),collection='DepthProxy',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            with pytest.raises(ToolError,match='work budget'):
                await wait(client,'inspect_botanical_depth_source',**(args|{'settings':settings|{'max_refinement_work':1}}))
            made=await wait(client,'create_botanical_depth_asset',**args,collection='DepthProxy',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            assert made['valid'] and made['packed_images']==6 and made['plan']['geometry']['depth_residuals']==depth
            geo_args=args|{'settings':geo_settings}
            geo=await wait(client,'inspect_botanical_depth_source',**geo_args)
            assert geo['maps']==plan['maps'] and geo['geometry']['plane_normal_source']['source']=='GEOMETRIC_AOV'
            assert geo['plan_sha256']!=plan['plan_sha256']
            explicit=await wait(client,'inspect_botanical_depth_source',**(args|{'settings':settings|{'plane_normal_source':'SHADING_PASS'}}))
            assert explicit==plan
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**geo_args,collection='GeometricProxy',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            geo_made=await wait(client,'create_botanical_depth_asset',**geo_args,collection='GeometricProxy',expected_plan=geo['plan_sha256'],accept_approximate_optics=True)
            assert geo_made['valid'] and geo_made['packed_images']==6
            assert (await wait(client,'inspect_botanical_tree',collection='DepthTree'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'depth-refinement.blend'})
            await client.call_tool('open_blend',{'path':'depth-refinement.blend'})
            if destination:=os.environ.get('MCPBLENDER_DEPTH_REFINEMENT_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'depth-geometric-input',out/'capture',dirs_exist_ok=True);shutil.copy2(library/'depth-refinement.blend',out/'depth-refinement.blend')
            shutil.rmtree(library/'depth-refine-input')
            shutil.rmtree(library/'depth-geometric-input')
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='DepthProxy')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256'] and not reopened['source_files_required']
            removed=await wait(client,'remove_botanical_depth_asset',collection='DepthProxy',expected_asset=reopened['asset_sha256']);assert removed['private_datablocks']==11
            geo_reopened=await wait(client,'inspect_botanical_depth_asset',collection='GeometricProxy')
            assert geo_reopened['valid'] and geo_reopened['asset_sha256']==geo_made['asset_sha256'] and not geo_reopened['source_files_required']
            geo_removed=await wait(client,'remove_botanical_depth_asset',collection='GeometricProxy',expected_asset=geo_reopened['asset_sha256']);assert geo_removed['private_datablocks']==11
            after=await wait(client,'inspect_botanical_tree',collection='DepthTree');assert after['valid']
            for key in ('model_sha256','members','foliage','root_world_matrix','geometry','metrics'):assert after[key]==before[key]
            return {'plan':plan,'legacy':legacy,'created':made,'reopened':reopened,'removed':removed,'geometric':{'plan':geo,'created':geo_made,'reopened':geo_reopened,'removed':geo_removed}}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_DEPTH_REFINEMENT_EVIDENCE'):
        (Path(destination)/'structured-proof.json').write_text(json.dumps(proof,indent=2))
