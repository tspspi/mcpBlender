"""Native constant/linked input calibration and front/back thin-leaf preservation."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_native_material_fields_and_side_semantics(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'material-fields.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy
from mathutils import Matrix
from pathlib import Path
from mcpblender import exr_scanline,capture_material_fields as schema
from mcpblender.blender import capture_material_fields as api,botanical_foliage
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.view_layers[0].name='TreeCapture';s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.render.film_transparent=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100
mesh=bpy.data.meshes.new('Plane');mesh.from_pydata([(-.73,-.73,0),(.73,-.73,0),(.73,.73,0),(-.73,.73,0)],[],[(0,1,2,3)]);obj=bpy.data.objects.new('Plane',mesh);s.collection.objects.link(obj)
data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);s.collection.objects.link(camera);s.camera=camera;data.type='ORTHO';data.ortho_scale=2;camera.location=(0,0,5)
material=bpy.data.materials.new('Principled');material.use_nodes=True;bs=material.node_tree.nodes['Principled BSDF'];bs.inputs['Alpha'].default_value=.6;bs.inputs['Metallic'].default_value=.1;bs.inputs['IOR'].default_value=1.42;bs.inputs['Transmission Weight'].default_value=.2;bs.inputs['Emission Color'].default_value=(.01,.02,.03,1);bs.inputs['Emission Strength'].default_value=2
rgb=material.node_tree.nodes.new('ShaderNodeRGB');rgb.outputs[0].default_value=(.1,.3,.5,1);material.node_tree.links.new(rgb.outputs[0],bs.inputs['Base Color'])
value=material.node_tree.nodes.new('ShaderNodeValue');value.outputs[0].default_value=.42;material.node_tree.links.new(value.outputs[0],bs.inputs['Roughness']);mesh.materials.append(material)
bs.mute=True
try:api.describe([material])
except ValueError as exc:assert 'unmuted' in str(exc)
else:raise AssertionError('Muted surface accepted')
bs.mute=False
contract=api.describe([material]);original=material.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_socket
# Default-input edits refuse before adding any worker AOV nodes.
bs.inputs['Metallic'].default_value=.4;count=len(material.node_tree.nodes)
try:api.install(s,contract)
except ValueError as exc:assert 'changed' in str(exc)
else:raise AssertionError('Changed snapshot binding accepted')
assert len(material.node_tree.nodes)==count;bs.inputs['Metallic'].default_value=.1
api.install(s,contract);assert material.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_socket==original

def render(name):
    s.frame_set(1);bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP'
    path=Path(OUTPUT)/(name+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
    return exr_scanline.decode(path,[*schema.channels(),'TreeCapture.Combined.A'])

def straight(data,key):
    row=next(f for f in schema.FIELDS if f['key']==key);i=16*32+16;w=data['channels']['TreeCapture.MCP_SurfaceWeight.X'][i]
    assert w>.99
    return [data['channels']['TreeCapture.'+row['name']+'.'+axis][i]/w for axis in ('RGB' if row['type']=='COLOR' else 'X')]

def near(actual,expected):assert len(actual)==len(expected) and max(abs(a-b) for a,b in zip(actual,expected))<1e-5,(actual,expected)
fields=render('principled');near(straight(fields,'base_color'),[.1,.3,.5]);near(straight(fields,'roughness'),[.42]);near(straight(fields,'metallic'),[.1]);near(straight(fields,'alpha'),[.6]);near(straight(fields,'ior'),[1.42]);near(straight(fields,'transmission_weight'),[.2]);near(straight(fields,'emission_color'),[.01,.02,.03]);near(straight(fields,'emission_strength'),[2]);near(straight(fields,'thin_mode'),[0]);near(straight(fields,'thin_weight'),[0])
assert abs(fields['channels']['TreeCapture.Combined.A'][16*32+16]-fields['channels']['TreeCapture.MCP_SurfaceWeight.X'][16*32+16])>.1
leaf=botanical_foliage.material('Leaf');mesh.materials.clear();mesh.materials.append(leaf);contract=api.describe([leaf]);before=leaf.node_tree.nodes['Output'].inputs['Surface'].links[0].from_socket;api.install(s,contract);assert leaf.node_tree.nodes['Output'].inputs['Surface'].links[0].from_socket==before
front=render('leaf-front');near(straight(front,'base_color'),[.055,.20,.012]);near(straight(front,'thin_mode'),[1]);near(straight(front,'thin_weight'),[.22]);near(straight(front,'transmission_weight'),[0]);near(straight(front,'thin_color'),[.22,.42,.06])
camera.matrix_world=Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,-5),(0,0,0,1)))
back=render('leaf-back');near(straight(back,'base_color'),[.12,.28,.035]);near(straight(back,'thin_weight'),[.22])
print('NATIVE_MATERIAL_FIELDS_CALIBRATED')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'NATIVE_MATERIAL_FIELDS_CALIBRATED' in result.stdout
