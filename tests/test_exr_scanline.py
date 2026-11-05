"""Bounded decoder against independent installed OpenEXR encoding and corruption."""
from pathlib import Path
import os
import shlex
import shutil
import struct
import subprocess
import pytest
from mcpblender import exr_scanline as exr

@pytest.fixture(scope='module')
def native_exrs(tmp_path_factory):
    if not shutil.which('c++') or not shutil.which('pkg-config'):pytest.skip('Existing compiler/OpenEXR headers required; no installation attempted')
    pkg=subprocess.run(['pkg-config','--cflags','--libs','OpenEXR'],capture_output=True,text=True)
    if pkg.returncode:pytest.skip('Existing OpenEXR development files required')
    root=tmp_path_factory.mktemp('native-exr');binary=root/'writer'
    subprocess.run(['c++','-std=c++17',str(Path(__file__).parent/'fixtures/exr_scanline.cpp'),'-o',str(binary),*shlex.split(pkg.stdout)],check=True,capture_output=True,text=True)
    subprocess.run([str(binary),str(root)],check=True,capture_output=True,text=True)
    return root

@pytest.mark.parametrize('codec',[0,1,2])
@pytest.mark.parametrize('multipart',[0,1])
@pytest.mark.parametrize('order',['','-decreasing'])
def test_native_encoded_values_and_orientation(native_exrs,codec,multipart,order):
    names=['field'+str(i) for i in range(8)]
    result=exr.decode(native_exrs/f'fixture-{codec}-{multipart}{order}.exr',names)
    assert result['data_window']==(-3,-2,31,16)
    assert result['width']==35 and result['height']==19
    for c,name in enumerate(names):
        assert list(result['channels'][name])==[((x*17+y*31+c*43)%101-50)/8 for y in range(19) for x in range(35)]
    # Skip unrequested parts while retaining exact per-channel association.
    assert list(exr.decode(native_exrs/f'fixture-{codec}-{multipart}{order}.exr',['field7'])['channels']['field7'])==list(result['channels']['field7'])


def test_corruption_limits_hash_and_cancellation(native_exrs,tmp_path,monkeypatch):
    source=native_exrs/'fixture-2-1.exr';payload=source.read_bytes();path=tmp_path/'bad.exr'
    with source.open('rb') as f:
        multi,parts=exr.headers(f);table=f.tell()
    overlap=bytearray(payload);overlap[table+8:table+16]=overlap[table:table+8]
    for data in (payload[:-1],payload+b'trailer',payload[:table]+b'\0'*8+payload[table+8:],overlap):
        path.write_bytes(data)
        with pytest.raises(ValueError):exr.decode(path,['field0'])
    path.write_bytes(payload);offset=struct.unpack_from('<Q',payload,table)[0]
    corrupted=bytearray(payload);struct.pack_into('<i',corrupted,offset,12);path.write_bytes(corrupted)
    with pytest.raises(ValueError,match='part'):exr.decode(path,['field0'])
    with pytest.raises(ValueError,match='hash'):exr.decode(source,['field0'],expected_sha256='0'*64)
    def stop():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):exr.decode(source,['field0'],cancelled=stop)
    with pytest.raises(ValueError,match='missing'):exr.decode(source,['missing'])
    monkeypatch.setattr(exr,'MAX_OUTPUT_BYTES',1)
    with pytest.raises(ValueError,match='memory'):exr.decode(source,['field0'])


def test_unsupported_profiles_corrupt_zip_and_work_budgets(native_exrs,tmp_path,monkeypatch):
    source=native_exrs/'fixture-2-1.exr';payload=source.read_bytes();path=tmp_path/'bad.exr'
    for flag in (0x200,0x800):
        data=bytearray(payload);struct.pack_into('<I',data,4,struct.unpack_from('<I',data,4)[0]|flag);path.write_bytes(data)
        with pytest.raises(ValueError,match='profile'):exr.decode(path,['field0'])
    data=payload.replace(b'compression\0compression\0\1\0\0\0\3',b'compression\0compression\0\1\0\0\0\4',1);path.write_bytes(data)
    with pytest.raises(ValueError,match='ZIP only'):exr.decode(path,['field0'])
    data=payload.replace(b'field0\0\2\0\0\0',b'field0\0\1\0\0\0',1);path.write_bytes(data)
    with pytest.raises(ValueError,match='float32'):exr.decode(path,['field0'])
    with source.open('rb') as f:
        exr.headers(f);offset=struct.unpack('<Q',f.read(8))[0]
    data=bytearray(payload);data[offset+12]^=255;path.write_bytes(data)
    with pytest.raises(ValueError,match='ZIP'):exr.decode(path,['field0'])
    monkeypatch.setattr(exr,'MAX_DECODED_BYTES',1)
    with pytest.raises(ValueError,match='work'):exr.decode(source,['field0'])


def test_nonregular_inputs_are_refused_before_reading(tmp_path):
    pipe=tmp_path/'fifo';os.mkfifo(pipe)
    for path in (tmp_path,pipe):
        with pytest.raises(ValueError,match='nonregular'):exr.decode(path,['channel'])


@pytest.mark.parametrize('count',[31,32,33])
def test_multipart_exact_part_budget_in_decoder_and_job_header(native_exrs,count):
    from mcpblender.render_jobs import image_header
    path=native_exrs/f'parts-{count}.exr'
    if count>32:
        with pytest.raises(ValueError,match='part budget'):exr.decode(path,['field0'])
        with pytest.raises(ValueError,match='part limit'):image_header(path)
    else:
        names=['field'+str(i) for i in range(count)]
        result=exr.decode(path,names)
        assert [list(result['channels'][n]) for n in names]==[[i-16.5] for i in range(count)]
        assert len(image_header(path)['parts'])==count
