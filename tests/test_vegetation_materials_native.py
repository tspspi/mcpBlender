"""Material source contracts distinguish optical parameters and encoded delivery."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_material_contracts_guards_detail_and_bundle_delivery(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'materials.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany,foliage,vegetation_materials as schema,vegetation_interchange as base,vegetation_lod_files as lodfiles
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,botanical_surfaces as surfaces,vegetation_materials as materials,vegetation_export as exporter,vegetation_lods as lods,vegetation_lod_export as lodexport,bridge
from mcpblender.wind_contracts import BotanicalExportPlan
from mcpblender.vegetation_lod_contracts import Source
from mcpblender.botanical_surface_contracts import Configure as SurfaceConfigure
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe});tree=trees.create({'collection':'MaterialOak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5});plan=leaves.dispatch('plan_botanical_foliage',{'collection':'MaterialOak','foliage':cfg})
tree=leaves.dispatch('configure_botanical_foliage',{'collection':'MaterialOak','foliage':cfg,'expected_tree':tree['tree_sha256'],'expected_foliage':plan['foliage_sha256']})
inspected=materials.inspect({'collection':'MaterialOak'});contract=inspected['contract'];schema.validate(contract)
leaf=next(m for m in contract['materials'] if m['model']=='MANAGED_THIN_FOLIAGE');bark=next(m for m in contract['materials'] if m['model']=='PRINCIPLED')
assert leaf['alpha']['mode']=='OPAQUE' and leaf['double_sided'] and leaf['transmission']['model']=='ARTISTIC_DIFFUSE_BACKLIGHT'
assert leaf['transmission']['thickness_m'] is None and all(v is None for v in leaf['maps'].values())
assert leaf['front_inputs']['Base Color']['source']=='CONSTANT_FRONT' and leaf['source_base_colors']['front']!=leaf['source_base_colors']['back']
assert not leaf['portable_optical_equivalence'] and leaf['bake_hint']['thin_foliage_mode']=='FRONT_PBR'
args=BotanicalExportPlan(collection='MaterialOak',material_mode='PARAMETERS').model_dump();old=exporter.inspect(args)
mat=bpy.data.materials[leaf['name']];mat.node_tree.nodes['Leaf Sides'].inputs[1].default_value=(.12,.3,.02,1)
try:exporter.export(args|{'expected_export':old['export_sha256'],'directory':OUTPUT+'/stale','max_bytes':512*1024**2})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Material edit did not invalidate parameter export guard')
for name,profile in ((bark['name'],'OAK_BARK'),(leaf['name'],'OAK_LEAF')):
    settings={'profile':profile}
    surfaces.configure(SurfaceConfigure(material=name,settings=settings,expected_material=surfaces.inspect({'material':name})['material_sha256']).model_dump())
contract=materials.inspect({'collection':'MaterialOak'})['contract'];leaf=next(m for m in contract['materials'] if m['model']=='MANAGED_THIN_FOLIAGE')
assert contract['missing_detail_uv']['shoots']==[{'material':bark['name'],'uv_map':'BarkUV'}]
assert leaf['detail']['profile']=='OAK_LEAF' and {'Base Color','Normal'}<=set(leaf['bake_required_inputs'])
plan=exporter.inspect(args);ids=set(bpy.data.user_map());guard=trees.inspect({'collection':'MaterialOak'})['tree_sha256']
result=exporter.export(args|{'expected_export':plan['export_sha256'],'directory':OUTPUT+'/tree','max_bytes':512*1024**2});base.validate(OUTPUT+'/tree')
record=json.loads((Path(OUTPUT)/'tree/manifest.json').read_text());assert set(record['material_delivery'])=={'wood','shoots','leaf-0','leaf-1','leaf-2'}
assert set(bpy.data.user_map())==ids and trees.inspect({'collection':'MaterialOak'})['tree_sha256']==guard
p=Source(collection='MaterialOak',levels=[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0}]).model_dump();plan=lods.plan(p)[-1]
state=lods.create(p|{'expected_plan':plan['plan_sha256'],'lod_collection':'MaterialLods','display_offset_m':[8,0,0]})
mc=materials.inspect({'lod_collection':'MaterialLods'});ids=set(bpy.data.user_map())
params={'lod_collection':'MaterialLods','expected_lods':state['lods_sha256'],'material_mode':'PARAMETERS','expected_materials':mc['materials_sha256'],'placement':'SOURCE','directory':OUTPUT+'/lods','max_bytes':512*1024**2}
try:lodexport.export(params|{'expected_materials':'0'*64})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale LOD material guard accepted')
lodexport.export(params);lodfiles.validate(OUTPUT+'/lods');assert set(bpy.data.user_map())==ids
image_plan=trees.plan({'recipe':recipe});image_tree=trees.create({'collection':'ImageOak','recipe':recipe,'expected_model':image_plan['model_sha256'],'location':[8,0,0],'radial_sides':8,'bark_tile_length':1})
image=bpy.data.images.new('SourcePixels',width=32,height=32,alpha=True);image.pixels.foreach_set([.2,.6,.1,1]*1024);image.filepath_raw=OUTPUT+'/source.png';image.file_format='PNG';image.save();bpy.data.images.remove(image)
image=bpy.data.images.load(OUTPUT+'/source.png',check_existing=False);image.pack()
mat=bpy.data.materials[image_tree['geometry']['bark_material']];texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
uv=mat.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='BarkUV';mat.node_tree.links.new(uv.outputs['UV'],texture.inputs['Vector']);mat.node_tree.links.new(texture.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
image_args=BotanicalExportPlan(collection='ImageOak',material_mode='PARAMETERS').model_dump();image_info=exporter.inspect(image_args)
assert image_info['materials']['materials'][0]['front_inputs']['Base Color']['source']=='TEXTURE_IMAGE'
assert 'Base Color' not in image_info['materials']['materials'][0]['bake_required_inputs']
exporter.export(image_args|{'expected_export':image_info['export_sha256'],'directory':OUTPUT+'/image-tree','max_bytes':512*1024**2})
base.validate(OUTPUT+'/image-tree');image_record=json.loads((Path(OUTPUT)/'image-tree/manifest.json').read_text())['material_delivery']['wood']
assert len(image_record['images'])==1 and image_record['images'][0]['width']==32 and image_record['rgba8_base_bytes_estimate']==4096
semantic=Path(OUTPUT)/'lods/semantics.json';data=json.loads(semantic.read_text());data['materials']['materials'][0]['alpha']['mode']='MASK';semantic.write_text(json.dumps(data))
r=Path(OUTPUT)/'lods/manifest.json';record=json.loads(r.read_text());record['files']=base.files(r.parent);r.write_text(json.dumps(record))
try:lodfiles.validate(r.parent)
except ValueError as e:assert 'material' in str(e).lower()
else:raise AssertionError('Contract tampering accepted after file rehash')
print('VEGETATION_MATERIAL_CONTRACT_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'VEGETATION_MATERIAL_CONTRACT_OK' in result.stdout
