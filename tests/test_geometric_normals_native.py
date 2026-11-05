"""Installed Cycles front/back smooth and bumped geometric-normal capture."""
import json,os,shutil,subprocess
from pathlib import Path
from test_botanical_native import pytestmark


def test_native_geometric_normals_and_unchanged_beauty(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(Path(__file__).with_name('native_geometric_normals.py')),'--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=180)
    (tmp_path/'native.log').write_text(run.stdout+'\n'+run.stderr)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'GEOMETRIC_NORMALS_NATIVE_OK' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text());assert len(proof)==8
    if destination:=os.environ.get('MCPBLENDER_GEOMETRIC_NORMAL_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in tmp_path.iterdir():
            if path.is_file():shutil.copy2(path,out/path.name)
