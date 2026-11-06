"""Native first-surface component IDs and worker-only source preservation."""
import sys,json,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0]);out=Path(args[1])
import bpy
from mcpblender import botany,component_ids,exr_scanline,tree_capture
from mcpblender.blender import botanical_foliage,capture_material_fields as material_fields,capture_components as api

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.device='CPU';s.cycles.use_denoising=True;s.cycles.use_adaptive_sampling=False;s.render.threads_mode='FIXED';s.render.threads=2
s.render.resolution_x=64;s.render.resolution_y=64;s.render.resolution_percentage=100;s.render.film_transparent=True;layer=s.view_layers[0];layer.name='TreeCapture'
for flag in tree_capture.PASSES:setattr(layer,'use_pass_'+flag,True)
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
mat=bpy.data.materials.new('Surface');mat.use_nodes=True
mesh=bpy.data.meshes.new('PrototypeMesh');mesh.from_pydata([(-.28,-.28,0),(.28,-.28,0),(.28,.28,0),(-.28,.28,0)],[],[(0,1,2,3)]);mesh.materials.append(mat)
prototype=bpy.data.objects.new('Prototype',mesh);sources=bpy.data.collections.new('UnlinkedPrototypes');sources.objects.link(prototype)
points=bpy.data.meshes.new('Points');points.from_pydata([(-.6,-.5,0),(.6,-.5,0)],[],[]);obj=bpy.data.objects.new('Instances',points);s.collection.objects.link(obj)
leaves=[{'rotation':(0,0,0),'scale':1,'variant':0,'parent_branch_index':0,'phase':0,'flutter':0} for _ in range(2)]
botanical_foliage.instance_population('Test',obj,points,sources,{'leaves':leaves})
wood=bpy.data.objects.new('Structural',mesh);wood.location=(0,.65,0);s.collection.objects.link(wood)
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);camera.location=(0,0,5);camera.data.type='ORTHO';camera.data.ortho_scale=3;s.camera=camera
roles={'pm':points,'po':obj};fields=material_fields.describe([mat],normal_moments=True);contract=api.describe(roles,fields)
before_nodes=len(mat.node_tree.nodes)
collision=points.attributes.new(name=component_ids.ATTRIBUTE,type='INT',domain='POINT')
try:api.describe(roles,fields)
except ValueError as exc:assert 'Reserved' in str(exc)
else:raise AssertionError('Reserved attribute accepted')
points.attributes.remove(collision)
reserved=mat.node_tree.nodes.new('ShaderNodeOutputAOV');reserved.aov_name=component_ids.FIELDS[0]['name']
try:api.describe(roles,fields)
except ValueError as exc:assert 'reserved' in str(exc)
else:raise AssertionError('Reserved component AOV accepted')
mat.node_tree.nodes.remove(reserved)
# Changed or duplicate source indices refuse before any derived attribute/node.
points.attributes['leaf_index'].data[1].value=0
try:api.install(s,contract,fields)
except ValueError as exc:assert 'indices' in str(exc)
else:raise AssertionError('Duplicate component indices accepted')
assert points.attributes.get(component_ids.ATTRIBUTE) is None and len(mat.node_tree.nodes)==before_nodes
points.attributes['leaf_index'].data[1].value=1


def render(label,names):
    bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP'
    path=out/(label+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
    if label=='after':
        with path.open('rb') as stream:assert len(exr_scanline.headers(stream)[1])==32
    return exr_scanline.decode(path,names)['channels']


beauty=['TreeCapture.Combined.'+a for a in 'RGBA'];baseline=render('before',beauty)
original_indices=[v.value for v in points.attributes['leaf_index'].data]
surface=mat.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_socket
material_fields.install(s,fields);api.install(s,contract,fields)
assert [v.value for v in points.attributes['leaf_index'].data]==original_indices
assert [v.value for v in points.attributes[component_ids.ATTRIBUTE].data]==[1,2]
assert mat.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_socket==surface
names=beauty+['TreeCapture.MCP_SurfaceWeight.X',*component_ids.channels()];after=render('after',names)
assert all(after[n]==baseline[n] for n in beauty),'Beauty changed'
pixels=[42*64+19,42*64+44,17*64+32]
assert [after[component_ids.channels()[0]][i] for i in pixels]==[1,2,0]
measured=component_ids.measure({'channels':after},after['TreeCapture.MCP_SurfaceWeight.X'],after[component_ids.channels()[0]],2,.001)
assert measured['integer_ids_valid'] and measured['distinct_leaf_count']==2 and measured['structural_pixels']>0
(out/'proof.json').write_text(json.dumps({'contract':contract,'measurement':measured,'beauty_exact':True,'source_indices_unchanged':True,'source_surface_link_unchanged':True},indent=2))
print('COMPONENT_CAPTURE_NATIVE_OK',flush=True)
