"""Bounded botanical profiles do not accept arbitrary shader/RNA parameters."""
import pytest
from mcpblender.botanical_surface_contracts import Create


def test_surface_profile_limits_and_opaque_colors():
    for settings in ({'profile':'UNKNOWN'},{'profile':'OAK_LEAF','vein_pairs':True},{'profile':'OAK_LEAF','vein_pairs':24},{'profile':'OAK_LEAF','vein_color':[.2,.4,.1,.5]},{'profile':'OAK_BARK','cross_scale':0},{'profile':'OAK_BARK','bump_distance':float('nan')},{'profile':'OAK_BARK','unexpected':1}):
        with pytest.raises(ValueError):Create.model_validate({'material':'Tree','settings':settings})
    assert Create.model_validate({'material':'Tree','settings':{'profile':'OAK_BARK'}}).settings.profile=='OAK_BARK'
