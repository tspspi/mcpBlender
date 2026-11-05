"""Creation-pinned Cycles roles, stale plans, owned edits and portable lifecycle."""
import os
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_DEPTH_NATIVE_SOURCE'),reason='Retained native material-field archive required')
def test_creation_roles_are_guarded_and_survive_reopen(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'roles.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nSOURCE='+repr(str(Path(os.environ['MCPBLENDER_DEPTH_NATIVE_SOURCE']).resolve()))+'\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy
from mcpblender.blender import depth_assets as api,bridge
from mcpblender.depth_asset_contracts import Source,Create
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
roles={'ALL_RAYS':('camera','shadow','diffuse','glossy','transmission','volume_scatter'),
       'CAMERA_ONLY':('camera',),'SECONDARY':('shadow','diffuse','glossy','transmission','volume_scatter'),
       'SHADOW_ONLY':('shadow',),'DIFFUSE_SHADOW':('diffuse','shadow')}
flags=tuple('visible_'+key for key in roles['ALL_RAYS']);baseline=None;plans=set()
# Establish the portable baseline: Blender drops unused factory-startup IDs on save.
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/baseline.blend');bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/baseline.blend')
original={kind:sorted(v.name for v in getattr(bpy.data,kind)) for kind in ('objects','meshes','materials','images','collections')}
for role,active in roles.items():
 args=Source(directory=SOURCE,view='FRONT',render_role=role).model_dump();plan=api.prepared(args)[0]
 expected={k:k.removeprefix('visible_') in active for k in flags}
 assert plan['render_role']==role and plan['ray_visibility']==expected;plans.add(plan['plan_sha256'])
 payload=(plan['geometry'],plan['maps'])
 if baseline is None:baseline=payload
 else:assert payload==baseline,'Ray role changed captured geometry or maps'
 p=Create(**args,collection='RoleAsset',expected_plan=plan['plan_sha256'],accept_approximate_optics=True).model_dump()
 before=set(bpy.data.user_map());changed=p|{'render_role':'CAMERA_ONLY' if role!='CAMERA_ONLY' else 'SHADOW_ONLY'}
 try:api.create(changed)
 except ValueError as exc:assert 'stale' in str(exc)
 else:raise AssertionError('Role change accepted stale creation plan')
 assert set(bpy.data.user_map())==before
 made=api.create(p);assert made['valid'] and made['render_role']==role and made['ray_visibility']==expected
 col,owned,meta,state=api.inspect({'collection':'RoleAsset'});obj=bpy.data.objects[meta['object']]
 assert col.hide_render and col.hide_viewport
 assert {k:getattr(obj,k) for k in flags}==expected
 obj.visible_camera=not obj.visible_camera
 edited=api.inspect({'collection':'RoleAsset'})[-1];assert not edited['valid'] and edited['asset_sha256']!=state['asset_sha256']
 assert edited['render_role']==role and edited['ray_visibility']['visible_camera']!=expected['visible_camera']
 try:api.remove({'collection':'RoleAsset','expected_asset':edited['asset_sha256']})
 except ValueError as exc:assert 'content' in str(exc)
 else:raise AssertionError('Edited ray visibility bypassed ownership guard')
 obj.visible_camera=expected['visible_camera'];assert api.inspect({'collection':'RoleAsset'})[-1]['valid']
 bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/'+role+'.blend');bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/'+role+'.blend')
 reopened=api.inspect({'collection':'RoleAsset'})[-1];assert reopened['valid'] and reopened['render_role']==role and reopened['ray_visibility']==expected
 assert reopened['asset_sha256']==made['asset_sha256']
 api.remove({'collection':'RoleAsset','expected_asset':reopened['asset_sha256']})
 assert {kind:sorted(v.name for v in getattr(bpy.data,kind)) for kind in original}==original
assert len(plans)==len(roles)
print('DEPTH_RENDER_ROLES_NATIVE_OK')
''')
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'DEPTH_RENDER_ROLES_NATIVE_OK' in run.stdout
