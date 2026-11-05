"""Whole-batch preflight and rollback over independent owned depth assets."""
import os
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_DEPTH_NATIVE_SOURCE'),reason='Retained native material-field archive required')
def test_layer_batch_rollback_limits_and_independent_reopen(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'layers.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nSOURCE='+repr(str(Path(os.environ['MCPBLENDER_DEPTH_NATIVE_SOURCE']).resolve()))+'\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,shutil
from pathlib import Path
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import LayersSource,LayersCreate
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/baseline.blend');bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/baseline.blend')
copy=Path(OUTPUT)/'capture';shutil.copytree(SOURCE,copy)
args=LayersSource(directory=str(copy),prefix='Stack',layers=[{'view':'FRONT','render_role':'CAMERA_ONLY'},{'view':'TOP','render_role':'SECONDARY','settings':{'geometry_mode':'ADAPTIVE_NORMAL'}}]).model_dump()
plan=api.layer_plan(args);assert len(plan['layers'])==2 and plan['totals']['pixels']>0
assert plan['totals']['triangles']==sum(v['geometry']['triangles'] for v in plan['layers'])
p=LayersCreate(**args,expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump();before=set(bpy.data.user_map())
for limits in ({'max_total_pixels':1024},{'max_total_texture_bytes':1024},{'max_total_triangles':2}):
 try:api.layer_plan(args|{'limits':args['limits']|limits})
 except ValueError as exc:assert 'budget' in str(exc)
 else:raise AssertionError('Aggregate budget ignored')
 assert set(bpy.data.user_map())==before
changed=p|{'layers':[p['layers'][0],p['layers'][1]|{'render_role':'SHADOW_ONLY'}]}
try:api.create_layers(changed)
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Changed batch accepted stale plan')
assert set(bpy.data.user_map())==before
foreign=bpy.data.collections.new('Stack-TOP');before_collision=set(bpy.data.user_map())
try:api.create_layers(p)
except ValueError as exc:assert 'exists' in str(exc)
else:raise AssertionError('Existing second target not preflighted')
assert set(bpy.data.user_map())==before_collision and not bpy.data.collections.get('Stack-FRONT')
bpy.data.collections.remove(foreign)
seen=[]
def cancel(value):
 seen.append(value)
 if value.get('layer_view')=='TOP' and value.get('phase')=='creating packed directional data images' and value['completed']==1:raise bridge.OperationCancelled('second-layer cancellation')
bridge.report_progress=cancel
try:api.create_layers(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Injected second-layer cancellation ignored')
assert any(v.get('layer_view')=='FRONT' for v in seen) and any(v.get('layer_view')=='TOP' for v in seen)
assert set(bpy.data.user_map())==before,'Batch rollback leaked the first layer or partial second layer'
bridge.report_progress=lambda v:None
# An external archive edit after the first successful layer must invalidate the
# second layer and roll the first one back. Only mutate this test's private copy.
source_file=copy/'source.blend';source_bytes=source_file.read_bytes();real_create=api.create
mutated=[]
def mutate_after_first(params,**kwargs):
 result=real_create(params,**kwargs)
 if params['view']=='FRONT':source_file.write_bytes(source_bytes+b'changed');mutated.append(True)
 return result
api.create=mutate_after_first
try:
 try:api.create_layers(p)
 except ValueError:pass
 else:raise AssertionError('Archive mutation between layers was accepted')
finally:api.create=real_create;source_file.write_bytes(source_bytes)
assert mutated and set(bpy.data.user_map())==before,'Changed source left a completed first layer behind'
result=api.create_layers(p);assert result['created_count']==2 and result['totals']==plan['totals']
assert {v['collection'] for v in result['assets']}=={'Stack-FRONT','Stack-TOP'}
for state in result['assets']:assert state['valid'] and state['ray_visibility']['visible_camera']==(state['render_role']=='CAMERA_ONLY')
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/layers.blend');bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/layers.blend');shutil.rmtree(copy)
for made in result['assets']:
 state=api.inspect({'collection':made['collection']})[-1];assert state['valid'] and state['asset_sha256']==made['asset_sha256']
 assert state['render_role']==made['render_role'];api.remove({'collection':state['collection'],'expected_asset':state['asset_sha256']})
assert not any(v.get(api.OWNER) for v in bpy.data.user_map())
print('DEPTH_LAYERS_NATIVE_OK')
''')
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'DEPTH_LAYERS_NATIVE_OK' in run.stdout
