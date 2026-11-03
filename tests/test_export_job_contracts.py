"""Recovery key authority, fresh guards and non-mutating missing output paths."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.export_job_contracts import Cleanup,Recover


def test_export_job_defaults_and_discovery(tmp_path):
    assert Cleanup(directory='asset',expected_job='a'*64).dry_run
    assert not Recover(directory='asset',expected_job='a'*64).publish
    with pytest.raises(ValueError):Cleanup(directory='asset',expected_job='bad')
    cfg=Config();cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_library_write=False
    server,state=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_export_job','list_export_jobs'}<=names
            assert not {'recover_export_job','cleanup_export_job'}&names
    asyncio.run(run())
    with pytest.raises(ValueError,match='inside'):state.prepare('inspect_export_job',{'directory':'../foreign'})
    state.prepare('inspect_export_job',{'directory':'missing-parent/asset'})
    assert not (tmp_path/'library').exists()


def test_addon_archive_includes_native_recovery_dependencies(tmp_path):
    from mcpblender.server import addon_zip
    import zipfile
    path=tmp_path/'addon.zip';addon_zip(path)
    with zipfile.ZipFile(path) as archive:
        names=set(archive.namelist())
        assert {'mcpblender/export_jobs.py','mcpblender/package_files.py','mcpblender/lod_files.py','mcpblender/skin_glb.py','mcpblender/blender/export_recovery.py'}<=names
        assert all(name.endswith('.py') for name in names)


def test_dependency_free_recipe_matches_frontend_defaults():
    from mcpblender.lod_contracts import Generate
    from mcpblender.lod_recipe import suggested_recipe
    value={'name':'Source','chain':'Asset','deformation':'STATIC','expected_source':'a'*64,'levels':[{'triangle_budget':100}]}
    assert suggested_recipe(value)==Generate.model_validate(value).model_dump(exclude_none=True)
