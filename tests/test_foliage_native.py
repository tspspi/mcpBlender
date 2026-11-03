"""Native shared prototypes and guarded foliage ownership lifecycle."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_instanced_foliage_lifecycle_and_failure_rollback(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender.blender import botanical_trees as trees,botanical_foliage as fol,bridge
from mcpblender.botanical_contracts import Plan,Create,Regenerate
from mcpblender.foliage_contracts import Foliage
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
p=Plan.model_validate({'recipe':{'attractors':96,'iterations':6,'node_budget':256}}).model_dump();plan=trees.plan(p)
a=Create.model_validate(p|{'collection':'Oak','expected_model':plan['model_sha256']}).model_dump(exclude_none=True)
state=trees.create(a);cfg=Foliage.model_validate({'shoots_per_bud':2,'attachment_nodes':4}).model_dump()
def attach(cfg,discard=False):
    state=trees.inspect({'collection':'Oak'})
    planned=fol.dispatch('plan_botanical_foliage',{'collection':'Oak','foliage':cfg})
    return fol.dispatch('configure_botanical_foliage',{'collection':'Oak','foliage':cfg,'expected_foliage':planned['foliage_sha256'],'expected_tree':state['tree_sha256'],'discard_derived_edits':discard})
state=attach(cfg);assert state['valid'],state
meta=state['foliage'];roles=fol.resolve_roles(meta)
assert sum(v.is_instance for v in bpy.context.evaluated_depsgraph_get().object_instances)==meta['metrics']['leaves']
assert len(roles['pc'].objects)==3 and not any(n.bl_idname=='GeometryNodeRealizeInstances' for n in roles['gn'].nodes)
assert meta['material']=='Oak_LeafSurface'
material=bpy.data.materials[meta['material']]
opt=fol.inspect_material({'material':material.name})
changed=fol.configure_material({'material':material.name,'expected_material':opt['material_sha256'],'translucent_mix':.4,'double_sided':False})
assert changed['settings']['translucent_mix']>.39 and not changed['settings']['double_sided']
assert trees.inspect({'collection':'Oak'})['valid']
# A linked optical input must never silently report changing an unused default.
node=material.node_tree.nodes.new('ShaderNodeValue');material.node_tree.links.new(node.outputs[0],material.node_tree.nodes['Optical Mix'].inputs[0])
opt=fol.inspect_material({'material':material.name})
try:fol.configure_material({'material':material.name,'expected_material':opt['material_sha256'],'translucent_mix':.2})
except ValueError as e:assert 'linked' in str(e)
else:raise AssertionError('Linked socket silently patched')
material.node_tree.nodes.remove(node)
# Native sources cannot be deleted if an unrelated object shares their mesh.
foreign=bpy.data.objects.new('ForeignLeaf',roles['lm0']);bpy.context.scene.collection.objects.link(foreign)
assert not trees.inspect({'collection':'Oak'})['can_remove'];bpy.data.objects.remove(foreign)
# Root placement is independent of derived component content.
root=bpy.data.objects[state['root']];root.location=(5,2,1);bpy.context.view_layer.update()
assert trees.inspect({'collection':'Oak'})['valid']
# Cancellation at final handoff restores exact native identities and public names.
state=trees.inspect({'collection':'Oak'});ids=set(bpy.data.user_map());names={i:i.name for i in ids};phase={}
bridge.report_progress=lambda v:(phase.clear(),phase.update(v))
def cancel():
    if phase.get('phase')=='verified botanical handoff before deletion':raise bridge.OperationCancelled('handoff')
bridge.check_cancelled=cancel
try:attach(cfg|{'variants':2})
except bridge.OperationCancelled:pass
else:raise AssertionError('No handoff cancellation')
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
assert set(bpy.data.user_map())==ids and all(i.name==n for i,n in names.items())
assert trees.inspect({'collection':'Oak'})['tree_sha256']==state['tree_sha256']
# Derived edits require explicit consent; the fresh plan is still inspectable.
roles['pm'].vertices[0].co.x+=.1
try:attach(cfg)
except ValueError as e:assert 'discard_derived_edits' in str(e)
else:raise AssertionError('Discarded leaf edit')
state=attach(cfg|{'variants':2},True);assert state['valid'] and state['foliage']['material']==material.name
roles=fol.resolve_roles(state['foliage']);assert len(roles['pc'].objects)==2
# Growth replacement keeps the foliage recipe and same shared material.
recipe=p['recipe']|{'height':12,'crown_width':10};plan=trees.plan({'recipe':recipe})
args=Regenerate.model_validate(a|{'recipe':recipe,'expected_model':plan['model_sha256'],'expected_tree':state['tree_sha256']}).model_dump(exclude_none=True)
state=trees.regenerate(args);assert state['valid'] and state['foliage']['recipe']['variants']==2
assert bpy.data.materials[state['foliage']['material']]==material
bpy.ops.wm.save_as_mainfile(filepath=str(Path(OUTPUT)/'foliage.blend'));bpy.ops.wm.open_mainfile(filepath=str(Path(OUTPUT)/'foliage.blend'))
state=trees.inspect({'collection':'Oak'});assert state['valid'],state
# Damaged canonical foliage forbids replacement but safe owned deletion remains possible.
roles=fol.resolve_roles(state['foliage']);roles['ft'].write('bad')
state=trees.inspect({'collection':'Oak'});assert state['replacement_blockers'] and state['can_remove']
trees.remove({'collection':'Oak','expected_tree':state['tree_sha256']})
assert not bpy.data.collections.get('Oak') and not bpy.data.node_groups.get('Oak_LeafInstances')
assert not any(c.name.startswith('Oak_') for c in bpy.data.collections)
# Standalone template cancellation removes all newly-created native IDs.
planned=fol.dispatch('plan_leaf_template',{'leaf':{}});ids=set(bpy.data.user_map());calls=[0]
def cancel_leaf():
    calls[0]+=1
    if calls[0]==2:raise bridge.OperationCancelled('leaf')
bridge.check_cancelled=cancel_leaf
try:fol.dispatch('create_leaf_template',{'name':'Leaf','leaf':{},'expected_leaf':planned['leaf_sha256']})
except bridge.OperationCancelled:pass
else:raise AssertionError('No template cancellation')
bridge.check_cancelled=lambda:None
assert set(bpy.data.user_map())==ids
print('FOLIAGE_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'FOLIAGE_NATIVE_OK' in result.stdout


def test_backlighting_and_double_sidedness_are_independent(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'optics.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json,os,shutil
from pathlib import Path
from mathutils import Vector
from mcpblender.blender import botanical_foliage as fol,bridge
bridge.check_cancelled=lambda:None
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
shape={'curl':0,'fold':0,'vein_ridge':0}
plan=fol.dispatch('plan_leaf_template',{'leaf':shape})
fol.dispatch('create_leaf_template',{'name':'TestLeaf','leaf':shape,'expected_leaf':plan['leaf_sha256']})
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
scene.render.resolution_x=96;scene.render.resolution_y=96;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
cam=bpy.data.objects.new('OpticsCamera',bpy.data.cameras.new('OpticsCamera'));scene.collection.objects.link(cam)
cam.location=(0,.066,-.3);cam.rotation_euler=(Vector((0,.066,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.15;scene.camera=cam
light=bpy.data.objects.new('Backlight',bpy.data.lights.new('Backlight','AREA'));scene.collection.objects.link(light);light.location=(0,.066,.25);light.data.energy=8;light.data.shape='DISK';light.data.size=.2
results={}
for name,mix,two in (('opaque',0,True),('translucent',1,True),('culled',1,False)):
    state=fol.inspect_material({'material':'TestLeaf_Surface'})
    fol.configure_material({'material':state['material'],'expected_material':state['material_sha256'],'translucent_mix':mix,'double_sided':two})
    path=Path(OUTPUT)/(name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    img=bpy.data.images.load(str(path),check_existing=False);pixels=list(img.pixels);results[name]={'rgb':sum(pixels[i] for i in range(len(pixels)) if i%4!=3)/(len(pixels)*.75),'alpha':sum(pixels[3::4])/(len(pixels)/4)};bpy.data.images.remove(img)
assert results['translucent']['rgb']>results['opaque']['rgb']+.02,results
assert results['opaque']['alpha']>.1 and results['translucent']['alpha']>.1,results
assert results['culled']['alpha']<results['translucent']['alpha']*.15,results
if target:=os.environ.get('MCPBLENDER_FOLIAGE_EVIDENCE_DIR'):
    out=Path(target);out.mkdir(parents=True,exist_ok=True)
    for name in results:shutil.copy2(Path(OUTPUT)/(name+'.png'),out/('backlit-'+name+'.png'))
    (out/'optics-proof.json').write_text(json.dumps(results,indent=2))
print('FOLIAGE_OPTICS_OK',results)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'FOLIAGE_OPTICS_OK' in result.stdout
