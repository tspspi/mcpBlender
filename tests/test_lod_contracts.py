"""LOD contracts, policy boundaries and bundle traversal refusal."""
import asyncio
import json
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server,State
from mcpblender.lod_contracts import Generate
from mcpblender.lod_files import validate,MARKER,glb_report


def test_budgets_and_bundle_paths(tmp_path):
    base={'name':'Source','chain':'Asset','expected_source':'a'*64,'levels':[{'triangle_budget':200},{'triangle_budget':50}]}
    assert Generate.model_validate(base).transfer_normals
    assert Generate.model_validate(base|{'deformation':'MORPH'}).deformation=='MORPH'
    for patch in ({'levels':[]},{'levels':[{'triangle_budget':50},{'triangle_budget':100}]},{'chain':'ä'*21},{'max_relative_error':float('nan')},{'pose_frames':[1,1]},{'pose_frames':[1048575]},{'skin_max_influences':5},{'skin_joint_importance':-1}):
        with pytest.raises(ValueError):Generate.model_validate(base|patch)
    (tmp_path/'manifest.json').write_text(json.dumps({'format':MARKER,'levels':[{'file':'../outside.glb'},{}]}))
    with pytest.raises(ValueError,match='member path'):validate(tmp_path)
    (tmp_path/'bad.glb').write_bytes(b'invalid')
    with pytest.raises(ValueError):glb_report(tmp_path/'bad.glb')


def test_readonly_lod_visibility_and_output_boundary(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_glb_deformation','inspect_lod_source','inspect_lod_chain','validate_lod_export','sample_lod_chain','inspect_lod_export'}<=names
            assert not {'generate_lod_chain','activate_lod_level','export_lod_chain'}&names
    asyncio.run(run())
    with pytest.raises(ValueError,match='inside'):
        state.prepare('export_lod_chain',{'chain':'Asset','expected_chain':'a'*64,'directory':'../outside'})


def test_deformation_read_path_and_limits(tmp_path):
    from mcpblender.lod_contracts import InspectGLB
    config=Config();config.stdio.library_root=str(tmp_path/'library')
    _,state=build_server(config)
    assert State.input_paths('inspect_glb_deformation',{'path':'asset.glb'})==['asset.glb']
    with pytest.raises(ValueError,match='inside'):state.prepare('inspect_glb_deformation',{'path':'../outside.glb'})
    (tmp_path/'library').mkdir(exist_ok=True);(tmp_path/'library/scene.blend').write_bytes(b'fixture')
    with pytest.raises(ValueError,match='end'):state.prepare('inspect_glb_deformation',{'path':'scene.blend'})
    for patch in ({'limit':9},{'animation_samples':2},{'sample_limit':17},{'offset':33}):
        with pytest.raises(ValueError):InspectGLB.model_validate({'path':'asset.glb'}|patch)


def test_morph_timeline_clip_contracts():
    from mcpblender.lod_contracts import ExportPlan,Export
    base={'chain':'Asset','timeline_clips':[{'name':'Walk','frame_start':-2,'frame_end':8}]}
    assert ExportPlan.model_validate(base).timeline_clips[0].frame_start==-2
    assert Export.model_validate(base|{'expected_chain':'a'*64,'directory':'bundle'}).timeline_clips
    for clips in ([{'name':'Walk','frame_start':1,'frame_end':1}],[{'name':'Walk','frame_start':1.5,'frame_end':9}],base['timeline_clips']*2,[{'name':'Walk','frame_start':0,'frame_end':10001}]):
        with pytest.raises(ValueError):ExportPlan.model_validate(base|{'timeline_clips':clips})


def test_adoption_contracts_and_permissions(tmp_path):
    from mcpblender.lod_contracts import AdoptionPlan,Adopt,Readopt
    base={'name':'Source','inputs':[{'name':'Manual'}]}
    assert AdoptionPlan.model_validate(base).input_geometry=='EVALUATED_STATIC'
    assert Adopt.model_validate(base|{'chain':'Asset','expected_source':'a'*64})
    assert Readopt.model_validate(base|{'chain':'Asset','expected_source':'a'*64,'expected_management':'b'*64}).preserve_placement
    for patch in ({'inputs':[]},{'inputs':[{'name':'Source'}]},{'inputs':[{'name':'Manual'}]*2},{'inputs':[{'name':'Manual','material_slots':[-1]}]}, {'inputs':[{'name':'Manual','material_slots':[256]}]}, {'pose_frames':[1,1]}, {'input_geometry':'LIVE'}, {'inputs':[{'name':'Manual','material_slots':[True]}]}, {'inputs':[{'name':'Manual','uv_maps':{'A':'UV','B':'UV'}}]}, {'max_relative_error':float('nan')}):
        with pytest.raises(ValueError):AdoptionPlan.model_validate(base|patch)
    with pytest.raises(ValueError):Adopt.model_validate(base|{'chain':'ä'*21,'expected_source':'a'*64})
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_lod_adoption' in names
            assert not {'adopt_lod_chain','readopt_lod_chain'}&names
    asyncio.run(run())
