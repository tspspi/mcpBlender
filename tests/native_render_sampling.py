"""Saved RNA settings, partial-update rollback, keyed-field refusal."""
import sys,json,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mcpblender.blender import render_sampling as sampling,bridge
bpy.ops.wm.open_mainfile(filepath=args[1],use_scripts=False);bpy.context.view_layer.update();expected=json.loads(Path(args[2]).read_text());scene=bpy.context.scene
assert sampling.snapshot(scene)['settings']==expected
before=sampling.snapshot(scene);check=bridge.check_cancelled
# First field changes, then cancellation: rollback must include unvisited fields.
def cancelled():
    if scene.cycles.samples==32:raise bridge.OperationCancelled('after first sampling mutation')
bridge.check_cancelled=cancelled
try:
    try:sampling.configure({'expected_sampling':before['sampling_sha256'],'settings':{'samples':32,'seed':13}})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Partial sampling mutation did not cancel')
finally:bridge.check_cancelled=check
assert sampling.snapshot(scene)==before
scene.cycles.keyframe_insert(data_path='seed',frame=1);animated=sampling.snapshot(scene)
assert 'cycles.seed' in animated['animated_fields']
try:sampling.configure({'expected_sampling':animated['sampling_sha256'],'settings':{'seed':4}})
except ValueError as exc:assert 'keyed' in str(exc)
else:raise AssertionError('Keyed seed overwritten')
assert scene.cycles.seed==expected['seed']
print('RENDER_SAMPLING_NATIVE_COMPLETE',flush=True)
