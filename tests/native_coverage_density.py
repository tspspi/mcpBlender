"""Measure capture-density effects when filtered coverage is rendered again."""
import sys,math,json,shutil
from array import array
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mcpblender import exr_scanline,image_comparison
out=Path(args[1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Coverage';s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);cam.location=(0,0,5);cam.data.type='ORTHO';cam.data.ortho_scale=2;s.camera=cam
mat=bpy.data.materials.new('OpaqueEmission');mat.use_nodes=True;tree=mat.node_tree;tree.nodes.clear();e=tree.nodes.new('ShaderNodeEmission');o=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(e.outputs[0],o.inputs['Surface'])
def render(name,size):
 assert shutil.disk_usage(out).free>2*1024**3
 s.render.resolution_x=size;s.render.resolution_y=size;bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
 s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(name+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
 ch=exr_scanline.decode(path,['Coverage.Combined.'+a for a in 'RGBA'])['channels'];return ch
proof={'configuration':{'output_resolution':32,'samples':256,'filter_type':s.cycles.pixel_filter_type,'filter_width':s.render.filter_size,'scope':'Opaque emission geometry versus filtered alpha cards at matched orthographic camera; nearest data images, no material-normal/lighting uncertainty. Edge control reaches image/card border; thin slats have transparent border padding. Not canopy or angular qualification.'}}
for shape in ('edge','slats'):
 vertices=[];faces=[]
 rects=[(1/32,-2,2,2)] if shape=='edge' else [(-.83+k*.2,-.85,-.83+k*.2+.045,.85) for k in range(9)]
 for l,b,r,t in rects:
  i=len(vertices);vertices.extend([(l,b,0),(r,b,0),(r,t,0),(l,t,0)]);faces.append((i,i+1,i+2,i+3))
 mesh=bpy.data.meshes.new(shape);mesh.from_pydata(vertices,[],faces);mesh.materials.append(mat);source=bpy.data.objects.new(shape,mesh);s.collection.objects.link(source)
 reference=None;proof[shape]={}
 for factor in (1,2,4):
  source.hide_render=False;size=32*factor;ch=render(shape+'-capture-'+str(factor),size)
  if factor==1:reference=[ch['Coverage.Combined.'+a][i] for i in range(32*32) for a in 'RGBA']
  alpha=ch['Coverage.Combined.A'];image=bpy.data.images.new(shape+str(factor),width=size,height=size,alpha=True,float_buffer=True);image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED';image.pixels.foreach_set(array('f',[v for y in range(size-1,-1,-1) for x in range(size) for v in (1.,1.,1.,alpha[y*size+x])]))
  proxy_mat=bpy.data.materials.new('Proxy');proxy_mat.use_nodes=True;nt=proxy_mat.node_tree;nt.nodes.clear();tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='CLIP';emit=nt.nodes.new('ShaderNodeEmission');transparent=nt.nodes.new('ShaderNodeBsdfTransparent');mix=nt.nodes.new('ShaderNodeMixShader');output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(tex.outputs['Alpha'],mix.inputs[0]);nt.links.new(transparent.outputs[0],mix.inputs[1]);nt.links.new(emit.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],output.inputs['Surface'])
  pm=bpy.data.meshes.new('Proxy');pm.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[],[(0,1,2,3)]);pm.uv_layers.new().data.foreach_set('uv',[0,0,1,0,1,1,0,1]);pm.materials.append(proxy_mat);obj=bpy.data.objects.new('Proxy',pm);s.collection.objects.link(obj);source.hide_render=True
  result=render(shape+'-proxy-'+str(factor),32);candidate=[result['Coverage.Combined.'+a][i] for i in range(32*32) for a in 'RGBA'];metrics=image_comparison.measure(reference,candidate,32,32,.5,lambda:None);proof[shape][str(factor)]=metrics
  print('COVERAGE',shape,factor,metrics['soft_alpha_iou'],metrics['mask_iou'],metrics['alpha_mae'],flush=True)
  bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(pm);bpy.data.materials.remove(proxy_mat);bpy.data.images.remove(image)
  (out/'proof.json').write_text(json.dumps(proof,indent=2))
 bpy.data.objects.remove(source,do_unlink=True);bpy.data.meshes.remove(mesh)
print('COVERAGE_DENSITY_COMPLETE')
