"""Native packed-image signatures retain legacy bytes and pixel-edit detection."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_streamed_packed_image_record_compatibility(tmp_path):
    script=tmp_path/'images.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mcpblender import botany
from mcpblender.blender import wind_preview,assemblies
images=[]
for i in range(3):
    image=bpy.data.images.new('Packed'+str(i),width=32,height=32)
    image.pixels[0:4]=(.1+i*.1,.2,.3,1);image.pack();images.append(image)
expected=botany.digest([(v.bl_rna.identifier,v.name,assemblies.record(v)) for v in sorted(images,key=lambda v:(v.bl_rna.identifier,v.name))])
actual=wind_preview.signature(set(images));assert actual==expected
original_props=assemblies.props
seen=[]
def bounded_props(value,*,exclude=()):
    if isinstance(value,bpy.types.Image):
        assert 'pixels' in exclude;seen.append(value.name)
    return original_props(value,exclude=exclude)
assemblies.props=bounded_props
compact=wind_preview.signature(set(images),packed_images=True);assert len(seen)==3
assert wind_preview.signature(set(images),packed_images=True)==compact
assemblies.props=original_props
images[0].pixels[0]=.8
try:wind_preview.signature(set(images),packed_images=True)
except ValueError as e:assert 'clean static packed' in str(e)
else:raise AssertionError('Dirty decoded buffer accepted')
assert wind_preview.signature(set(images))!=actual
images[0].pack();assert wind_preview.signature(set(images),packed_images=True)!=compact
print('STREAMED_IMAGE_SIGNATURE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'STREAMED_IMAGE_SIGNATURE_OK' in result.stdout
