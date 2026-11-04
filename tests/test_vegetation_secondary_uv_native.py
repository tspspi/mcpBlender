"""Owned multi-mesh secondary layout rollback before and after graph publication."""
import json
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark
from mcpblender.vegetation_lod_contracts import Source,SecondaryUV


def test_secondary_batch_cancellation_ownership_and_second_revision(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'secondary-owned.py'
    source=Source(collection='Master',levels=[{'leaf_budget':70,'radial_sides':6,'max_coverage_loss':1,'max_silhouette_loss':1}],resolution=64).model_dump()
    settings=SecondaryUV(lod_collection='Lods',expected_lods='0'*64,assets=['lod-1-wood','leaf-0'],texture_width=512,texture_height=512,
                         chart_layout={'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4,'allow_stretch':True}).model_dump()
    script.write_text('import sys,json\nsys.path.insert(0,'+repr(str(repo))+')\nSOURCE=json.loads('+repr(json.dumps(source))+')\nSETTINGS=json.loads('+repr(json.dumps(settings))+')\n'+r'''
import bpy
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_lods as lods,vegetation_uv as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe});tree=trees.create({'collection':'Master','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5,'variants':1})
pop=leaves.dispatch('plan_botanical_foliage',{'collection':'Master','foliage':cfg})
tree=leaves.dispatch('configure_botanical_foliage',{'collection':'Master','foliage':cfg,'expected_tree':tree['tree_sha256'],'expected_foliage':pop['foliage_sha256']})
plan=lods.plan(SOURCE)[-1];state=lods.create(SOURCE|{'lod_collection':'Lods','expected_plan':plan['plan_sha256']})
col,owned,meta,state=lods.inspect({'lod_collection':'Lods'});original=col[lods.META];ids=set(bpy.data.user_map());guard=state['lods_sha256']
settings=SETTINGS|{'expected_lods':guard}
for phase in ('authoring vegetation secondary UV','verified vegetation secondary UV batch'):
    def stop(v):
        if v.get('phase')==phase and (phase!='authoring vegetation secondary UV' or v.get('asset')=='leaf-0'):raise bridge.OperationCancelled('secondary batch')
    bridge.report_progress=stop
    try:api.create(settings)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Secondary batch cancellation ignored')
    bridge.report_progress=lambda v:None
    assert set(bpy.data.user_map())==ids and col[lods.META]==original
    assert lods.inspect(settings)[-1]['lods_sha256']==guard
    assert trees.inspect({'collection':'Master'})['tree_sha256']==tree['tree_sha256']
state=api.create(settings);assert state['valid'] and len(state['secondary_uv'])==2
first=state['secondary_uv'];ids=set(bpy.data.user_map())
# Ordinary raw UV editing still refuses owned meshes after the typed transaction.
from mcpblender.blender import uv
obj=bpy.data.objects[state['mesh_assets']['leaf-0']['name']]
try:uv.dispatch('create_secondary_uv',{'name':obj.name,'uv_map':'RawUV','expected_uv':uv.fingerprint(obj,'RawUV'),'make_single_user':False})
except ValueError as exc:assert 'Managed owned' in str(exc)
else:raise AssertionError('Raw ownership bypass accepted')
# Another appended layout preserves the complete earlier baseline and record.
state=api.create(settings|{'expected_lods':state['lods_sha256'],'uv_map':'UV3','assets':['leaf-0'],'chart_layout':None})
assert state['valid'] and state['secondary_uv']['leaf-0'][0]==first['leaf-0'][0]
assert len(state['secondary_uv']['leaf-0'])==2 and state['mesh_assets']['leaf-0']['uv_maps'][-2:]==['UV2','UV3']
# A foreign mesh user refuses even before staging, leaving IDs and current guard intact.
obj=bpy.data.objects[state['mesh_assets']['leaf-0']['name']];outside=bpy.data.objects.new('Foreign',obj.data);bpy.context.scene.collection.objects.link(outside)
current=lods.inspect(settings)[-1];before=set(bpy.data.user_map())
try:api.create(settings|{'expected_lods':current['lods_sha256'],'uv_map':'UV4'})
except ValueError as exc:assert 'valid unchanged' in str(exc)
else:raise AssertionError('Foreign mesh user accepted')
assert set(bpy.data.user_map())==before
bpy.data.objects.remove(outside,do_unlink=True)
assert lods.inspect(settings)[-1]['valid']
# A recomputed record hash cannot conceal a different actual map witness.
from mcpblender import botany
raw=col[lods.META];changed=json.loads(raw);entry=changed['secondary_uv']['leaf-0'][-1]
entry['uv_witness']['UV3']='f'*64;entry['record_sha256']=botany.digest({k:v for k,v in entry.items() if k!='record_sha256'})
col[lods.META]=json.dumps(changed,sort_keys=True)
assert not lods.inspect(settings)[-1]['valid'];col[lods.META]=raw
assert lods.inspect(settings)[-1]['valid']
changed=json.loads(raw);changed['secondary_uv']=[];col[lods.META]=json.dumps(changed)
assert not lods.inspect(settings)[-1]['valid'];col[lods.META]=raw
print('VEGETATION_SECONDARY_UV_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'VEGETATION_SECONDARY_UV_OK' in result.stdout
