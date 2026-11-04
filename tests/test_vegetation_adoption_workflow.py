"""Code-disabled LOD PBR adoption, packed-image independence and field export."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_adopt_shared_leaf_and_reduced_wood_maps(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5,'variants':1};pop=await wait(client,'plan_botanical_foliage',collection='Source',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='Source',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            for m in (await tool(client,'inspect_vegetation_materials',collection='Source'))['contract']['materials']:
                info=await tool(client,'inspect_botanical_surface',material=m['name'])
                await wait(client,'configure_botanical_surface',material=m['name'],settings={'profile':'OAK_LEAF' if m['model']=='MANAGED_THIN_FOLIAGE' else 'OAK_BARK'},expected_material=info['material_sha256'])
            args={'collection':'Source','levels':[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0}]}
            plan=await wait(client,'inspect_botanical_lod_source',**args)
            profile=await wait(client,'create_botanical_lods',**args,expected_plan=plan['plan_sha256'],lod_collection='Lods',display_offset_m=[8,0,0])
            await tool(client,'remove_botanical_tree',collection='Source',expected_tree=tree['tree_sha256'])
            args={'lod_collection':'Lods','assets':['lod-1-wood','leaf-0'],'missing_uv_policy':'BAKE_LAYOUT'}
            plan=await tool(client,'inspect_vegetation_bake_source',**args)
            preparation=await wait(client,'prepare_vegetation_bake',**args,expected_plan=plan['plan_sha256'],bake_collection='Bake')
            entries=[]
            for role,row in preparation['components'].items():
                info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake']);assert info['bake_sha256']==row['initial_bake_sha256']
                await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'expected_bake':info['bake_sha256'],'directory':role,'width':64,'height':64,'samples':2,'margin':1,'maps':['BASE_COLOR','NORMAL','AO','ROUGHNESS','ALPHA']},'wait':True})
                entries.append({'asset':role,'directory':role})
            await client.call_tool('save_blend',{'path':'before-adoption.blend'})
            shutil.copytree(root/'library',root/'adoption-fixture')
            if dest:=os.environ.get('MCPBLENDER_VEGETATION_ADOPTION_EVIDENCE_DIR'):shutil.copytree(root/'adoption-fixture',Path(dest)/'before',dirs_exist_ok=True)
            args={'lod_collection':'Lods','bake_collection':'Bake','entries':entries}
            with pytest.raises(ToolError,match='accept_front_pbr'):
                await wait(client,'inspect_vegetation_bake_adoption',**args)
            args['accept_front_pbr']=True
            with pytest.raises(ToolError,match='budget'):
                await wait(client,'inspect_vegetation_bake_adoption',**args,max_texture_bytes=4096)
            plan=await wait(client,'inspect_vegetation_bake_adoption',**args)
            assert plan['rgba8_base_bytes']==2*5*64*64*4
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'adopt_vegetation_bakes',**args,expected_plan='0'*64)
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==profile['lods_sha256']
            state=await wait(client,'adopt_vegetation_bakes',**args,expected_plan=plan['plan_sha256']);assert state['valid'],state
            assert set(state['baked_materials'])=={'lod-1-wood','leaf-0'}
            # Revisions can reuse BakeUV without allocating another UV channel.
            # Private source images/AO groups must be copied so the preparation
            # does not create external users of profile-owned resources.
            revargs={'lod_collection':'Lods','assets':['leaf-0'],'uv_strategy':'EXISTING'}
            revplan=await tool(client,'inspect_vegetation_bake_source',**revargs)
            assert revplan['private_images_copied']==5
            revision=await wait(client,'prepare_vegetation_bake',**revargs,expected_plan=revplan['plan_sha256'],bake_collection='Revision')
            assert revision['valid'] and revision['components']['leaf-0']['prepared_mesh']['uv']==revplan['assets']['leaf-0']['mesh']['uv']
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==state['lods_sha256']
            copy=(await client.call_tool('get_object_info',{'name':revision['components']['leaf-0']['name']})).data
            old_bake=revision['components']['leaf-0']['initial_bake_sha256']
            await tool(client,'configure_shader_node',material=copy['materials'][0],node={'name':'Surface','type':'ShaderNodeBsdfPrincipled','inputs':[{'socket':'IOR','value':1.7}]})
            await tool(client,'configure_shader_node',material=copy['materials'][0],node={'name':'RevisionTint','type':'ShaderNodeMixRGB','properties':{'blend_type':'MULTIPLY'},'inputs':[{'socket':0,'value':1},{'socket':2,'value':[1,.2,.2,1]}]})
            await tool(client,'connect_shader_nodes',material=copy['materials'][0],replace_existing=True,links=[{'from_node':'BASE_COLOR','from_socket':'Color','to_node':'RevisionTint','to_socket':1},{'from_node':'RevisionTint','from_socket':'Color','to_node':'Surface','to_socket':'Base Color'}])
            changed=await tool(client,'inspect_vegetation_bake',bake_collection='Revision');assert changed['content_changed']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'refresh_vegetation_bake',bake_collection='Revision',expected_preparation=revision['preparation_sha256'])
            revision=await tool(client,'refresh_vegetation_bake',bake_collection='Revision',expected_preparation=changed['preparation_sha256'])
            assert revision['valid'] and revision['revision']==1 and revision['components']['leaf-0']['initial_bake_sha256']!=old_bake
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==state['lods_sha256']
            row=revision['components']['leaf-0'];info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake'])
            await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'expected_bake':info['bake_sha256'],'directory':'leaf-revision','width':64,'height':64,'samples':2,'margin':1,'maps':['BASE_COLOR','NORMAL','AO','ROUGHNESS','ALPHA']},'wait':True})
            oldmaps=json.loads((root/'library/leaf-0/manifest.json').read_text())['maps'];newmaps=json.loads((root/'library/leaf-revision/manifest.json').read_text())['maps']
            oldgreen=next(m for m in oldmaps if m['map']=='BASE_COLOR')['statistics']['mean'][1]
            newgreen=next(m for m in newmaps if m['map']=='BASE_COLOR')['statistics']['mean'][1];assert newgreen<oldgreen*.8
            replace={'lod_collection':'Lods','bake_collection':'Revision','entries':[{'asset':'leaf-0','directory':'leaf-revision'}],'replace_existing':True,'max_texture_bytes':plan['rgba8_base_bytes']}
            with pytest.raises(ToolError,match='accept_front_pbr'):await wait(client,'inspect_vegetation_bake_adoption',**replace)
            replace['accept_front_pbr']=True;newplan=await wait(client,'inspect_vegetation_bake_adoption',**replace)
            assert newplan['replaced_assets']==['leaf-0'] and newplan['rgba8_base_bytes']==plan['rgba8_base_bytes']
            oldrecord=state['baked_materials']['leaf-0'];state=await wait(client,'adopt_vegetation_bakes',**replace,expected_plan=newplan['plan_sha256'])
            assert state['valid'] and state['baked_materials']['leaf-0']['revision']==2
            assert state['baked_materials']['leaf-0']['previous_adoption_sha256']==oldrecord['adoption_sha256']
            assert state['baked_materials']['leaf-0']['inherited_material_adapters'] and state['baked_materials']['leaf-0']['inherited_sampling_changes']
            assert state['lods_sha256']==(await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']
            await client.call_tool('save_blend',{'path':'tinted.blend'})
            # An original retained preparation remains a valid source ancestor,
            # even after a newer preparation was made from packed PBR materials.
            restore={'lod_collection':'Lods','bake_collection':'Bake','entries':[{'asset':'leaf-0','directory':'leaf-0'}],'accept_front_pbr':True}
            with pytest.raises(ToolError,match='replace_existing'):await wait(client,'inspect_vegetation_bake_adoption',**restore)
            restore['replace_existing']=True;restoreplan=await wait(client,'inspect_vegetation_bake_adoption',**restore)
            state=await wait(client,'adopt_vegetation_bakes',**restore,expected_plan=restoreplan['plan_sha256'])
            assert state['valid'] and state['baked_materials']['leaf-0']['revision']==3
            assert next(m['sha256'] for m in state['baked_materials']['leaf-0']['maps'] if m['map']=='BASE_COLOR')==next(m['sha256'] for m in oldrecord['maps'] if m['map']=='BASE_COLOR')
            await tool(client,'remove_vegetation_bake',bake_collection='Revision',expected_preparation=revision['preparation_sha256'])
            assert (await tool(client,'inspect_vegetation_bake',bake_collection='Bake'))['preparation_sha256']==preparation['preparation_sha256']
            # Remove the preparation and all external texture files. Owned packed
            # images, original UVs, wind fields and shared prototype identity survive.
            await tool(client,'remove_vegetation_bake',bake_collection='Bake',expected_preparation=preparation['preparation_sha256'])
            for entry in entries:shutil.rmtree(root/'library'/entry['directory'])
            shutil.rmtree(root/'library/leaf-revision')
            await client.call_tool('save_blend',{'path':'adopted.blend'})
            await client.call_tool('open_blend',{'path':'adopted.blend'})
            state=await tool(client,'inspect_botanical_lods',lod_collection='Lods');assert state['valid']
            # Adopted profiles automatically retain material and optical-loss
            # witnesses even with the default export material_mode.
            exported=await wait(client,'export_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'],directory='delivery')
            assert len(exported['proof']['assets'])==5 and exported['proof']['shared_leaf_templates']==1
            semantic=json.loads((root/'library/delivery/semantics.json').read_text());manifest=json.loads((root/'library/delivery/manifest.json').read_text())
            assert semantic['baked_materials']['leaf-0']['inherited_material_adapters']
            for role in ('leaf-0','lod-1-wood'):
                delivery=manifest['material_delivery'][role]
                assert len(delivery['images'])>=3 and all(m['encoded'].get('occlusionTexture') and m['encoded'].get('normalTexture') for m in delivery['materials'])
                assert len(semantic['baked_materials'][role]['uv_witness'])>=2
            if dest:=os.environ.get('MCPBLENDER_VEGETATION_ADOPTION_EVIDENCE_DIR'):shutil.copytree(root/'library',Path(dest),dirs_exist_ok=True)
            await tool(client,'remove_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'])
            assert (await wait(client,'validate_botanical_lod_bundle',directory='delivery'))['format']=='mcpblender-vegetation-lod-bundle-v1'
    asyncio.run(run())

    # Exercise rollback after allocation and after actual swaps in a disposable
    # native process, using the same real worker outputs and native snapshot.
    script=root/'fault.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nROOT='+repr(str(root/'adoption-fixture'))+'\n'+r'''
import bpy
from mcpblender.blender import vegetation_adoption as adoption,vegetation_lods as lods,bridge
from mcpblender.vegetation_bake_contracts import Adoption
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.wm.open_mainfile(filepath=ROOT+'/before-adoption.blend',load_ui=False,use_scripts=False)
p=Adoption(lod_collection='Lods',bake_collection='Bake',entries=[{'asset':r,'directory':ROOT+'/'+r} for r in ('lod-1-wood','leaf-0')],accept_front_pbr=True).model_dump()
plan=adoption.plan(p)[-1];p['expected_plan']=plan['plan_sha256'];before=set(bpy.data.user_map());guard=lods.inspect(p)[-1]['lods_sha256'];names={v:v.name for v in before}
calls=[0]
def cancel(v):
    if v.get('phase')=='packing vegetation PBR maps':calls[0]+=1
    if calls[0]==2:raise bridge.OperationCancelled('cancel map packing')
bridge.report_progress=cancel
try:adoption.adopt(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Map packing cancellation missed')
bridge.report_progress=lambda v:None
assert set(bpy.data.user_map())==before and lods.inspect(p)[-1]['lods_sha256']==guard
inspect=lods.inspect
def fail_after_swap(p,**kwargs):
    result=inspect(p,**kwargs)
    if result[-1]['baked_materials']:raise RuntimeError('fault after swaps')
    return result
lods.inspect=fail_after_swap
try:adoption.adopt(p)
except RuntimeError as e:assert str(e)=='fault after swaps'
else:raise AssertionError('Post-swap verification fault missed')
lods.inspect=inspect
assert set(bpy.data.user_map())==before and lods.inspect(p)[-1]['lods_sha256']==guard
assert all(v.name==name for v,name in names.items())
# Source file edits are refused before staging IDs.
from pathlib import Path
image=Path(ROOT)/'leaf-0/textures/normal.png';original=image.read_bytes();image.write_bytes(original+b'changed')
try:adoption.plan(p)
except ValueError as e:assert 'changed' in str(e)
else:raise AssertionError('Modified bake adopted')
assert set(bpy.data.user_map())==before
# External image references block whole-profile cleanup; packed resources are
# private to the adopted profile and do not depend on preparation lifetimes.
image.write_bytes(original)
state=adoption.adopt(p);assert state['valid']
# Replacement rollback protects existing maps too, then repeated replacement
# retires obsolete private resources without growing the owned ID inventory.
p['replace_existing']=True;plan=adoption.plan(p)[-1];p['expected_plan']=plan['plan_sha256']
ids=set(bpy.data.user_map());guard=lods.inspect(p)[-1]['lods_sha256'];count=len(lods.inspect(p)[1])
def fail_replacement(p,**kwargs):
    result=inspect(p,**kwargs)
    if any(r.get('revision',1)>1 for r in result[-1]['baked_materials'].values()):raise RuntimeError('replacement fault')
    return result
lods.inspect=fail_replacement
try:adoption.adopt(p)
except RuntimeError as e:assert str(e)=='replacement fault'
else:raise AssertionError('Replacement rollback missed')
lods.inspect=inspect
assert set(bpy.data.user_map())==ids and lods.inspect(p)[-1]['lods_sha256']==guard
for revision in (2,3):
    p['expected_plan']=adoption.plan(p)[-1]['plan_sha256'];state=adoption.adopt(p)
    assert state['valid'] and all(r['revision']==revision for r in state['baked_materials'].values())
    assert len(lods.inspect(p)[1])==count and state['lods_sha256']==lods.inspect(p)[-1]['lods_sha256']
col,owned,meta,state=lods.inspect(p);private=next(v for v in owned if isinstance(v,bpy.types.Image))
foreign=bpy.data.materials.new('Foreign');foreign.use_nodes=True;foreign.node_tree.nodes.new('ShaderNodeTexImage').image=private
state=lods.inspect(p)[-1];assert state['ownership_blockers']
try:adoption.plan(p)
except ValueError as e:assert 'Valid unchanged' in str(e)
else:raise AssertionError('Externally referenced maps replaced')
try:lods.dispatch('remove_botanical_lods',{'lod_collection':'Lods','expected_lods':state['lods_sha256']})
except ValueError as e:assert 'ownership' in str(e)
else:raise AssertionError('External image dependency deleted')
bpy.data.materials.remove(foreign)
state=lods.inspect(p)[-1];assert state['valid']
result=lods.dispatch('remove_botanical_lods',{'lod_collection':'Lods','expected_lods':state['lods_sha256']})
assert result['owned_baked_materials_removed']==2
from mcpblender.blender import vegetation_bake as prep
assert prep.inspect({'bake_collection':'Bake'})[-1]['valid']
print('ADOPTION_ROLLBACK_OK')
''')
    if dest:=os.environ.get('MCPBLENDER_VEGETATION_ADOPTION_EVIDENCE_DIR'):shutil.copy2(script,Path(dest)/'fault.py')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'ADOPTION_ROLLBACK_OK' in result.stdout
