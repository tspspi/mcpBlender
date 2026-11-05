"""Moment reconstruction against independent unit-vector mixture oracles."""
import math
import random
import struct
import pytest
from mcpblender.normal_quadrature import fit,moments


def oracle(atoms):
    mean=[sum(a['weight']*a['direction'][i] for a in atoms) for i in range(3)]
    matrix=[[sum(a['weight']*a['direction'][i]*a['direction'][j] for a in atoms) for j in range(3)] for i in range(3)]
    return mean+[matrix[i][j] for i,j in ((0,0),(0,1),(0,2),(1,1),(1,2),(2,2))]


def test_flat_and_two_facet_distributions():
    single=fit([0,0,1,0,0,0,0,0,1]);assert len(single['atoms'])==1
    assert single['tolerance']==1e-5 and single['max_eigen_rotations']==64
    source=[0,0,.5,.75,0,0,0,0,.25];result=fit(source)
    assert len(result['atoms'])==2 and result['max_component_residual']<1e-12
    for atom in result['atoms']:assert abs(atom['direction'][2]-.5)<1e-12
    assert fit(source)==result


def test_many_oracle_mixtures_and_float32_rounding():
    rng=random.Random(84201)
    for count in (1,2,3,4,8,32):
        for _ in range(15):
            samples=[];weights=[rng.random() for _ in range(count)];mass=sum(weights)
            for w in weights:
                n=[rng.gauss(0,1) for _ in range(3)];length=math.sqrt(sum(v*v for v in n));samples.append({'weight':w/mass,'direction':[v/length for v in n]})
            original=oracle(samples)
            for values in (original,[struct.unpack('f',struct.pack('f',v))[0] for v in original]):
                saved=values[:];result=fit(values);assert values==saved
                atoms=result['atoms'];assert 1<=len(atoms)<=4 and all(v['weight']>0 for v in atoms)
                assert abs(sum(v['weight'] for v in atoms)-1)<1e-12
                assert max(abs(sum(t*t for t in v['direction'])-1) for v in atoms)<1e-12
                assert max(abs(a-b) for a,b in zip(oracle(atoms),original))<1e-5


def test_invalid_inputs_budgets_and_cancellation():
    for v in ([0]*9,[0,0,1,1,0,0,0,0,0],[math.nan]*9):
        with pytest.raises(ValueError):fit(v)
    with pytest.raises(ValueError,match='budget'):fit([.2,.3,.4,.2,0,0,.3,0,.5],max_rotations=1)
    def cancel():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):fit([0,0,1,0,0,0,0,0,1],cancelled=cancel)


def test_bounded_sampling_failure_reporting_and_contracts():
    from mcpblender.normal_quadrature import inspect_values
    from mcpblender.botanical_capture_contracts import Data
    with pytest.raises(ValueError):Data(directory='input',normal_quadrature=True)
    with pytest.raises(ValueError):Data(directory='input',material_inputs=True,normal_quadrature=True,max_quadrature_pixels=True)
    alpha=[1.]*100;geometry={'channels':{'TreeCapture.Combined.A':alpha}};values=[[0.]*100 for _ in range(9)];values[2]=[1.]*100;values[8]=[1.]*100
    report=inspect_values(geometry,[1.]*100,values,.01,7)
    assert report['candidate_pixels']==100 and report['sampled_pixels']==7 and report['successful_pixels']==7
    assert report['max_atoms']==1 and report['max_component_residual']<1e-12
    values[8][0]=0
    report=inspect_values(geometry,[1.]*100,values,.01,7)
    assert report['failed_pixels']==1 and report['successful_pixels']==6 and report['failure_reasons']


def test_sampling_excludes_invalid_coverage_without_editing_it():
    from mcpblender.normal_quadrature import inspect_values
    alpha=[1.,1.1,float('nan'),0.];geometry={'channels':{'TreeCapture.Combined.A':alpha}}
    values=[[0.]*4 for _ in range(9)];values[2]=[1.]*4;values[8]=[1.]*4
    report=inspect_values(geometry,[1.]*4,values,.01,4)
    assert report['candidate_pixels']==1 and report['sampled_pixels']==1 and report['successful_pixels']==1
    assert alpha[1]==1.1 and math.isnan(alpha[2])
