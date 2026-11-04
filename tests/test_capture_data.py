"""Independent analytic orthographic surface witness and observational semantics."""
from array import array
import math
import pytest
from mcpblender import capture_data
from mcpblender.botanical_capture_contracts import Data


def plane():
    identity=[[1.,0,0,0],[0,1.,0,0],[0,0,1.,0],[0,0,0,1.]]
    camera=[row[:] for row in identity];camera[2][3]=5
    fields={'Combined.A':[1]*4,'Depth.Z':[4]*4,'Position.X':[-.5,.5,-.5,.5],
            'Position.Y':[.5,.5,-.5,-.5],'Position.Z':[1]*4,'Normal.X':[0]*4,'Normal.Y':[0]*4,'Normal.Z':[1]*4}
    decoded={'width':2,'height':2,'data_window':(0,0,1,1),'channels':{'TreeCapture.'+k:array('f',v) for k,v in fields.items()}}
    meta={'source_root_matrix_world':identity,'scene_unit_scale':1,'bounds_root_local_m':{'min':[-1,-1,0],'max':[1,1,2]}}
    view={'view':'TOP','camera':'View','matrix_world':camera,'ortho_scale':2,'clip_start':.001,'clip_end':10}
    return decoded,meta,view


def test_analytic_plane_projection_units_and_raw_normal_lengths():
    data,meta,view=plane();report=capture_data.measure(data,meta,view,.5)
    assert report['covered_pixels']==report['opaque_pixels']==4
    assert report['reconstructed_outside_bounds']==report['covered_without_depth']==0
    for key in ('depth_position_error_m','position_projection_error_px','covered_normal_length_error'):assert report['statistics'][key]['max']==0
    data['channels']['TreeCapture.Position.Z'][0]+=.125;meta['scene_unit_scale']=.01
    data['channels']['TreeCapture.Normal.Z'][1]=.5
    report=capture_data.measure(data,meta,view,.5)
    assert report['statistics']['depth_position_error_m']['max']==pytest.approx(.00125)
    assert report['nonunit_covered_normal']==1 and report['statistics']['covered_normal_length_error']['max']==.5
    assert data['channels']['TreeCapture.Normal.Z'][1]==.5  # no normalization


def test_coverage_nohit_and_invalid_data_are_distinct():
    data,meta,view=plane();data['channels']['TreeCapture.Depth.Z'][0]=1e10
    data['channels']['TreeCapture.Combined.A'][1]=.5
    data['channels']['TreeCapture.Position.X'][2]=math.nan
    report=capture_data.measure(data,meta,view,.5)
    assert report['covered_pixels']==3 and report['covered_without_depth']==report['opaque_without_depth']==1 and report['uncovered_with_depth']==1
    assert report['nonfinite_covered']==1 and report['statistics']['depth_position_error_m']['count']==1
    data['data_window']=(-1,0,0,1)
    with pytest.raises(ValueError,match='data window'):capture_data.measure(data,meta,view,.5)
    data,meta,view=plane();view['matrix_world'][0][0]=2
    with pytest.raises(ValueError,match='uniform'):capture_data.measure(data,meta,view,.5)


def test_data_request_bounds():
    assert Data(directory='bundle')
    for patch in ({'views':['FRONT','FRONT']},{'views':[]},{'max_total_pixels':True},{'alpha_threshold':1},{'max_pixels':4194305}):
        with pytest.raises(ValueError):Data(directory='bundle',**patch)


def test_rotated_scaled_translated_root_keeps_metres_and_projection():
    data,meta,view=plane()
    meta['source_root_matrix_world']=[[0,0,2,2],[0,2,0,3],[-2,0,0,4],[0,0,0,1]]
    meta['scene_unit_scale']=.01
    view['matrix_world']=[[0,0,1,12],[0,1,0,3],[-1,0,0,4],[0,0,0,1]]
    view['ortho_scale']=4;view['clip_end']=20
    fields=data['channels'];fields['TreeCapture.Depth.Z']=array('f',[8]*4)
    fields['TreeCapture.Position.X']=array('f',[4]*4)
    fields['TreeCapture.Position.Y']=array('f',[4,4,2,2])
    fields['TreeCapture.Position.Z']=array('f',[5,3,5,3])
    fields['TreeCapture.Normal.X']=array('f',[1]*4);fields['TreeCapture.Normal.Z']=array('f',[0]*4)
    result=capture_data.measure(data,meta,view,.5)
    assert result['world_pixel_m']==.02 and result['reconstructed_outside_bounds']==0
    assert result['statistics']['depth_position_error_m']['max']==0
    assert result['statistics']['position_projection_error_px']['max']==0


def test_invalid_pose_magnitude_and_clipping_refuse():
    data,meta,view=plane()
    for i in range(3):meta['source_root_matrix_world'][i][i]=1e300
    with pytest.raises(ValueError,match='scale'):capture_data.measure(data,meta,view,.5)
    data,meta,view=plane();view['clip_end']=math.inf
    with pytest.raises(ValueError,match='clipping'):capture_data.measure(data,meta,view,.5)
