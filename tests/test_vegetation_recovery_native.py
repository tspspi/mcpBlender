"""Real complete bundles recover after abrupt Blender death, with no scene replay."""
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark
from mcpblender.export_jobs import inspect,recover,cleanup


@pytest.mark.parametrize('kind',['BOTANICAL','VEGETATION_LOD'])
def test_dead_blender_complete_bundle_publish_without_native_source(tmp_path,kind):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'dead_writer.py';target=tmp_path/'delivery'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nKIND='+repr(kind)+'\nTARGET='+repr(str(target))+'\n'+r'''
import os,bpy
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_export as botanical,vegetation_lods as lods,domains,bridge,attributes
from mcpblender.attribute_contracts import ExportPlan
from mcpblender.vegetation_lod_contracts import Source
from mcpblender.wind_contracts import BotanicalExportPlan
from mcpblender.export_jobs import inspect
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
obj=bpy.data.objects['Cube'];a=obj.data.attributes.new('weight','FLOAT','POINT')
plan=ExportPlan(name='Cube',fields=[{'attribute':'weight','semantic':'weight'}]).model_dump()
from mcpblender.blender import attribute_export
planned=attribute_export.inspect(plan)
domains.dispatch('export_attribute_bundle',plan|{'expected_export':planned['export_sha256'],'directory':TARGET+'-numeric','max_bytes':64*1024**2})
assert inspect(TARGET+'-numeric','stdio')['record']['state']=='published'
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
p=trees.plan({'recipe':recipe});source=trees.create({'collection':'RecoveryOak','recipe':recipe,'expected_model':p['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5});p=leaves.dispatch('plan_botanical_foliage',{'collection':'RecoveryOak','foliage':cfg})
source=leaves.dispatch('configure_botanical_foliage',{'collection':'RecoveryOak','foliage':cfg,'expected_tree':source['tree_sha256'],'expected_foliage':p['foliage_sha256']})
if KIND=='BOTANICAL':
    args=BotanicalExportPlan(collection='RecoveryOak').model_dump();plan=botanical.inspect(args)
    command='export_botanical_bundle';args|={'expected_export':plan['export_sha256']};phase='verified botanical bundle before publication'
else:
    args=Source(collection='RecoveryOak',levels=[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0}]).model_dump();plan=lods.plan(args)[-1]
    state=lods.create(args|{'expected_plan':plan['plan_sha256'],'lod_collection':'RecoveryLods','display_offset_m':[8,0,0]})
    command='export_botanical_lods';args={'lod_collection':'RecoveryLods','expected_lods':state['lods_sha256'],'placement':'SOURCE'};phase='verified vegetation LOD bundle before publication'
def die(v):
    if v.get('phase')==phase:os._exit(23)
bridge.report_progress=die
domains.dispatch(command,args|{'directory':TARGET,'max_bytes':512*1024**2})
raise AssertionError('Dead-writer boundary was not reached')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==23,result.stdout+'\n'+result.stderr
    state=inspect(target,'stdio');assert state['record']['kind']==kind and not state['writer_active'] and state['stage_exists'] and not target.exists()
    ready=recover(target,'stdio',state['job_sha256']);assert ready['record']['state']=='ready' and not ready['replayed']
    with pytest.raises(ValueError,match='protected'):cleanup(target,'stdio',ready['job_sha256'],dry_run=False)
    published=recover(target,'stdio',ready['job_sha256'],publish=True);assert published['record']['state']=='published' and published['target_is_original_stage']
    with pytest.raises(ValueError,match='protected'):cleanup(target,'stdio',published['job_sha256'],dry_run=False)
    numeric=inspect(str(target)+'-numeric','stdio');assert numeric['record']['kind']=='NUMERIC' and numeric['record']['state']=='published'
