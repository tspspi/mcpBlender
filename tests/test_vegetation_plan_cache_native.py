"""Bounded pure-data planning reuse remains bound to source, options and budgets."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_native_plan_cache_rechecks_source_and_budget_authority(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'cache.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from unittest.mock import patch
from mcpblender import botany,foliage
from mcpblender.vegetation_lod_contracts import Source
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_lods as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
p=trees.plan({'recipe':recipe});state=trees.create({'collection':'Source','recipe':recipe,'expected_model':p['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5});lp=leaves.dispatch('plan_botanical_foliage',{'collection':'Source','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'Source','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':lp['foliage_sha256']})
args=Source(collection='Source',levels=[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0}]).model_dump()
initial=api.plan(args)[-1];ids=set(bpy.data.user_map());assert initial['valid']
assert len(json.dumps(api._planning_cache))<=16*1024**2
with patch.object(api.solver,'plan',side_effect=AssertionError('Projection unexpectedly repeated')):
 assert api.plan(args)[-1]==initial
# Every changed policy/source must go through the solver rather than reuse data.
for change in ({'max_projected_triangles':1},{'max_gain_evaluations':1},{'margin':2.6},{'levels':[{'leaf_budget':100,'radial_sides':8,'min_branch_radius_m':0}]}):
 with patch.object(api.solver,'plan',side_effect=ValueError('EXPECTED_CACHE_MISS')):
  try:api.plan(args|change)
  except ValueError as e:assert 'EXPECTED_CACHE_MISS' in str(e)
  else:raise AssertionError('Changed request reused cache')
root=bpy.data.objects[state['root']];location=root.location.copy();root.location.x+=1
with patch.object(api.solver,'plan',side_effect=ValueError('EXPECTED_CACHE_MISS')):
 try:api.plan(args)
 except ValueError as e:assert 'EXPECTED_CACHE_MISS' in str(e)
 else:raise AssertionError('Changed source reused cache')
root.location=location;bpy.context.view_layer.update()
assert api.plan(args)[-1]==initial
# Expiration drops cached data; no host/API handles survive there.
with patch.object(api.time,'monotonic',return_value=api._planning_cache['created_at']+301),patch.object(api.solver,'plan',side_effect=ValueError('EXPECTED_CACHE_MISS')):
 try:api.plan(args)
 except ValueError as e:assert 'EXPECTED_CACHE_MISS' in str(e)
 else:raise AssertionError('Expired plan reused')
assert api._planning_cache is None and set(bpy.data.user_map())==ids
initial=api.plan(args)[-1]
with patch.object(api.solver,'plan',side_effect=AssertionError('Create repeated verified planning')):
 created=api.create(args|{'expected_plan':initial['plan_sha256'],'lod_collection':'CachedLods','display_offset_m':[8,0,0]})
assert created['valid'] and api._planning_cache is None
assert all(q['coverage_loss']==0 for q in created['levels'][1]['wood_quality'].values())
assert min(f['frame_min_m'][1] for v,f in created['levels'][1]['wood_quality_frame'].items() if v in ('FRONT','SIDE'))<=0
# Interrupt the first semantic-text write after native geometry/pose validation.
# All staged IDs must disappear, preserving the existing profile and source.
before=set(bpy.data.user_map());source_guard=trees.inspect({'collection':'Source'})['tree_sha256']
planned=api.plan(args)[-1]
def cancel_write(progress):
 if progress.get('phase')=='writing botanical LOD semantics':raise bridge.OperationCancelled('semantic-write witness')
with patch.object(bridge,'report_progress',side_effect=cancel_write):
 try:api.create(args|{'expected_plan':planned['plan_sha256'],'lod_collection':'CancelledText','display_offset_m':[8,0,0]})
 except bridge.OperationCancelled:pass
 else:raise AssertionError('Semantic write cancellation did not fire')
assert set(bpy.data.user_map())==before and trees.inspect({'collection':'Source'})['tree_sha256']==source_guard
assert api.inspect({'lod_collection':'CachedLods'})[-1]['valid']
print('LOD_CACHE_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'LOD_CACHE_NATIVE_OK' in result.stdout
