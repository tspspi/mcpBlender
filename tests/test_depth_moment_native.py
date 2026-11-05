"""Inspect independently reopened packed moment assets and guarded transport."""
import os
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_MOMENT_NATIVE_ASSET'), reason='Retained structured moment asset required')
def test_moment_asset_implicit_normals_transport_guard_and_reopen(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    asset = Path(os.environ['MCPBLENDER_MOMENT_NATIVE_ASSET']).resolve()
    script = tmp_path/'moment-native.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nASSET='+repr(str(asset))+'\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender.blender import depth_assets as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.wm.open_mainfile(filepath=ASSET)
col,owned,meta,good=api.inspect({'collection':'Approximate'})
assert good['valid'] and good['shader_recipe']==api.MOMENT_SHADER_RECIPE
assert good['plan']['material_transport']=={'use_bump_map_correction':True}
mat=next(v for v in owned if isinstance(v,bpy.types.Material))
closures=[n for n in mat.node_tree.nodes if n.type in ('BSDF_PRINCIPLED','BSDF_TRANSLUCENT')]
assert len(closures)==2 and all(not n.inputs['Normal'].is_linked for n in closures)
assert all(not p.use_smooth for p in bpy.data.objects[meta['object']].data.polygons)
mat.cycles.use_bump_map_correction=False
changed=api.inspect({'collection':'Approximate'})[-1]
assert not changed['valid'] and changed['asset_sha256']!=good['asset_sha256']
assert 'Depth asset material transport settings changed' in changed['issues']
try:api.remove({'collection':'Approximate','expected_asset':good['asset_sha256']})
except ValueError as exc:assert 'stale' in str(exc)
else:raise AssertionError('Material transport change did not invalidate old guard')
try:api.remove({'collection':'Approximate','expected_asset':changed['asset_sha256']})
except ValueError as exc:assert 'content' in str(exc)
else:raise AssertionError('Changed material transport admitted for removal')
mat.cycles.use_bump_map_correction=True
assert api.inspect({'collection':'Approximate'})[-1]['asset_sha256']==good['asset_sha256']
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/roundtrip.blend')
bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/roundtrip.blend')
reopened=api.inspect({'collection':'Approximate'})[-1]
assert reopened['valid'] and reopened['asset_sha256']==good['asset_sha256']
col,owned,meta,_=api.inspect({'collection':'Approximate'})
obj=bpy.data.objects[meta['object']];mesh=obj.data
geometry={'vertices':[v for p in mesh.vertices for v in p.co],
          'uvs':[v for loop in mesh.uv_layers[0].data for v in loop.uv],
          'faces':[tuple(p.vertices) for p in mesh.polygons]}
maps={}
for key,name in meta['images'].items():
 image=bpy.data.images[name];w,h=image.size;pixels=list(image.pixels)
 maps[key]=[v for y in range(h-1,-1,-1) for v in pixels[y*w*4:(y+1)*w*4]]
# Replay the already qualified numerical plan to isolate native allocation and
# rollback after all resources, including the new geometric material, exist.
original=api.material;prepared=api.prepared;before=set(bpy.data.user_map())
api.prepared=lambda *args,**kwargs:(meta['plan'],geometry,maps)
def fail(*args,**kwargs):
 assert kwargs['geometric_normals']
 original(*args,**kwargs)
 raise RuntimeError('injected material creation failure')
api.material=fail
try:api.create({'collection':'Rollback','view':'FRONT','expected_plan':meta['plan']['plan_sha256'],'accept_approximate_optics':True})
except RuntimeError as exc:assert 'injected' in str(exc)
else:raise AssertionError('Injected failure ignored')
finally:api.material=original;api.prepared=prepared
assert set(bpy.data.user_map())==before,'Moment creation rollback leaked native resources'
# The retained file no longer needs source files; removal still works.
removed=api.remove({'collection':'Approximate','expected_asset':reopened['asset_sha256']})
assert removed['private_datablocks']==11
Path(OUTPUT+'/proof.json').write_text(json.dumps({'before':good,'changed':changed,'reopened':reopened,'removed':removed},indent=2))
print('MOMENT_ASSET_NATIVE_OK')
''')
    run = subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2',
        '--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'MOMENT_ASSET_NATIVE_OK' in run.stdout
    if evidence:=os.environ.get('MCPBLENDER_MOMENT_NATIVE_EVIDENCE'):
        out=Path(evidence);out.mkdir(parents=True,exist_ok=True)
        (out/'native-guard-proof.json').write_text((tmp_path/'proof.json').read_text())
