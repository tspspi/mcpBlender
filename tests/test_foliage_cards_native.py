"""Native source guards, physical scale, view normals and exact rollback."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_card_units_guards_preservation_and_rollback(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'cards.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import foliage_cards as cards,bridge
from mcpblender.card_contracts import Plan
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_plane_add();source=bpy.context.object;source.name='Source'
mat=bpy.data.materials.new('SourceSurface');mat.use_nodes=True;source.data.materials.append(mat)
for unit in (1,.01):
    bpy.context.scene.unit_settings.scale_length=unit
    unit=bpy.context.scene.unit_settings.scale_length
    source.scale=(.06/unit,.1/unit,1);source.location=(.2/unit,.3/unit,.01/unit);bpy.context.view_layer.update()
    args=Plan(sources=['Source']).model_dump();ids=set(bpy.data.user_map());matrix=source.matrix_world.copy()
    selected=set(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    state=cards.inspect(args)
    assert set(bpy.data.user_map())==ids and state['card_area_m2']>.024
    for patch in ({'padding':.04},{'view':'FRONT'}):
        try:cards.create(args|patch|{'name':'Refused','expected_card':state['card_sha256']})
        except ValueError:pass
        else:raise AssertionError('Stale options accepted')
        assert set(bpy.data.user_map())==ids
    source.location.x+=1
    try:cards.create(args|{'name':'Refused','expected_card':state['card_sha256']})
    except ValueError as e:assert 'stale' in str(e)
    else:raise AssertionError('Stale source accepted')
    source.matrix_world=matrix;bpy.context.view_layer.update();assert cards.inspect(args)['card_sha256']==state['card_sha256']
    def progress(v):
        if v['phase']=='verified fitted card before handoff':raise bridge.OperationCancelled('before handoff')
    bridge.report_progress=progress
    try:cards.create(args|{'name':'Rollback','expected_card':state['card_sha256']})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('No cancellation')
    bridge.report_progress=lambda v:None
    assert set(bpy.data.user_map())==ids and source.matrix_world==matrix
    result=cards.create(args|{'name':'Card'+str(unit),'expected_card':state['card_sha256']})
    obj=bpy.data.objects[result['object']];mesh=obj.data;mesh.calc_loop_triangles()
    assert len(mesh.loop_triangles)==state['triangles'] and result['bake_inspection']['complete']
    points=[obj.matrix_world@v.co for v in mesh.vertices]
    assert abs((max(v.x for v in points)-min(v.x for v in points))*unit-.1248)<1e-6
    assert abs(points[0].z*unit-.005)<1e-6
    assert all(p.normal.z>.999 for p in mesh.polygons)
    assert set(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active
    assert source.matrix_world==matrix and bpy.context.scene.unit_settings.scale_length==unit
    # Source shader edits also invalidate the plan, without modifying the target.
    state=cards.inspect(args);socket=mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'];socket.default_value=.17 if socket.default_value>.3 else .63
    try:cards.create(args|{'name':'ChangedMaterial','expected_card':state['card_sha256']})
    except ValueError as e:assert 'stale' in str(e)
    else:raise AssertionError('Material change accepted')
    assert 'ChangedMaterial' not in bpy.data.objects
# A mesh which also emits instances must not silently fit only its own surface.
bpy.ops.mesh.primitive_cube_add();child=bpy.context.object;child.parent=source
source.instance_type='VERTS';bpy.context.view_layer.update()
try:cards.inspect(args)
except ValueError as e:assert 'instances' in str(e)
else:raise AssertionError('Unrealized source instances were ignored')
source.instance_type='NONE'
print('FITTED_CARDS_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'FITTED_CARDS_NATIVE_OK' in result.stdout
