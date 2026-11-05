"""Compare real captured canopy coverage density at a declared output grid."""
import sys,json,shutil
from pathlib import Path
argv=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,argv[0])
import bpy
from mathutils import Matrix
from mcpblender import image_comparison,exr_scanline
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda value:None
out=Path(argv[3]);out.mkdir(parents=True,exist_ok=True);proof={}
for resolution in (32,128):
 source=Path(argv[1] if resolution==32 else argv[2]).resolve();bpy.ops.wm.open_mainfile(filepath=str(source/'source.blend'))
 args=Source(directory=str(source),view='FRONT',settings={'output_resolution':32,'tile_pixels':4}).model_dump();plan=api.prepared(args)[0];created=api.create(Create(**args,collection='SamplingProxy',expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump());assert created['valid']
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Sampling';s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
 for obj in list(s.objects):
  if obj.type=='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
 view=plan['source']['view'];cam=bpy.data.objects.new('SamplingCamera',bpy.data.cameras.new('SamplingCamera'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=view['ortho_scale'];cam.data.clip_start=view['clip_start'];cam.data.clip_end=view['clip_end'];cam.matrix_world=Matrix(view['matrix_world']);s.camera=cam
 asset=bpy.data.collections['SamplingProxy'];source_cols=[c for c in s.collection.children if c!=asset];images={}
 for kind in ('source','proxy'):
  assert shutil.disk_usage(out).free>2*1024**3
  asset.hide_render=kind=='source'
  for col in source_cols:col.hide_render=kind!='source'
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False);s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/f'{resolution}-{kind}.exr';bpy.data.images['Render Result'].save_render(str(path),scene=s)
  ch=exr_scanline.decode(path,['Sampling.Combined.'+a for a in 'RGBA'])['channels'];images[kind]=[ch['Sampling.Combined.'+a][i] for i in range(32*32) for a in 'RGBA']
 metrics=image_comparison.measure(images['source'],images['proxy'],32,32,.5,lambda:None);proof[str(resolution)]={'plan':plan,'created':created,'metrics':metrics,'render_samples':256,'output_resolution':32}
 print('CANOPY_SAMPLING',resolution,metrics['mask_iou'],metrics['soft_alpha_iou'],metrics['alpha_mae'],metrics['overlap_luminance_relative_bias'],flush=True);(out/'proof.json').write_text(json.dumps(proof,indent=2))
print('CANOPY_DENSITY_COMPLETE')
