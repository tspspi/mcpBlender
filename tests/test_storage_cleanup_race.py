"""Storage observations survive owned output cleanup between filesystem reads."""
from pathlib import Path
import pytest
from mcpblender import storage


@pytest.mark.parametrize('boundary',['disk_usage','device_stat'])
def test_removed_output_directory_uses_surviving_parent(tmp_path,monkeypatch,boundary):
    target=tmp_path/'job';target.mkdir();original_usage=storage.shutil.disk_usage;original_stat=Path.stat;read=[False]
    def usage(path):
        if path==target:
            if boundary=='disk_usage':
                target.rmdir();raise FileNotFoundError(target)
            result=original_usage(path);read[0]=True;return result
        return original_usage(path)
    def stat(path,*args,**kwargs):
        if path==target and read[0]:
            read[0]=False;target.rmdir();raise FileNotFoundError(target)
        return original_stat(path,*args,**kwargs)
    monkeypatch.setattr(storage.shutil,'disk_usage',usage);monkeypatch.setattr(Path,'stat',stat)
    value=storage.snapshot(target)
    assert value['path']==str(target) and value['filesystem_path']==str(tmp_path)
    assert value['device']==tmp_path.stat().st_dev and value['free_bytes']>0
