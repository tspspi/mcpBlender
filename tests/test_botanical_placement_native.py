"""Regeneration preserves authored transform modes/deltas without decomposition."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_centimetre_large_scale_rotation_modes_and_deltas(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'placement.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
planned=trees.plan({'recipe':recipe})
state=trees.create({'collection':'PlacedOak','recipe':recipe,'expected_model':planned['model_sha256'],'location':[300,100,0],'radial_sides':5,'bark_tile_length':1})
channels=('location','rotation_euler','rotation_quaternion','rotation_axis_angle','scale','delta_location','delta_rotation_euler','delta_rotation_quaternion','delta_scale')
for mode in ('XYZ','QUATERNION','AXIS_ANGLE'):
    root=bpy.data.objects[state['root']];root.rotation_mode=mode;root.rotation_euler=(.2,-.3,.4);root.rotation_quaternion=(.9238795,0,0,.3826834);root.rotation_axis_angle=(.5,0,0,1);root.scale=(120,)*3
    root.delta_location=(3,-2,1);root.delta_scale=(1.01,)*3;root.delta_rotation_euler=(.01,.02,.03);bpy.context.view_layer.update()
    matrix=root.matrix_world.copy();values={k:tuple(getattr(root,k)) for k in channels};guard=trees.inspect({'collection':'PlacedOak'})['tree_sha256']
    cfg=foliage.recipe({'shoots_per_bud':1,'attachment_nodes':2})
    plan=leaves.dispatch('plan_botanical_foliage',{'collection':'PlacedOak','foliage':cfg})
    state=leaves.dispatch('configure_botanical_foliage',{'collection':'PlacedOak','foliage':cfg,'expected_tree':guard,'expected_foliage':plan['foliage_sha256']})
    root=bpy.data.objects[state['root']]
    assert root.matrix_world==matrix and root.rotation_mode==mode
    assert {k:tuple(getattr(root,k)) for k in channels}==values
print('BOTANICAL_PLACEMENT_EXACT_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_PLACEMENT_EXACT_OK' in result.stdout
