"""Moment-exact diffuse closure reconstruction versus native facet references."""
from pathlib import Path
exec(compile(Path(__file__).with_name('native_normal_filtering.py').read_text(),'native_normal_filtering.py','exec'))
from mcpblender import normal_quadrature
reference=proof;reconstruction={}
for filter_name,(kind,width) in reference['filters'].items():
 s.cycles.pixel_filter_type=kind;s.render.filter_size=width
 row=reference['controls'][filter_name+'-mixed-world'];weight=row['Calibration.Probe_W.X'];keys=('NX','NY','NZ','XX','XY','XZ','YY','YZ','ZZ');fitted=normal_quadrature.fit([row['Calibration.Probe_'+k+'.X']/weight for k in keys]);material=bpy.data.materials.new('Reconstructed'+filter_name);material.use_nodes=True;tree=material.node_tree;tree.nodes.clear();current=None;mass=0
 for atom in fitted['atoms']:
  normal=tree.nodes.new('ShaderNodeCombineXYZ')
  for i,v in enumerate(atom['direction']):normal.inputs[i].default_value=v
  diffuse=tree.nodes.new('ShaderNodeBsdfDiffuse');diffuse.inputs['Color'].default_value=(.2,.2,.2,1);diffuse.inputs['Roughness'].default_value=0;tree.links.new(normal.outputs[0],diffuse.inputs['Normal'])
  if current is None:current=diffuse.outputs[0]
  else:
   blend=tree.nodes.new('ShaderNodeMixShader');blend.inputs[0].default_value=atom['weight']/(mass+atom['weight']);tree.links.new(current,blend.inputs[1]);tree.links.new(diffuse.outputs[0],blend.inputs[2]);current=blend.outputs[0]
  mass+=atom['weight']
 output=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(current,output.inputs['Surface']);mesh=bpy.data.meshes.new('FlatReconstruction');mesh.from_pydata([(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0)],[],[(0,1,2,3)]);mesh.materials.append(material);obj=bpy.data.objects.new('FlatReconstruction',mesh);s.collection.objects.link(obj)
 for key in ('visible_shadow','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter'):setattr(obj,key,False)
 for lighting in ('world','sun'):
  s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0;sun=None
  if lighting=='sun':
   light=bpy.data.lights.new('Sun','SUN');light.energy=2;light.angle=0;sun=bpy.data.objects.new('Sun',light);s.collection.objects.link(sun)
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False);s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(filter_name+'-reconstructed-'+lighting+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s);data=exr_scanline.decode(path,['Calibration.Combined.'+a for a in 'RGBA'])['channels'];index=16*32+16;actual=[data['Calibration.Combined.'+a][index] for a in 'RGBA'];expected=[reference['controls'][filter_name+'-mixed-'+lighting]['Calibration.Combined.'+a] for a in 'RGBA'];entry={'quadrature':fitted,'reference_rgba':expected,'reconstructed_rgba':actual,'relative_red_bias':actual[0]/expected[0]-1,'alpha_exact':actual[3]==expected[3]};reconstruction[filter_name+'-'+lighting]=entry;(out/'reconstruction-proof.json').write_text(json.dumps(reconstruction,indent=2));print('RECONSTRUCTION_RENDER_DONE',filter_name,lighting,entry['relative_red_bias'],flush=True)
  if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
 bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
print('NORMAL_QUADRATURE_NATIVE_COMPLETE')
