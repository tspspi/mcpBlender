"""Numeric fields preserve UVs, shape/skin identity and ownership on rollback."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_numeric_domains_shared_isolation_and_shape_identity(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'attributes.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender.blender import attributes as a,bridge
from mcpblender.attribute_contracts import Create,Update,Ramp,Edit
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
obj=bpy.data.objects['Cube'];mesh=obj.data
uv=mesh.uv_layers.new(name='LightmapUV');uv.active_render=True;mesh.uv_layers.active=uv
color=mesh.color_attributes.new(name='OriginalColor',type='FLOAT_COLOR',domain='POINT')
for item in color.data:item.color=(.2,.4,.6,1)
mesh.color_attributes.active_color_name=color.name;mesh.color_attributes.default_color_name=color.name
before=a.inspect({'name':'Cube','offset':0,'limit':32});geometry=before['geometry_sha256'];uvs={u.name:[tuple(x.uv) for x in u.data] for u in mesh.uv_layers}
def params(cls,extra):
    return cls.model_validate({'name':'Cube','attribute':'weight','expected_attributes':a.inspect({'name':'Cube'})['attributes_sha256']}|extra).model_dump(exclude_none=True)
for domain,kind,value in [('POINT','FLOAT',.25),('EDGE','INT',17),('FACE','BOOLEAN',True),('CORNER','FLOAT_VECTOR',[1,-2,3]),('POINT','FLOAT_COLOR',[.1,.2,.3,1])]:
    name=domain+'_'+kind
    result=a.edit('create_mesh_attribute',params(Create,{'attribute':name,'domain':domain,'data_type':kind,'value':value}))
    assert result['attributes_sha256'] and result['geometry_sha256']==geometry
    actual=result['values'][0]['value']
    if isinstance(value,list):assert len(actual)==len(value) and all(abs(a-b)<1e-6 for a,b in zip(actual,value))
    elif kind in {'INT','BOOLEAN'}:assert actual==value
    else:assert abs(actual-value)<1e-6
    if kind=='BOOLEAN':
        a.edit('set_mesh_attribute_values',params(Update,{'attribute':name,'indices':[0,2],'values':[False,True]}))
        assert [v['value'] for v in a.inspect({'name':'Cube','attribute':name,'limit':3})['values']]==[False,True,True]
assert {u.name:[tuple(x.uv) for x in u.data] for u in mesh.uv_layers}==uvs
assert a.selectors(mesh)==before['selectors']
state=a.inspect({'name':'Cube'});ids=set(bpy.data.user_map())
for command,cls,extra in [('create_mesh_attribute',Create,{'attribute':'Rollback','data_type':'FLOAT','value':1}),('set_mesh_attribute_values',Update,{'attribute':'POINT_FLOAT','value':.9}),('remove_mesh_attribute',Edit,{'attribute':'EDGE_INT'})]:
    args=params(cls,extra)
    def cancel(v):
        if v.get('phase')=='verified numeric attribute edit':raise bridge.OperationCancelled('staged metadata')
    bridge.report_progress=cancel
    try:a.edit(command,args)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Attribute edit did not cancel')
    bridge.report_progress=lambda v:None
    assert a.inspect({'name':'Cube'})['attributes_sha256']==state['attributes_sha256'] and set(bpy.data.user_map())==ids
for name in ('position','UVMap','LightmapUV','OriginalColor'):
    if name=='OriginalColor':continue # Custom supported colors are intentionally editable.
    try:a.edit('remove_mesh_attribute',params(Edit,{'attribute':name}))
    except ValueError:pass
    else:raise AssertionError('Protected geometry/UV field removed')
# Linked users get a distinct metadata mesh only with explicit isolation.
copy=obj.copy();copy.data=mesh;bpy.context.scene.collection.objects.link(copy)
args=params(Update,{'attribute':'POINT_FLOAT','value':.75})
try:a.edit('set_mesh_attribute_values',args)
except ValueError as e:assert 'shared' in str(e)
else:raise AssertionError('Shared field mutated')
ids=set(bpy.data.user_map());shared_guard=a.inspect({'name':'Cube'})['attributes_sha256']
def cancel_isolated(v):raise bridge.OperationCancelled('isolated attribute edit')
bridge.report_progress=cancel_isolated
try:a.edit('set_mesh_attribute_values',args|{'make_single_user':True})
except bridge.OperationCancelled:pass
else:raise AssertionError('Isolated edit did not cancel')
bridge.report_progress=lambda v:None
assert obj.data==copy.data==mesh and set(bpy.data.user_map())==ids
assert a.inspect({'name':'Cube'})['attributes_sha256']==shared_guard
a.edit('set_mesh_attribute_values',args|{'make_single_user':True})
assert obj.data!=copy.data and copy.data==mesh and mesh.attributes['POINT_FLOAT'].data[0].value==.25
assert obj.data.attributes['POINT_FLOAT'].data[0].value==.75
mesh=obj.data
# Single-user metadata edits retain shape keys/actions and armature modifiers.
obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Smile');key.data[0].co.z+=.25;key.value=.5;key.keyframe_insert('value',frame=1)
modifier=obj.modifiers.new('Keep armature','ARMATURE');shape=mesh.shape_keys;action=shape.animation_data.action;old_geometry=a.inspect({'name':'Cube'})['geometry_sha256']
shape_coords={k.name:[tuple(v.co) for v in k.data] for k in shape.key_blocks}
a.edit('create_mesh_attribute',params(Create,{'attribute':'AfterShape','data_type':'FLOAT_VECTOR','value':[0,1,0]}))
a.edit('ramp_mesh_attribute',params(Ramp,{'attribute':'POINT_FLOAT','axis':'Z'}))
assert obj.data==mesh and mesh.shape_keys==shape and shape.animation_data.action==action and obj.modifiers.get('Keep armature')==modifier
assert {v.value for v in mesh.attributes['POINT_FLOAT'].data}=={0.,1.}
assert a.inspect({'name':'Cube'})['geometry_sha256']==old_geometry
assert {k.name:[tuple(v.co) for v in k.data] for k in shape.key_blocks}==shape_coords
shared=obj.copy();shared.data=mesh;bpy.context.scene.collection.objects.link(shared)
ids=set(bpy.data.user_map())
try:a.edit('set_mesh_attribute_values',params(Update,{'attribute':'POINT_FLOAT','value':1,'make_single_user':True}))
except ValueError as e:assert 'shared shape-key' in str(e)
else:raise AssertionError('Shared shape-key mesh isolation was implicit')
assert set(bpy.data.user_map())==ids;bpy.data.objects.remove(shared,do_unlink=True)
try:a.edit('set_mesh_attribute_values',args)
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale attribute guard accepted')
print('NUMERIC_ATTRIBUTES_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'NUMERIC_ATTRIBUTES_NATIVE_OK' in result.stdout
