"""A moment match must not be mistaken for rendered optical equivalence."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from test_botanical_native import pytestmark


def test_moment_exact_flat_shader_still_fails_world_lighting(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(Path(__file__).with_name('native_normal_quadrature.py')),'--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    proof=json.loads((tmp_path/'reconstruction-proof.json').read_text())
    for filter_name in ('box','default'):
        for lighting in ('world','sun'):
            entry=proof[filter_name+'-'+lighting]
            assert entry['quadrature']['max_component_residual']<1e-5 and len(entry['quadrature']['atoms'])<=4
            assert entry['alpha_exact']
        assert abs(proof[filter_name+'-sun']['relative_red_bias'])<1e-5
        # Fixed geometric normals and a weighted shader-normal mixture do not
        # reproduce the native faceted surface under the existing 10% gate.
        assert proof[filter_name+'-world']['relative_red_bias']<-.1
    if destination:=os.environ.get('MCPBLENDER_QUADRATURE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copy2(tmp_path/'reconstruction-proof.json',out/'native-proof.json')
