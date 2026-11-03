"""Native bake preparation retains dense zero face material-index attributes."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_new_uv_preparation_preserves_dense_zero_material_indices(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'defaults.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import vegetation_bake as prep,bridge,assemblies,textures
from mcpblender.vegetation_bake_contracts import Source
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None
bpy.ops.mesh.primitive_plane_add();obj=bpy.context.object
mat=bpy.data.materials.new('Source');mat.use_nodes=True;obj.data.materials.append(mat)
if 'material_index' not in obj.data.attributes:obj.data.attributes.new(name='material_index',type='INT',domain='FACE')
before=assemblies.attribute_records(obj.data);witness=textures.mesh_signature(obj,obj.data)
# A static source fixture exercises the complete owned preparation implementation.
prep.objects=lambda p:({'wood':obj},'a'*64)
p=Source(collection='StaticFixture',tile_padding_pixels=4,texture_width=128,texture_height=128).model_dump()
planned=prep.plan(p)[-1];state=prep.create(p|{'bake_collection':'Prepared','expected_plan':planned['plan_sha256']})
assert state['valid']
target=bpy.data.objects[state['components']['wood']['name']]
actual={a['name']:a for a in assemblies.attribute_records(target.data)}
assert all(actual.get(a['name'])==a for a in before if not a['name'].startswith('.'))
assert textures.mesh_signature(obj,obj.data)==witness
assert target.data.attributes['material_index'].data[0].value==0
prep.remove({'bake_collection':'Prepared','expected_preparation':state['preparation_sha256']})
print('DENSE_DEFAULT_FACE_ATTRIBUTE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'DENSE_DEFAULT_FACE_ATTRIBUTE_OK' in result.stdout
