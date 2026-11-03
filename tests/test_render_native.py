"""Dirty/unpacked image snapshots refuse before writing or launching workers."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_render_snapshot_refuses_unfrozen_pixels_without_live_edits(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nTARGET='+repr(str(tmp_path/'batch'))+'\n'+r'''
import bpy
from pathlib import Path
from mcpblender.blender import render_batches,compositing
image=bpy.data.images.new('UnsavedPixels',width=16,height=16)
p={'cameras':['Camera'],'expected_settings':compositing.pipeline()['settings_sha256'],'directory':TARGET}
ids=set(bpy.data.user_map())
for packed in (False,True):
    if packed:
        image.pixels=[.8,.2,.1,1.]*(16*16)
        image.pack();image.scale(32,32)
        assert image.packed_file and image.is_dirty
    try:render_batches.launch(p)
    except ValueError as e:assert 'packed/self-contained' in str(e)
    else:raise AssertionError('Unfrozen image snapshot accepted')
    assert set(bpy.data.user_map())==ids and not Path(TARGET).exists()
print('RENDER_SNAPSHOT_INPUT_GUARD_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'RENDER_SNAPSHOT_INPUT_GUARD_OK' in result.stdout
