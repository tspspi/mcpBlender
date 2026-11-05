"""Dense depth-aware asset authoring and an explicitly private hybrid control.

Usage: blender ... --python this.py -- repo capture baseline output
"""
import sys,json,math,shutil,time
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]
sys.path.insert(0,args[0])
import bpy
from mathutils import Matrix
from mcpblender import capture_data,exr_scanline,image_comparison
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
bridge.check_cancelled=lambda:None
last=[0]
def progress(p):
 if time.monotonic()-last[0]>15:print('DENSE_PROGRESS',p,flush=True);last[0]=time.monotonic()
bridge.report_progress=progress
out=Path(args[3]);out.mkdir(parents=True,exist_ok=True)
bundle=Path(args[1]).resolve()
_,_,meta,rows=capture_data.source(dict(directory=str(bundle),views=['FRONT','BACK'],max_pixels=1048576,max_total_pixels=2097152))
front=rows[0][0]
baseline=Path(args[2])
bpy.ops.wm.open_mainfile(filepath=str(baseline/'layers.blend'))
original=api.inspect({'collection':'Layerprimary'})[-1];assert original['valid']
assert api.remove({'collection':'Layerprimary','expected_asset':original['asset_sha256']})['private_datablocks']==11
settings=original['plan']['geometry']['options']|{'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','depth_tolerance_m':.05,'max_refinement_work':16000000}
source=Source(directory=str(bundle),view='FRONT',settings=settings).model_dump()
plan=api.prepared(source)[0];assert plan['maps']==original['plan']['maps']
made=api.create(Create(**source,collection='Layerprimary',expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump())
assert made['valid'] and 'depth_residuals' in made['plan']['geometry']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'refined.blend'));bpy.ops.wm.open_mainfile(filepath=str(out/'refined.blend'))
assets={name:api.inspect({'collection':'Layer'+name})[-1] for name in ('primary','masked')}
assert all(v['valid'] for v in assets.values()) and assets['primary']['asset_sha256']==made['asset_sha256']
primary=bpy.data.objects[assets['primary']['object']]
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=128;s.render.resolution_y=128;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Occlusion';s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
for obj in list(s.objects):
 if obj.type=='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=front['ortho_scale'];cam.data.clip_start=front['clip_start'];cam.data.clip_end=front['clip_end'];cam.matrix_world=Matrix(front['matrix_world']);s.camera=cam
cols={key:bpy.data.collections['Layer'+key] for key in assets}
source_cols=[c for c in s.collection.children if c not in cols.values()]
source_objects={o for col in source_cols for o in col.all_objects}
source_flags={o.name:{key:getattr(o,key) for key in api.RAY_FLAGS} for o in source_objects}
primary_flags={key:getattr(primary,key) for key in api.RAY_FLAGS}
variants=['native','primary','hybrid']
proof={'assets':assets,'comparisons':{},'baseline_checks':{},'scope':'Depth-refined primary is supported and guarded; hybrid is a PRIVATE camera-only flag control invalidating its ALL_RAYS guard. Original source flags restored before final inspect. No optical or hybrid delivery equivalence.'}
from mcpblender import exr_comparison
for lighting in ('world','sun_front','sun_back'):
 s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0;sun=None;reference=None
 if lighting!='world':
  data=bpy.data.lights.new('Sun','SUN');data.energy=2;data.angle=0;sun=bpy.data.objects.new('Sun',data);s.collection.objects.link(sun);sun.rotation_euler=cam.rotation_euler
  if lighting=='sun_back':sun.rotation_euler.rotate_axis('Y',math.pi)
 for variant in variants:
  print('DENSE_RENDER',lighting,variant,flush=True)
  assert shutil.disk_usage(out).free>2*1024**3
  for col in source_cols:col.hide_render=variant=='primary'
  cols['primary'].hide_render=variant=='native';cols['masked'].hide_render=True
  for obj in source_objects:obj.visible_camera=False if variant=='hybrid' else source_flags[obj.name]['visible_camera']
  for key in api.RAY_FLAGS:setattr(primary,key,key in api.RAY_ROLES['CAMERA_ONLY'] if variant=='hybrid' else primary_flags[key])
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False);s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(lighting+'-'+variant+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s);ch=exr_scanline.decode(path,['Occlusion.Combined.'+a for a in 'RGBA'])['channels'];rgba=[ch['Occlusion.Combined.'+a][i] for i in range(128*128) for a in 'RGBA']
  channels=exr_scanline.decode(baseline/(lighting+'-source.exr'),['Occlusion.Combined.'+a for a in 'RGBA'])['channels']
  reference=[channels['Occlusion.Combined.'+a][i] for i in range(128*128) for a in 'RGBA']
  row=image_comparison.measure(reference,rgba,128,128,.5,lambda:None)
  proof['comparisons'][lighting+'-'+variant]=row
  if variant=='native':
   frozen='source' if variant=='native' else 'primary'
   proof['baseline_checks'][lighting+'-'+variant]=exr_comparison.compare(baseline/(lighting+'-'+frozen+'.exr'),path,reference_pass='Occlusion.Combined',candidate_pass='Occlusion.Combined',scales=[1],policy={'max_premultiplied_rgb_rmse':1e-6,'max_alpha_mae':1e-6})
   assert proof['baseline_checks'][lighting+'-'+variant]['passed'],'Frozen baseline changed'
  print('HYBRID_SECONDARY',lighting,variant,row['overlap_luminance_relative_bias'],flush=True)
  (out/'proof.json').write_text(json.dumps(proof,indent=2))
 if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
for obj in source_objects:
 for key,value in source_flags[obj.name].items():setattr(obj,key,value)
for key,value in primary_flags.items():setattr(primary,key,value)
for col in cols.values():col.hide_render=True
for made in assets.values():assert api.inspect({'collection':made['collection']})[-1]['valid']
for collection in ('Layerprimary','Layermasked'):
 state=api.inspect({'collection':collection})[-1]
 assert api.remove({'collection':collection,'expected_asset':state['asset_sha256']})['private_datablocks']==11
assert not any(v.get(api.OWNER) for v in bpy.data.user_map())
print('DEPTH_REFINEMENT_NATIVE_OK',flush=True)
