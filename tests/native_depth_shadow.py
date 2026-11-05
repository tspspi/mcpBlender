"""Native Cycles comparison: original source, primary, unmasked and masked rear.

Usage: blender ... --python this.py -- repo capture output
"""
import sys,json,math,shutil
from pathlib import Path
sys.path.insert(0,sys.argv[sys.argv.index("--")+1])
import bpy
from mathutils import Matrix
from mcpblender import capture_data,exr_scanline,image_comparison
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
out=Path(sys.argv[sys.argv.index('--')+3]);out.mkdir(parents=True,exist_ok=True)
bundle=Path(sys.argv[sys.argv.index('--')+2]).resolve()
_,_,meta,rows=capture_data.source(dict(directory=str(bundle),views=['FRONT','BACK'],max_pixels=1048576,max_total_pixels=2097152))
front=rows[0][0]
bpy.ops.wm.open_mainfile(filepath=str(bundle/'source.blend'))
settings={'geometry_mode':'ADAPTIVE_NORMAL','max_slope':64,'output_resolution':32}
# Both numerical cancellation and partial image allocation must leave no IDs.
trial=Source(directory=str(bundle),view='BACK',render_role='SHADOW_ONLY',settings=settings,shadow_mask={'receiver_view':'FRONT'}).model_dump()
trial_plan=api.prepared(trial)[0]
trial_create=Create(**trial,collection='CancelledLayer',expected_plan=trial_plan['plan_sha256'],accept_approximate_optics=True).model_dump()
before=set(bpy.data.user_map())
for phase in ('pairing opposed shadow depth samples','creating packed directional data images'):
 def cancel(value):
  if value.get('phase')==phase and (phase.startswith('pairing') or value.get('completed')==1):raise bridge.OperationCancelled('mask cancellation control')
 bridge.report_progress=cancel
 try:api.create(trial_create)
 except bridge.OperationCancelled:pass
 else:raise AssertionError('Cancellation ignored')
 assert set(bpy.data.user_map())==before,'Masked asset rollback leaked IDs'
bridge.report_progress=lambda v:None
try:api.create(trial_create|{'shadow_mask':{'receiver_view':'FRONT','minimum_span_m':.01}})
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Mask threshold change accepted a stale plan')
assert set(bpy.data.user_map())==before
assets={}
for name,view,role,mask in [('primary','FRONT','ALL_RAYS',None),('unmasked','BACK','SHADOW_ONLY',None),('masked','BACK','SHADOW_ONLY',{'receiver_view':'FRONT'})]:
 args=Source(directory=str(bundle),view=view,render_role=role,settings=settings,shadow_mask=mask).model_dump();plan=api.prepared(args)[0]
 assets[name]=api.create(Create(**args,collection='Layer'+name,expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump())
assert assets['masked']['plan']['shadow_mask']['retained_alpha_mass']<assets['masked']['plan']['shadow_mask']['original_alpha_mass']
# Packed independent data and plan survive source-independent native readback.
bpy.ops.wm.save_as_mainfile(filepath=str(out/'layers.blend'))
bpy.ops.wm.open_mainfile(filepath=str(out/'layers.blend'))
for made in assets.values():
 state=api.inspect({'collection':made['collection']})[-1]
 assert state['valid'] and state['asset_sha256']==made['asset_sha256']
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Occlusion';s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
for obj in list(s.objects):
 if obj.type=='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=front['ortho_scale'];cam.data.clip_start=front['clip_start'];cam.data.clip_end=front['clip_end'];cam.matrix_world=Matrix(front['matrix_world']);s.camera=cam
cols={key:bpy.data.collections['Layer'+key] for key in assets}
source_cols=[c for c in s.collection.children if c not in cols.values()]
variants=['source','primary','unmasked','masked']
proof={'assets':assets,'comparisons':{},'scope':'Guarded authoring; small fixture, matched front camera at 32 square pixels only. No all-angle, population or general optical qualification.'}
for lighting in ('world','sun_front','sun_back'):
 s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0;sun=None;reference=None
 if lighting!='world':
  data=bpy.data.lights.new('Sun','SUN');data.energy=2;data.angle=0;sun=bpy.data.objects.new('Sun',data);s.collection.objects.link(sun);sun.rotation_euler=cam.rotation_euler
  if lighting=='sun_back':sun.rotation_euler.rotate_axis('Y',math.pi)
 for variant in variants:
  assert shutil.disk_usage(out).free>2*1024**3
  for col in source_cols:col.hide_render=variant!='source'
  for key,col in cols.items():col.hide_render=variant=='source' or (key!='primary' and key!=variant)
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False);s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(lighting+'-'+variant+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s);ch=exr_scanline.decode(path,['Occlusion.Combined.'+a for a in 'RGBA'])['channels'];rgba=[ch['Occlusion.Combined.'+a][i] for i in range(32*32) for a in 'RGBA']
  if variant=='source':reference=rgba
  else:
   row=image_comparison.measure(reference,rgba,32,32,.5,lambda:None);proof['comparisons'][lighting+'-'+variant]=row;print('OCCLUSION',lighting,variant,row['overlap_luminance_relative_bias'],flush=True);(out/'proof.json').write_text(json.dumps(proof,indent=2))
 if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
for col in cols.values():col.hide_render=True
for made in assets.values():
 state=api.inspect({'collection':made['collection']})[-1];assert state['valid'] and state['asset_sha256']==made['asset_sha256']
# Packed alpha edits are guarded, including after all render visibility is restored.
_,owned,meta,state=api.inspect({'collection':'Layermasked'})
image=bpy.data.images[meta['images']['base_coverage']];values=list(image.pixels[:]);values[3]=.5
image.pixels.foreach_set(values)
bad=api.inspect({'collection':'Layermasked'})[-1];assert not bad['valid']
try:api.remove({'collection':'Layermasked','expected_asset':bad['asset_sha256']})
except ValueError:pass
else:raise AssertionError('Mutated shadow data removed as an unchanged asset')
bpy.ops.wm.open_mainfile(filepath=str(out/'layers.blend'))
for made in assets.values():
 state=api.inspect({'collection':made['collection']})[-1];assert state['valid']
 removed=api.remove({'collection':made['collection'],'expected_asset':state['asset_sha256']});assert removed['private_datablocks']==11
assert not any(v.get(api.OWNER) for v in bpy.data.user_map())
print('PAIRED_SHADOW_NATIVE_OK')
