"""Keep semantic JSON exact while avoiding huge native text-editor lines."""
import json
import subprocess
from pathlib import Path
import pytest
from mcpblender import json_text


def test_wrapping_preserves_quoted_punctuation_unicode_and_numbers():
    record={'leaves':[{'id':str(i),'quoted':'a, "b", \\,\n\u03b1','value':[1.5,-2,None,True]} for i in range(100)]}
    parts=list(json_text.chunks(record,line_limit=64,chunk_limit=256,max_line=512))
    encoded=''.join(parts)
    assert len(parts)>10 and json.loads(encoded)==record
    assert encoded.replace('\n','')==json.dumps(record,sort_keys=True,allow_nan=False)
    assert max(map(len,encoded.splitlines()))<512
    assert all(p.endswith('\n') for p in parts[:-1])
    with pytest.raises(ValueError,match='line limit'):
        list(json_text.chunks({'oversized':'x'*1024},line_limit=64,max_line=512))
    with pytest.raises(ValueError):list(json_text.chunks({'bad':float('nan')}))


@pytest.mark.skipif(not __import__('os').environ.get('MCPBLENDER_TEST_BLENDER'),reason='Requires native Blender')
def test_large_native_text_roundtrip_has_bounded_lines(tmp_path):
    script=tmp_path/'text.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json,time
from mcpblender.json_text import chunks
value={'leaves':[{'id':f'leaf-{i}','position':[i*.001,2.,3.],'rotation':[.1,.2,.3],'phase':.5,'parent':'branch-123','flutter':.25} for i in range(88704)]}
text=bpy.data.texts.new('SemanticWitness');start=time.monotonic();count=0
for part in chunks(value):text.write(part);count+=1
actual=text.as_string()
assert count>32 and len(actual)>10*1024**2
assert max(map(len,actual.splitlines()))<65536
assert json.loads(actual)==value
print('BOUNDED_JSON_NATIVE_OK',len(actual),count,time.monotonic()-start)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOUNDED_JSON_NATIVE_OK' in result.stdout
