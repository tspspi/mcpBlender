"""Native world isolation, image packing, user edits and reversible publication."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_world_staging_image_admission_and_shared_scene_preservation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'world.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nROOT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json,math
from pathlib import Path
from mcpblender.blender import environment as api,bridge
from mcpblender.environment_contracts import Configure
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
scene=bpy.context.scene;old=scene.world;original=api.inspect();ids=set(bpy.data.user_map())
def config(settings,**kw):return Configure(expected_environment=api.inspect()['environment_sha256'],settings=settings,**kw).model_dump()
def stop(value):
    if value.get('phase')=='verified environment before handoff':raise bridge.OperationCancelled('world handoff')
bridge.report_progress=stop
try:api.configure(config({'mode':'COLOR','color':[.1,.2,.3]},film_transparent=True))
except bridge.OperationCancelled:pass
else:raise AssertionError('Environment cancellation ignored')
assert scene.world==old and not old.use_fake_user and not scene.render.film_transparent
assert set(bpy.data.user_map())==ids and api.inspect()['environment_sha256']==original['environment_sha256']
bridge.report_progress=lambda v:None
old.mist_settings.start=7;old.mist_settings.depth=31
other=bpy.data.scenes.new('SharedWorldScene');other.world=old;source=api.content(old)
state=api.configure(config({'mode':'COLOR','color':[.1,.2,.3]}));assert state['managed_unchanged'] and other.world==old
assert api.content(old)==source
assert scene.world.mist_settings.start==7 and scene.world.mist_settings.depth==31
# Adding another scene user invalidates a token before any IDs are allocated.
p=config({'mode':'COLOR'});other.world=scene.world;ids=set(bpy.data.user_map())
try:api.configure(p)
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Changed world sharing accepted')
assert set(bpy.data.user_map())==ids
other.world=old
# Replacing an unchanged single-user managed world retires only its own data.
world_name=scene.world.name;state=api.configure(config({'mode':'SKY','sun_elevation_degrees':40}));assert state['managed_unchanged']
assert state['retired_previous_managed'] and world_name not in bpy.data.worlds
sky=scene.world.node_tree.nodes['Sky'];assert sky.sky_type in api.catalog()['sky_models'] and abs(sky.sun_elevation-math.radians(40))<1e-6
# An edited managed graph is preserved and pinned, not silently deleted.
changed=scene.world;changed.node_tree.nodes['Sky'].sun_elevation=.2
assert not api.inspect()['managed_unchanged']
state=api.configure(config({'mode':'COLOR'}));assert state['previous_world_retained'] and changed.use_fake_user
# Build a small FLOAT EXR fixture and verify real header admission before load.
image=bpy.data.images.new('HDRInput',width=16,height=8,float_buffer=True)
image.pixels.foreach_set([v for y in range(8) for x in range(16) for v in ((4.,.1,.1,1.) if x<8 else (.1,.1,4.,1.))])
path=Path(ROOT)/'environment.exr';image.filepath_raw=str(path);image.file_format='OPEN_EXR';image.save()
from mcpblender import environment_files
info=environment_files.inspect(path,1024**2,128);assert (info['width'],info['height'])==(16,8)
args=config({'mode':'HDRI','image_path':str(path),'rotation_degrees':90})
before=api.inspect()['environment_sha256'];ids=set(bpy.data.user_map());bridge.report_progress=stop
try:api.configure(args)
except bridge.OperationCancelled:pass
else:raise AssertionError('HDRI cancellation ignored')
assert api.inspect()['environment_sha256']==before and set(bpy.data.user_map())==ids
bridge.report_progress=lambda v:None
state=api.configure(args);assert state['managed_unchanged'] and state['settings']['is_float']
world=scene.world;packed=world.node_tree.nodes['Environment'].image
assert packed.packed_file and not packed.filepath and packed.size[:]==(16,8)
assert abs(world.node_tree.nodes['Rotation'].inputs['Rotation'].default_value.z-math.pi/2)<1e-6
path.unlink();assert api.inspect()['managed_unchanged']
blend=Path(ROOT)/'environment.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.wm.open_mainfile(filepath=str(blend),load_ui=False,use_scripts=False)
scene=bpy.context.scene;assert api.inspect()['managed_unchanged']
image_name=scene.world.node_tree.nodes['Environment'].image.name
state=api.configure(config({'mode':'COLOR'}));assert state['retired_previous_managed'] and image_name not in bpy.data.images
# Root binding film flags participate in the guard; stale edits allocate no IDs.
p=config({'mode':'COLOR'});scene.render.film_transparent=not scene.render.film_transparent;ids=set(bpy.data.user_map())
try:api.configure(p)
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale environment accepted')
assert set(bpy.data.user_map())==ids
# Animated and object-dependent graphs report explicit inspection refusals.
world=scene.world;world.keyframe_insert(data_path='color',frame=1)
assert not api.inspect()['can_configure'] and api.inspect()['environment_sha256'] is None
world.animation_data_clear()
coord=world.node_tree.nodes.new('ShaderNodeTexCoord');coord.object=bpy.data.objects['Cube']
assert not api.inspect()['can_configure'] and any('Object-dependent' in v for v in api.inspect()['issues'])
world.node_tree.nodes.remove(coord);assert api.inspect()['can_configure']
print('ENVIRONMENT_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'ENVIRONMENT_NATIVE_OK' in result.stdout
