"""Native implicit/linked/nonunit/bump and shared-closure moment calibration."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from test_botanical_native import pytestmark


def test_native_normal_inputs_and_worker_moment_wiring(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(Path(__file__).with_name('native_normal_inputs.py')),'--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'NORMAL_INPUT_MOMENTS_NATIVE_OK' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text());assert proof['thin_mismatch']['refused']
    if destination:=os.environ.get('MCPBLENDER_NORMAL_INPUT_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copy2(tmp_path/'proof.json',out/'native-proof.json')
