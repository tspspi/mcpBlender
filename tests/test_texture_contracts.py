"""Bake limits, library boundaries, read-only discovery and owned file inventory."""
import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.texture_contracts import BakeTextures,TextureSources
from mcpblender.texture_files import inventory,manifest,verify_steps,write_json,MARKER


def test_bake_limits_paths_and_policy(tmp_path):
    base={'name':'Low','expected_bake':'a'*64,'directory':'bundle'}
    for extra in ({'maps':['NORMAL','NORMAL']},{'width':4096,'height':4096},{'samples':0},{'cage_extrusion':float('nan')},{'sources':['Low']},{'cage':'Cage'},{'max_ray_distance':0}):
        with pytest.raises(ValueError):BakeTextures.model_validate(base|extra)
    with pytest.raises(ValueError):TextureSources(name='Low',sources=['High','High'])
    with pytest.raises(ValueError):TextureSources(name='Low',thin_foliage_mode='AUTOMATIC')
    assert TextureSources(name='Low').thin_foliage_mode=='REFUSE'
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    with pytest.raises(ValueError,match='library_root'):state.prepare('bake_textures',base|{'directory':'../outside'})
    with pytest.raises(ValueError,match='library_root'):state.prepare('inspect_projected_normal_transfer',{'directory':'../outside'})
    assert state.input_paths('inspect_projected_normal_transfer',{'directory':'bundle'})==['bundle']
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_texture_bake','validate_texture_bake','inspect_texture_job','inspect_projected_normal_transfer'}<=names
            assert not names & {'bake_textures','recover_texture_job','cleanup_texture_job'}
    asyncio.run(run())


def test_texture_inventory_hash_controls_and_preservation(tmp_path):
    (tmp_path/'textures').mkdir();(tmp_path/'textures/normal.png').write_bytes(b'normal')
    (tmp_path/'source.blend').write_bytes(b'source');(tmp_path/'asset.blend').write_bytes(b'asset')
    write_json(tmp_path/MARKER,{'state':'cancelled'})
    saved=manifest(tmp_path);list(verify_steps(tmp_path,saved))
    (tmp_path/'textures/normal.png').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='changed'):list(verify_steps(tmp_path,saved))
    unknown=tmp_path/'keep.txt';unknown.write_text('user')
    with pytest.raises(ValueError,match='Unknown'):inventory(tmp_path)
    assert unknown.read_text()=='user';unknown.unlink()
    (tmp_path/'textures/normal.png').unlink();(tmp_path/'textures/normal.png').symlink_to(tmp_path/'asset.blend')
    with pytest.raises(ValueError,match='symlink'):inventory(tmp_path)


def test_inventory_tolerates_atomic_status_rename(tmp_path,monkeypatch):
    from pathlib import Path
    pending=tmp_path/'result.json.tmp';pending.write_text('{}')
    (tmp_path/'asset.blend').write_bytes(b'asset')
    original=Path.lstat
    def disappeared(path,*args,**kwargs):
        if path==pending:raise FileNotFoundError(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'lstat',disappeared)
    rows,_=inventory(tmp_path)
    assert rows==[{'path':'asset.blend','bytes':5}]
