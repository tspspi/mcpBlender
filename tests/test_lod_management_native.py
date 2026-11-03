"""Native stale-source rebuild, shared data retention and handoff rollback."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_lod_rebuild_remove_ownership_and_handoff_rollback(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from mathutils import Matrix
from mcpblender.blender import lods,lod_management as manager,bridge
from mcpblender.lod_contracts import Generate,Rebuild
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(4,0,2));source=bpy.context.object;source.name='Source'
plan=lods.inspect_source({'name':'Source'})
p=Generate.model_validate({'name':'Source','chain':'Asset','expected_source':plan['source_sha256'],'levels':[{'triangle_budget':250},{'triangle_budget':120}],'max_relative_error':.3,'error_samples':64}).model_dump(exclude_none=True)
first=lods.generate(p);old_id=json.loads(bpy.data.collections['Asset'][lods.META])['id']
legacy=json.loads(bpy.data.collections['Asset'][lods.META]);legacy.pop('generation_recipe');bpy.data.collections['Asset'][lods.META]=json.dumps(legacy)
assert manager.inventory({'chain':'Asset'})[-1]['suggested_rebuild']['levels'][0]['triangle_budget']==250
first=lods.inspect_chain({'chain':'Asset'})
lods.activate({'chain':'Asset','expected_chain':first['chain_sha256'],'level':2})
root=bpy.data.objects['Asset_Root'];root.location.x+=3;bpy.context.view_layer.update();matrix=root.matrix_world.copy()
# Keep nested collection links and authored static root parenting on rebuild.
container=bpy.data.collections.new('Container');bpy.context.scene.collection.children.link(container)
collection=bpy.data.collections['Asset'];container.children.link(collection);bpy.context.scene.collection.children.unlink(collection)
parent=bpy.data.objects.new('PlacementParent',None);bpy.context.scene.collection.objects.link(parent);parent.location=(10,0,0);parent.rotation_euler.z=.25
root.parent=parent;root.matrix_world=matrix;bpy.context.view_layer.update();matrix=root.matrix_world.copy()
constraint=root.constraints.new('LIMIT_LOCATION')
controlled=manager.inventory({'chain':'Asset'})[-1];assert controlled['can_remove'] and not controlled['can_rebuild'] and controlled['rebuild_blockers']
root.constraints.remove(constraint)
# An outside object uses an old level's mesh: keep that data after replacement.
mesh=bpy.data.objects['Asset_LOD1'].data;outside=bpy.data.objects.new('SharedMeshUser',mesh);bpy.context.scene.collection.objects.link(outside)
state=manager.inventory({'chain':'Asset'})[-1];assert state['can_rebuild'] and mesh.name in state['preserved_shared_meshes'],state
# Source hiding is reversible if cancellation arrives after the flag mutation.
count=0
def hide_cancel():
    global count
    count+=1
    if count==2:raise bridge.OperationCancelled('visibility rollback')
bridge.check_cancelled=hide_cancel
try:manager.source_visibility({'chain':'Asset','expected_management':state['management_sha256'],'hide_viewport':True,'hide_render':True})
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected source visibility rollback')
bridge.check_cancelled=lambda:None
assert not source.hide_viewport and not source.hide_render
assert manager.inventory({'chain':'Asset'})[-1]['management_sha256']==state['management_sha256']
# An instancer is an external native reference to the owned collection.
instance=bpy.data.objects.new('ForeignInstance',None);instance.instance_type='COLLECTION';instance.instance_collection=bpy.data.collections['Asset'];bpy.context.scene.collection.objects.link(instance)
assert not manager.inventory({'chain':'Asset'})[-1]['can_remove']
bpy.data.objects.remove(instance,do_unlink=True)
# Native object references prevent deleting/replacing their targets.
constraint=outside.constraints.new('COPY_LOCATION');constraint.target=bpy.data.objects['Asset_LOD2']
blocked=manager.inventory({'chain':'Asset'})[-1];assert not blocked['can_remove'] and any('references' in b for b in blocked['blockers'])
outside.constraints.remove(constraint)
# Source changes make the old snapshot stale, but rebuilding from it stays owned.
for v in source.data.vertices:v.co.z*=1.2
source.data.update();bpy.context.view_layer.update()
state=manager.inventory({'chain':'Asset'})[-1];assert state['source_stale_or_unavailable'] and state['can_rebuild']
recipe=state['suggested_rebuild'];recipe['levels']=[{'triangle_budget':220},{'triangle_budget':100}]
args=Rebuild.model_validate(recipe|{'expected_management':state['management_sha256']}).model_dump(exclude_none=True)
# Select an old LOD: rollback and successful replacement must preserve its role.
for obj in bpy.context.selected_objects:obj.select_set(False)
active=bpy.data.objects['Asset_LOD2'];active.select_set(True);bpy.context.view_layer.objects.active=active
before=set(bpy.data.user_map());guard=state['management_sha256'];phase={}
def progress(value):phase.update(value)
for boundary in ('verified replacement before LOD handoff','verified LOD handoff before deletion'):
    phase.clear()
    def cancel():
        if phase.get('phase')==boundary:raise bridge.OperationCancelled('handoff rollback')
    bridge.check_cancelled=cancel;bridge.report_progress=progress
    try:manager.rebuild(args)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Expected staged replacement cancellation')
    assert set(bpy.data.user_map())==before
    assert manager.inventory({'chain':'Asset'})[-1]['management_sha256']==guard
    assert bpy.context.view_layer.objects.active==active and active.select_get()
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
rebuilt=manager.rebuild(args);assert rebuilt['valid'] and not rebuilt['source_stale_or_unavailable'],rebuilt
assert rebuilt['replaced_id']==old_id and bpy.data.objects['Asset_Root'].matrix_world==matrix
assert bpy.data.objects['Asset_Root'].parent==parent and 'Asset' in container.children
assert rebuilt['levels'][2]['triangles']<=100 and not bpy.data.objects['Asset_LOD2'].hide_viewport
assert bpy.context.view_layer.objects.active==bpy.data.objects['Asset_LOD2'] and bpy.data.objects['Asset_LOD2'].select_get()
assert outside.data==mesh and mesh.name in bpy.data.meshes
assert not any(o.name.startswith(('mcp_LOD_old_','mcp_LOD_rebuild_')) for o in bpy.data.objects)
assert source.name in bpy.data.objects and len(source.data.vertices)==266
# Shrinking the number of levels keeps an available representation visible.
state=manager.inventory({'chain':'Asset'})[-1]
smaller=Rebuild.model_validate(state['suggested_rebuild']|{'levels':[{'triangle_budget':80}],'expected_management':state['management_sha256']}).model_dump(exclude_none=True)
short=manager.rebuild(smaller);assert len(short['levels'])==2 and not bpy.data.objects['Asset_LOD1'].hide_viewport
# Explicit reset opts out of old placement and collection/render flags.
bpy.data.collections['Asset'].hide_render=True;bpy.data.objects['Asset_Root'].hide_render=True
state=manager.inventory({'chain':'Asset'})[-1]
reset=Rebuild.model_validate(state['suggested_rebuild']|{'expected_management':state['management_sha256'],'preserve_placement':False,'preserve_visibility':False}).model_dump(exclude_none=True)
manager.rebuild(reset)
assert bpy.data.objects['Asset_Root'].parent is None and not bpy.data.objects['Asset_Root'].hide_render and not bpy.data.collections['Asset'].hide_render
assert all(abs(bpy.data.objects['Asset_Root'].matrix_world[i][j]-source.matrix_world[i][j])<1e-6 for i in range(4) for j in range(4))
fake=bpy.data.objects['Asset_LOD0'].data;fake.use_fake_user=True
# Editing owned level geometry invalidates its contents but not deletion ownership.
bpy.data.objects['Asset_LOD1'].data.vertices[0].co.x+=.1
state=manager.inventory({'chain':'Asset'})[-1];assert state['can_remove'] and state['content_issues']
# Stale management guard refuses before deleting any data.
try:manager.remove({'chain':'Asset','expected_management':guard})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Expected stale management refusal')
result=manager.remove({'chain':'Asset','expected_management':state['management_sha256']})
assert 'Asset' not in bpy.data.collections and not any(o.name.startswith('Asset_') for o in bpy.data.objects)
assert source.name in bpy.data.objects and outside.data==mesh and mesh.name in bpy.data.meshes
assert fake.name in bpy.data.meshes and fake.use_fake_user
# Morph handoff cancellation must remove temporary Keys as well as meshes.
source.shape_key_add(name='Basis');tip=source.shape_key_add(name='Tip');tip.data[0].co.z+=.15;tip.value=.3
morph_source=lods.inspect_source({'name':'Source','deformation':'MORPH'});base_ids=set(bpy.data.user_map())
recipe=Generate.model_validate({'name':'Source','deformation':'MORPH','chain':'MorphAsset','expected_source':morph_source['source_sha256'],'levels':[{'triangle_budget':220},{'triangle_budget':100}],'max_relative_error':.3,'max_pose_error':.3,'error_samples':64,'pose_frames':[1,5,9]}).model_dump(exclude_none=True)
lods.generate(recipe);state=manager.inventory({'chain':'MorphAsset'})[-1];assert state['can_rebuild'],state
args=Rebuild.model_validate(state['suggested_rebuild']|{'expected_management':state['management_sha256']}).model_dump(exclude_none=True)
before_morph=set(bpy.data.user_map());phase.clear();bridge.report_progress=progress
def cancel_morph():
    if phase.get('phase')=='verified LOD handoff before deletion':raise bridge.OperationCancelled('morph handoff')
bridge.check_cancelled=cancel_morph
try:manager.rebuild(args)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected morph handoff cancellation')
assert set(bpy.data.user_map())==before_morph
assert manager.inventory({'chain':'MorphAsset'})[-1]['management_sha256']==state['management_sha256']
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
manager.rebuild(args);state=manager.inventory({'chain':'MorphAsset'})[-1]
manager.remove({'chain':'MorphAsset','expected_management':state['management_sha256']})
assert set(bpy.data.user_map())==base_ids
assert lods.inspect_source({'name':'Source','deformation':'MORPH'})['source_sha256']==morph_source['source_sha256']
print('LOD_MANAGEMENT_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'LOD_MANAGEMENT_NATIVE_OK' in result.stdout
