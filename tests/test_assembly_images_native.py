"""Assembly images use saved bytes, never generic writable pixel records."""
import os
from pathlib import Path
import subprocess
from test_assembly_native import pytestmark


def test_image_graph_copy_guards_and_external_file_changes(tmp_path):
    script=tmp_path/'image-assets.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender.blender import assemblies as assets,bridge
from mcpblender.assembly_contracts import Create,Place
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object;obj.name='Textured'
mat=bpy.data.materials.new('Paint');mat.use_nodes=True;obj.data.materials.append(mat)
images=[]
for i in range(7):
    image=bpy.data.images.new('Texture'+str(i),width=1024,height=1024);image.generated_color=(.1+i*.02,.3,.4,1);image.pixels[0:4]=(.1+i*.02,.3,.4,1);image.pack();images.append(image)
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
# Reject any accidental generic pixel-property traversal anywhere in this path.
original=assets.props;seen=[]
def bounded(value,*,exclude=()):
    if isinstance(value,bpy.types.Image):assert 'pixels' in exclude;seen.append(value.name)
    return original(value,exclude=exclude)
assets.props=bounded
plan=assets.source({'objects':['Textured']})[2];assert plan['can_create'] and plan['graph_signature_version']==2,plan
base=set(bpy.data.user_map());original_image=images[0]
original_image.pixels[0]=.9
dirty=assets.source({'objects':['Textured']})[2];assert not dirty['can_create'] and any('unsaved' in v for v in dirty['blockers'])
try:assets.create(Create(objects=['Textured'],collection='Refused',expected_source=dirty['source_sha256']).model_dump())
except ValueError as e:assert 'unsaved' in str(e)
else:raise AssertionError('Unsaved pixel copy accepted')
assert set(bpy.data.user_map())==base
original_image.pack();changed=assets.source({'objects':['Textured']})[2]
assert changed['can_create'] and changed['source_sha256']!=plan['source_sha256']
created=assets.create(Create(objects=['Textured'],collection='Prototype',expected_source=changed['source_sha256']).model_dump())
assert created['valid'] and created['source_signature_version']==2
copy=bpy.data.objects[created['copied_objects']['Textured']];private={n.image for n in copy.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE'}
assert not set(images)&private
first=assets.place(Place(collection='Prototype',expected_asset=created['assembly_sha256'],name='One').model_dump())
second=assets.place(Place(collection='Prototype',expected_asset=created['assembly_sha256'],name='Two',location=[3,0,0]).model_dump())
assert bpy.data.objects['One'].instance_collection==bpy.data.objects['Two'].instance_collection
# Legacy prototypes keep their identity and historical source hash; guards are current.
col=bpy.data.collections['Prototype'];meta=json.loads(col[assets.META]);history=meta['source_sha256'];meta.pop('source_signature_version');col[assets.META]=json.dumps(meta)
legacy=assets.inspect_asset({'collection':'Prototype'});assert legacy['valid'] and legacy['source_signature_version']==1 and json.loads(col[assets.META])['source_sha256']==history
generated=bpy.data.images.new('Generated',width=16,height=16);mat.node_tree.nodes.new('ShaderNodeTexImage').image=generated
assert assets.source({'objects':['Textured']})[2]['can_create']
# External image bytes participate even without reloading Blender's image cache.
path=Path(OUTPUT)/'external.png';file_image=bpy.data.images.new('External',width=16,height=16);file_image.generated_color=(.2,.4,.6,1);file_image.filepath_raw=str(path);file_image.file_format='PNG';file_image.save();bpy.data.images.remove(file_image)
file_image=bpy.data.images.load(str(path),check_existing=False);mat.node_tree.nodes.new('ShaderNodeTexImage').image=file_image
external=assets.source({'objects':['Textured']})[2];assert external['can_create']
payload=path.read_bytes();path.write_bytes(payload+b'changed')
assert assets.source({'objects':['Textured']})[2]['source_sha256']!=external['source_sha256']
path.write_bytes(payload);assert assets.source({'objects':['Textured']})[2]['source_sha256']==external['source_sha256']
changed_once=[False]
def mutate_file():
    if not changed_once[0]:path.write_bytes(payload+b'race');changed_once[0]=True
assert 'changed while hashing' in assets.image_record(file_image,mutate_file)[2]
path.write_bytes(payload)
# Reading a cached image reference to a nonregular file must not block on open.
import os
fifo=Path(OUTPUT)/'not-an-image';os.mkfifo(fifo);old_path=file_image.filepath_raw;file_image.filepath_raw=str(fifo)
assert 'nonregular' in assets.image_record(file_image)[2]
file_image.filepath_raw=old_path;fifo.unlink()

path.unlink();missing=assets.source({'objects':['Textured']})[2];assert not missing['can_create'] and any('Unreadable' in v for v in missing['blockers'])
path.write_bytes(payload)
file_image.source='SEQUENCE';assert not assets.source({'objects':['Textured']})[2]['can_create'];file_image.source='FILE'
# File/total caps are checked without allocating encoded or decoded Python arrays.
previous=assets.IMAGE_FILE_LIMIT;assets.IMAGE_FILE_LIMIT=1
assert not assets.source({'objects':['Textured']})[2]['can_create'];assets.IMAGE_FILE_LIMIT=previous
previous=assets.IMAGE_TOTAL_LIMIT;assets.IMAGE_TOTAL_LIMIT=1
try:assets.source({'objects':['Textured']})
except ValueError as e:assert 'two GiB' in str(e)
else:raise AssertionError('Aggregate image budget ignored')
assets.IMAGE_TOTAL_LIMIT=previous
assert seen and assets.inspect_asset({'collection':'Prototype'})['valid']
saved=Path(OUTPUT)/'textured-assembly.blend';bpy.ops.wm.save_as_mainfile(filepath=str(saved));bpy.ops.wm.open_mainfile(filepath=str(saved),load_ui=False,use_scripts=False)
assert assets.inspect_asset({'collection':'Prototype'})['valid'] and assets.instance({'name':'One'})['world_bounds']
print('BOUNDED_ASSEMBLY_IMAGES_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOUNDED_ASSEMBLY_IMAGES_OK' in result.stdout
