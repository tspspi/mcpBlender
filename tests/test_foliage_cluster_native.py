"""Selected native sources preserve UV corners, semantics and physical placement."""
import json
from pathlib import Path
import subprocess
from mcpblender.botanical_contracts import Create,SecondaryUV
from mcpblender.foliage_cluster_contracts import Create as Cluster
from test_botanical_native import pytestmark


def test_native_cluster_geometry_uv_lifecycle_and_card_fit(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'clusters.py'
    args=Create(collection='Master',expected_model='0'*64,recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}).model_dump(exclude_none=True)
    secondary=SecondaryUV(collection='Master',expected_tree='0'*64,assets=['leaf-0'],texture_width=512,texture_height=512,chart_layout={'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4,'allow_stretch':True}).model_dump()
    cluster=Cluster(collection='Master',cluster_collection='Cluster',cluster_index=0,expected_plan='0'*64,max_leaves=8,display_offset_m=[7,0,0]).model_dump()
    script.write_text('import sys,json\nsys.path.insert(0,'+repr(str(repo))+')\nARGS=json.loads('+repr(json.dumps(args))+')\nUV=json.loads('+repr(json.dumps(secondary))+')\nCFG=json.loads('+repr(json.dumps(cluster))+')\nROOT='+repr(str(tmp_path))+'\n'+r'''
import bpy,math
from mathutils import Vector,Euler
from mcpblender import foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,botanical_uv,foliage_clusters as api,bridge,foliage_cards
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
planned=trees.plan(ARGS);state=trees.create(ARGS|{'expected_model':planned['model_sha256']})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5,'variants':1})
pop=leaves.dispatch('plan_botanical_foliage',{'collection':'Master','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'Master','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':pop['foliage_sha256']})
state=botanical_uv.create(UV|{'expected_tree':state['tree_sha256']})
root=bpy.data.objects[state['root']];root.rotation_euler.z=.4;root.location=(100,200,0);root.scale.x*=1.3;bpy.context.view_layer.update()
state=trees.inspect({'collection':'Master'});ids=set(bpy.data.user_map());selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active;frame=bpy.context.scene.frame_current
plan=api.plan(CFG);cfg=CFG|{'expected_plan':plan['plan_sha256']}
for phase in ('preparing bounded foliage cluster geometry','verified foliage cluster before handoff'):
 def stop(v):
  if v.get('phase')==phase:raise bridge.OperationCancelled(phase)
 bridge.report_progress=stop
 try:api.create(cfg)
 except bridge.OperationCancelled:pass
 else:raise AssertionError('Cluster cancellation ignored')
 bridge.report_progress=lambda v:None
 assert set(bpy.data.user_map())==ids and trees.inspect({'collection':'Master'})['tree_sha256']==state['tree_sha256']
try:api.create(cfg|{'expected_plan':'0'*64})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale plan accepted')
result=api.create(cfg)
bpy.ops.object.mode_set(mode='EDIT')
try:
 try:api.inspect({'cluster_collection':'Cluster'})
 except ValueError as e:assert 'Object mode' in str(e)
 else:raise AssertionError('Cluster inspection accepted Edit mode')
finally:bpy.ops.object.mode_set(mode='OBJECT')
assert result['valid'] and result['source_unchanged'] and len(result['uv_schema']['names'])==2
assert list(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active and bpy.context.scene.frame_current==frame
values,roles,layout,partition,guard=api.prepare(cfg);obj=bpy.data.objects[result['object']];mesh=obj.data;template=roles['lo0'].data;indices=partition['clusters'][0]['leaf_indices']
assert [m.name for m in mesh.materials]==[m.name for m in template.materials]
vpos=0;fpos=0;lpos=0;error=0;expected_edges={}
for index in indices:
 leaf=layout['leaves'][index];rotation=Euler(leaf['rotation'],'XYZ').to_matrix()
 for edge in template.edges:expected_edges[tuple(sorted(vpos+i for i in edge.vertices))]=(edge.use_seam,edge.use_edge_sharp)
 for v in template.vertices:
  local=Vector(leaf['position'])+leaf['scale']*(rotation@v.co)
  expected=root.matrix_world@local+Vector(cfg['display_offset_m'])/.01
  error=max(error,((obj.matrix_world@mesh.vertices[vpos].co)-expected).length*.01)
  assert mesh.attributes['leaf_index'].data[vpos].value==index
  assert mesh.attributes['bot_branch_index'].data[vpos].value==leaf['parent_branch_index']
  vpos+=1
 for f in template.polygons:
  assert mesh.polygons[fpos].material_index==f.material_index and mesh.polygons[fpos].use_smooth==f.use_smooth;fpos+=1
 for n in result['uv_schema']['names']:
  for j,corner in enumerate(template.uv_layers[n].data):assert tuple(mesh.uv_layers[n].data[lpos+j].uv)==tuple(corner.uv)
 for j,normal in enumerate(template.corner_normals):
  expected=(root.matrix_world.to_3x3().inverted().transposed()@(rotation@normal.vector)).normalized()
  actual=(obj.matrix_world.to_3x3().inverted().transposed()@mesh.corner_normals[lpos+j].vector).normalized()
  assert math.degrees(2*math.asin(min(1,(expected-actual).length/2)))<.05,(index,j,tuple(expected),tuple(actual))
 lpos+=len(template.loops)
assert error<1e-5,error
assert {tuple(sorted(e.vertices)):(e.use_seam,e.use_edge_sharp) for e in mesh.edges}==expected_edges
# Existing fitted-card pipeline accepts the ordinary selected source.
cardargs={'sources':[obj.name],'view':'TOP','outline':'CONVEX_HULL','padding':.02,'standoff_m':.005,'resolution':64,'max_vertices':64,'max_triangles':100000,'thin_foliage_mode':'FRONT_PBR'}
card=foliage_cards.inspect(cardargs);assert card['projection']['geometry_coverage_fraction']>0
created=foliage_cards.create(cardargs|{'name':'ClusterCard','expected_card':card['card_sha256']});assert created['bake_inspection']['complete']
# Object/generated coordinate sampling must refuse before native staging.
mat=template.materials[0];tree=mat.node_tree;node=tree.nodes.new('ShaderNodeTexNoise');tree.links.new(node.outputs['Color'],tree.nodes['Leaf Surface'].inputs['Base Color'])
badplan=api.plan(cfg);before=set(bpy.data.user_map())
try:api.create(cfg|{'cluster_collection':'Unsafe','expected_plan':badplan['plan_sha256']})
except ValueError as e:assert 'explicit UV' in str(e),str(e)
else:raise AssertionError('Implicit generated sampling accepted')
assert set(bpy.data.user_map())==before
coords=tree.nodes.new('ShaderNodeTexCoord');tree.links.new(coords.outputs['Generated'],node.inputs['Vector'])
try:api.sampling(mat)
except ValueError as e:assert 'UV texture coordinates' in str(e)
else:raise AssertionError('Explicit generated coordinates accepted')
tree.links.new(coords.outputs['UV'],node.inputs['Vector']);api.sampling(mat)
coords.from_instancer=True
try:api.sampling(mat)
except ValueError as e:assert 'instancer UV' in str(e)
else:raise AssertionError('Instancer UV sampling accepted')
tree.nodes.remove(coords);tree.nodes.remove(node)
# Restore the original managed front/back color link removed by the test.
tree.links.new(tree.nodes['Leaf Sides'].outputs[0],tree.nodes['Leaf Surface'].inputs['Base Color'])
result=api.inspect({'cluster_collection':'Cluster'})[-1]
foreign=bpy.data.objects.new('Foreign',None);bpy.data.collections['Cluster'].objects.link(foreign)
blocked=api.inspect({'cluster_collection':'Cluster'})[-1];assert blocked['ownership_blockers']
try:api.dispatch('remove_botanical_foliage_cluster',{'cluster_collection':'Cluster','expected_cluster':blocked['cluster_sha256'],'discard_derived_edits':True})
except ValueError:pass
else:raise AssertionError('Foreign membership allowed deletion')
bpy.data.objects.remove(foreign,do_unlink=True)
foreign=bpy.data.objects.new('MeshBorrower',mesh);bpy.context.scene.collection.objects.link(foreign)
assert api.inspect({'cluster_collection':'Cluster'})[-1]['ownership_blockers']
bpy.data.objects.remove(foreign,do_unlink=True)
original_x=mesh.vertices[0].co.x;mesh.vertices[0].co.x+=.01
edited=api.inspect({'cluster_collection':'Cluster'})[-1];assert not edited['valid'] and edited['issues']
try:api.dispatch('remove_botanical_foliage_cluster',{'cluster_collection':'Cluster','expected_cluster':edited['cluster_sha256']})
except ValueError as e:assert 'discard_derived_edits' in str(e)
else:raise AssertionError('Edited snapshot removed silently')
mesh.vertices[0].co.x=original_x
mesh.uv_layers.active_index=1-mesh.uv_layers.active_index
assert api.inspect({'cluster_collection':'Cluster'})[-1]['issues']
mesh.uv_layers.active_index=result['uv_schema']['active']
# Saving/reopening retains an independently owned valid snapshot.
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/cluster.blend');bpy.ops.wm.open_mainfile(filepath=ROOT+'/cluster.blend')
result=api.inspect({'cluster_collection':'Cluster'})[-1]
assert result['valid'] and result['source_unchanged']
source=trees.inspect({'collection':'Master'});trees.dispatch('remove_botanical_tree',{'collection':'Master','expected_tree':source['tree_sha256']})
result=api.inspect({'cluster_collection':'Cluster'})[-1];assert not result['source_present'] and result['source_unchanged'] is None
api.dispatch('remove_botanical_foliage_cluster',{'cluster_collection':'Cluster','expected_cluster':result['cluster_sha256'],'discard_derived_edits':True})
assert 'Cluster' not in bpy.data.collections and all(bpy.data.materials.get(m['material']) for m in result['material_sampling_at_creation'])
# A valid master may author a secondary UV on only one of several variants.
# Refuse mixing these schemas instead of silently dropping/zero-filling maps.
planned=trees.plan(ARGS);state=trees.create(ARGS|{'expected_model':planned['model_sha256']})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5,'variants':3})
pop=leaves.dispatch('plan_botanical_foliage',{'collection':'Master','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'Master','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':pop['foliage_sha256']})
state=botanical_uv.create(UV|{'expected_tree':state['tree_sha256']})
mixed=CFG|{'anchor_order':0,'max_leaves':1024}
plan=api.plan(mixed);before=set(bpy.data.user_map())
try:api.create(mixed|{'expected_plan':plan['plan_sha256']})
except ValueError as e:assert 'identical UV' in str(e),str(e)
else:raise AssertionError('Mixed variant UV schemas accepted')
assert set(bpy.data.user_map())==before and trees.inspect({'collection':'Master'})['tree_sha256']==state['tree_sha256']
print('CLUSTER_NATIVE_PASSED',error)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'CLUSTER_NATIVE_PASSED' in result.stdout
