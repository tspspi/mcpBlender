"""Native front invariance and back-face shading versus implicit normal reference."""
from pathlib import Path
import os
import subprocess
from test_botanical_native import pytestmark


def test_captured_normals_follow_geometric_sidedness(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'sided.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from mathutils import Matrix
from pathlib import Path
from mcpblender.blender import depth_assets as api
from mcpblender import exr_scanline
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].use_pass_normal=True;s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
values={'base_coverage':[.2,.2,.2,1],'normal_roughness':[0,0,1,.65],'emission':[0,0,0,0],'thin':[.2,.2,.2,0],'surface':[0,1.5,0,1],'witness':[0,0,1,1]};images={}
for name,value in values.items():
 im=bpy.data.images.new(name,width=4,height=4,alpha=True,float_buffer=True);im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED';im.pixels.foreach_set(value*16);im.pack();images[name]=im
created=[];fixed=api.material('Fixed',images,created);legacy=fixed.copy();legacy.name='LegacyControl';reference=fixed.copy();reference.name='ImplicitReference'
for material in (legacy,reference):
 tree=material.node_tree;normal=next(n for n in tree.nodes if n.type=='VECT_MATH' and n.operation=='NORMALIZE')
 for node in (n for n in tree.nodes if n.type in {'BSDF_PRINCIPLED','BSDF_TRANSLUCENT'}):
  for link in list(node.inputs['Normal'].links):tree.links.remove(link)
  if material==legacy:tree.links.new(normal.outputs[0],node.inputs['Normal'])
mesh=bpy.data.meshes.new('Plane');mesh.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[],[(0,1,2,3)]);mesh.materials.append(fixed);uv=mesh.uv_layers.new();uv.data.foreach_set('uv',[0,0,1,0,1,1,0,1]);obj=bpy.data.objects.new('Plane',mesh);s.collection.objects.link(obj);root=bpy.data.objects.new('Root',None);s.collection.objects.link(root);obj.parent=root
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);s.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=6
report={}
def render(label,material,back):
 mesh.materials[0]=material
 camera.matrix_world=root.matrix_basis@(Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,-5),(0,0,0,1))) if back else Matrix.Translation((0,0,5)));bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
 s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=Path(OUTPUT)/(label+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
 names=['ViewLayer.Combined.'+a for a in 'RGBA']+['ViewLayer.Normal.'+a for a in 'XYZ'];channels=exr_scanline.decode(path,names)['channels'];i=16*32+16
 report[label]={k:v[i] for k,v in channels.items()};return channels
for rotated in (False,True):
 root.matrix_basis=(Matrix.Rotation(1.5707963267948966,4,'Y') if rotated else Matrix.Identity(4))@Matrix.Scale(2,4)
 for thin in (False,True):
  im=images['thin'];im.pixels.foreach_set([.2,.2,.2,.22 if thin else 0]*16);im.pack()
  label=str(rotated)+'-'+str(thin)
  old=render(label+'-front-old',legacy,False);front=render(label+'-front-fixed',fixed,False)
  assert all(front[k]==old[k] for k in front),'Front primary rendering changed'
  back=render(label+'-back-fixed',fixed,True);native=render(label+'-back-reference',reference,True)
  for axis in 'RGB':
   key='ViewLayer.Combined.'+axis;assert abs(back[key][16*32+16]-native[key][16*32+16])<1e-6
   assert back[key][16*32+16]>.03
  expected=[-1,0,0] if rotated else [0,0,-1]
  assert max(abs(back['ViewLayer.Normal.'+a][16*32+16]-e) for a,e in zip('XYZ',expected))<1e-6
  if not thin:
   broken=render(label+'-back-old',legacy,True)
   assert broken['ViewLayer.Combined.R'][16*32+16]==0
(Path(OUTPUT)/'proof.json').write_text(json.dumps(report,indent=2));print('SIDED_NORMALS_NATIVE_OK')
''')
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'SIDED_NORMALS_NATIVE_OK' in run.stdout
    if destination:=os.environ.get('MCPBLENDER_SIDED_NORMAL_EVIDENCE'):
        import shutil
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        shutil.copy2(tmp_path/'proof.json',out/'plane-proof.json')
