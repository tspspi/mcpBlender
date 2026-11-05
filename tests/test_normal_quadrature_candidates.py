"""Alternative factorizations must conserve an independent mixture oracle."""
import math
import random
import struct
import pytest
from mcpblender import normal_quadrature


@pytest.mark.parametrize('quantized',[False,True])
def test_bounded_factor_orientations_conserve_independent_mixture(quantized):
    rng=random.Random(881)
    for count in (1,2,4,12,32):
        for _ in range(5):
            points=[]
            for i in range(count):
                z=rng.uniform(-1,1);phi=rng.uniform(0,2*math.pi);r=math.sqrt(1-z*z)
                points.append((r*math.cos(phi),r*math.sin(phi),z))
            values=[sum(v[j] for v in points)/count for j in range(3)]
            values += [sum(v[i]*v[j] for v in points)/count for i,j in ((0,0),(0,1),(0,2),(1,1),(1,2),(2,2))]
            if quantized:values=[struct.unpack('<f',struct.pack('<f',v))[0] for v in values]
            for seed in (0,1,2,7,31,63):
                result=normal_quadrature.fit(values,factor_seed=seed)
                atoms=result['atoms']
                assert len(atoms)<=4 and all(a['weight']>0 for a in atoms)
                assert sum(a['weight'] for a in atoms)==pytest.approx(1,abs=1e-12)
                assert all(math.hypot(*a['direction'])==pytest.approx(1,abs=1e-12) for a in atoms)
                actual=[sum(a['weight']*a['direction'][j] for a in atoms) for j in range(3)]
                actual += [sum(a['weight']*a['direction'][i]*a['direction'][j] for a in atoms) for i,j in ((0,0),(0,1),(0,2),(1,1),(1,2),(2,2))]
                assert max(abs(a-b) for a,b in zip(values,actual))<=1e-5
                assert result['factor_seed']==seed and result['bisection_steps']<=156


@pytest.mark.parametrize('seed',[-1,64,True,.5,None])
def test_invalid_factor_orientation_budget(seed):
    with pytest.raises(ValueError,match='factor seed'):
        normal_quadrature.fit([0,0,1,0,0,0,0,0,1],factor_seed=seed)


def test_cancelled_factor_search_propagates():
    def cancelled():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):
        normal_quadrature.fit([0,0,1,0,0,0,0,0,1],factor_seed=63,cancelled=cancelled)
