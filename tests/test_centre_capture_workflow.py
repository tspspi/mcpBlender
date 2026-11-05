"""Existing one-sample capture: explicit first-hit data through structured MCP."""
import asyncio,json,math,os,shutil
from pathlib import Path
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_capture_workflow import drain_captures
from test_depth_candidates import wait
from mcpblender import capture_data,exr_scanline,geometric_normals


def test_single_sample_native_capture_correspondence_and_depth_asset(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='CentreTree',recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='CentreTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='CentreTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='CentreTree')
            args={'collection':'CentreTree','views':['FRONT','BACK'],'resolution':32,'samples':1,'material_fields':True,'geometric_normals':True,'normal_moments':True}
            plan=await wait(client,'inspect_botanical_view_capture',**args)
            captured=await wait(client,'capture_botanical_views',**args,directory='centre-input',expected_capture=plan['capture_sha256'])
            assert captured['botanical_capture']['options']['samples']==1
            data=await wait(client,'inspect_botanical_capture_data',directory='centre-input',views=args['views'],alpha_threshold=.001,material_inputs=True)
            checks=[]
            archive,proof,metadata,rows=capture_data.source({'directory':str(root/'library/centre-input'),'views':args['views'],'max_pixels':1024,'max_total_pixels':2048})
            for view,row in rows:
                names=['TreeCapture.Combined.A','TreeCapture.Depth.Z','TreeCapture.MCP_SurfaceWeight.X','TreeCapture.MCP_MaterialId.X',*geometric_normals.channels()]
                channels=exr_scanline.decode(archive/row['file'],names,expected_sha256=row['sha256'])['channels']
                covered=0;maximum=0.
                for i,a in enumerate(channels[names[0]]):
                    assert abs(a-round(a))<1e-6 # This fixture has opaque surfaces.
                    if a<=.001:continue
                    covered+=1;depth=channels[names[1]][i];w=channels[names[2]][i]
                    assert view['clip_start']<=depth<=view['clip_end'] and abs(w-1)<1e-6
                    identity=channels[names[3]][i]/w;assert abs(identity-round(identity))<1e-6
                    normal=[channels[n][i]/w for n in names[4:]];error=abs(math.sqrt(sum(v*v for v in normal))-1)
                    maximum=max(maximum,error);assert error<1e-5
                assert covered>0
                measured=next(v for v in data['views'] if v['view']==view['view'])
                assert measured['covered_without_depth']==0
                assert measured['statistics']['depth_position_error_m']['max']<.001
                assert measured['statistics']['position_projection_error_px']['max']<.01
                assert measured['material_inputs']['normal_moments']['input_moments_valid']
                checks.append({'view':view['view'],'covered_pixels':covered,'maximum_geometric_unit_length_error':maximum})
            settings={'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','plane_normal_source':'GEOMETRIC_AOV','depth_tolerance_m':.05,'max_slope':64}
            source={'directory':'centre-input','view':'FRONT','settings':settings}
            proposed=await wait(client,'inspect_botanical_depth_source',**source)
            residuals=proposed['geometry']['depth_residuals']
            assert residuals['unknown_depth_pixels']==0 and residuals['measured_depth_pixels']>0
            assert proposed['geometry']['estimated_edge_tiles']==0
            made=await wait(client,'create_botanical_depth_asset',**source,collection='CentreDepth',expected_plan=proposed['plan_sha256'],accept_approximate_optics=True)
            assert made['valid'] and made['packed_images']==6
            assert (await wait(client,'inspect_botanical_tree',collection='CentreTree'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'centre-depth.blend'})
            await client.call_tool('open_blend',{'path':'centre-depth.blend'})
            if destination:=os.environ.get('MCPBLENDER_CENTRE_CAPTURE_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(archive,out/'capture',dirs_exist_ok=True);shutil.copy2(root/'library/centre-depth.blend',out/'centre-depth.blend')
            shutil.rmtree(archive)
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='CentreDepth')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256'] and not reopened['source_files_required']
            removed=await wait(client,'remove_botanical_depth_asset',collection='CentreDepth',expected_asset=reopened['asset_sha256'])
            assert removed['private_datablocks']==11
            return {'capture':captured,'checks':checks,'data':data,'plan':proposed,'created':made,'reopened':reopened,'removed':removed}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_CENTRE_CAPTURE_EVIDENCE'):
        (Path(destination)/'structured-proof.json').write_text(json.dumps(proof,indent=2))
