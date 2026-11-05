"""Measure native small-canopy moment reconstruction; report quality failures."""
import sys,json,shutil,math
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mathutils import Matrix
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
from mcpblender import exr_scanline,image_comparison
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda value:None
source=Path(args[1]).resolve();out=Path(args[2]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source/'source.blend'))
args=Source(directory=str(source),view='FRONT',settings={'geometry_mode':'MOMENT_FACETS','max_moment_candidates':64}).model_dump();plan=api.prepared(args)[0]
created=api.create(Create(**args,collection='CanopyMoment',expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump());assert created['valid']
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.cycles.use_adaptive_sampling=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=64;s.render.resolution_y=64;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Qualification';s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
for obj in list(s.objects):
 if obj.type=='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
view=plan['source']['view'];cam=bpy.data.objects.new('QualificationCamera',bpy.data.cameras.new('QualificationCamera'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=view['ortho_scale'];cam.data.clip_start=view['clip_start'];cam.data.clip_end=view['clip_end'];cam.matrix_world=Matrix(view['matrix_world']);s.camera=cam
asset=bpy.data.collections['CanopyMoment'];source_cols=[c for c in s.collection.children if c!=asset]
proof={'plan':plan,'created':created,'render_samples':32,'resolution':64,'scope':'Actual small canopy primary comparison with native secondary transport enabled; not a dense or angular qualification','comparisons':{}}
for lighting in ('world','sun_front','sun_back'):
 s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0
 sun=None
 if lighting!='world':
  data=bpy.data.lights.new('QualificationSun','SUN');data.energy=2;data.angle=0;sun=bpy.data.objects.new('QualificationSun',data);s.collection.objects.link(sun);sun.rotation_euler=cam.rotation_euler
  if lighting=='sun_back':sun.rotation_euler.rotate_axis('Y',math.pi)
 images={}
 for kind in ('source','reconstruction'):
  assert shutil.disk_usage(out).free>2*1024**3
  asset.hide_render=kind=='source';asset.hide_viewport=False
  for col in source_cols:col.hide_render=kind!='source'
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
  s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(lighting+'-'+kind+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
  ch=exr_scanline.decode(path,['Qualification.Combined.'+a for a in 'RGBA'])['channels'];images[kind]=[v for i in range(64*64) for a in 'RGBA' for v in [ch['Qualification.Combined.'+a][i]]]
 metrics=image_comparison.measure(images['source'],images['reconstruction'],64,64,.5,lambda:None);proof['comparisons'][lighting]=metrics
 print('CANOPY_COMPARE',lighting,metrics['overlap_luminance_relative_bias'],flush=True)
 (out/'proof.json').write_text(json.dumps(proof,indent=2))
 if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
for col in source_cols:col.hide_render=False
asset.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(out/'canopy-moment.blend'))
print('CANOPY_CANDIDATE_NATIVE_COMPLETE')
