"""Native source-preserving bake preparation, sampling pins and owned cleanup."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_owned_bake_preparation_and_sampling(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'prepare.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,faulthandler
faulthandler.enable()
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,botanical_surfaces as surfaces,vegetation_bake as prep,bridge,textures
from mcpblender.botanical_surface_contracts import Configure
from mcpblender.vegetation_bake_contracts import Source
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:print(v,flush=True)
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe});tree=trees.create({'collection':'Oak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5});plan=leaves.dispatch('plan_botanical_foliage',{'collection':'Oak','foliage':cfg})
tree=leaves.dispatch('configure_botanical_foliage',{'collection':'Oak','foliage':cfg,'expected_tree':tree['tree_sha256'],'expected_foliage':plan['foliage_sha256']})
parent=bpy.data.objects.new('SourcePlacement',None);bpy.context.scene.collection.objects.link(parent);parent.scale=(2,1,.7)
root=trees.inventory({'collection':'Oak'})[1];root.parent=parent;root.rotation_euler=(.2,.1,.4);root.location=(3,2,1);bpy.context.view_layer.update()
args=Source(collection='Oak').model_dump();objects,_=prep.objects(args)
# Explicit source UVs are preserved; missing procedural source UVs need consent.
for role,profile in (('wood','OAK_BARK'),('leaf-0','OAK_LEAF')):
    material=objects[role].data.materials[0]
    surfaces.configure(Configure(material=material.name,settings={'profile':profile},expected_material=surfaces.inspect({'material':material.name})['material_sha256']).model_dump())
objects['wood'].data.materials[0].use_fake_user=True
plan=prep.plan(args)[-1];assert not plan['can_prepare'] and plan['source_sampling_changes'][0]['asset']=='shoots'
ids=set(bpy.data.user_map())
try:prep.create(args|{'expected_plan':plan['plan_sha256'],'bake_collection':'Refuse'})
except ValueError as e:assert 'source UVs missing' in str(e)
else:raise AssertionError('Missing source UVs silently generated')
assert ids==set(bpy.data.user_map())
args['missing_uv_policy']='BAKE_LAYOUT';plan=prep.plan(args)[-1];assert plan['can_prepare']
original={role:textures.mesh_signature(o,o.data) for role,o in objects.items()};mats={m:textures.material_signature(m,thin_foliage_mode='FRONT_PBR') for o in objects.values() for m in o.data.materials}
selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
state=prep.create(args|{'expected_plan':plan['plan_sha256'],'bake_collection':'Bake'})
assert state['valid'] and len(state['components'])==5,state
assert selected==list(bpy.context.selected_objects) and active==bpy.context.view_layer.objects.active
assert original=={role:textures.mesh_signature(o,o.data) for role,o in objects.items()}
assert all(textures.material_signature(m,thin_foliage_mode='FRONT_PBR')==sig for m,sig in mats.items())
for role,row in state['components'].items():
    obj=bpy.data.objects[row['name']];src=objects[role]
    assert textures.mesh_signature(obj,obj.data)['matrix']==textures.mesh_signature(src,src.data)['matrix']
    assert obj.data!=src.data and not set(obj.data.materials)&set(src.data.materials)
    assert len(obj.data.vertices)==len(src.data.vertices) and len(obj.data.loops)==len(src.data.loops)
    for layer in src.data.uv_layers:assert [tuple(v.uv) for v in layer.data]==[tuple(v.uv) for v in obj.data.uv_layers[layer.name].data]
    assert textures.inspect(row['inspect_texture_bake'])['complete']
# A stale source plan refuses before creating IDs.
try:prep.create(args|{'expected_plan':'0'*64,'bake_collection':'Stale'})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale source accepted')
# Failure after real UV work rolls back exact created IDs and UI selection.
ids=set(bpy.data.user_map());counter=[0]
def cancel(v):
    counter[0]+=1
    if counter[0]==2:raise bridge.OperationCancelled('cancel preparation')
bridge.report_progress=cancel
try:prep.create(args|{'expected_plan':plan['plan_sha256'],'bake_collection':'Cancelled'})
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected cancellation')
bridge.report_progress=lambda v:None
assert ids==set(bpy.data.user_map()) and selected==list(bpy.context.selected_objects)
# Wind-derived LOD creation has a uniform-placement contract; independent bake
# preparation above has already verified the sheared original affine matrices.
root.parent=None;root.rotation_euler=(0,0,0);root.location=(0,0,0);bpy.context.view_layer.update()
# A reduced native LOD/profile can also be prepared; copies survive its removal.
from mcpblender.blender import vegetation_lods as lods
from mcpblender.vegetation_lod_contracts import Source as LodSource
largs=LodSource(collection='Oak',levels=[{'leaf_budget':70,'radial_sides':6}]).model_dump();lp=lods.plan(largs)[-1]
ls=lods.create(largs|{'expected_plan':lp['plan_sha256'],'lod_collection':'Lods','display_offset_m':[8,0,0]})
bargs=Source(lod_collection='Lods',assets=['lod-1-wood','leaf-0'],missing_uv_policy='BAKE_LAYOUT').model_dump();bp=prep.plan(bargs)[-1]
bs=prep.create(bargs|{'expected_plan':bp['plan_sha256'],'bake_collection':'LodBake'})
assert bs['valid'] and len(bs['components'])==2
lods.dispatch('remove_botanical_lods',{'lod_collection':'Lods','expected_lods':ls['lods_sha256']})
bs=prep.inspect({'bake_collection':'LodBake'})[-1];assert bs['valid']
prep.remove({'bake_collection':'LodBake','expected_preparation':bs['preparation_sha256']})
# Owned copy independence, persistence and external-reference blockers.
guard=trees.inspect({'collection':'Oak'})['tree_sha256'];trees.remove({'collection':'Oak','expected_tree':guard})
assert prep.inspect({'bake_collection':'Bake'})[-1]['valid']
print('BEFORE_SAVE',flush=True)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/prepared.blend')
print('BEFORE_REOPEN',flush=True)
bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/prepared.blend')
state=prep.inspect({'bake_collection':'Bake'})[-1];assert state['valid']
obj=bpy.data.objects[state['components']['leaf-0']['name']];foreign=bpy.data.objects.new('Foreign',obj.data);bpy.context.scene.collection.objects.link(foreign)
state=prep.inspect({'bake_collection':'Bake'})[-1];assert state['ownership_blockers']
try:prep.remove({'bake_collection':'Bake','expected_preparation':state['preparation_sha256']})
except ValueError as e:assert 'External reference' in str(e)
else:raise AssertionError('External shared mesh removed')
bpy.data.objects.remove(foreign,do_unlink=True)
state=prep.inspect({'bake_collection':'Bake'})[-1];prep.remove({'bake_collection':'Bake','expected_preparation':state['preparation_sha256']})
assert not bpy.data.collections.get('Bake')
# Implicit image coordinates are pinned to the original render UV, even after
# the new map becomes active. A disconnected Texture Coordinate UV consumer is
# also pinned; existing explicit UV and unrelated maps stay untouched.
recipe=botany.recipe({'attractors':32,'iterations':1,'node_budget':128});plan=trees.plan({'recipe':recipe})
tree=trees.create({'collection':'ImageOak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':6,'bark_tile_length':1})
args=Source(collection='ImageOak').model_dump();obj=prep.objects(args)[0]['wood'];mat=obj.data.materials[0]
img=bpy.data.images.new('Source',width=32,height=32);img.filepath_raw=OUTPUT+'/source.png';img.file_format='PNG';img.save();bpy.data.images.remove(img);img=bpy.data.images.load(OUTPUT+'/source.png');img.pack()
node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=img;mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
coord=mat.node_tree.nodes.new('ShaderNodeTexCoord');sep=mat.node_tree.nodes.new('ShaderNodeSeparateXYZ');mat.node_tree.links.new(coord.outputs['UV'],sep.inputs[0])
plan=prep.plan(args)[-1];state=prep.create(args|{'expected_plan':plan['plan_sha256'],'bake_collection':'ImageBake'})
copy=bpy.data.objects[state['components']['wood']['name']];shader=copy.data.materials[0].node_tree
assert shader.nodes[node.name].inputs['Vector'].links[0].from_node.uv_map=='BarkUV'
assert shader.nodes[sep.name].inputs[0].links[0].from_node.uv_map=='BarkUV'
assert not node.inputs['Vector'].is_linked and sep.inputs[0].links[0].from_node==coord
print('VEGETATION_BAKE_PREPARED_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'VEGETATION_BAKE_PREPARED_OK' in result.stdout
