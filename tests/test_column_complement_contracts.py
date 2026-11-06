"""The component-column approximation has one explicit, bounded capture view."""
import pytest
from mcpblender.botanical_subset_contracts import Source


def test_column_complement_is_distinct_from_whole_leaf_selection():
    for mode in ('OBSERVED','UNOBSERVED'):
        assert Source(directory='capture',selection=mode,views=['FRONT','BACK']).selection==mode
    assert Source(directory='capture',selection='COLUMN_COMPLEMENT').views==['FRONT']
    with pytest.raises(ValueError,match='exactly one'):Source(directory='capture',selection='COLUMN_COMPLEMENT',views=['FRONT','BACK'])
