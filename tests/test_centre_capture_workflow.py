"""Existing one-sample capture: explicit first-hit data through structured MCP."""
import asyncio,json,math,os,shutil,subprocess
import pytest
from pathlib import Path
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_capture_workflow import drain_captures
from test_depth_candidates import wait
from mcpblender import capture_data,exr_scanline,geometric_normals,component_ids


@pytest.mark.parametrize('with_components',[False,True])
def test_single_sample_native_capture_correspondence_and_depth_asset(assets_live,with_components):
    root,path=assets_live
    tree_name='ComponentTree' if with_components else 'CentreTree'
    capture_dir='component-input' if with_components else 'centre-input'
    blend_path='component-depth.blend' if with_components else 'centre-depth.blend'
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection=tree_name,recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection=tree_name,foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection=tree_name,foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection=tree_name)
            args={'collection':tree_name,'views':['FRONT','BACK'],'resolution':32,'samples':1,'material_fields':True,'geometric_normals':True,'normal_moments':not with_components,'component_ids':with_components}
            plan=await wait(client,'inspect_botanical_view_capture',**args)
            captured=await wait(client,'capture_botanical_views',**args,directory=capture_dir,expected_capture=plan['capture_sha256'])
            assert captured['botanical_capture']['options']['samples']==1
            data=await wait(client,'inspect_botanical_capture_data',directory=capture_dir,views=args['views'],alpha_threshold=.001,material_inputs=True)
            if with_components:
                compact=await wait(client,'inspect_botanical_capture_data',directory=capture_dir,views=['FRONT'],alpha_threshold=.001)
                assert compact['views'][0]['component_ids']==data['views'][0]['component_ids']
                assert captured['botanical_capture']['component_ids']['leaf_count']==before['foliage']['metrics']['leaves']
            checks=[]
            archive,proof,metadata,rows=capture_data.source({'directory':str(root/'library'/capture_dir),'views':args['views'],'max_pixels':1024,'max_total_pixels':2048})
            if with_components:
                component=metadata['component_ids']
                code='import bpy\nbpy.ops.wm.open_mainfile(filepath='+repr(str(archive/'source.blend'))+',use_scripts=False)\n'
                code+='assert bpy.data.meshes['+repr(component['point_mesh'])+'].attributes.get('+repr(component_ids.ATTRIBUTE)+') is None\n'
                code+='assert not any(n.type=="OUTPUT_AOV" and n.aov_name=="MCP_LeafComponent" for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes)\n'
                probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python-expr',code],capture_output=True,text=True,timeout=45)
                assert probe.returncode==0,probe.stdout+probe.stderr
            for view,row in rows:
                names=['TreeCapture.Combined.A','TreeCapture.Depth.Z','TreeCapture.MCP_SurfaceWeight.X','TreeCapture.MCP_MaterialId.X',*geometric_normals.channels()]
                channels=exr_scanline.decode(archive/row['file'],names,expected_sha256=row['sha256'])['channels']
                component_values=exr_scanline.decode(archive/row['file'],component_ids.channels(),expected_sha256=row['sha256'])['channels'][component_ids.channels()[0]] if with_components else None
                covered=0;maximum=0.
                for i,a in enumerate(channels[names[0]]):
                    assert abs(a-round(a))<1e-6 # This fixture has opaque surfaces.
                    if a<=.001:continue
                    covered+=1;depth=channels[names[1]][i];w=channels[names[2]][i]
                    assert view['clip_start']<=depth<=view['clip_end'] and abs(w-1)<1e-6
                    identity=channels[names[3]][i]/w;assert abs(identity-round(identity))<1e-6
                    if with_components:
                        component=component_values[i]/w
                        assert abs(component-round(component))<1e-6 and 0<=component<=metadata['component_ids']['leaf_count']
                    normal=[channels[n][i]/w for n in names[4:]];error=abs(math.sqrt(sum(v*v for v in normal))-1)
                    maximum=max(maximum,error);assert error<1e-5
                assert covered>0
                measured=next(v for v in data['views'] if v['view']==view['view'])
                assert measured['covered_without_depth']==0
                assert measured['statistics']['depth_position_error_m']['max']<.001
                assert measured['statistics']['position_projection_error_px']['max']<.01
                if with_components:
                    assert measured['component_ids']['integer_ids_valid'] and measured['component_ids']['structural_pixels']>0
                    assert measured['component_ids']['distinct_leaf_count']>0 and len(measured['component_ids']['leaf_index_preview'])<=16
                else:assert measured['material_inputs']['normal_moments']['input_moments_valid']
                checks.append({'view':view['view'],'covered_pixels':covered,'maximum_geometric_unit_length_error':maximum})
            settings={'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','plane_normal_source':'GEOMETRIC_AOV','depth_tolerance_m':.05,'max_slope':64}
            source={'directory':capture_dir,'view':'FRONT','settings':settings}
            proposed=await wait(client,'inspect_botanical_depth_source',**source)
            residuals=proposed['geometry']['depth_residuals']
            assert residuals['unknown_depth_pixels']==0 and residuals['measured_depth_pixels']>0
            assert proposed['geometry']['estimated_edge_tiles']==0
            made=await wait(client,'create_botanical_depth_asset',**source,collection='CentreDepth',expected_plan=proposed['plan_sha256'],accept_approximate_optics=True)
            assert made['valid'] and made['packed_images']==6
            assert (await wait(client,'inspect_botanical_tree',collection=tree_name))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':blend_path})
            await client.call_tool('open_blend',{'path':blend_path})
            if destination:=os.environ.get('MCPBLENDER_CENTRE_CAPTURE_EVIDENCE'):
                out=Path(destination)/'components' if with_components else Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(archive,out/'capture',dirs_exist_ok=True);shutil.copy2(root/'library'/blend_path,out/'centre-depth.blend')
            shutil.rmtree(archive)
            reopened=await wait(client,'inspect_botanical_depth_asset',collection='CentreDepth')
            assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256'] and not reopened['source_files_required']
            removed=await wait(client,'remove_botanical_depth_asset',collection='CentreDepth',expected_asset=reopened['asset_sha256'])
            assert removed['private_datablocks']==11
            return {'capture':captured,'checks':checks,'data':data,'plan':proposed,'created':made,'reopened':reopened,'removed':removed}
    proof=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_CENTRE_CAPTURE_EVIDENCE'):
        out=Path(destination)/'components' if with_components else Path(destination)
        (out/'structured-proof.json').write_text(json.dumps(proof,indent=2))
