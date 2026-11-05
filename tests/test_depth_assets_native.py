"""Native transactional cleanup, unit placement, packed readback and ownership."""
import os
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_DEPTH_NATIVE_SOURCE'),reason='Retained native material-field archive required')
@pytest.mark.parametrize('geometry_mode',['FLAT','ADAPTIVE_NORMAL'])
def test_native_depth_rollback_placement_and_foreign_users(tmp_path,geometry_mode):
    script=tmp_path/'depth-native.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nSOURCE='+repr(str(Path(os.environ['MCPBLENDER_DEPTH_NATIVE_SOURCE']).resolve()))+'\nOUTPUT='+repr(str(tmp_path))+'\nMODE='+repr(geometry_mode)+'\n'+r'''
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
scene=bpy.context.scene;scene.unit_settings.scale_length=.1
args=Source(directory=SOURCE,view='FRONT',settings={'geometry_mode':MODE}).model_dump();plan,geometry,maps=api.prepared(args)
source=Matrix(plan['source']['source_root_matrix_world']);target=Matrix(plan['root_matrix_world'])
for point in [(0,0,0),(1,2,3),(-3,4,1)]:
    assert ((source@Vector(point))*plan['source']['scene_unit_scale']-(target@Vector(point))*.1).length<1e-5
p=Create(**args,collection='DepthNative',expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump()
before=set(bpy.data.user_map());recipe=api.SHADER_RECIPE;api.SHADER_RECIPE='CHANGED_RECIPE_CONTROL'
try:api.create(p)
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Changed shader recipe did not invalidate plan')
finally:api.SHADER_RECIPE=recipe
assert set(bpy.data.user_map())==before
original_objects={o.name:(o.type,[tuple(v.co) for v in o.data.vertices] if o.type=='MESH' else None) for o in scene.objects}
def fail(value):
    if value.get('phase')=='creating packed directional data images' and value['completed']==1:raise bridge.OperationCancelled('cancel after first packed image')
bridge.report_progress=fail
try:api.create(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Injected cancellation ignored')
assert set(bpy.data.user_map())==before,'Rollback leaked native datablocks'
bridge.report_progress=lambda v:None
made=api.create(p);assert made['valid'] and made['packed_images']==6
col,owned,meta,state=api.inspect({'collection':'DepthNative'});root=bpy.data.objects[meta['root']];obj=bpy.data.objects[meta['object']]
assert col.hide_render and col.hide_viewport
# Verify all packed signed/vector/scalar/alpha lanes, including mixed data alpha.
for name,expected in maps.items():
    image=next(v for v in owned if isinstance(v,bpy.types.Image) and v.name.endswith('-'+name));assert image.alpha_mode=='CHANNEL_PACKED' and image.packed_file
    w,h=image.size
    for x,y in [(0,0),(w//2,h//2),(w//3,h//3)]:
        a=(y*w+x)*4;b=((h-1-y)*w+x)*4
        assert max(abs(expected[a+j]-image.pixels[b+j]) for j in range(4))<1e-6,(name,x,y)
# Root movement and display toggles remain supported; source capture untouched.
root.location.x+=2;root.rotation_euler.z+=.3;col.hide_render=False;col.hide_viewport=False
state=api.inspect({'collection':'DepthNative'})[-1];assert state['valid'] and state['asset_sha256']!=made['asset_sha256']
try:api.remove({'collection':'DepthNative','expected_asset':made['asset_sha256']})
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Stale root/visibility guard accepted')
vertex=obj.data.vertices[0];saved=vertex.co.copy();vertex.co.x+=1
changed=api.inspect({'collection':'DepthNative'})[-1];assert not changed['valid']
try:api.remove({'collection':'DepthNative','expected_asset':changed['asset_sha256']})
except ValueError as exc:assert 'content' in str(exc)
else:raise AssertionError('Changed mesh removed')
vertex.co=saved
foreign=bpy.data.objects.new('ForeignDepthMeshUser',obj.data);scene.collection.objects.link(foreign)
blocked=api.inspect({'collection':'DepthNative'})[-1];assert not blocked['valid'] and blocked['ownership_blockers']
bpy.data.objects.remove(foreign,do_unlink=True)
state=api.inspect({'collection':'DepthNative'})[-1];assert state['valid']
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/packed.blend')
bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/packed.blend')
state=api.inspect({'collection':'DepthNative'})[-1];assert state['valid']
api.remove({'collection':'DepthNative','expected_asset':state['asset_sha256']})
assert not any(v.get(api.OWNER) for v in bpy.data.user_map())
for name,(kind,vertices) in original_objects.items():
    obj=bpy.data.objects[name];assert obj.type==kind
    if vertices is not None:assert [tuple(v.co) for v in obj.data.vertices]==vertices
print('DEPTH_ASSET_NATIVE_OK')
''')
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'DEPTH_ASSET_NATIVE_OK' in run.stdout


