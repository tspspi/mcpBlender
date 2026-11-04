"""Master UV rollback and regenerated public-name handoff preserve original IDs."""
import json
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark
from mcpblender.botanical_contracts import Create,SecondaryUV


def test_master_secondary_authoring_and_regeneration_rollback(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'master-uv.py'
    args=Create(collection='Master',expected_model='0'*64,recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}).model_dump(exclude_none=True)
    layout=SecondaryUV(collection='Master',expected_tree='0'*64,assets=['wood','leaf-0'],texture_width=512,texture_height=512,
                       chart_layout={'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4,'allow_stretch':True}).model_dump()
    script.write_text('import sys,json\nsys.path.insert(0,'+repr(str(repo))+')\nARGS=json.loads('+repr(json.dumps(args))+')\nLAYOUT=json.loads('+repr(json.dumps(layout))+')\n'+r'''
import bpy
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,botanical_uv as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
plan=trees.plan(ARGS);args=ARGS|{'expected_model':plan['model_sha256']};tree=trees.create(args)
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5,'variants':1})
pop=leaves.dispatch('plan_botanical_foliage',{'collection':'Master','foliage':cfg})
tree=leaves.dispatch('configure_botanical_foliage',{'collection':'Master','foliage':cfg,'expected_tree':tree['tree_sha256'],'expected_foliage':pop['foliage_sha256']})
col=bpy.data.collections['Master'];original=col[trees.META];ids=set(bpy.data.user_map());names={v:v.name for v in ids};guard=tree['tree_sha256']
settings=LAYOUT|{'expected_tree':guard}
for phase in ('authoring botanical secondary UV','verified botanical secondary UV batch'):
    def stop(v):
        if v.get('phase')==phase and (phase!='authoring botanical secondary UV' or v.get('asset')=='leaf-0'):raise bridge.OperationCancelled('master UV')
    bridge.report_progress=stop
    try:api.create(settings)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Master UV cancellation ignored')
    bridge.report_progress=lambda v:None
    assert set(bpy.data.user_map())==ids and col[trees.META]==original
    assert all(v.name==name for v,name in names.items())
    assert trees.inspect({'collection':'Master'})['tree_sha256']==guard
tree=api.create(settings);assert tree['valid'] and set(tree['secondary_uv'])=={'wood','leaf-0'}
ids=set(bpy.data.user_map());names={v:v.name for v in ids};guard=tree['tree_sha256'];original=col[trees.META]
for policy in ('PRESERVE','REPROJECT'):
    recipe=args['recipe'] if policy=='PRESERVE' else args['recipe']|{'height':6,'seed':2}
    plan=trees.plan({'recipe':recipe})
    regen=args|{'recipe':recipe,'expected_model':plan['model_sha256'],'expected_tree':guard,'preserve_placement':True,'discard_derived_edits':False,'secondary_uv_policy':policy}
    def stop(v):
        if v.get('phase')=='verified botanical handoff before deletion':raise bridge.OperationCancelled('regenerated UV handoff')
    bridge.report_progress=stop
    try:trees.regenerate(regen)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Regenerated UV handoff cancellation ignored')
    bridge.report_progress=lambda v:None
    assert set(bpy.data.user_map())==ids and col[trees.META]==original
    assert all(v.name==name for v,name in names.items())
    assert trees.inspect({'collection':'Master'})['tree_sha256']==guard
# Metadata cannot mask different actual coordinates even with a new record hash.
meta=json.loads(original);record=meta['secondary_uv']['wood'][0];record['uv_witness']['UV2']='f'*64
record['record_sha256']=botany.digest({k:v for k,v in record.items() if k!='record_sha256'});col[trees.META]=json.dumps(meta)
assert not trees.inspect({'collection':'Master'})['valid'];col[trees.META]=original
assert trees.inspect({'collection':'Master'})['valid']
print('BOTANICAL_SECONDARY_UV_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_SECONDARY_UV_OK' in result.stdout
