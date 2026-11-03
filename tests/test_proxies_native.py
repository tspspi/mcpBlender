"""Native grouping, conservative solids, shadow budgets and owned rollback."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_proxy_groups_solids_budgets_freshness_and_cleanup(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,bmesh,json
from mathutils import Vector
from mcpblender.blender import proxies as p,bridge
from mcpblender.proxy_contracts import Source,Generate
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_cube_add(location=(4,0,1));cube=bpy.context.object;cube.name='A'
bpy.ops.mesh.primitive_cube_add(location=(8,0,1));second=bpy.context.object;second.name='B';second.scale=(-1,2,1)
# Guarded visibility preserves source state on cancellation and refuses animation.
state=p.render_visibility({'name':'A'});count=0
def visibility_cancel():
    global count
    count+=1
    if count==2:raise bridge.OperationCancelled('after visibility edit')
bridge.check_cancelled=visibility_cancel
try:p.configure_visibility({'name':'A','expected_visibility':state['visibility_sha256'],'visible_shadow':False})
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected visibility rollback')
assert p.render_visibility({'name':'A'})['visibility_sha256']==state['visibility_sha256']
bridge.check_cancelled=lambda:None
cube.keyframe_insert('hide_render',frame=1)
state=p.render_visibility({'name':'A'});assert 'hide_render' in state['animated_fields']
try:p.configure_visibility({'name':'A','expected_visibility':state['visibility_sha256'],'hide_render':True})
except ValueError as e:assert 'animated' in str(e)
else:raise AssertionError('Expected animated visibility refusal')
base=Source.model_validate({'objects':['A','B'],'method':'BOX','grouping':'COMBINED','padding':.1}).model_dump()
before=set(bpy.data.user_map());source=p.inspect_source(base);assert source['proxy_count']==1 and source['vertices']==16
assert set(bpy.data.user_map())==before
args=Generate.model_validate(base|{'collection':'Box','expected_source':source['source_sha256']}).model_dump()
phase={}
def progress(v):phase.update(v)
for when in ('generated','published'):
    phase.clear()
    def cancel():
        if (when=='generated' and phase.get('phase')=='verified asset proxy') or (when=='published' and 'Box' in bpy.context.scene.collection.children):raise bridge.OperationCancelled('owned rollback')
    bridge.check_cancelled=cancel;bridge.report_progress=progress
    try:p.generate(args)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Expected cancellation')
    assert set(bpy.data.user_map())==before
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
box=p.generate(args);assert box['valid'] and box['source_matches'] and box['total_proxies']==1
record=box['proxies'][0];obj=bpy.data.objects[record['name']]
assert all(abs(a-b)<1e-5 for a,b in zip(record['mesh']['bounds']['min'],[2.9,-2.1,-.1]))
assert abs(record['volume']-6.2*4.2*2.2)<1e-4 and obj.hide_render
assert record['quality']['max_sampled_outside_distance']<1e-5
# A convex envelope of separated components fills the gap; per-source grouping
# keeps each collider separate. The measured surface error exposes this choice.
settings=Source.model_validate({'objects':['A','B'],'method':'CONVEX_HULL','grouping':'COMBINED'}).model_dump()
plan=p.inspect_source(settings);hull=p.generate(Generate.model_validate(settings|{'collection':'Hull','expected_source':plan['source_sha256']}).model_dump())
assert hull['valid'] and abs(hull['proxies'][0]['volume']-40)<1e-4
assert hull['proxies'][0]['quality']['max_sampled_outside_distance']<1e-5
bm=bmesh.new();bm.from_mesh(bpy.data.objects[hull['proxies'][0]['name']].data)
assert all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True)>0;bm.free()
settings['grouping']='PER_SOURCE';plan=p.inspect_source(settings)
separate=p.generate(Generate.model_validate(settings|{'collection':'Separate','expected_source':plan['source_sha256']}).model_dump())
assert separate['total_proxies']==2
# Reject a quality budget and a partial output-name collision without leaked IDs.
settings['max_relative_error']=0;settings['grouping']='COMBINED';plan=p.inspect_source(settings);ids=set(bpy.data.user_map())
try:p.generate(Generate.model_validate(settings|{'collection':'TooLoose','expected_source':plan['source_sha256']}).model_dump())
except ValueError as e:assert 'surface error' in str(e)
else:raise AssertionError('Expected approximation refusal')
assert set(bpy.data.user_map())==ids
settings['max_relative_error']=None;settings['grouping']='PER_LEAF';plan=p.inspect_source(settings)
collision=bpy.data.objects.new('Conflict_0001',None);bpy.context.scene.collection.objects.link(collision);ids=set(bpy.data.user_map())
try:p.generate(Generate.model_validate(settings|{'collection':'Conflict','expected_source':plan['source_sha256']}).model_dump())
except ValueError as e:assert 'already exists' in str(e)
else:raise AssertionError('Expected name conflict')
assert set(bpy.data.user_map())==ids
# Flat hulls must refuse and clean all owned output.
bpy.ops.mesh.primitive_plane_add();plane=bpy.context.object;plane.name='Flat'
flat=Source.model_validate({'objects':['Flat']}).model_dump();flatplan=p.inspect_source(flat);ids=set(bpy.data.user_map())
try:p.generate(Generate.model_validate(flat|{'collection':'FlatHull','expected_source':flatplan['source_sha256']}).model_dump())
except (ValueError,RuntimeError):pass
else:raise AssertionError('Expected flat volume refusal')
assert set(bpy.data.user_map())==ids
# Budgeted shadow mesh retains material and UV, without camera/diffuse visibility.
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(0,0,2));sphere=bpy.context.object;sphere.name='ShadowSource'
mat=bpy.data.materials.new('SharedShadow');sphere.data.materials.append(mat)
shadow=Source.model_validate({'objects':['ShadowSource'],'purpose':'SHADOW','method':'DECIMATE','triangle_budget':120,'max_relative_error':.2}).model_dump()
plan=p.inspect_source(shadow);ids=set(bpy.data.user_map());result=p.generate(Generate.model_validate(shadow|{'collection':'Shadow','expected_source':plan['source_sha256']}).model_dump())
record=result['proxies'][0];out=bpy.data.objects[record['name']]
assert record['mesh']['triangles']<=120 and record['mesh']['uv_maps'] and out.data.materials[0]==mat
assert out.visible_shadow and not any(getattr(out,key) for key in p.RAYS if key!='visible_shadow')
# All transient decimation objects and meshes were discarded.
assert len(set(bpy.data.user_map())-ids)==3
# Render in an isolated scene: only the proxy casts a displaced shadow, with no
# original sphere linked and no camera-visible proxy silhouette at image center.
from pathlib import Path
proof=bpy.data.scenes.new('ShadowProof');proof.render.engine='CYCLES';proof.cycles.device='CPU';proof.cycles.samples=16
proof.render.resolution_x=128;proof.render.resolution_y=128;proof.render.resolution_percentage=100
proof.view_settings.view_transform='Standard';proof.render.image_settings.file_format='PNG'
proof.world=bpy.data.worlds.new('ProofWorld');proof.world.use_nodes=True;proof.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.3,.3,.3,1)
plane_mesh=bpy.data.meshes.new('ProofGroundMesh');plane_mesh.from_pydata([(-6,-6,0),(6,-6,0),(6,6,0),(-6,6,0)],[],[(0,1,2,3)])
ground=bpy.data.objects.new('ProofGround',plane_mesh);proof.collection.objects.link(ground)
shadow_copy=bpy.data.objects.new('ProofShadow',out.data);proof.collection.objects.link(shadow_copy)
for key in p.RAYS:setattr(shadow_copy,key,getattr(out,key))
sun_data=bpy.data.lights.new('ProofSun','SUN');sun_data.energy=3;sun=bpy.data.objects.new('ProofSun',sun_data);proof.collection.objects.link(sun);sun.rotation_euler=(0,.9,0)
cam_data=bpy.data.cameras.new('ProofCamera');cam_data.type='ORTHO';cam_data.ortho_scale=10
cam=bpy.data.objects.new('ProofCamera',cam_data);proof.collection.objects.link(cam);cam.location=(0,0,10);cam.rotation_euler=(0,0,0);proof.camera=cam
folder=Path(__file__).parent
pixels=[]
for label,hidden in [('shadow-on',False),('shadow-off',True)]:
    shadow_copy.hide_render=hidden;proof.render.filepath=str(folder/(label+'.png'))
    bpy.ops.render.render(write_still=True,scene=proof.name)
    image=bpy.data.images.load(proof.render.filepath,check_existing=False);pixels.append(list(image.pixels));bpy.data.images.remove(image)
on,off=pixels;assert len(on)==128*128*4
luma=lambda v,i:sum(v[i:i+3])/3
changed=sum(luma(off,i)-luma(on,i)>.05 for i in range(0,len(on),4))
assert changed>100,changed
assert max(abs(luma(off,(y*128+x)*4)-luma(on,(y*128+x)*4)) for y in range(60,68) for x in range(60,68))<.02
(folder/'shadow-render-proof.json').write_text(json.dumps({'darkened_pixels':changed,'resolution':[128,128],'camera_center_unchanged':True}))
shadow_copy.hide_render=False
sphere.location.x+=1;bpy.context.view_layer.update();fresh=p.inspect({'collection':'Shadow'})
assert fresh['valid'] and not fresh['source_matches']
child=bpy.data.objects.new('Dependent',None);bpy.context.scene.collection.objects.link(child);child.parent=out
try:p.remove({'collection':'Shadow','expected_proxy':fresh['proxy_sha256']})
except ValueError as e:assert 'references' in str(e)
else:raise AssertionError('Expected dependent refusal')
bpy.data.objects.remove(child,do_unlink=True);fresh=p.inspect({'collection':'Shadow'});p.remove({'collection':'Shadow','expected_proxy':fresh['proxy_sha256']})
assert 'Shadow' not in bpy.data.collections and sphere.name in bpy.data.objects and mat.name in bpy.data.materials
bpy.ops.wm.save_as_mainfile(filepath=str(__import__('pathlib').Path(__file__).parent/'proxies-native.blend'))
print('PROXIES_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PROXIES_NATIVE_OK' in result.stdout
    if evidence:=os.environ.get('MCPBLENDER_PROXY_EVIDENCE_DIR'):
        out=Path(evidence);out.mkdir(parents=True,exist_ok=True);
        for name in ('proxies-native.blend','shadow-on.png','shadow-off.png','shadow-render-proof.json'):shutil.copy2(tmp_path/name,out/name)
