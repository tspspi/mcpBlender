"""Multi-view planning keeps individual guards and source/units unchanged."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_view_family_native_guards_budgets_and_rollback(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'views.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.card_contracts import Views
from mcpblender.blender import foliage_cards as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
obj=bpy.data.objects['Cube'];obj.rotation_euler=(.2,.3,.4)
for unit in (1,.01):
 bpy.context.scene.unit_settings.scale_length=unit;unit=bpy.context.scene.unit_settings.scale_length;obj.scale=(.06/unit,.1/unit,.05/unit);obj.location=(.2/unit,.3/unit,.01/unit);bpy.context.view_layer.update()
 args=Views(sources=['Cube'],resolution=64).model_dump();before=set(bpy.data.user_map());matrix=obj.matrix_world.copy();location=list(obj.location);selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
 family=api.views(args);assert family==api.views(args) and family['projected_triangles']==36
 assert family['total_card_triangles']==sum(r['card']['triangles'] for r in family['views'])
 for row in family['views']:
  assert api.inspect(row['create_parameters'])['card_sha256']==row['card']['card_sha256']
  assert row['camera_frame_view']=={'TOP':'TOP','FRONT':'FRONT','SIDE':'RIGHT'}[row['view']]
 for patch,message in (({'max_projected_triangles':35},'projected triangle'),({'max_total_card_triangles':1},'total card triangle')):
  try:api.views(args|patch)
  except ValueError as e:assert message in str(e)
  else:raise AssertionError('Family budget ignored')
 def stop(v):
  if v.get('phase')=='fitting foliage card alternatives' and v.get('view')=='FRONT':raise bridge.OperationCancelled('second view')
 bridge.report_progress=stop
 try:api.views(args)
 except bridge.OperationCancelled:pass
 else:raise AssertionError('Family cancellation ignored')
 bridge.report_progress=lambda v:None
 assert set(bpy.data.user_map())==before and obj.matrix_world==matrix
 obj.location.x+=1/unit;bpy.context.view_layer.update()
 try:api.create(family['views'][0]['create_parameters']|{'name':'Stale'})
 except ValueError as e:assert 'stale' in str(e)
 else:raise AssertionError('Stale view guard accepted')
 obj.location=location;bpy.context.view_layer.update()
 assert api.views(args)['views_sha256']==family['views_sha256']
 for row in family['views']:
  created=api.create(row['create_parameters']|{'name':row['view']+str(unit)})
  assert created['bake_inspection']['complete'] and created['card']['card_sha256']==row['card']['card_sha256']
 assert obj.matrix_world==matrix and bpy.context.scene.unit_settings.scale_length==unit
 assert list(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active
# A flat source cannot be silently accepted as a full three-view family.
bpy.ops.mesh.primitive_plane_add();plane=bpy.context.object;plane.name='PlaneSource';plane.data.materials.append(bpy.data.materials['Material'])
args=Views(sources=[plane.name]).model_dump();before=set(bpy.data.user_map())
try:api.views(args)
except ValueError as e:assert 'edge-on' in str(e) or 'sampled surface' in str(e)
else:raise AssertionError('Degenerate views silently skipped')
assert set(bpy.data.user_map())==before
print('VIEW_FAMILY_PASSED')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'VIEW_FAMILY_PASSED' in result.stdout
