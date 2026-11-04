"""LOD GLBs keep shared templates, wind IDs and explicit physical placement."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_native_lod_interchange_modes_cancellation_and_independent_validation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'export_lods.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany,foliage,wind,vegetation_lod_files as files,vegetation_interchange as common
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_lods as lods,vegetation_lod_export as api,bridge
from mcpblender.vegetation_lod_contracts import Source
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe});source=trees.create({'collection':'DeliveryOak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[300,100,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5});pop=leaves.dispatch('plan_botanical_foliage',{'collection':'DeliveryOak','foliage':cfg})
source=leaves.dispatch('configure_botanical_foliage',{'collection':'DeliveryOak','foliage':cfg,'expected_tree':source['tree_sha256'],'expected_foliage':pop['foliage_sha256']})
root=bpy.data.objects[source['root']];root.rotation_euler.z=.3;root.scale*=1.2;bpy.context.view_layer.update()
p=Source(collection='DeliveryOak',levels=[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0},{'leaf_budget':100,'radial_sides':8,'min_branch_radius_m':0,'max_coverage_loss':.55,'max_silhouette_loss':.55},{'leaf_budget':2,'radial_sides':5,'min_branch_radius_m':1,'max_coverage_loss':1,'max_silhouette_loss':1}]).model_dump()
plan=lods.plan(p)[-1];state=lods.create(p|{'expected_plan':plan['plan_sha256'],'lod_collection':'DeliveryLods','display_offset_m':[8,0,0]})
source=trees.inspect({'collection':'DeliveryOak'});trees.remove({'collection':'DeliveryOak','expected_tree':source['tree_sha256'],'discard_derived_edits':False})
state=lods.inspect({'lod_collection':'DeliveryLods'})[-1];assert state['valid'];ids=set(bpy.data.user_map());frame=bpy.context.scene.frame_current;selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
args={'lod_collection':'DeliveryLods','expected_lods':state['lods_sha256'],'directory':OUTPUT+'/source','placement':'SOURCE','max_bytes':512*1024**2}
for patch in ({'expected_lods':'0'*64},{'max_bytes':1024}):
    try:api.export(args|patch)
    except ValueError:pass
    else:raise AssertionError('LOD export guard/byte budget bypassed')
for phase in ('verified attribute bundle before publication','verified vegetation LOD bundle before publication'):
    def stop(v):
        if v.get('phase')==phase:raise bridge.OperationCancelled('LOD export cancellation')
    bridge.report_progress=stop
    try:api.export(args)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('LOD export cancellation ignored')
    bridge.report_progress=lambda v:None
    assert not Path(args['directory']).exists() and set(bpy.data.user_map())==ids
    assert not list(Path(OUTPUT).glob('.mcpblender-vegetation-lods-*'))
    assert lods.inspect(args)[-1]['lods_sha256']==state['lods_sha256']
original_rename=api.os.rename;failed=Path(OUTPUT)/'failed-publication';moved=[0]
def fail_publication(src,dst):
    if Path(dst).parent==failed:
        if moved[0]:raise OSError('injected publication failure')
        original_rename(src,dst);moved[0]+=1;(failed/'foreign.txt').write_bytes(b'preserve unrelated data');return
    return original_rename(src,dst)
def arm(v):
    if v.get('phase')=='verified vegetation LOD bundle before publication':api.os.rename=fail_publication
bridge.report_progress=arm
try:
    try:api.export(args|{'directory':str(failed)})
    except OSError:pass
    else:raise AssertionError('Publication fault did not fire')
finally:api.os.rename=original_rename;bridge.report_progress=lambda v:None
assert (failed/'foreign.txt').read_bytes()==b'preserve unrelated data'
assert set(bpy.data.user_map())==ids and lods.inspect(args)[-1]['lods_sha256']==state['lods_sha256']
result=api.export(args);proof=files.validate(args['directory']);assert proof==result['proof']
assert [l['leaf_instances'] for l in proof['levels']]==[140,110,100,2] and proof['shared_leaf_templates']==3 and len(proof['assets'])==11
assert [l['expanded_triangles'] for l in proof['levels'][:3]]==[28548,22668,20708]
assert proof['levels'][-1]['branches']==10
shown=api.export(args|{'directory':OUTPUT+'/displayed','placement':'DISPLAYED'});assert shown['proof']['placement_mode']=='DISPLAYED'
a=json.loads((Path(OUTPUT)/'source/semantics.json').read_text());b=json.loads((Path(OUTPUT)/'displayed/semantics.json').read_text())
assert abs(a['wind']['placement']['translation_m'][0]-3)<1e-5 and abs(b['wind']['placement']['translation_m'][0]-11)<1e-5
assert abs(a['wind']['placement']['scale']-1.2)<1e-5
assert set(bpy.data.user_map())==ids and bpy.context.scene.frame_current==frame and list(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active
assert lods.inspect(args)[-1]['lods_sha256']==state['lods_sha256']
try:api.export(args)
except FileExistsError:pass
else:raise AssertionError('Existing LOD export overwritten')
folder=Path(args['directory']);record=json.loads((folder/'manifest.json').read_text());semantic=folder/'semantics.json';original=semantic.read_bytes()
data=json.loads(original);data['levels'][1]['leaf_indices'][0]=139;semantic.write_text(json.dumps(data));record['files']=common.files(folder);(folder/'manifest.json').write_text(json.dumps(record))
try:files.validate(folder)
except ValueError as e:assert 'identity mapping' in str(e)
else:raise AssertionError('LOD identity tamper accepted after rehash')
semantic.write_bytes(original);record['files']=common.files(folder);(folder/'manifest.json').write_text(json.dumps(record));assert files.validate(folder)==proof
lods.dispatch('remove_botanical_lods',{'lod_collection':'DeliveryLods','expected_lods':state['lods_sha256']});assert files.validate(folder)==proof
print('LOD_INTERCHANGE_OK')
'''.replace('OUTPUT',repr(str(tmp_path))))
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'LOD_INTERCHANGE_OK' in result.stdout
