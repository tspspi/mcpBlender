"""Real native geometry distinguishes conditional centre hits from area coverage."""
import os,shutil,subprocess
from pathlib import Path
import pytest

@pytest.mark.blender
@pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Requires opted-in installed Blender')
def test_quarter_pixel_geometry_excludes_selecting_centre_sample(tmp_path):
    helper=Path(__file__).with_name('native_projected_coverage_sampling.py')
    result=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(tmp_path)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PROJECTED_COVERAGE_ANALYTIC_COMPLETE' in result.stdout
