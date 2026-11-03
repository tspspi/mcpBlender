"""Native isolated-scene export, cancellation, decoder failure and exact ID cleanup."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


@pytest.mark.parametrize('scene_unit_scale',[1,.01])
def test_package_native_publication_rollback_and_source_preservation(tmp_path,scene_unit_scale):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nSCENE_UNIT_SCALE='+repr(scene_unit_scale)+'\n'+r'''
import bpy
from pathlib import Path
from mcpblender.blender import asset_packages as packages,bridge
from mcpblender.package_contracts import Plan
from mcpblender.package_files import validate
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=SCENE_UNIT_SCALE
bpy.ops.mesh.primitive_cube_add(location=(3,1,2));obj=bpy.context.object;obj.name='Source'
# Unpacked texture bytes and loaded pixel edits both participate in the guard.
import struct,zlib
root=Path(__file__).parent
chunk=lambda kind,data:struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
texture=root/'source.png';texture_bytes=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\0\0\xff'))+chunk(b'IEND',b'');texture.write_bytes(texture_bytes)
image=bpy.data.images.load(str(texture));material=bpy.data.materials.new('SourcePBR');material.use_nodes=True
node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes['Principled BSDF'].inputs['Base Color']);obj.data.materials.append(material)
bpy.context.scene.frame_set(3,subframe=.25)
p=Plan.model_validate({'assets':[{'id':'cube','objects':['Source']}]}).model_dump(exclude_none=True)
before=set(bpy.data.user_map());selected=[o.name for o in bpy.context.selected_objects];active=bpy.context.view_layer.objects.active;frame=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
plan=packages.plan(p);assert plan['can_export'],plan
assert set(bpy.data.user_map())==before
old_pixel=image.pixels[0];image.pixels[0]=.5;image.update()
assert packages.plan(p)['source_sha256']!=plan['source_sha256']
image.pixels[0]=old_pixel;image.update()
assert packages.plan(p)['source_sha256']==plan['source_sha256']
texture.unlink();missing=packages.plan(p);assert not missing['can_export'] and any('external image' in b for b in missing['blockers'])
texture.write_bytes(texture_bytes);assert packages.plan(p)['source_sha256']==plan['source_sha256']
root=Path(__file__).parent;params=p|{'expected_source':plan['source_sha256'],'directory':str(root/'package')}
# A failed mkdir must never adopt or delete a pre-existing staging directory.
from types import SimpleNamespace
occupied=root/'.mcpblender-package-occupied';occupied.mkdir();(occupied/'foreign.txt').write_text('preserve')
uuid4=packages.uuid.uuid4;packages.uuid.uuid4=lambda:SimpleNamespace(hex='occupied')
try:packages.export(params)
except FileExistsError:pass
else:raise AssertionError('Expected staging collision refusal')
finally:packages.uuid.uuid4=uuid4
assert (occupied/'foreign.txt').read_text()=='preserve' and set(bpy.data.user_map())==before
(occupied/'foreign.txt').unlink();occupied.rmdir()
phase={}
def progress(v):phase.update(v)
for boundary in ('verified package mesh and embedded dependencies','verified asset package inventory'):
    phase.clear()
    def cancel():
        if phase.get('phase')==boundary:raise bridge.OperationCancelled('package boundary')
    bridge.report_progress=progress;bridge.check_cancelled=cancel
    try:packages.export(params)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Expected package cancellation')
    assert set(bpy.data.user_map())==before and not (root/'package').exists()
    assert not list(root.glob('.mcpblender-package-*'))
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
original=packages.inspect_static_glb
packages.inspect_static_glb=lambda *a,**k:(_ for _ in ()).throw(ValueError('injected decode failure'))
try:packages.export(params)
except ValueError as e:assert 'injected' in str(e)
else:raise AssertionError('Expected decoder failure')
finally:packages.inspect_static_glb=original
assert set(bpy.data.user_map())==before and not list(root.glob('.mcpblender-package-*'))
result=packages.export(params);assert result['valid'] and result['assets']==1 and validate(root/'package')['valid']
assert set(bpy.data.user_map())==before
assert [o.name for o in bpy.context.selected_objects]==selected and bpy.context.view_layer.objects.active==active
assert (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)==frame
assert packages.plan(p)['source_sha256']==plan['source_sha256']
try:packages.export(params)
except FileExistsError:pass
else:raise AssertionError('Expected no-overwrite refusal')
print('PACKAGE_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PACKAGE_NATIVE_OK' in result.stdout
