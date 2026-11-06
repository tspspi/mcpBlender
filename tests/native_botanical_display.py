"""Independent object/ray preservation plus failure/cancel/context guards."""
import sys,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mcpblender.blender import botanical_display as display,bridge
refs=[{'kind':'SOURCE','collection':'DisplayTree'},{'kind':'DEPTH','collection':'DisplayDepth'},{'kind':'SUBSET','collection':'DisplaySubset'}]
fields=('hide_viewport','hide_render','visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow')
def object_state():
    return {o.name:({k:getattr(o,k) for k in fields},[list(r) for r in o.matrix_basis],o.hide_get() if o.name in bpy.context.view_layer.objects else None) for o in bpy.data.objects}
bpy.ops.wm.open_mainfile(filepath=args[1],use_scripts=False);bpy.context.view_layer.update();original=object_state()
# hide_get can be unavailable for globally hidden collections; record actual
# per-view-layer hide flags separately through visible baseline occurrences.
baseline={k:(v[0],v[1]) for k,v in original.items()}
_,before=display.inspect({'targets':refs});assert before['valid']
source=bpy.data.collections['DisplayTree'];old_flags={r['collection']:r['visibility'] for r in before['targets']};check=bridge.check_cancelled
changes=[r|{'hide_render':i==0,'hide_viewport':i==0} for i,r in enumerate(refs)]
def cancel():
    if source.hide_render:raise bridge.OperationCancelled('after first display target mutation')
bridge.check_cancelled=cancel
try:
    try:display.configure({'targets':changes,'expected_display':before['display_sha256']})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Partial display switch did not cancel')
finally:bridge.check_cancelled=check
assert {r['collection']:r['visibility'] for r in display.inspect({'targets':refs})[-1]['targets']}==old_flags
assert display.inspect({'targets':refs})[-1]['display_sha256']==before['display_sha256']
# Disabled render layers also change the context guard, without changing data.
layer_state=display.inspect({'targets':refs})[-1];bpy.context.view_layer.use=False
disabled=display.inspect({'targets':refs})[-1];assert disabled['display_sha256']!=layer_state['display_sha256']
assert all(not row['collection_render_enabled'] for target in disabled['targets'] for row in target['contexts'] if row['scene']==bpy.context.scene.name)
bpy.context.view_layer.use=True
# Layer exclusions and ancestor flags participate in the guard, remain visible
# in diagnostics, and are never silently reset by this collection-only tool.
layer=bpy.context.view_layer.layer_collection.children['DisplayTree'];layer.exclude=True;bpy.context.view_layer.update();excluded=display.inspect({'targets':refs})[-1]
assert excluded['display_sha256']!=before['display_sha256'] and any(p['exclude'] for row in excluded['targets'][0]['contexts'] for p in row['path'])
try:display.configure({'targets':changes,'expected_display':before['display_sha256']})
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Stale layer context accepted')
assert layer.exclude;layer.exclude=False;bpy.context.view_layer.update()
other=bpy.data.scenes.new('OtherScene');other.collection.children.link(source);shared=display.inspect({'targets':refs})[-1];assert not shared['valid']
try:display.configure({'targets':changes,'expected_display':shared['display_sha256']})
except ValueError:pass
else:raise AssertionError('Cross-scene display mutation accepted')
assert {r['collection']:r['visibility'] for r in display.inspect({'targets':refs})[-1]['targets']}==old_flags
bpy.data.scenes.remove(other);bpy.context.view_layer.update()
# Property animation support is native-version dependent. If exposed, target
# drivers must be reported/refused. Unsupported collections cannot be driven.
if source.bl_rna.properties['hide_render'].is_animatable:
    curve=source.driver_add('hide_render');curve.driver.expression='0';bpy.context.view_layer.update();driven=display.inspect({'targets':refs})[-1]
    assert 'hide_render' in driven['targets'][0]['animated_fields']
    try:display.configure({'targets':changes,'expected_display':driven['display_sha256']})
    except ValueError as exc:assert 'driven' in str(exc)
    else:raise AssertionError('Driven collection visibility overwritten')
    source.driver_remove('hide_render')
bpy.ops.wm.open_mainfile(filepath=args[2],use_scripts=False);bpy.context.view_layer.update();after=object_state();assert {k:(v[0],v[1]) for k,v in after.items()}==baseline
assert display.inspect({'targets':refs})[-1]['valid']
print('BOTANICAL_DISPLAY_NATIVE_COMPLETE',{'objects_preserved':len(baseline),'rollback':True,'layer_context':True,'foreign_scene':True},flush=True)
