"""Code-disabled vegetation preparation into real isolated PBR baking."""
import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from mcpblender.texture_files import read_json
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_prepared_leaf_and_bark_bake_without_code(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5};pop=await wait(client,'plan_botanical_foliage',collection='Source',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='Source',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            # A nonuniform parent plus root rotation gives inherited shear.
            await tool(client,'create_primitive',name='SourcePlacement',kind='CUBE')
            await tool(client,'set_parent',name=tree['root'],parent='SourcePlacement',keep_world=True)
            await client.call_tool('set_object_transform',{'name':'SourcePlacement','scale':[2,1,.7]})
            await client.call_tool('set_object_transform',{'name':tree['root'],'rotation_euler':[.2,.1,.4],'location':[3,2,1]})
            tree=await tool(client,'inspect_botanical_tree',collection='Source')
            # Include procedural detail in both actual bakes; keep canonical tree
            # geometry untouched. The petiole uses the shared bark material without
            # BarkUV; explicitly permit generated copy-only coordinates for it.
            materials=await tool(client,'inspect_vegetation_materials',collection='Source')
            for material in materials['contract']['materials']:
                settings={'profile':'OAK_LEAF' if material['model']=='MANAGED_THIN_FOLIAGE' else 'OAK_BARK'}
                info=await tool(client,'inspect_botanical_surface',material=material['name'])
                await wait(client,'configure_botanical_surface',material=material['name'],settings=settings,expected_material=info['material_sha256'])
            args={'collection':'Source','assets':['wood','leaf-0'],'missing_uv_policy':'BAKE_LAYOUT'}
            plan=await tool(client,'inspect_vegetation_bake_source',**args);assert plan['can_prepare']
            state=await wait(client,'prepare_vegetation_bake',**args,expected_plan=plan['plan_sha256'],bake_collection='Bake')
            assert state['valid'] and set(state['components'])=={'wood','leaf-0'}
            source=await tool(client,'inspect_botanical_tree',collection='Source')
            assert source['tree_sha256']==tree['tree_sha256']
            await tool(client,'remove_botanical_tree',collection='Source',expected_tree=source['tree_sha256'])
            await client.call_tool('save_blend',{'path':'prepared.blend'})
            await client.call_tool('open_blend',{'path':'prepared.blend'})
            state=await tool(client,'inspect_vegetation_bake',bake_collection='Bake');assert state['valid']
            for role,row in state['components'].items():
                info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake']);assert info['complete'],info
                maps=['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']
                result=(await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'expected_bake':info['bake_sha256'],'directory':role,'maps':maps,'width':64,'height':64,'samples':2,'margin':1},'wait':True})).data
                assert result['live_scene_unchanged']
                assert (await tool(client,'inspect_vegetation_bake',bake_collection='Bake'))['preparation_sha256']==state['preparation_sha256']
                saved=read_json(root/'library'/role/'manifest.json');assert {m['map'] for m in saved['maps']}==set(maps)
                if role=='leaf-0':assert saved['material_adapters'] and saved['material_adapters'][0]['omitted_features']
                else:assert not saved['material_adapters']
                color=next(m for m in saved['maps'] if m['map']=='BASE_COLOR')['statistics']
                assert any(color['max'][i]-color['min'][i]>.005 for i in range(3)),color
                # Exclude unpainted background using the baked opacity map, so
                # a solid patch surrounded by black cannot pass as procedural detail.
                def pixels(kind):
                    image=root/'library'/role/next(m['path'] for m in saved['maps'] if m['map']==kind)
                    raw=subprocess.run(['ffmpeg','-v','error','-i',str(image),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout
                    assert len(raw)==64*64*3
                    return list(zip(raw[0::3],raw[1::3],raw[2::3]))
                painted=[v for v,a in zip(pixels('BASE_COLOR'),pixels('ALPHA')) if a[0]>250]
                assert len(painted)>100 and len(set(painted))>16
                assert max(max(v[i] for v in painted)-min(v[i] for v in painted) for i in range(3))>20
            if dest:=os.environ.get('MCPBLENDER_VEGETATION_BAKE_EVIDENCE_DIR'):
                shutil.copytree(root/'library',Path(dest),dirs_exist_ok=True)
            # Only independent file bundles remain after guarded copy cleanup.
            await tool(client,'remove_vegetation_bake',bake_collection='Bake',expected_preparation=state['preparation_sha256'])
            for role in ('wood','leaf-0'):
                await client.call_tool('open_blend',{'path':role+'/asset.blend'})
                assert (await tool(client,'validate_texture_bake',directory=role))['validated']
                obj=(await client.call_tool('get_object_info',{'name':state['components'][role]['name']})).data
                expected=state['source']['assets'][role]['mesh']['matrix']
                assert max(abs(a-b) for row,other in zip(obj['matrix_world'],expected) for a,b in zip(row,other))<1e-6
    asyncio.run(run())
