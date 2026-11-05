"""Stable native and shader identity under instance selection and persistence."""
import sys,json,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0]);out=Path(args[1])
import bpy
from mcpblender import exr_scanline
from mcpblender.blender import botanical_foliage,botanical_trees

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.device='CPU';s.cycles.use_denoising=False;s.cycles.use_adaptive_sampling=False
s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=64;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
layer=s.view_layers[0];layer.name='Ids'
mat=bpy.data.materials.new('PrototypeMaterial');mat.use_nodes=True;tree=mat.node_tree
for field in ('leaf_index','id'):
    attr=tree.nodes.new('ShaderNodeAttribute');attr.attribute_type='INSTANCER';attr.attribute_name=field
    aov=layer.aovs.add();aov.name=field;aov.type='VALUE';node=tree.nodes.new('ShaderNodeOutputAOV');node.aov_name=field;tree.links.new(attr.outputs['Fac'],node.inputs['Value'])
info=tree.nodes.new('ShaderNodeObjectInfo');aov=layer.aovs.add();aov.name='Random';aov.type='VALUE';node=tree.nodes.new('ShaderNodeOutputAOV');node.aov_name=aov.name;tree.links.new(info.outputs['Random'],node.inputs['Value'])
mesh=bpy.data.meshes.new('PrototypeMesh');mesh.from_pydata([(-.38,-.38,0),(.38,-.38,0),(.38,.38,0),(-.38,.38,0)],[],[(0,1,2,3)]);mesh.materials.append(mat)
prototype=bpy.data.objects.new('Prototype',mesh);sources=bpy.data.collections.new('UnlinkedPrototypes');sources.objects.link(prototype)
points=bpy.data.meshes.new('Points');points.from_pydata([(-.6,0,0),(.6,0,0)],[],[]);obj=bpy.data.objects.new('Instances',points);s.collection.objects.link(obj)
leaves=[{'rotation':(0,0,0),'scale':1,'variant':0,'parent_branch_index':0,'phase':0,'flutter':0} for _ in range(2)]
group=botanical_foliage.instance_population('Test',obj,points,sources,{'leaves':leaves},[13,79])
assert [v.value for v in points.attributes['id'].data]==[13,79]
points.attributes.new(name='keep',type='BOOLEAN',domain='POINT')
instance=next(n for n in group.nodes if n.bl_idname=='GeometryNodeInstanceOnPoints')
field=group.nodes.new('GeometryNodeInputNamedAttribute');field.data_type='BOOLEAN';field.inputs['Name'].default_value='keep';group.links.new(field.outputs['Attribute'],instance.inputs['Selection'])
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);camera.location=(0,0,5);camera.data.type='ORTHO';camera.data.ortho_scale=3;s.camera=camera


def select(right_only):
    # Reacquire RNA attributes after any CustomData collection mutation.
    bpy.data.meshes['Points'].attributes['keep'].data.foreach_set('value',[not right_only,True]);bpy.data.meshes['Points'].update();bpy.context.view_layer.update()


def right_instance():
    values=[]
    for item in bpy.context.evaluated_depsgraph_get().object_instances:
        if item.is_instance and item.parent and item.parent.original.name=='Instances' and item.matrix_world.translation.x>0:
            # Iterator RNA handles expire when iteration advances.
            values.append({'persistent_id':list(item.persistent_id),'random_id':int(item.random_id),'matrix':[list(row) for row in item.matrix_world]})
    assert len(values)==1
    return values[0]


def render(label):
    s=bpy.context.scene;bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP'
    path=out/(label+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
    names=['Ids.Combined.A','Ids.leaf_index.X','Ids.id.X','Ids.Random.X']
    data=exr_scanline.decode(path,names)['channels'];i=16*64+44
    assert data[names[0]][i]==1 and data[names[1]][i]==79
    return {n:data[n][i] for n in names}


select(False);before=right_instance();full=render('full')
assert full['Ids.id.X']==79
select(True);after=right_instance();selected=render('selected')
assert before==after and full==selected,'Native or shader identity changed after selection'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'stable-ids.blend'));bpy.ops.wm.open_mainfile(filepath=str(out/'stable-ids.blend'),use_scripts=False)
assert [v.value for v in bpy.data.meshes['Points'].attributes['id'].data]==[13,79]
select(True);assert right_instance()==before;reopened=render('reopened');assert reopened==full
# Demonstrate the regression with the old implicit-ID behavior on the same
# instancer and retained pose, rather than merely checking an attribute exists.
points=bpy.data.meshes['Points'];points.attributes.remove(points.attributes['id'])
select(False);legacy_full=right_instance();legacy_pixel=render('legacy-full')
select(True);legacy_selected=right_instance();legacy_subset_pixel=render('legacy-selected')
assert legacy_full['matrix']==legacy_selected['matrix']
assert legacy_full['persistent_id']!=legacy_selected['persistent_id'] and legacy_full['random_id']!=legacy_selected['random_id']
assert legacy_pixel['Ids.Random.X']!=legacy_subset_pixel['Ids.Random.X']
proof={'before':before,'selected':after,'reopened':reopened,'shader_pixel':full,'legacy_before':legacy_full,'legacy_selected':legacy_selected,'legacy_random_pixels':[legacy_pixel['Ids.Random.X'],legacy_subset_pixel['Ids.Random.X']]}
(out/'proof.json').write_text(json.dumps(proof,indent=2));print('NATIVE_INSTANCE_IDS_OK',flush=True)
