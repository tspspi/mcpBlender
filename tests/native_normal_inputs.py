"""Native input-normal/closure semantics and worker-only moment AOVs."""
import sys,json,shutil
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0]);out=Path(args[1]);assert shutil.disk_usage(out).free>2*1024**3
import bpy
from mathutils import Matrix
from mcpblender import exr_scanline,normal_moments
from mcpblender.blender import botanical_foliage,capture_material_fields as fields
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True;s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5;vl=s.view_layers[0];vl.name='TreeCapture';vl.use_pass_normal=True
mesh=bpy.data.meshes.new('Plane');mesh.from_pydata([(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0)],[],[(0,1,2,3)]);obj=bpy.data.objects.new('Plane',mesh);s.collection.objects.link(obj)
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);s.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=2
report={}
def render(label,side,extra=()):
 camera.matrix_world=Matrix.Translation((0,0,5)) if side=='front' else Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,-5),(0,0,0,1)));bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
 path=out/(label+'.exr');s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';bpy.data.images['Render Result'].save_render(str(path),scene=s)
 names=['TreeCapture.Combined.'+a for a in 'RGBA']+['TreeCapture.Normal.'+a for a in 'XYZ']+list(extra);return exr_scanline.decode(path,names)['channels']
for mode in ('implicit','unlinked_default','linked_unit','linked_nonunit','linked_grazing','bump','thin_implicit','thin_linked','thin_bump','linked_zero','thin_mismatch'):
 for aov in list(vl.aovs):vl.aovs.remove(aov)
 thin=mode.startswith('thin');mat=botanical_foliage.material(mode) if thin else bpy.data.materials.new(mode);mat.use_nodes=True;nt=mat.node_tree
 if thin:p=nt.nodes['Leaf Surface'];trans=nt.nodes['Thin Backlighting']
 else:
  nt.nodes.clear();p=nt.nodes.new('ShaderNodeBsdfPrincipled');output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(p.outputs[0],output.inputs['Surface'])
 if mode=='unlinked_default':p.inputs['Normal'].default_value=(.6,0,.8)
 if mode in ('linked_unit','linked_nonunit','linked_grazing','thin_linked','linked_zero','thin_mismatch'):
  node=nt.nodes.new('ShaderNodeCombineXYZ');node.inputs[0].default_value=.3 if mode=='linked_nonunit' else .6;node.inputs[2].default_value=.4 if mode=='linked_nonunit' else .8
  if mode=='linked_grazing':node.inputs[0].default_value=.995;node.inputs[2].default_value=.0998749217772
  if mode=='linked_zero':node.inputs[0].default_value=0;node.inputs[2].default_value=0
  nt.links.new(node.outputs[0],p.inputs['Normal'])
  if thin and mode!='thin_mismatch':nt.links.new(node.outputs[0],trans.inputs['Normal'])
 if mode in ('bump','thin_bump'):
  noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3;node=nt.nodes.new('ShaderNodeBump');node.inputs['Strength'].default_value=.7;node.inputs['Distance'].default_value=.2;nt.links.new(noise.outputs['Fac'],node.inputs['Height']);nt.links.new(node.outputs['Normal'],p.inputs['Normal'])
  if thin:nt.links.new(node.outputs['Normal'],trans.inputs['Normal'])
 if mesh.materials:mesh.materials[0]=mat
 else:mesh.materials.append(mat)
 if mode=='thin_mismatch':
  before=len(nt.nodes);assert 'normal_moments' not in fields.describe([mat])
  try:fields.describe([mat],normal_moments=True)
  except ValueError as exc:assert 'shared' in str(exc)
  else:raise AssertionError('Mismatched closure normals admitted')
  assert len(nt.nodes)==before;report[mode]={'refused':True};continue
 baseline={side:render(mode+'-'+side+'-before',side) for side in ('front','back')};contract=fields.describe([mat],normal_moments=True);surface=p.inputs['Normal'].links[0].from_socket if p.inputs['Normal'].links else None
 fields.install(s,contract)
 assert (p.inputs['Normal'].links[0].from_socket if p.inputs['Normal'].links else None)==surface
 for side in ('front','back'):
  extra=['TreeCapture.MCP_SurfaceWeight.X',*normal_moments.channels()];data=render(mode+'-'+side+'-after',side,extra)
  assert all(data['TreeCapture.Combined.'+a]==baseline[side]['TreeCapture.Combined.'+a] for a in 'RGBA'),'Beauty changed: '+mode+'-'+side
  measure=normal_moments.measure({'channels':data},data[extra[0]],[data[n] for n in extra[1:]],.001)
  if mode=='linked_grazing':assert measure['input_moments_valid'] and not measure['normal_pass_first_moment_agrees'],(side,measure)
  else:assert measure['input_moments_valid'] and measure['normal_pass_first_moment_agrees'],(mode,side,measure)
  report[mode+'-'+side]={'contract':contract['normal_moments'],'measurement':measure,'beauty_exact':True};(out/'proof.json').write_text(json.dumps(report,indent=2));print('NORMAL_MOMENT_INPUT_DONE',mode,side,flush=True)
(out/'proof.json').write_text(json.dumps(report,indent=2));print('NORMAL_INPUT_MOMENTS_NATIVE_OK',flush=True)
