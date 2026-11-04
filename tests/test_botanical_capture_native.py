"""Independent evaluated framing witness and capture rollback boundaries."""
import subprocess
from pathlib import Path
from test_botanical_native import pytestmark


def test_capture_bounds_transforms_guards_and_rollback(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'capture-probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,math
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view
from mcpblender.blender import botanical_trees as trees,botanical_foliage as foliage,botanical_capture as capture,bridge,render_batches
from mcpblender.botanical_contracts import Plan,Create
from mcpblender.foliage_contracts import LayoutPlan,Configure
from mcpblender.botanical_capture_contracts import Source
from mcpblender.card_views import DIRECTIONS
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe=Plan(recipe={'attractors':64,'iterations':4,'node_budget':128}).model_dump()
model=trees.plan(recipe);state=trees.create(Create(**recipe,collection='Trial',expected_model=model['model_sha256']).model_dump())
f=LayoutPlan(collection='Trial',foliage={'shoots_per_bud':2,'attachment_nodes':4}).model_dump();layout=foliage.dispatch('plan_botanical_foliage',f)
state=foliage.dispatch('configure_botanical_foliage',Configure(**f,expected_tree=state['tree_sha256'],expected_foliage=layout['foliage_sha256']).model_dump())
col,root,members=trees.inventory({'collection':'Trial'})[:3]
parent=bpy.data.objects.new('Placement',None);bpy.context.scene.collection.objects.link(parent);parent.location=(4,-3,1);parent.rotation_euler=(.2,.3,.4);parent.scale=(1.2,)*3
root.parent=parent;root.location=(2,1,0);root.rotation_euler=(.1,.2,.5);root.scale=(1.4,)*3
bpy.context.view_layer.update()
p=Source(collection='Trial',views=list(DIRECTIONS),resolution=64).model_dump();values,_,plan=capture.source(p)
original=trees.inspect(p)['tree_sha256'];ids=set(bpy.data.user_map());names={v:v.name for v in ids}
# Enumerate actual evaluated instance vertices independently; no analytical box
# implementation is reused by this reference witness.
inverse=Matrix(plan['source_root_matrix_world']).inverted();points=[]
wood=members[0];roles=foliage.resolve_roles(values[-1]['foliage']);objects={wood,roles['so'],*(roles['lo'+str(i)] for i in range(values[-1]['foliage']['recipe']['variants']))}
for inst in bpy.context.evaluated_depsgraph_get().object_instances:
    if inst.object.original not in objects:continue
    for vertex in inst.object.data.vertices:points.append(inst.matrix_world@vertex.co)
assert points
bounds=plan['bounds_root_local_m']
for world in points:
    local=inverse@world
    assert all(bounds['min'][i]-1e-5<=local[i]<=bounds['max'][i]+1e-5 for i in range(3))
for view in plan['views']:
    data=bpy.data.cameras.new('Witness');cam=bpy.data.objects.new('Witness',data);bpy.context.scene.collection.objects.link(cam);cam.matrix_world=Matrix(view['matrix_world']);data.type='ORTHO';data.ortho_scale=view['ortho_scale'];data.clip_start=view['clip_start'];data.clip_end=view['clip_end']
    bpy.context.scene.render.resolution_x=64;bpy.context.scene.render.resolution_y=64;bpy.context.scene.render.resolution_percentage=100;bpy.context.view_layer.update()
    for point in points:
        ndc=world_to_camera_view(bpy.context.scene,cam,point)
        assert 0<ndc.x<1 and 0<ndc.y<1 and data.clip_start<ndc.z<data.clip_end,(view,ndc)
    bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(data)
assert set(bpy.data.user_map())==ids
# Hide the entire source, keeping its static authored hierarchy. Planning must
# not alter any flags or depend on a visible/evaluated world matrix cache.
col.hide_viewport=True;col.hide_render=True
hidden=capture.source(p)[-1];assert hidden['source_root_matrix_world']==plan['source_root_matrix_world']
original=trees.inspect(p)['tree_sha256']
# No scene/ID/flag leak after snapshot write fails, after completed snapshot and
# during cooperative analytical bounds cancellation.
launch=render_batches.launch
for write in (False,True):
    def fail(params,**kw):
        if write:kw['snapshot_writer'](OUTPUT+'/isolated.blend')
        raise RuntimeError('injected capture failure')
    render_batches.launch=fail
    try:capture.capture(p|{'expected_capture':hidden['capture_sha256'],'directory':OUTPUT+'/job','threads':2,'max_bytes':2**30,'timeout_seconds':60})
    except RuntimeError as exc:assert 'injected' in str(exc)
    else:raise AssertionError('No injected failure')
    assert set(bpy.data.user_map())==ids and all(v.name==name for v,name in names.items())
    assert trees.inspect(p)['tree_sha256']==original and col.hide_viewport and col.hide_render
render_batches.launch=launch

def stop(value):
    if value.get('phase')=='bounding native tree instances':raise bridge.OperationCancelled('bounds cancelled')
bridge.report_progress=stop
try:capture.source(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Cancellation ignored')
bridge.report_progress=lambda v:None
assert set(bpy.data.user_map())==ids and trees.inspect(p)['tree_sha256']==original
material=members[0].data.materials[0];material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.123
try:capture.capture(p|{'expected_capture':hidden['capture_sha256']})
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Shader edit did not invalidate source plan')
# Native color ramp internals and external shader-coordinate objects also enter
# the resource guard, beyond primitive socket/property records.
rgb=material.node_tree.nodes.new('ShaderNodeRGB');before=capture.source(p)[-1]['capture_sha256'];rgb.outputs[0].default_value=(.2,.3,.4,1)
assert capture.source(p)[-1]['capture_sha256']!=before
node=material.node_tree.nodes.new('ShaderNodeValToRGB');before=capture.source(p)[-1]['capture_sha256'];node.color_ramp.elements[0].color=(.1,.2,.3,1)
assert capture.source(p)[-1]['capture_sha256']!=before
coord=bpy.data.objects.new('ShaderCoordinates',None);bpy.context.scene.collection.objects.link(coord)
tex=material.node_tree.nodes.new('ShaderNodeTexCoord');tex.object=coord
before=capture.source(p)[-1]['capture_sha256'];coord.location.x=2
assert capture.source(p)[-1]['capture_sha256']!=before
bpy.data.objects.remove(coord,do_unlink=True)
before=capture.source(p)[-1]['capture_sha256'];roles['po'].visible_shadow=False
assert capture.source(p)[-1]['capture_sha256']!=before
output=next(n for n in material.node_tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial');disp=material.node_tree.nodes.new('ShaderNodeDisplacement');material.node_tree.links.new(disp.outputs['Displacement'],output.inputs['Displacement'])
try:capture.source(p)
except ValueError as exc:assert 'displacement' in str(exc)
else:raise AssertionError('Unbounded material displacement accepted')
material.node_tree.nodes.remove(disp)
# Effective object-linked overrides must enter both field bindings and guards.
slot=members[0].material_slots[0];original_material=slot.material;original_link=slot.link
other=bpy.data.materials.new('ObjectLinkedCaptureMaterial');other.use_nodes=True
slot.link='OBJECT';slot.material=other
fields=capture.source(p|{'material_fields':True})[-1]
assert other.name in {m['material'] for m in fields['material_fields']['materials']}
slot.material=original_material
assert capture.source(p|{'material_fields':True})[-1]['capture_sha256']!=fields['capture_sha256']
slot.link=original_link;bpy.data.materials.remove(other)
root.scale.x=2
try:capture.source(p)
except ValueError as exc:assert 'uniform' in str(exc)
else:raise AssertionError('Nonuniform root accepted')
# Actual isolated rendering of the globally hidden source, with editing flags
# preserved in both the live tree and retained snapshot.
root.scale=(1.4,)*3
from pathlib import Path
from types import SimpleNamespace
import time,json
from mcpblender import render_jobs
from mcpblender.image_comparison import decode_png
Path(OUTPUT+'/test-bridge').mkdir()
bridge._bridge=SimpleNamespace(path=OUTPUT+'/test-bridge/bridge.sock',active={'command':'capture_botanical_views','operation_id':'hidden-native-reference','owner':'native-test'})
args=p|{'views':['FRONT'],'resolution':32,'samples':1};hidden=capture.source(args)[-1];before=trees.inspect(p)['tree_sha256'];ids=set(bpy.data.user_map())
receipt=capture.capture(args|{'expected_capture':hidden['capture_sha256'],'directory':OUTPUT+'/hidden-render','threads':2,'max_bytes':2**30,'timeout_seconds':45})
assert receipt['_external_render'] and col.hide_render and col.hide_viewport
assert set(bpy.data.user_map())==ids and trees.inspect(p)['tree_sha256']==before
deadline=time.monotonic()+50
while True:
    status=render_jobs.read_json(OUTPUT+'/hidden-render/status.json')
    assert status['state'] not in {'failed','cancelled'},status
    if status['state']=='succeeded':break
    assert time.monotonic()<deadline
    time.sleep(.1)
proof=render_jobs.validate(OUTPUT+'/hidden-render','native-test');assert proof['valid']
w,h,pixels=decode_png(Path(proof['frames'][0]).read_bytes());assert sum(pixels[3::4])>1
assert trees.inspect(p)['tree_sha256']==before and col.hide_render and col.hide_viewport
bridge._bridge=None
print('BOTANICAL_CAPTURE_NATIVE_WITNESS_OK',len(points))
''')
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'BOTANICAL_CAPTURE_NATIVE_WITNESS_OK' in run.stdout
