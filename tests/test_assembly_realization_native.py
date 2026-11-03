"""Native nested affine realization, attributes, frozen poses and rollback."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_realization_nested_mirror_shear_attributes_pose_and_rollback(tmp_path):
    script=tmp_path/'probe.py';source=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy,json
from mathutils import Matrix,Vector
from mcpblender.blender import assemblies as a,assembly_realization as r,bridge
from mcpblender.assembly_contracts import Create,Place
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_cube_add(location=(2,0,1));source=bpy.context.object;source.name='Source'
mat=bpy.data.materials.new('Shared');source.data.materials.append(mat)
for poly in source.data.polygons:poly.use_smooth=True
source.data.normals_split_custom_set_from_vertices([v.co.normalized() for v in source.data.vertices])
attr=source.data.attributes.new('wind_weight','FLOAT','POINT')
for i,v in enumerate(attr.data):v.value=i/8
source.shape_key_add(name='Basis');key=source.shape_key_add(name='Tall')
for v in key.data:v.co.z*=2
key.value=.6
plan=a.source({'objects':['Source']})[2]
asset=a.create(Create.model_validate({'objects':['Source'],'collection':'Prototype','expected_source':plan['source_sha256'],'origin_mode':'WORLD_ORIGIN'}).model_dump())
a.place(Place.model_validate({'collection':'Prototype','expected_asset':asset['assembly_sha256'],'name':'Mirrored','location':[10,0,0],'scale':[-2,1,1]}).model_dump())
# Affine transforms can also arise from parent scale/rotation; snapshot the exact
# dependency-graph leaf matrix instead of decomposing it onto the new object.
parent=bpy.data.objects.new('PlacementParent',None);bpy.context.scene.collection.objects.link(parent);parent.scale=(1,2,1);parent.rotation_euler.z=.4
bpy.data.objects['Mirrored'].parent=parent;bpy.data.objects['Mirrored'].rotation_euler.z=.7
nested=a.source({'objects':['Mirrored']})[2]
outer=a.create(Create.model_validate({'objects':['Mirrored','PlacementParent'],'collection':'OuterPrototype','expected_source':a.source({'objects':['Mirrored','PlacementParent']})[2]['source_sha256'],'origin_mode':'WORLD_ORIGIN'}).model_dump())
a.place(Place.model_validate({'collection':'OuterPrototype','expected_asset':outer['assembly_sha256'],'name':'Outer','location':[30,0,0]}).model_dump())
bpy.context.view_layer.update()
p={'instances':['Mirrored','Outer']};before=set(bpy.data.user_map());selected=[o.name for o in bpy.context.selected_objects];active=bpy.context.view_layer.objects.active.name
plan=r.inspect(p);assert len(plan['leaves'])==2 and plan['vertices']==16 and plan['triangles']==24,plan
assert set(bpy.data.user_map())==before
params=p|{'collection':'Frozen','expected_source':plan['source_sha256']}
# Ordinary cancellation at final publication rolls back exactly, too.
phase={}
def progress(v):phase.update(v)
for stage in ('mesh','published'):
    phase.clear()
    def cancel():
        if (stage=='mesh' and phase.get('phase')=='realizing evaluated assembly meshes') or (stage=='published' and 'Frozen' in bpy.context.scene.collection.children):
            raise bridge.OperationCancelled('owned rollback')
    bridge.report_progress=progress;bridge.check_cancelled=cancel
    try:r.realize(params)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Expected cancellation')
    assert set(bpy.data.user_map())==before and r.inspect(p)['source_sha256']==plan['source_sha256']
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
result=r.realize(params);assert result['static_snapshot'] and result['materials_shared']
assert r.inspect(p)['source_sha256']==plan['source_sha256']
assert [o.name for o in bpy.context.selected_objects]==selected and bpy.context.view_layer.objects.active.name==active
for record in result['leaves']:
    obj=bpy.data.objects[record['object']];mesh=obj.data
    assert obj.matrix_world==Matrix.Identity(4) and not obj.parent and not obj.modifiers and not mesh.shape_keys and not obj.animation_data
    assert len(mesh.uv_layers)==1 and mesh.materials[0]==bpy.data.objects[record['source_object']].data.materials[0]
    assert list(mesh.attributes['wind_weight'].data[i].value for i in range(8))==[i/8 for i in range(8)]
    assert r.mesh_record(mesh)==record['mesh']
    # Each native source vertex transformed by its exact sheared/mirrored world
    # matrix is retained. Polygon normals must agree with outward geometry.
    original=bpy.data.objects[record['source_object']].evaluated_get(bpy.context.evaluated_depsgraph_get())
    expected=[Matrix(record['source_matrix_world'])@v.co for v in original.data.vertices]
    assert max((v.co-e).length for v,e in zip(mesh.vertices,expected))<1e-5
    normal_matrix=Matrix(record['source_matrix_world']).to_3x3().inverted().transposed()
    expected_normals={loop.vertex_index:(normal_matrix@original.data.corner_normals[loop.index].vector).normalized() for loop in original.data.loops}
    assert all(mesh.corner_normals[loop.index].vector.dot(expected_normals[loop.vertex_index])>.999 for loop in mesh.loops)

    center=sum((v.co for v in mesh.vertices),Vector())/len(mesh.vertices)
    assert all(poly.normal.dot(poly.center-center)>0 for poly in mesh.polygons)
# Changing the copied prototype's shape no longer changes the frozen result.
frozen=[r.mesh_record(bpy.data.objects[n].data)['geometry_sha256'] for n in result['objects']]
proto=bpy.data.objects[asset['copied_objects']['Source']];proto.data.shape_keys.key_blocks['Tall'].value=0;bpy.context.view_layer.update()
assert r.inspect(p)['source_sha256']!=plan['source_sha256']
assert [r.mesh_record(bpy.data.objects[n].data)['geometry_sha256'] for n in result['objects']]==frozen
try:r.realize(params|{'collection':'Stale'})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Expected stale source refusal')
assert 'Stale' not in bpy.data.collections
# Un-realized Geometry Nodes instances must be emitted as separate mesh leaves.
mesh=bpy.data.meshes.new('GNHostMesh');host=bpy.data.objects.new('GNHost',mesh);bpy.context.scene.collection.objects.link(host)
group=bpy.data.node_groups.new('InstanceRecipe','GeometryNodeTree');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
line=group.nodes.new('GeometryNodeMeshLine');line.inputs['Count'].default_value=2;line.inputs['Offset'].default_value=(3,0,0)
cube=group.nodes.new('GeometryNodeMeshCube');cube.inputs['Size'].default_value=(1,1,1)
points=group.nodes.new('GeometryNodeInstanceOnPoints');output=group.nodes.new('NodeGroupOutput')
group.links.new(line.outputs['Mesh'],points.inputs['Points']);group.links.new(cube.outputs['Mesh'],points.inputs['Instance']);group.links.new(points.outputs['Instances'],output.inputs['Geometry'])
host.modifiers.new('Instances','NODES').node_group=group
native_plan=a.source({'objects':['GNHost']})[2];assert native_plan['can_create'],native_plan
gn=a.create(Create.model_validate({'objects':['GNHost'],'collection':'GNPrototype','expected_source':native_plan['source_sha256'],'origin_mode':'WORLD_ORIGIN'}).model_dump())
a.place(Place.model_validate({'collection':'GNPrototype','expected_asset':gn['assembly_sha256'],'name':'GNPlaced','location':[50,0,0]}).model_dump())
gnp={'instances':['GNPlaced']};gnplan=r.inspect(gnp)
assert gnplan['vertices']==16 and len(gnplan['leaves'])==2,gnplan
assert abs(gnplan['world_bounds']['min'][0]-49.5)<1e-6 and abs(gnplan['world_bounds']['max'][0]-53.5)<1e-6
collision=bpy.data.objects.new('Collision_0001',None);bpy.context.scene.collection.objects.link(collision);ids=set(bpy.data.user_map())
try:r.realize(gnp|{'collection':'Collision','expected_source':gnplan['source_sha256']})
except ValueError as e:assert 'already exists' in str(e)
else:raise AssertionError('Expected component name conflict')
assert set(bpy.data.user_map())==ids and r.inspect(gnp)['source_sha256']==gnplan['source_sha256']
gnresult=r.realize(gnp|{'collection':'FrozenGN','expected_source':gnplan['source_sha256']})
assert len(gnresult['objects'])==2 and all(len(bpy.data.objects[n].data.vertices)==8 for n in gnresult['objects'])
bpy.ops.wm.save_as_mainfile(filepath=str(__import__('pathlib').Path(__file__).parent/'realization.blend'))
print('REALIZATION_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'REALIZATION_NATIVE_OK' in result.stdout
