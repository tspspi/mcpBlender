"""Native coverage/normal moment measurement with unoccluded diffuse controls."""
import sys,json,math,shutil
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]
sys.path.insert(0,args[0])
import bpy
from mcpblender import exr_scanline,capture_material_fields
out=Path(args[1]).resolve();assert shutil.disk_usage(out).free>2*1024**3
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True;default_filter=(s.cycles.pixel_filter_type,s.render.filter_size);s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1);vl=s.view_layers[0];vl.name='Calibration';vl.use_pass_normal=True
mat=bpy.data.materials.new('DiffuseProbe');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear();diffuse=nt.nodes.new('ShaderNodeBsdfDiffuse');diffuse.inputs['Color'].default_value=(.2,.2,.2,1);diffuse.inputs['Roughness'].default_value=0;output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(diffuse.outputs[0],output.inputs['Surface']);geometry=nt.nodes.new('ShaderNodeNewGeometry');xyz=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(geometry.outputs['Normal'],xyz.inputs[0])
fields={'W':None,'NX':xyz.outputs[0],'NY':xyz.outputs[1],'NZ':xyz.outputs[2]}
for label,i,j in [('XX',0,0),('YY',1,1),('ZZ',2,2),('XY',0,1),('XZ',0,2),('YZ',1,2)]:
 node=nt.nodes.new('ShaderNodeMath');node.operation='MULTIPLY';nt.links.new(xyz.outputs[i],node.inputs[0]);nt.links.new(xyz.outputs[j],node.inputs[1]);fields[label]=node.outputs[0]
for label,socket in fields.items():
 aov=vl.aovs.add();aov.name='Probe_'+label;aov.type='VALUE';node=nt.nodes.new('ShaderNodeOutputAOV');node.aov_name=aov.name
 if socket is None:node.inputs['Value'].default_value=1
 else:nt.links.new(socket,node.inputs['Value'])
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);camera.location=(0,0,5);camera.data.type='ORTHO';camera.data.ortho_scale=2;s.camera=camera
proof={'filters':{'box':['BOX',1],'default':default_filter},'samples':256,'resolution':32,'controls':{},'scope':'Primary-only native diffuse facets; custom scalar AOVs measure actual shader geometry normal moments. No normal-distribution model inferred from one vector.'}
for filter_name,(kind,width) in proof['filters'].items():
 s.cycles.pixel_filter_type=kind;s.render.filter_size=width
 for shape in ('flat','edge','mixed','mixed_edge'):
  vertices=[];faces=[];mixed=shape.startswith('mixed');edge=shape.endswith('edge');step=1/128 if mixed else 4;count=512 if mixed else 1
  for k in range(count):
   original=-2+k*step;low=max(original,1/32) if edge else original;high=original+step
   if low>=high:continue
   slope=(math.sqrt(3) if k%2==0 else -math.sqrt(3)) if mixed else 0;center=original+step/2;z0=(low-center)*slope;z1=(high-center)*slope;i=len(vertices);vertices.extend([(low,-2,z0),(high,-2,z1),(high,2,z1),(low,2,z0)]);faces.append((i,i+1,i+2,i+3))
  mesh=bpy.data.meshes.new(shape);mesh.from_pydata(vertices,[],faces);mesh.materials.append(mat);obj=bpy.data.objects.new(shape,mesh);s.collection.objects.link(obj)
  for key in ('visible_shadow','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter'):setattr(obj,key,False)
  for lighting in ('world','sun'):
   assert shutil.disk_usage(out).free>2*1024**3;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0;sun=None
   if lighting=='sun':
    data=bpy.data.lights.new('Sun','SUN');data.energy=2;data.angle=0;sun=bpy.data.objects.new('Sun',data);s.collection.objects.link(sun)
   bpy.context.view_layer.update();bpy.ops.render.render(write_still=False);s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(filter_name+'-'+shape+'-'+lighting+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
   names=['Calibration.Combined.'+a for a in 'RGBA']+['Calibration.Normal.'+a for a in 'XYZ']+['Calibration.Probe_'+f+'.X' for f in fields];data=exr_scanline.decode(path,names)['channels'];i=16*32+16
   row={k:v[i] for k,v in data.items()};row['center_normal_length']=math.sqrt(sum(row['Calibration.Normal.'+a]**2 for a in 'XYZ'));row['mean_rgb_on_central_16px']=sum(data['Calibration.Combined.R'][y*32+x] for y in range(8,24) for x in range(8,24))/256
   measured={'channels':{'TreeCapture.Combined.A':data['Calibration.Combined.A'],**{'TreeCapture.Normal.'+a:data['Calibration.Normal.'+a] for a in 'XYZ'}}}
   row['filtering']=capture_material_fields.normal_filtering(measured,data['Calibration.Probe_W.X'],.001)
   row['pass_agreement_max_abs_error']=max(abs(x-y) for axis in 'XYZ' for x,y in zip(data['Calibration.Normal.'+axis],data['Calibration.Probe_N'+axis+'.X']))
   assert row['pass_agreement_max_abs_error']<1e-5
   proof['controls'][filter_name+'-'+shape+'-'+lighting]=row;(out/'proof.json').write_text(json.dumps(proof,indent=2));print('NORMAL_CALIBRATION_DONE',shape,lighting,flush=True)
   if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
  bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
print('NORMAL_CALIBRATION_COMPLETE',flush=True)
