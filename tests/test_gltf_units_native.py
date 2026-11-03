"""Mixed-unit project scope and source-preserving physical GLB export."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_mixed_scene_export_refuses_before_write_and_active_scope_is_physical(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy
from pathlib import Path
from mcpblender.blender import bridge,workflows
from mcpblender.skin_glb import Document,point
bridge.check_cancelled=lambda:None
scene=bpy.context.scene;scene.unit_settings.scale_length=.01;unit=scene.unit_settings.scale_length
other=bpy.data.scenes.new('Different Units');other.unit_settings.scale_length=1
obj=bpy.data.objects['Cube'];matrix=obj.matrix_world.copy();ids=set(bpy.data.user_map())
path=Path(OUTPUT)/'all.glb';path.write_bytes(b'original')
try:bridge.dispatch('export_glb',{'path':str(path),'selected_only':False,'animations':False,'overwrite':True})
except ValueError as e:assert 'Mixed scene units' in str(e)
else:raise AssertionError('Mixed-unit all-scene export accepted')
assert path.read_bytes()==b'original' and set(bpy.data.user_map())==ids
result=workflows.export_objects_glb({'objects':['Cube'],'path':str(Path(OUTPUT)/'active.glb'),'animations':False,'overwrite':False})
assert result['unit_normalization']['scene_unit_scale']==unit
file=Document(Path(OUTPUT)/'active.glb',morphs=True);world=file.world(None,0)[file.mesh_node]
coords=[point(world,p) for _,_,p,_,_ in file.vertices()]
assert all(abs(max(p[a] for p in coords)-min(p[a] for p in coords)-2*unit)<1e-7 for a in range(3))
assert obj.matrix_world==matrix and set(bpy.data.user_map())==ids and scene.unit_settings.scale_length==unit
print('GLTF_UNIT_SCOPE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'GLTF_UNIT_SCOPE_OK' in result.stdout
