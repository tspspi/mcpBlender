"""Native read-only wind sampling, placement, source guards and atomic cancellation."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_native_wind_source_preservation_units_and_cancelled_publication(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'wind.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json,math
from pathlib import Path
from mcpblender import botany,foliage,wind
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,botanical_wind as motion,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe})
state=trees.create({'collection':'WindOak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[300,100,0],'radial_sides':5,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':1,'attachment_nodes':2})
planned=leaves.dispatch('plan_botanical_foliage',{'collection':'WindOak','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'WindOak','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':planned['foliage_sha256']})
root=bpy.data.objects[state['root']];root.rotation_euler.z=.3;root.scale*=1.2;bpy.context.view_layer.update()
args={'collection':'WindOak','wind':wind.recipe({})};state=trees.inspect(args)
ids=set(bpy.data.user_map());matrix=root.matrix_world.copy();frame=bpy.context.scene.frame_current
info=motion.inspect(args);assert abs(info['placement']['scale']-1.2)<1e-6 and abs(info['placement']['translation_m'][0]-3)<1e-6
sample=motion.sample(args|{'seconds':[0,.5,1.5],'offset':0,'leaf_offset':0,'limit':4,'max_work':100000})
assert all(s['metrics']['max_segment_length_error_m']<1e-12 and s['metrics']['max_junction_error_m']==0 and s['metrics']['root_anchor_displacement_m']==0 for s in sample['samples'])
assert all(s['leaves'] for s in sample['samples']) and sample['samples'][0]['leaves']!=sample['samples'][1]['leaves']
assert trees.inspect(args)['tree_sha256']==state['tree_sha256'] and set(bpy.data.user_map())==ids
assert root.matrix_world==matrix and bpy.context.scene.frame_current==frame
path=Path(OUTPUT)/'wind.json';path.write_bytes(b'original');foreign=Path(str(path)+'.tmp');foreign.write_bytes(b'foreign')
export=args|{'expected_wind':info['wind_sha256'],'path':str(path),'overwrite':True,'max_bytes':64*1024**2}
phase=[]
def report(v):
    if v['phase']=='publishing portable wind semantics':phase.append(True)
def cancel():
    if phase and list(Path(OUTPUT).glob('.mcpblender-wind-*')):raise bridge.OperationCancelled('before atomic publication')
bridge.report_progress=report;bridge.check_cancelled=cancel
try:motion.export(export)
except bridge.OperationCancelled:pass
else:raise AssertionError('Missing wind publication cancellation')
assert path.read_bytes()==b'original' and foreign.read_bytes()==b'foreign' and not list(Path(OUTPUT).glob('.mcpblender-wind-*'))
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
for patch in ({'expected_wind':'0'*64},{'max_bytes':1024}):
    try:motion.export(export|patch)
    except ValueError:pass
    else:raise AssertionError('Wind guard/byte limit bypassed')
    assert path.read_bytes()==b'original'
result=motion.export(export);saved=json.loads(path.read_text())
assert saved['field']==wind.field(args['wind']) and saved['foliage']['leaves'] and saved['model']['branches']
assert result['bytes']==path.stat().st_size and trees.inspect(args)['tree_sha256']==state['tree_sha256']
assert set(bpy.data.user_map())==ids and foreign.read_bytes()==b'foreign'
root.scale.x*=2;bpy.context.view_layer.update()
try:motion.inspect(args)
except ValueError as e:assert 'uniform' in str(e)
else:raise AssertionError('Nonuniform wind placement accepted')
print('BOTANICAL_WIND_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_WIND_NATIVE_OK' in result.stdout
