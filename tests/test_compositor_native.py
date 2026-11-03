"""Native compositor handoff, shared scenes and settings rollback invariants."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_graph_handoff_and_settings_preserve_exact_native_state(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import compositing as c,bridge
from mcpblender.compositor_contracts import Graph,Color,Passes,Attach
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
scene=bpy.context.scene

def spec(value=1):
    return Graph.model_validate({'group':'FX','nodes':[{'name':'Color','type':'CompositorNodeRGB','output_value':[value,.2,.1,1]},{'name':'Out','type':'NodeGroupOutput'}],
        'links':[{'from_node':'Color','from_socket':'Color','to_node':'Out','to_socket':'Image'}]}).model_dump(exclude_none=True)
def apply(spec):return c.configure_graph(spec)
initial=set(bpy.data.user_map());state=c.pipeline()
# Inspector catalogs must leave no extra IDs, users or scalar state.
for name in c.NODE_TYPES:c.catalog({'node_type':name})
assert set(bpy.data.user_map())==initial
assert c.inspect_pipeline()['settings_sha256']==state['settings_sha256']
assert set(bpy.data.user_map())==initial
first=apply(spec());tree=c.graph('FX')
c.attach({'group':'FX','expected_graph':first['graph_sha256'],'enabled':True,'expected_settings':c.pipeline()['settings_sha256']})
assert scene.compositing_node_group==tree
other=bpy.data.scenes.new('Other');other.compositing_node_group=tree
state=c.describe(tree);assert len(state['users'])==2
args=spec(.5)|{'replace':True,'expected_graph':state['graph_sha256']}
try:apply(args)
except ValueError as e:assert 'allow_shared' in str(e)
else:raise AssertionError('Shared edits accepted without opt-in')
ids=set(bpy.data.user_map());phase={}
def progress(v):phase.clear();phase.update(v)
bridge.report_progress=progress
for boundary in ('staged compositor node','verified compositor handoff'):
    phase.clear()
    def cancel():
        if phase.get('phase')==boundary:raise bridge.OperationCancelled(boundary)
    bridge.check_cancelled=cancel
    try:apply(args|{'allow_shared':True})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Missing cancellation')
    bridge.check_cancelled=lambda:None
    assert set(bpy.data.user_map())==ids
    assert scene.compositing_node_group==tree and other.compositing_node_group==tree
    assert c.describe(tree)['graph_sha256']==state['graph_sha256']
bridge.report_progress=lambda v:None
updated=apply(args|{'allow_shared':True});tree=c.graph('FX')
assert scene.compositing_node_group==other.compositing_node_group==tree
assert updated['graph_sha256']!=state['graph_sha256']
# Native direct UI edits invalidate the graph guard, including non-editable fields.
tree.nodes['Color'].mute=True
try:apply(spec(.3)|{'replace':True,'expected_graph':updated['graph_sha256'],'allow_shared':True})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Native node edit did not invalidate guard')
tree.nodes['Color'].mute=False
# Nested users cannot silently receive a new interface/identity.
outer=bpy.data.node_groups.new('Outer','CompositorNodeTree');node=outer.nodes.new('CompositorNodeGroup');node.node_tree=tree
state=c.describe(tree)
try:apply(spec(.3)|{'replace':True,'expected_graph':state['graph_sha256'],'allow_shared':True})
except ValueError as e:assert 'nested/external' in str(e)
else:raise AssertionError('Nested graph remapped')
bpy.data.node_groups.remove(outer)
# Invalid graph preflight and cycles leave bound graph identities unchanged.
state=c.describe(tree);ids=set(bpy.data.user_map())
bad=spec(.3)|{'replace':True,'expected_graph':state['graph_sha256'],'allow_shared':True};bad['links'][0]['from_socket']='Missing'
try:apply(bad)
except ValueError:pass
else:raise AssertionError('Invalid socket accepted')
assert set(bpy.data.user_map())==ids and scene.compositing_node_group==tree
cycle=spec(.3)|{'replace':True,'expected_graph':state['graph_sha256'],'allow_shared':True}
cycle['nodes']=[{'name':'A','type':'CompositorNodeExposure'},{'name':'B','type':'CompositorNodeExposure'},{'name':'Out','type':'NodeGroupOutput'}]
cycle['links']=[{'from_node':'A','from_socket':'Image','to_node':'B','to_socket':'Image'},{'from_node':'B','from_socket':'Image','to_node':'A','to_socket':'Image'},{'from_node':'B','from_socket':'Image','to_node':'Out','to_socket':'Image'}]
try:apply(cycle)
except ValueError as e:assert 'cycles' in str(e)
else:raise AssertionError('Compositor cycle accepted')
assert set(bpy.data.user_map())==ids and scene.compositing_node_group==tree
# Color changes preflight against installed dynamic enum values and rollback.
original=c.pipeline();ids=set(bpy.data.user_map())
try:c.configure_color({'expected_settings':original['settings_sha256'],'view_transform':'MISSING','exposure':2})
except (ValueError,TypeError):pass
else:raise AssertionError('Unknown color transform accepted')
assert set(bpy.data.user_map())==ids and c.pipeline()['settings_sha256']==original['settings_sha256']
# Cancel after application (second check); scratch scene must be gone from guards.
for kind in ('color','passes','binding'):
    original=c.pipeline();ids=set(bpy.data.user_map());calls=[0]
    def cancel():
        calls[0]+=1
        if calls[0]==2:raise bridge.OperationCancelled(kind)
    bridge.check_cancelled=cancel
    try:
        if kind=='color':c.configure_color({'expected_settings':original['settings_sha256'],'exposure':2})
        elif kind=='passes':c.configure_passes({'expected_settings':original['settings_sha256'],'passes':{'z':True}})
        else:c.attach({'expected_settings':original['settings_sha256'],'enabled':False})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('No settings cancellation')
    bridge.check_cancelled=lambda:None
    assert set(bpy.data.user_map())==ids
    assert c.pipeline()['settings_sha256']==original['settings_sha256']
# A successful settings return must equal the state inspected after scratch cleanup.
result=c.configure_color({'expected_settings':c.pipeline()['settings_sha256'],'view_transform':'Standard','look':'None','exposure':1})
assert result['settings_sha256']==c.pipeline()['settings_sha256']
# Native color animation is retained and targeted edits are refused.
scene.view_settings.keyframe_insert(data_path='exposure',frame=1)
try:c.configure_color({'expected_settings':c.pipeline()['settings_sha256'],'exposure':2})
except ValueError as e:assert 'keyed/driven' in str(e)
else:raise AssertionError('Animated setting overwritten')
ids=set(bpy.data.user_map())
assert c.inspect_pipeline()['settings_sha256']==c.pipeline()['settings_sha256']
assert set(bpy.data.user_map())==ids
c.configure_color({'expected_settings':c.pipeline()['settings_sha256'],'gamma':1.1})
assert set(bpy.data.user_map())==ids
# Scene-owned indirect graph animation is also read-only, not just Tree actions.
tree.nodes['Color'].outputs[0].keyframe_insert(data_path='default_value',frame=1)
assert not c.describe(tree)['editable'] and c.describe(tree)['graph_sha256'] is None
tree.animation_data_clear()
# Imported actions can carry cross-ID string paths even though normal scene
# keyframe insertion refuses them. Preserve/refuse those conservatively too.
anim=scene.animation_data
bag=anim.action.layers[0].strips[0].channelbag(anim.action_slot)
bag.fcurves.new(data_path='compositing_node_group.nodes["Color"].outputs[0].default_value',index=0)
state=c.describe(tree);assert not state['editable'] and not state['complete'] and state['graph_sha256'] is None
try:apply(spec(.2)|{'replace':True,'expected_graph':'a'*64,'allow_shared':True})
except ValueError as e:assert 'unanimated' in str(e)
else:raise AssertionError('Scene-owned graph animation overwritten')
# Disable supports an imported graph; enabling it does not claim ownership.
foreign=bpy.data.node_groups.new('Imported','CompositorNodeTree');scene.compositing_node_group=foreign
c.attach({'expected_settings':c.pipeline()['settings_sha256'],'enabled':False})
try:c.attach({'expected_settings':c.pipeline()['settings_sha256'],'enabled':True})
except ValueError:pass
else:raise AssertionError('Imported graph enabled as managed')
print('COMPOSITOR_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'COMPOSITOR_NATIVE_OK' in result.stdout
