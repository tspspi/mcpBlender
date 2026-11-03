"""Repair new target charts without modifying geometry or authored UV maps."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_folded_target_repair_and_budget(tmp_path):
    script=tmp_path/'repair.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import vegetation_bake as prep,bridge,textures,uv
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
mesh=bpy.data.meshes.new('Charts');mesh.from_pydata([(0,0,0),(1,0,0),(1,1,.2),(0,1,0)],[],[(0,1,2,3)]);mesh.update()
obj=bpy.data.objects.new('Charts',mesh);bpy.context.scene.collection.objects.link(obj)
authored=mesh.uv_layers.new(name='Authored');authored.data.foreach_set('uv',[0,0,1,0,1,1,0,1])
target=mesh.uv_layers.new(name='BakeUV');target.data.foreach_set('uv',[0,0,1,1,1,0,0,1]);mesh.uv_layers.active=target
before=textures.mesh_signature(obj,mesh);coords=[tuple(v.uv) for v in target.data]
try:prep.repair_charts(obj,'BakeUV',.02,0)
except ValueError as e:assert 'repair budget' in str(e)
else:raise AssertionError('Disabled repair accepted folded UVs')
assert [tuple(v.uv) for v in mesh.uv_layers['BakeUV'].data]==coords
assert prep.repair_charts(obj,'BakeUV',.02,1)==[0]
after=textures.mesh_signature(obj,mesh)
assert all(before[k]==after[k] for k in ('geometry','matrix','corner_normals','materials','texspace'))
assert dict(before['uv'])['Authored']==dict(after['uv'])['Authored']
coordinates,islands,triangles=uv.layout(mesh,mesh.uv_layers['BakeUV'],obj.matrix_world,1024,1024)
assert all(0<=v<=1.000001 for p in coordinates for v in p) and all(i['uv_area']>0 for i in islands)
assert uv.overlaps(triangles,100)['complete'] and not uv.overlaps(triangles,100)['face_pairs']
print('BAKE_UV_REPAIR_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BAKE_UV_REPAIR_OK' in result.stdout


def test_default_oak_wood_bake_layout(tmp_path):
    import os
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'default.py'
    output=os.environ.get('MCPBLENDER_UV_SCALABILITY_EVIDENCE_DIR',str(tmp_path))
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(output)+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany
from mcpblender.blender import botanical_trees as trees,vegetation_bake as prep,bridge,uv
from mcpblender.vegetation_bake_contracts import Source
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe=botany.recipe({});plan=trees.plan({'recipe':recipe})
tree=trees.create({'collection':'Oak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
p=Source(collection='Oak',assets=['wood'],max_corners=500000).model_dump();planned=prep.plan(p)[-1]
assert tree['metrics']['height']==14 and planned['corners']>40000
state=prep.create(p|{'expected_plan':planned['plan_sha256'],'bake_collection':'Bake'})
assert state['valid'] and trees.inspect({'collection':'Oak'})['tree_sha256']==tree['tree_sha256']
row=state['components']['wood'];obj=bpy.data.objects[row['name']]
_,islands,triangles=uv.layout(obj.data,obj.data.uv_layers['BakeUV'],obj.matrix_world,1024,1024);overlap=uv.overlaps(triangles,200000)
assert overlap['complete'] and not overlap['face_pairs'] and all(i['uv_area']>1e-20 for i in islands)
proof={'branches':tree['metrics']['branches'],'height':14,'corners':planned['corners'],'repaired_faces':row['repaired_uv_faces'],'overlap':overlap,'source_unchanged':True}
root=Path(OUTPUT);root.mkdir(parents=True,exist_ok=True);(root/'proof.json').write_text(json.dumps(proof,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'prepared.blend'))
print('DEFAULT_OAK_UV_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'DEFAULT_OAK_UV_OK' in result.stdout
