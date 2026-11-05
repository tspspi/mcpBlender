"""Selection keeps semantic/native/shader identity through save and reopen."""
import os,shutil,subprocess,json
from pathlib import Path
from test_botanical_native import pytestmark


def test_native_instance_ids_survive_selection_and_reopen(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(Path(__file__).with_name('native_instance_ids.py')),'--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=120)
    (tmp_path/'native.log').write_text(run.stdout+'\n'+run.stderr)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'NATIVE_INSTANCE_IDS_OK' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text());assert proof['before']==proof['selected']
    if destination:=os.environ.get('MCPBLENDER_INSTANCE_ID_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for file in tmp_path.iterdir():
            if file.is_file():shutil.copy2(file,out/file.name)