def test_native_packed_shader_lanes_and_rotated_root(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'packed-lanes.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,math
from mathutils import Matrix
from pathlib import Path
from mcpblender.blender import depth_assets as api
from mcpblender import exr_scanline
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=32;s.render.resolution_y=32;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_layers[0].name='Calibration'
values={'base_coverage':[.1,.2,.3,.6],'normal_roughness':[0,0,.5,.42],'emission':[.01,.02,.03,2.5],'thin':[.22,.42,.06,.22],'surface':[.1,1.42,.2,1],'witness':[1,0,2,1]}
images={}
for name,value in values.items():
    im=bpy.data.images.new(name,width=4,height=4,alpha=True,float_buffer=True);im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED';im.pixels.foreach_set(value*16);im.pack();images[name]=im
created=[];mat=api.material('PackedCalibration',images,created);tree=mat.node_tree
bs=next(n for n in tree.nodes if n.type=='BSDF_PRINCIPLED');thin=next(n for n in tree.nodes if n.type=='BSDF_TRANSLUCENT')
checks={'base':(bs.inputs['Base Color'],[.1,.2,.3]),'roughness':(bs.inputs['Roughness'],[.42]),'metallic':(bs.inputs['Metallic'],[.1]),'ior':(bs.inputs['IOR'],[1.42]),'transmission':(bs.inputs['Transmission Weight'],[.2]),'emission':(bs.inputs['Emission Color'],[.01,.02,.03]),'strength':(bs.inputs['Emission Strength'],[2.5]),'thin':(thin.inputs['Color'],[.22,.42,.06]),'normal':(bs.inputs['Normal'],[0,0,1])}
optical=next(n for n in tree.nodes if n.type=='MIX_SHADER' and n.inputs[1].links[0].from_node==bs)
coverage=next(n for n in tree.nodes if n.type=='MIX_SHADER' and n.inputs[1].links[0].from_node.type=='BSDF_TRANSPARENT')
checks.update(thin_weight=(optical.inputs[0],[.22]),coverage=(coverage.inputs[0],[.6]))
for name,(port,expected) in checks.items():
    aov=s.view_layers[0].aovs.add();aov.name=name;aov.type='COLOR' if len(expected)==3 else 'VALUE'
    output=tree.nodes.new('ShaderNodeOutputAOV');output.aov_name=name;tree.links.new(port.links[0].from_socket,output.inputs['Color' if len(expected)==3 else 'Value'])
aov=s.view_layers[0].aovs.add();aov.name='weight';aov.type='VALUE';n=tree.nodes.new('ShaderNodeOutputAOV');n.aov_name='weight';n.inputs['Value'].default_value=1
mesh=bpy.data.meshes.new('Plane');mesh.from_pydata([(-.8,-.8,0),(.8,-.8,0),(.8,.8,0),(-.8,.8,0)],[],[(0,1,2,3)]);uv=mesh.uv_layers.new();uv.data.foreach_set('uv',[0,0,1,0,1,1,0,1]);mesh.materials.append(mat)
obj=bpy.data.objects.new('Plane',mesh);s.collection.objects.link(obj);root=bpy.data.objects.new('MovableRoot',None);s.collection.objects.link(root);obj.parent=root
cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);s.collection.objects.link(cam);cd.type='ORTHO';cd.ortho_scale=2;s.camera=cam
for rotated in (False,True):
    root.matrix_basis=Matrix.Rotation(math.pi/2,4,'Y') if rotated else Matrix.Identity(4)
    cam.matrix_world=root.matrix_basis@Matrix.Translation((0,0,5));bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=Path(OUTPUT)/('rotated.exr' if rotated else 'rest.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
    names=['Calibration.weight.X',*('Calibration.'+name+'.'+axis for name,(_,expected) in checks.items() for axis in ('RGB' if len(expected)==3 else 'X'))]
    channels=exr_scanline.decode(path,names)['channels'];i=16*32+16;weight=channels['Calibration.weight.X'][i];assert weight>.9
    for name,(_,expected) in checks.items():
        if name=='normal' and rotated:expected=[1,0,0]
        actual=[channels['Calibration.'+name+'.'+axis][i]/weight for axis in ('RGB' if len(expected)==3 else 'X')]
        assert max(abs(a-b) for a,b in zip(actual,expected))<1e-5,(name,actual,expected,rotated)
print('PACKED_SHADER_LANES_AND_ROOT_NORMALS_OK')
''')
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'PACKED_SHADER_LANES_AND_ROOT_NORMALS_OK' in run.stdout
