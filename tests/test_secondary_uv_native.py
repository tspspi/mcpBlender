"""Secondary UV atomic staging and exact preservation of native mesh state."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_secondary_uv_preflight_cancel_and_native_preservation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'secondary.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import uv,bridge
from mcpblender.uv_contracts import UVSecondary
bridge.check_cancelled=lambda:None
obj=bpy.data.objects['Cube'];mesh=obj.data
for e in mesh.edges:e.use_seam=e.index%2==0
for v in mesh.vertices:v.select=v.index%2==0
mesh.uv_layers.active=mesh.uv_layers[0]
second=mesh.uv_layers.new(name='DetailUV')
for i,v in enumerate(second.data):v.uv=(i*.125,i*.25)
mesh.uv_layers.active=second;mesh.uv_layers[0].active_render=True
obj.shape_key_add(name='Basis');obj.shape_key_add(name='Detail')
obj.data.shape_keys.key_blocks['Detail'].data[0].co.z+=.25
mesh.update()
def snapshot():
    return {'maps':[(l.name,[tuple(v.uv) for v in l.data]) for l in mesh.uv_layers],
            'active':mesh.uv_layers.active.name,'render':[l.active_render for l in mesh.uv_layers],
            'seams':[e.use_seam for e in mesh.edges],'selected':[v.select for v in mesh.vertices],
            'coords':[tuple(v.co) for v in mesh.vertices],
            'shapes':[[tuple(v.co) for v in key.data] for key in mesh.shape_keys.key_blocks]}
def params(**kw):
    name=kw.get('uv_map','UV2')
    return UVSecondary(name='Cube',expected_uv=uv.fingerprint(obj,name),**kw).model_dump()
original=snapshot();ids=set(bpy.data.user_map())
def cancel():raise bridge.OperationCancelled('before secondary publication')
bridge.check_cancelled=cancel
try:uv.dispatch('create_secondary_uv',params())
except bridge.OperationCancelled:pass
else:raise AssertionError('Cancellation ignored')
assert snapshot()==original and set(bpy.data.user_map())==ids
bridge.check_cancelled=lambda:None
result=uv.dispatch('create_secondary_uv',params())
after=snapshot();assert after['maps'][:2]==original['maps'] and len(after['maps'])==3
for k in ('active','seams','selected','coords','shapes'):assert after[k]==original[k],k
assert after['render']==[True,False,False] and result['uv_channel']==2
assert result['active_uv_map']=='DetailUV' and result['render_uv_map']=='UVMap'
# Appending/renaming another channel invalidates even an absent target guard.
p=params(uv_map='LaterUV');mesh.uv_layers[1].name='RenamedDetail'
try:uv.dispatch('create_secondary_uv',p)
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Channel rename did not invalidate guard')
# Ownership checks refuse before staging and leave managed contents unchanged.
obj['mcpblender_vegetation_lod_owner']='a'*32
before=snapshot();ids=set(bpy.data.user_map())
try:uv.dispatch('create_secondary_uv',params(uv_map='LaterUV'))
except ValueError as e:assert 'Managed owned' in str(e)
else:raise AssertionError('Managed edit accepted')
assert snapshot()==before and set(bpy.data.user_map())==ids
del obj['mcpblender_vegetation_lod_owner']
while len(mesh.uv_layers)<8:mesh.uv_layers.new(name='Extra')
ids=set(bpy.data.user_map());before=snapshot()
try:uv.dispatch('create_secondary_uv',params(uv_map='Ninth'))
except ValueError as e:assert 'eight' in str(e)
else:raise AssertionError('Ninth layer accepted')
assert snapshot()==before and set(bpy.data.user_map())==ids
while mesh.uv_layers:mesh.uv_layers.remove(mesh.uv_layers[-1])
ids=set(bpy.data.user_map())
try:uv.dispatch('create_secondary_uv',params())
except ValueError as e:assert 'primary' in str(e)
else:raise AssertionError('Secondary without primary accepted')
assert len(mesh.uv_layers)==0 and set(bpy.data.user_map())==ids
print('SECONDARY_UV_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'SECONDARY_UV_OK' in result.stdout
