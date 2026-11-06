"""Frequent native checkpoints must not flood durable broker progress writes."""
import os,shutil,subprocess
from pathlib import Path
import pytest

@pytest.mark.blender
@pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Requires opted-in installed Blender')
def test_native_cooperative_cancellation_poll_rate_and_phase():
    helper=Path(__file__).with_name('native_cancellation_polling.py')
    result=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1])],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'CANCELLATION_POLLING_COMPLETE' in result.stdout
    assert 'DURABLE_CANCELLATION_POLLING_COMPLETE' in result.stdout
