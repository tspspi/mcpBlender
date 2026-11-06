"""Explicit leaf-only occupancy and policy-contained batch inputs."""
import pytest
from mcpblender.config import Config
from mcpblender.depth_asset_contracts import Source,LayersSource
from mcpblender.server import build_server,State


def test_weighted_depth_requires_leaf_domain_and_resolves_all_inputs(tmp_path):
    for component in ('ALL','STRUCTURE'):
        with pytest.raises(ValueError,match='LEAVES'):Source(directory='reference',view='FRONT',component_filter=component,projected_coverage_directory='coverage')
    cfg=Config();cfg.stdio.library_root=str(tmp_path);cfg.bridge.socket_path=str(tmp_path/'socket')
    (tmp_path/'reference').mkdir();(tmp_path/'coverage').mkdir();_,state=build_server(cfg)
    layer={'view':'FRONT','component_filter':'LEAVES','projected_coverage_directory':'coverage'}
    single=state.prepare('inspect_botanical_depth_source',{'directory':'reference',**layer})
    batch=state.prepare('inspect_botanical_depth_layers',LayersSource(directory='reference',prefix='Weighted',layers=[layer]).model_dump())
    for command,args in [('inspect_botanical_depth_source',single),('create_botanical_depth_asset',single),('inspect_botanical_depth_layers',batch),('create_botanical_depth_layers',batch)]:
        assert set(State.input_paths(command,args))=={str(tmp_path/'reference'),str(tmp_path/'coverage')}
    for command,args in [('inspect_botanical_depth_source',{'directory':'reference',**(layer|{'projected_coverage_directory':'../outside'})}),('inspect_botanical_depth_layers',{'directory':'reference','prefix':'Weighted','layers':[layer|{'projected_coverage_directory':'../outside'}]})]:
        with pytest.raises(ValueError):state.prepare(command,args)
