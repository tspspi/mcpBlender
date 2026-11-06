"""Known quarter-pixel squares expose selecting-centre sample bias in Cycles."""
import json,resource,sys
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0]);out=Path(args[1])
import bpy
from mcpblender import exr_scanline,projected_coverage as schema
from mcpblender.blender.projected_coverage import configure_sampling
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=16;s.render.resolution_y=16;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name=schema.LAYER
s.world=bpy.data.worlds.new('Black');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
mat=bpy.data.materials.new('White');mat.use_nodes=True;n=mat.node_tree.nodes;n.clear();e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(1,1,1,1);o=n.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(e.outputs[0],o.inputs['Surface'])
verts=[];faces=[]
for y in range(16):
    for x in range(16):
        cx=x-7.5;cy=y-7.5;k=len(verts);verts.extend([(cx-.25,cy-.25,0),(cx+.25,cy-.25,0),(cx+.25,cy+.25,0),(cx-.25,cy+.25,0)]);faces.append((k,k+1,k+2,k+3))
mesh=bpy.data.meshes.new('QuarterSquares');mesh.from_pydata(verts,[],faces);mesh.materials.append(mat);obj=bpy.data.objects.new('QuarterSquares',mesh);s.collection.objects.link(obj)
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);camera.location=(0,0,10);camera.data.type='ORTHO';camera.data.ortho_scale=16;s.camera=camera
rows=[]
for count,offset in [(1,0),(64,0),(64,1),(256,1)]:
    profile=schema.sampling(max(64,count));configure_sampling(s,profile)
    s.cycles.samples=count+offset;s.cycles.sample_offset=offset;s.cycles.sample_subset_length=count
    bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP'
    file=out/f'squares-{count}-{offset}.exr';bpy.data.images['Render Result'].save_render(str(file),scene=s)
    a=exr_scanline.decode(file,[schema.LAYER+'.Combined.A'])['channels'][schema.LAYER+'.Combined.A'];mean=sum(a)/256
    rows.append({'effective_samples':count,'offset':offset,'mean':mean,'true_coverage':.25})
assert rows[0]['mean']==1,rows
assert rows[1]['mean']-.25>.005,rows
assert abs(rows[2]['mean']-.25)<.002 and abs(rows[3]['mean']-.25)<.001,rows
print('PROJECTED_COVERAGE_ANALYTIC_COMPLETE '+json.dumps(rows),flush=True)
