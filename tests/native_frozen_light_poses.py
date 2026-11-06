"""Read the exact historical camera/SUN recipe as numeric qualification inputs."""
import sys,json,math,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));args=sys.argv[sys.argv.index('--')+1:]
import bpy
from mathutils import Matrix
meta=json.loads((Path(args[0])/'job.json').read_text())['botanical_capture'];view=next(v for v in meta['views'] if v['view']=='FRONT')
# Same camera matrix setter and Euler rotate_axis path as the frozen native
# generator. No source project/model edits; this only produces numeric inputs.
cam=bpy.data.objects.new('PoseReference',bpy.data.cameras.new('PoseReference'));bpy.context.scene.collection.objects.link(cam);cam.matrix_world=Matrix(view['matrix_world']);front=list(cam.rotation_euler);back=cam.rotation_euler.copy();back.rotate_axis('Y',math.pi);bpy.context.view_layer.update()
body={'camera_location':list(cam.location),'camera_rotation_euler':front,'camera_matrix_evaluated':[list(r) for r in cam.matrix_world],'sun_front':front,'sun_back':list(back),'view':view}
Path(args[1]).write_text(json.dumps(body,indent=2));print('FROZEN_LIGHT_POSES_READ',flush=True)
