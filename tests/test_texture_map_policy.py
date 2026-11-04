"""Projected alpha padding policy witnesses, legacy compatibility and tampering."""
import copy
import pytest
from mcpblender.texture_files import projected_map_policy as policy,validate_map_policy as validate


def test_unpadded_projected_alpha_and_legacy_or_self_bakes():
    job={'sources':['Leaves'],'maps':['BASE_COLOR','ALPHA'],'margin':8}
    expected={'method':'PROJECTED_ALPHA_NO_EXTEND_V1','alpha_margin':0,'other_map_margin':8}
    assert policy(job)==expected
    assert policy(job|{'sources':[]}) is None
    assert policy(job|{'maps':['NORMAL']}) is None
    assert policy(job|{'_texture_pipeline':'ATLAS'}) is None
    assert validate({}, {'maps':[{'map':'ALPHA'}]},job) is None # Historical bundles retain old meaning.
    saved={'map_policy':expected,'maps':[{'map':'BASE_COLOR','bake_margin':8},{'map':'ALPHA','bake_margin':0}]}
    record={'map_policy':expected};job=job|{'map_policy':expected}
    assert validate(record,saved,job)==expected
    for target in ('record','saved','job'):
        values={'record':copy.deepcopy(record),'saved':copy.deepcopy(saved),'job':copy.deepcopy(job)}
        values[target]['map_policy']['alpha_margin']=1
        with pytest.raises(ValueError,match='policy binding'):validate(values['record'],values['saved'],values['job'])
    changed=copy.deepcopy(saved);changed['maps'][1]['bake_margin']=8
    with pytest.raises(ValueError,match='padding differs'):validate(record,changed,job)
    changed=copy.deepcopy(saved);changed['maps'][1]['bake_margin']=False
    with pytest.raises(ValueError,match='padding differs'):validate(record,changed,job)
    with pytest.raises(ValueError,match='policy binding'):validate({},saved,job)
    with pytest.raises(ValueError,match='inventory'):validate(record,saved|{'maps':saved['maps'][:1]},job)
