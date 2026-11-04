"""All-level wood/shoot/template layout quality, without image-bake claims."""
from pathlib import Path
import os
import subprocess
from test_botanical_native import pytestmark


def test_complete_profile_pixel_chart_allocation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'profile.py'
    output=os.environ.get('MCPBLENDER_CHART_LAYOUT_EVIDENCE_DIR',str(tmp_path))
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(output)+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_lods as lods,vegetation_bake as prep,texture_quality as quality,bridge,vegetation_materials,botanical_surfaces as surfaces
from mcpblender.vegetation_lod_contracts import Source as LodSource
from mcpblender.vegetation_bake_contracts import Source
from mcpblender.texture_quality_contracts import Inspect
from mcpblender.botanical_surface_contracts import Configure
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
planned=trees.plan({'recipe':recipe})
tree=trees.create({'collection':'Source','recipe':recipe,'expected_model':planned['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5,'variants':3})
planned=leaves.dispatch('plan_botanical_foliage',{'collection':'Source','foliage':cfg})
tree=leaves.dispatch('configure_botanical_foliage',{'collection':'Source','foliage':cfg,'expected_tree':tree['tree_sha256'],'expected_foliage':planned['foliage_sha256']})
source_objects=prep.objects({'collection':'Source'})[0]
for row in vegetation_materials.contract(source_objects)['materials']:
    surfaces.configure(Configure(material=row['name'],settings={'profile':'OAK_LEAF' if row['model']=='MANAGED_THIN_FOLIAGE' else 'OAK_BARK'},expected_material=surfaces.inspect({'material':row['name']})['material_sha256']).model_dump())
p=LodSource(collection='Source',levels=[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0},{'leaf_budget':100,'radial_sides':8,'min_branch_radius_m':0,'max_coverage_loss':.6,'max_silhouette_loss':.6},{'leaf_budget':60,'radial_sides':5,'max_coverage_loss':.75,'max_silhouette_loss':.75}]).model_dump()
planned=lods.plan(p)[-1];profile=lods.create(p|{'expected_plan':planned['plan_sha256'],'lod_collection':'Lods','display_offset_m':[0,0,0]})
p=Source(lod_collection='Lods',missing_uv_policy='BAKE_LAYOUT',texture_width=1024,texture_height=1024,tile_padding_pixels=8,chart_layout={'allow_stretch':True}).model_dump()
bad=p|{'chart_layout':p['chart_layout']|{'max_charts':1}};planned=prep.plan(bad)[-1];ids=set(bpy.data.user_map())
try:prep.create(bad|{'expected_plan':planned['plan_sha256'],'bake_collection':'Refused'})
except ValueError as e:assert 'max_charts' in str(e)
else:raise AssertionError('Chart budget did not refuse')
assert set(bpy.data.user_map())==ids and lods.inspect({'lod_collection':'Lods'})[-1]['lods_sha256']==profile['lods_sha256']
planned=prep.plan(p)[-1];state=prep.create(p|{'expected_plan':planned['plan_sha256'],'bake_collection':'Prepared'})
assert state['valid'] and len(state['components'])==11
assert lods.inspect({'lod_collection':'Lods'})[-1]['lods_sha256']==profile['lods_sha256']
root=Path(OUTPUT);root.mkdir(parents=True,exist_ok=True);proof={}
for role,row in state['components'].items():
    q=Inspect(name=row['name'],uv_map='BakeUV',width=1024,height=1024,min_texels_per_meter=32,min_chart_pixels=4,padding_pixels=2,mip_levels=1).model_dump()
    report=quality.inspect(q);proof[role]={'quality':report,'layout':row['chart_layout']}
    (root/'quality.json').write_text(json.dumps(proof,indent=2))
    print(role,report['complete'],report['passed'],report.get('minimum_directional_texels_per_meter'),flush=True)
    assert report['passed'],(role,report)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'prepared-profile.blend'))
bpy.ops.wm.open_mainfile(filepath=str(root/'prepared-profile.blend'),load_ui=False,use_scripts=False)
assert prep.inspect({'bake_collection':'Prepared'})[-1]['valid']
print('COMPLETE_PIXEL_CHART_PROFILE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=420)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'COMPLETE_PIXEL_CHART_PROFILE_OK' in result.stdout
