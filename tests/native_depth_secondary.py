"""Guarded dense secondary-role authoring; compare frozen source and controls.

Usage: blender ... --python this.py -- repo capture baseline control output
The baseline and control are the retained dense shadow and private ray-role runs.
"""
import sys,json,math,time,shutil
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]
sys.path.insert(0,args[0])
import bpy
from mathutils import Matrix
from mcpblender import capture_data,exr_comparison
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
bundle,baseline,control,out=map(Path,args[1:]);out.mkdir(parents=True,exist_ok=True)
bridge.check_cancelled=lambda:None
last=[0.]
def progress(value):
 if time.monotonic()-last[0]>15:print('SECONDARY_PROGRESS',value,flush=True);last[0]=time.monotonic()
bridge.report_progress=progress
_,_,_,rows=capture_data.source(dict(directory=str(bundle),views=['FRONT','BACK'],max_pixels=1048576,max_total_pixels=2097152))
front=rows[0][0];proof={'roles':{},'scope':'Guarded native camera-excluded mask roles, dense fixture matched FRONT camera at 128px and three lights only. Report quality rejection, not qualified optical equivalence.'}
for role in ('DIFFUSE_SHADOW','SECONDARY'):
 bpy.ops.wm.open_mainfile(filepath=str(baseline/'layers.blend'))
 original=api.inspect({'collection':'Layermasked'})[-1];assert original['valid']
 removed=api.remove({'collection':'Layermasked','expected_asset':original['asset_sha256']});assert removed['private_datablocks']==11
 source=Source(directory=str(bundle),view='BACK',render_role=role,shadow_mask={'receiver_view':'FRONT'},settings=original['plan']['geometry']['options']).model_dump()
 plan=api.prepared(source)[0]
 assert plan['geometry']==original['plan']['geometry'] and plan['maps']==original['plan']['maps']
 assert plan['shadow_mask']['mask_float32_sha256']==original['plan']['shadow_mask']['mask_float32_sha256']
 print('SECONDARY_PLAN',role,plan['geometry']['triangles'],flush=True)
 made=api.create(Create(**source,collection='Layermasked',expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump())
 assert made['valid'] and made['ray_visibility']==plan['ray_visibility'] and made['render_role']==role
 blend=out/(role+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.wm.open_mainfile(filepath=str(blend))
 reopened=api.inspect({'collection':'Layermasked'})[-1];assert reopened['valid'] and reopened['asset_sha256']==made['asset_sha256']
 primary=api.inspect({'collection':'Layerprimary'})[-1];assert primary['valid']
 proof['roles'][role]={'created':made,'reopened':reopened,'comparisons':{},'control_checks':{}}
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=128;s.render.resolution_y=128;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Occlusion';s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
 for obj in list(s.objects):
  if obj.type=='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
 cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=front['ortho_scale'];cam.data.clip_start=front['clip_start'];cam.data.clip_end=front['clip_end'];cam.matrix_world=Matrix(front['matrix_world']);s.camera=cam
 cols=[bpy.data.collections['Layerprimary'],bpy.data.collections['Layermasked']]
 for col in s.collection.children:col.hide_render=col not in cols
 for lighting in ('world','sun_front','sun_back'):
  assert shutil.disk_usage(out).free>2*1024**3
  s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0;sun=None
  if lighting!='world':
   data=bpy.data.lights.new('Sun','SUN');data.energy=2;data.angle=0;sun=bpy.data.objects.new('Sun',data);s.collection.objects.link(sun);sun.rotation_euler=cam.rotation_euler
   if lighting=='sun_back':sun.rotation_euler.rotate_axis('Y',math.pi)
  print('SECONDARY_RENDER',role,lighting,flush=True)
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
  s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP'
  path=out/(lighting+'-'+role+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
  result=exr_comparison.compare(baseline/(lighting+'-source.exr'),path,reference_pass='Occlusion.Combined',candidate_pass='Occlusion.Combined',policy={'max_overlap_rgb_rmse':.05,'max_abs_overlap_luminance_relative_bias':.1})
  check=exr_comparison.compare(control/(lighting+'-'+role+'.exr'),path,reference_pass='Occlusion.Combined',candidate_pass='Occlusion.Combined',scales=[1],policy={'max_premultiplied_rgb_rmse':1e-6,'max_alpha_mae':1e-6})
  assert check['passed'],'Supported authored role differs from isolated control'
  proof['roles'][role]['comparisons'][lighting]=result;proof['roles'][role]['control_checks'][lighting]=check
  print('SECONDARY_MEASURED',role,lighting,result['levels'][0]['overlap_luminance_relative_bias'],result['passed'],flush=True)
  (out/'proof.json').write_text(json.dumps(proof,indent=2))
  if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
 for col in cols:col.hide_render=True
 state=api.inspect({'collection':'Layermasked'})[-1];assert state['valid'] and state['asset_sha256']==made['asset_sha256']
 for collection in ('Layermasked','Layerprimary'):
  state=api.inspect({'collection':collection})[-1]
  assert api.remove({'collection':collection,'expected_asset':state['asset_sha256']})['private_datablocks']==11
 assert not any(v.get(api.OWNER) for v in bpy.data.user_map())
print('SECONDARY_DENSE_NATIVE_OK',flush=True)
