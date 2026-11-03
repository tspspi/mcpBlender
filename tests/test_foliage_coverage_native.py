"""Compare CPU projected coverage against independently rendered native instances."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_projected_blades_match_native_orthographic_alpha(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,os,json,shutil
from pathlib import Path
from mathutils import Vector
from mcpblender import foliage,foliage_coverage as c
from mcpblender.blender import botanical_trees as trees,botanical_foliage as fol,bridge
from mcpblender.botanical_contracts import Plan,Create
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
p=Plan.model_validate({'recipe':{'height':3,'crown_width':2.5,'trunk_radius':.08,'attractors':96,'iterations':6,'node_budget':256,'segment_length':.2}}).model_dump();plan=trees.plan(p)
a=Create.model_validate(p|{'collection':'Oak','expected_model':plan['model_sha256']}).model_dump(exclude_none=True)
state=trees.create(a);cfg={'shoots_per_bud':4,'attachment_nodes':8,'shoot_length':.5,'leaf':{'length':.2,'width':.1}}
planned=fol.dispatch('plan_botanical_foliage',{'collection':'Oak','foliage':cfg})
state=fol.dispatch('configure_botanical_foliage',{'collection':'Oak','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':planned['foliage_sha256']})
col,root,objects,text,owned,links,model,state=trees.inventory({'collection':'Oak'});layout=foliage.generate(model,cfg)
report=c.analyze(model,layout,resolution=128,views=['FRONT'],margin=.3)
view=report['views']['FRONT'];roles=fol.resolve_roles(state['foliage']);objects[0].hide_render=True;roles['so'].hide_render=True
# Native render uses generated geometry instances, not CPU layout/raster outputs.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.film_transparent=True
scene.render.resolution_x=128;scene.render.resolution_y=128;scene.render.resolution_percentage=100
lo,hi=view['frame_min_m'],view['frame_max_m'];width=hi[0]-lo[0];height=hi[1]-lo[1]
scene.render.pixel_aspect_x=width/height;scene.render.pixel_aspect_y=1
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam)
center=Vector(((lo[0]+hi[0])/2,0,(lo[1]+hi[1])/2));cam.location=center+Vector((0,-10,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.sensor_fit='HORIZONTAL';cam.data.ortho_scale=width;scene.camera=cam
path=Path(OUTPUT)/'coverage-native.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
img=bpy.data.images.load(str(path),check_existing=False);alpha=list(img.pixels)[3::4];native=sum(v>.5 for v in alpha)
expected=view['covered_pixels'];assert expected>150
assert abs(native-expected)/expected<.15,(native,expected,view)
if target:=os.environ.get('MCPBLENDER_FOLIAGE_EVIDENCE_DIR'):
    out=Path(target);out.mkdir(parents=True,exist_ok=True);shutil.copy2(path,out/path.name);(out/'coverage-native-proof.json').write_text(json.dumps({'cpu':report,'native_opaque_pixels':native},indent=2))
print('COVERAGE_NATIVE_OK',native,expected)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'COVERAGE_NATIVE_OK' in result.stdout
