"""Real native custom-field export, independently decoded and tamper-rejected."""
import json
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark
from mcpblender.attribute_glb import verify,FORMAT


def test_actual_custom_fields_and_uv2(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'export.py';glb=tmp_path/'fields.glb';witness=tmp_path/'source.json'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from mcpblender.blender.bridge import gltf_compatibility
from mcpblender.attribute_glb import FORMAT,CORNER
obj=bpy.data.objects['Cube'];mesh=obj.data
mesh.materials.clear()
for name in ('First','Second'):
    m=bpy.data.materials.new(name);m.use_nodes=True;mesh.materials.append(m)
for polygon in mesh.polygons:polygon.material_index=polygon.index%2
uv=mesh.uv_layers.new(name='LightmapUV')
for i,v in enumerate(uv.data):v.uv=(i/32,.25+i/64)
fields=[]
for name,width,kind in [('_BEND',1,'FLOAT'),('_ANCHOR',3,'FLOAT_VECTOR'),('_PHASE',1,'FLOAT')]:
    attr=mesh.attributes.new(name=name,type=kind,domain='CORNER');values=[]
    for i,item in enumerate(attr.data):
        row=[i*.125] if width==1 else [i*.5,-i*.25,1+i*.125]
        if width==1:item.value=row[0]
        else:item.vector=row
        values.append(row)
    fields.append({'semantic':name,'components':width,'values':values})
a=mesh.attributes.new(name=CORNER,type='FLOAT',domain='CORNER')
for i,item in enumerate(a.data):item.value=i
mesh.calc_loop_triangles()
source={'format':FORMAT,'positions':[list(mesh.vertices[l.vertex_index].co) for l in mesh.loops],
        'uvs':[[list(v.uv) for v in layer.data] for layer in mesh.uv_layers],
        'triangles':[list(t.loops) for t in mesh.loop_triangles],'fields':fields}
mesh.update()
with gltf_compatibility():bpy.ops.export_scene.gltf(filepath=GLB,export_format='GLB',use_selection=True,export_animations=False,export_attributes=True)
open(WITNESS,'w').write(json.dumps(source))
'''.replace('filepath=GLB','filepath='+repr(str(glb))).replace('WITNESS',repr(str(witness))))
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    source=json.loads(witness.read_text());proof=verify(glb,source)
    assert proof['uv_channels']==2 and proof['triangles']==12 and proof['source_corners']==24 and proof['primitives']==2
    source['fields'][0]['values'][3][0]+=.1
    import pytest
    with pytest.raises(ValueError,match='custom field'):verify(glb,source)
    original=json.loads(witness.read_text())
    for kind in ('position','uv','triangle','nonfinite','placement'):
        changed=json.loads(json.dumps(original))
        if kind=='position':changed['positions'][0][0]+=.1
        elif kind=='uv':changed['uvs'][1][0][0]+=.1
        elif kind=='triangle':changed['triangles'][0].reverse()
        elif kind=='nonfinite':changed['fields'][0]['values'][0][0]=float('inf')
        else:changed['matrix_world']=[[1,0,0,1],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        with pytest.raises(ValueError):verify(glb,changed)



def test_bundle_packing_isolation_and_cancellation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'bundle.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender.blender import attribute_export as api,bridge,attributes
from mcpblender.attribute_contracts import ExportBundle,ExportPlan
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
obj=bpy.data.objects['Cube'];mesh=obj.data;mesh.use_fake_user=True
obj.location=(3,-2,5);obj.rotation_euler=(.2,-.3,.4);obj.scale=(1.2,.8,1.1);bpy.context.scene.unit_settings.scale_length=.01
uv=mesh.uv_layers.new(name='LightmapUV')
for i,item in enumerate(uv.data):item.uv=(i/32,.3+i/64)
fields=[]
for name,kind,domain,value in [('weight','FLOAT','POINT',.25),('branch','INT','FACE',16777216),('flag','BOOLEAN','FACE',True),('anchor','FLOAT_VECTOR','CORNER',(-3,2,7)),('rgba','FLOAT_COLOR','POINT',(2,.2,3,1))]:
    a=mesh.attributes.new(name=name,type=kind,domain=domain)
    for item in a.data:
        if kind=='FLOAT_VECTOR':item.vector=value
        elif kind=='FLOAT_COLOR':item.color=value
        else:item.value=value
    fields.append({'attribute':name,'semantic':'wind.'+name})
mesh.update();bpy.context.view_layer.update()
p=ExportPlan(name='Cube',fields=fields).model_dump();info=api.inspect(p);ids=set(bpy.data.user_map());guard=attributes.inspect({'name':'Cube'})['attributes_sha256']
p=ExportBundle(**p,expected_export=info['export_sha256'],directory=OUTPUT).model_dump()
def stop(v):
    if v.get('phase')=='verified attribute bundle before publication':raise bridge.OperationCancelled('publication')
bridge.report_progress=stop
try:api.export(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Export cancellation ignored')
assert not Path(OUTPUT).exists() and set(bpy.data.user_map())==ids
assert not list(Path(OUTPUT).parent.glob('.mcpblender-fields-*'))
assert attributes.inspect({'name':'Cube'})['attributes_sha256']==guard
bridge.report_progress=lambda v:None
result=api.export(p);assert result['proof']['uv_channels']==2 and result['proof']['world_placement_verified']
assert abs(result['proof']['scene_unit_scale']-.01)<1e-8 and len(result['proof']['fields'])==10
assert api.validate({'directory':OUTPUT})['proof']==result['proof']
assert set(bpy.data.user_map())==ids and attributes.inspect({'name':'Cube'})['attributes_sha256']==guard
try:api.export(p)
except FileExistsError:pass
else:raise AssertionError('Existing bundle overwritten')
asset=Path(OUTPUT)/'asset.glb';original=Path(OUTPUT)/'original.glb';asset.rename(original);asset.symlink_to(original.name)
try:api.validate({'directory':OUTPUT})
except ValueError as e:assert 'symlinks' in str(e)
else:raise AssertionError('Symlinked bundle file accepted')
asset.unlink();original.rename(asset)
data=asset.read_bytes();asset.write_bytes(data+b'x')
try:api.validate({'directory':OUTPUT})
except ValueError:pass
else:raise AssertionError('Corrupt bundle accepted')
asset.write_bytes(data)
mesh.attributes['branch'].data[0].value=16777217
try:api.inspect(ExportPlan(name='Cube',fields=fields).model_dump())
except ValueError as e:assert 'integers exactly' in str(e)
else:raise AssertionError('Lossy integer packing accepted')
print('ATTRIBUTE_BUNDLE_OK')
'''.replace('OUTPUT',repr(str(tmp_path/'delivery'))))
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'ATTRIBUTE_BUNDLE_OK' in result.stdout
