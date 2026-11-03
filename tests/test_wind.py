"""Known field phases, rigid hierarchical invariants and bounded motion sampling."""
import math
import pytest
from mcpblender import wind as w,botany as b,foliage
from mcpblender.wind_contracts import Sample,Settings


def model():return b.generate({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})


def test_common_field_known_answer_and_reproducibility():
    field={'steady_mps':[1,2,3],'waves':[{'amplitude_mps':[2,0,0],'wave_vector_rad_per_m':[1,0,0],'angular_frequency_rad_per_s':2,'phase_rad':0}]}
    assert w.velocity(field,[math.pi/2,0,0],0)==pytest.approx([3,2,3])
    assert w.velocity(field,[math.pi/2,0,0],math.pi/4)==pytest.approx([1,2,3])
    assert w.field({})==w.field({'gust_mps':1,'steady_mps':[2,0,0]})
    assert w.field({})!=w.field({'seed':2})
    for settings in ({'seed':True},{'waves':0},{'gust_mps':-1},{'steady_mps':[0,float('inf'),0]},{'frequency_hz':0},{'unknown':1}):
        with pytest.raises(ValueError):w.recipe(settings)
        with pytest.raises(ValueError):Settings.model_validate(settings)


def test_hierarchy_preserves_lengths_junctions_root_and_rigid_leaves():
    m=model();layout=foliage.generate(m,{'shoots_per_bud':1,'attachment_nodes':2})
    where={'rotation':[[0,-1,0],[1,0,0],[0,0,1]],'translation_m':[4,7,1],'scale':2}
    result=w.solve(m,{},.31,where);again=w.solve(m,{},.31,where);assert result==again
    assert result['metrics']['max_segment_length_error_m']<1e-12 and result['metrics']['max_junction_error_m']==0
    assert result['metrics']['root_anchor_displacement_m']==0 and result['metrics']['max_endpoint_displacement_m']>.001
    steady=w.solve(m,{'steady_mps':[2,0,0],'gust_mps':0},0)
    assert steady['branches'][0]['end_world_m'][0]>m['branches'][0]['end'][0]
    bound=w.rotation_bound(m,{},where)
    assert result['metrics']['max_accumulated_rotation_degrees']<=bound['accumulated_angle_upper_bound_degrees']
    assert w.rotation_bound(m,{'max_segment_degrees':0})['rotation_budget_proven_for_all_times']
    lookup={p['id']:p for p in result['branches']}
    for branch,pose in zip(m['branches'],result['branches']):
        assert b.length(b.sub(pose['end_world_m'],pose['start_world_m']))==pytest.approx(2*b.length(b.sub(branch['end'],branch['start'])),abs=1e-12)
        product=w.mm(w.transpose(pose['rotation_local']),pose['rotation_local'])
        assert all(abs(product[i][j]-(i==j))<1e-12 for i in range(3) for j in range(3))
        if branch['parent_id']:assert pose['start_world_m']==lookup[branch['parent_id']]['end_world_m']
    leaf=layout['leaves'][0];branch=m['branches'][leaf['parent_branch_index']]
    pose=w.leaf_pose(leaf,branch,lookup[branch['id']],{},.31,where)
    a=w.mv(pose['rotation_local'],(.1,.2,.3));c=w.mv(pose['rotation_local'],(.3,.2,.4))
    assert b.length(b.sub(a,c))==pytest.approx(math.sqrt(.05))
    assert abs(pose['flutter_angle_degrees'])<=4
    assert w.solve(m,{},1.1,where)['branches']!=result['branches']
    rest=w.solve(m,{'steady_mps':[0,0,0],'gust_mps':0},1)
    assert rest['metrics']['max_endpoint_displacement_m']<1e-12
    assert w.leaf_pose(leaf,branch,rest['branches'][branch_index(m,branch)],{'steady_mps':[0,0,0],'gust_mps':0},1)['flutter_angle_degrees']==0


def branch_index(m,branch):return next(i for i,v in enumerate(m['branches']) if v['id']==branch['id'])


def test_limits_placement_and_cooperative_cancellation():
    for placement in ({'scale':0},{'rotation':[[1,0,0],[0,2,0],[0,0,1]]},{'rotation':[[-1,0,0],[0,1,0],[0,0,1]]}):
        with pytest.raises(ValueError):w.placement(placement)
    fitted=w.placement({'rotation':[[1,1e-8,0],[0,1,0],[0,0,1]]})
    assert fitted['rotation']==[list(row) for row in w.IDENTITY]
    for settings in ({'seconds':[0,0]},{'seconds':[1e7]},{'max_work':0}):
        with pytest.raises(ValueError):Sample.model_validate({'collection':'Oak'}|settings)
    def stop():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):w.solve(model(),{},0,cancelled=stop)
    with pytest.raises(ValueError,match='rotation budget'):w.solve(model(),{'steady_mps':[100,100,0],'bend_degrees_per_mps':10,'max_segment_degrees':10,'max_accumulated_degrees':1},0)
