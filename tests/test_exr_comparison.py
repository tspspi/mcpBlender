"""Independent HDR/alpha encoding, channel selection and unchanged numeric gates."""
from pathlib import Path
import shlex
import shutil
import subprocess
import pytest
from mcpblender import exr_comparison as exr


@pytest.fixture(scope='module')
def hdr_files(tmp_path_factory):
    if not shutil.which('c++') or not shutil.which('pkg-config'):pytest.skip('Existing compiler/OpenEXR headers required')
    pkg=subprocess.run(['pkg-config','--cflags','--libs','OpenEXR'],capture_output=True,text=True)
    if pkg.returncode:pytest.skip('Existing OpenEXR development files required; no installation attempted')
    root=tmp_path_factory.mktemp('hdr-comparison');binary=root/'writer'
    subprocess.run(['c++','-std=c++17',str(Path(__file__).parent/'fixtures/exr_comparison.cpp'),'-o',str(binary),*shlex.split(pkg.stdout)],check=True,capture_output=True,text=True)
    subprocess.run([str(binary),str(root)],check=True,capture_output=True,text=True)
    return root


def compare(root,a='premult',b='premult',**kwargs):
    return exr.compare(root/(a+'.exr'),root/(b+'.exr'),reference_pass=kwargs.pop('reference_pass_override','Layer.Combined'),candidate_pass=kwargs.pop('candidate_pass_override','Layer.Combined'),**kwargs)


def test_hdr_negative_channels_partial_alpha_and_premultiplication_once(hdr_files):
    result=compare(hdr_files,b='straight',candidate_alpha_mode='STRAIGHT')
    assert result['passed'] and result['method']=='PREMULTIPLIED_BOX_EXR_V1'
    assert result['width']==5 and result['height']==3
    assert result['reference_sha256']!=result['candidate_sha256']
    for row in result['levels']:
        assert row['premultiplied_rgb_rmse']==0 and row['overlap_rgb_rmse']==0
        assert row['overlap_reference_luminance']>1
    wrong=compare(hdr_files,b='straight')
    assert not wrong['passed'] and wrong['levels'][0]['overlap_rgb_rmse']>1
    assert compare(hdr_files,b='bare',candidate_pass_override='')['passed']


def test_hdr_error_thresholds_can_exceed_one_and_null_gates_survive(hdr_files):
    strict=compare(hdr_files,b='bright',policy={'max_abs_overlap_luminance_relative_bias':.1})
    assert not strict['passed'] and all(r['overlap_luminance_relative_bias']==pytest.approx(1) for r in strict['levels'])
    relaxed=compare(hdr_files,b='bright',policy={'max_premultiplied_rgb_rmse':5,'max_overlap_rgb_rmse':5,'max_abs_overlap_luminance_relative_bias':None})
    assert relaxed['passed'] and relaxed['policy']['max_abs_overlap_luminance_relative_bias'] is None
    for name in ('black','negative'):
        row=compare(hdr_files,a=name,b=name,policy={'max_abs_overlap_luminance_relative_bias':.1})
        assert not row['passed'] and row['levels'][0]['overlap_luminance_relative_bias'] is None


def test_explicit_pass_identity_dimensions_and_source_pixel_budget(hdr_files):
    wrong=compare(hdr_files,candidate_pass_override='Other.Combined')
    assert not wrong['passed'] and wrong['candidate_pass']=='Other.Combined'
    with pytest.raises(ValueError,match='pixel budget'):compare(hdr_files,max_pixels=14)
    with pytest.raises(ValueError,match='dimensions'):compare(hdr_files,b='wrong-size')
    with pytest.raises(ValueError,match='full-frame'):compare(hdr_files,a='offset',b='offset')
    with pytest.raises(ValueError,match='missing'):compare(hdr_files,reference_pass_override='Missing.Combined')


@pytest.mark.parametrize('name',['nan','bad-alpha'])
def test_invalid_numeric_samples_refuse_without_clamping(hdr_files,name):
    with pytest.raises(ValueError):compare(hdr_files,b=name)


def test_cancellation_and_no_input_file_mutation(hdr_files):
    path=hdr_files/'premult.exr';before=path.read_bytes()
    def stop():raise InterruptedError('cancelled')
    with pytest.raises(InterruptedError):compare(hdr_files,cancelled=stop)
    compare(hdr_files);assert path.read_bytes()==before
