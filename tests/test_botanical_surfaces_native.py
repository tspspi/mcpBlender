"""Shared botanical detail ownership and reversible staged shader handoff."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_surface_identity_original_sources_guards_and_cancellation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from mcpblender.blender import botanical_surfaces as s,botanical_foliage as f,bridge
from mcpblender.botanical_surface_contracts import Create
bridge.check_cancelled=lambda:None
for name,profile in (('Bark','OAK_BARK'),('Leaf','OAK_LEAF')):
    p=Create.model_validate({'material':name,'settings':{'profile':profile}}).model_dump()
    state=s.dispatch('create_botanical_surface',p);assert state['detail_valid']
    mat=bpy.data.materials[name];tree=mat.node_tree;original_id=mat.as_pointer()
    bpy.data.objects['Cube'].data.materials.append(mat)
    nodes=set(tree.nodes);links={(v.from_node.name,v.from_socket.identifier,v.to_node.name,v.to_socket.identifier) for v in tree.links};metadata=mat[s.META]
    before=set(bpy.data.user_map());calls=[0]
    def cancel():
        calls[0]+=1
        if calls[0]==2:raise bridge.OperationCancelled('surface handoff')
    bridge.check_cancelled=cancel
    try:s.configure(p|{'expected_material':state['material_sha256']})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Missing surface cancellation')
    bridge.check_cancelled=lambda:None
    assert set(bpy.data.user_map())==before and set(tree.nodes)==nodes and mat[s.META]==metadata
    assert links=={(v.from_node.name,v.from_socket.identifier,v.to_node.name,v.to_socket.identifier) for v in tree.links}
    assert s.inspect({'material':name})['material_sha256']==state['material_sha256']
    # Thin optical controls remain independently editable and do not invalidate detail.
    if profile=='OAK_LEAF':
        opt=f.inspect_material({'material':name});f.configure_material({'material':name,'expected_material':opt['material_sha256'],'roughness':.8,'translucent_mix':.4})
        assert s.inspect({'material':name})['detail_valid']
        from mcpblender.blender.textures import material_signature
        try:material_signature(mat)
        except ValueError as e:assert 'directly to Principled' in str(e)
        else:raise AssertionError('Thin shader silently accepted for PBR bake')
    extra=tree.nodes.new('ShaderNodeRGB');extra.name='User Detail';extra.outputs[0].default_value=(.1,.2,.3,1)
    state=s.inspect({'material':name});state=s.configure(p|{'expected_material':state['material_sha256']})
    assert state['detail_valid'] and mat.as_pointer()==original_id and len(tree.nodes)==len(nodes)+1 and tree.nodes.get('User Detail')==extra
    # Color-ramp edits are real detail changes, even though they are nested RNA.
    if profile=='OAK_BARK':
        ramp=next(v for v in tree.nodes if v.type=='VALTORGB')
        interpolation=ramp.color_ramp.interpolation;ramp.color_ramp.interpolation='CONSTANT'
        assert not s.inspect({'material':name})['detail_valid']
        ramp.color_ramp.interpolation=interpolation
        old=list(ramp.color_ramp.elements[0].color);ramp.color_ramp.elements[0].color=(1,0,1,1)
        edited=s.inspect({'material':name});assert not edited['detail_valid'] and edited['material_sha256']!=state['material_sha256']
        try:s.configure(p|{'expected_material':edited['material_sha256']})
        except ValueError as e:assert 'edited' in str(e)
        else:raise AssertionError('Manual detail edit discarded')
        ramp.color_ramp.elements[0].color=old
    state=s.inspect({'material':name});calls[0]=0;bridge.check_cancelled=cancel
    before_nodes=set(tree.nodes)
    try:s.remove({'material':name,'expected_material':state['material_sha256']})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Missing remove cancellation')
    bridge.check_cancelled=lambda:None
    assert set(tree.nodes)==before_nodes and s.inspect({'material':name})['material_sha256']==state['material_sha256']
    state=s.inspect({'material':name});removed=s.remove({'material':name,'expected_material':state['material_sha256']});assert not removed['managed']
    assert mat.as_pointer()==original_id and not any(v.name.startswith('Botanical_') for v in tree.nodes)
    if profile=='OAK_LEAF':
        assert tree.nodes['Leaf Surface'].inputs['Base Color'].links[0].from_node==tree.nodes['Leaf Sides']
        assert not tree.nodes['Leaf Surface'].inputs['Normal'].is_linked
        assert f.inspect_material({'material':name})['settings']['roughness']>.79
# Creating a material rolls back its native IDs even if final cancellation occurs.
ids=set(bpy.data.user_map());calls=[0]
def stop():
    calls[0]+=1
    if calls[0]==4:raise bridge.OperationCancelled('created surface')
bridge.check_cancelled=stop
p=Create.model_validate({'material':'Cancelled','settings':{'profile':'OAK_LEAF'}}).model_dump()
try:s.dispatch('create_botanical_surface',p)
except bridge.OperationCancelled:pass
else:raise AssertionError('No create cancellation')
assert set(bpy.data.user_map())==ids
bridge.check_cancelled=lambda:None
from mcpblender.blender import botanical_trees as trees
from mcpblender.botanical_contracts import Plan,Create as TreeCreate,Regenerate
from mcpblender.botanical_surface_contracts import Bark,Leaf
p=Plan.model_validate({'recipe':{'attractors':96,'iterations':6,'node_budget':256}}).model_dump();plan=trees.plan(p)
args=TreeCreate.model_validate(p|{'collection':'SurfaceOak','expected_model':plan['model_sha256']}).model_dump(exclude_none=True)
state=trees.create(args);cfg={'shoots_per_bud':1,'attachment_nodes':2}
planned=f.dispatch('plan_botanical_foliage',{'collection':'SurfaceOak','foliage':cfg})
state=f.dispatch('configure_botanical_foliage',{'collection':'SurfaceOak','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':planned['foliage_sha256']})
material_names=[state['geometry']['bark_material'],state['foliage']['material']]
identities={n:bpy.data.materials[n].as_pointer() for n in material_names}
for name,recipe in zip(material_names,(Bark().model_dump(),Leaf().model_dump())):
    info=s.inspect({'material':name});s.configure({'material':name,'expected_material':info['material_sha256'],'settings':recipe})
state=trees.inspect({'collection':'SurfaceOak'});assert state['valid']
recipe=p['recipe']|{'height':12,'crown_width':10};plan=trees.plan({'recipe':recipe})
regen=Regenerate.model_validate(args|{'recipe':recipe,'expected_model':plan['model_sha256'],'expected_tree':state['tree_sha256']}).model_dump(exclude_none=True)
state=trees.regenerate(regen);assert state['valid']
assert all(s.inspect({'material':n})['detail_valid'] and bpy.data.materials[n].as_pointer()==identities[n] for n in material_names)
print('BOTANICAL_SURFACE_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_SURFACE_NATIVE_OK' in result.stdout
