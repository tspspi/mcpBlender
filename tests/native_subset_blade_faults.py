"""Independent exact-ID rollback after native blade geometry/material/map staging."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from mcpblender.blender import botanical_subsets as subsets,subset_blade_cards as cards,vegetation_bake as prep,botanical_trees as trees,bridge
from mcpblender.botanical_subset_contracts import Source
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None
filename,library=sys.argv[sys.argv.index('--')+1:];bpy.ops.wm.open_mainfile(filepath=filename,load_ui=False,use_scripts=False)
state=prep.inspect({'bake_collection':'BladePrep'})[-1]
p=Source(directory=library+'/capture',selection='COLUMN_COMPLEMENT',include_structure=False,blade_cards={'bake_collection':'BladePrep','expected_preparation':state['preparation_sha256'],'entries':[{'asset':'leaf-0','directory':library+'/blade'}]}).model_dump()
ids=set(bpy.data.user_map());names={v:v.name for v in ids};selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
planned=subsets.plan(p)[-1];assert set(bpy.data.user_map())==ids
before=trees.inspect({'collection':'Tree'})['tree_sha256'];original=cards.build;reached=[]
def fault(*args):
    mesh=original(*args);assert len(mesh.materials)==2;assert any(n.type=='TEX_IMAGE' for n in mesh.materials[0].node_tree.nodes);reached.append(True)
    raise bridge.OperationCancelled('after packed native blade staging')
cards.build=fault
try:subsets.create(p|{'expected_plan':planned['plan_sha256'],'subset_collection':'FaultedCards'})
except bridge.OperationCancelled:pass
else:raise AssertionError('Fault injection not reached')
finally:cards.build=original
assert reached==[True]
assert ids==set(bpy.data.user_map()) and names=={v:v.name for v in ids}
assert selected==list(bpy.context.selected_objects) and active==bpy.context.view_layer.objects.active
assert prep.inspect({'bake_collection':'BladePrep'})[-1]['preparation_sha256']==state['preparation_sha256']
assert trees.inspect({'collection':'Tree'})['tree_sha256']==before
print('NATIVE_BLADE_CARD_ROLLBACK_OK',flush=True)
