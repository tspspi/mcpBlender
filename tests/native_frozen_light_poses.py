"""Read the exact historical camera/SUN recipe as numeric qualification inputs."""
import sys,json,math,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));args=sys.argv[sys.argv.index('--')+1:]
import bpy
from mathutils import Matrix,Vector
meta=json.loads((Path(args[0])/'job.json').read_text())['botanical_capture'];view=next(v for v in meta['views'] if v['view']=='FRONT')
# Same camera matrix setter and Euler rotate_axis path as the frozen native
# generator. No source project/model edits; this only produces numeric inputs.
cam=bpy.data.objects.new('PoseReference',bpy.data.cameras.new('PoseReference'));bpy.context.scene.collection.objects.link(cam);cam.matrix_world=Matrix(view['matrix_world']);front=list(cam.rotation_euler);back=cam.rotation_euler.copy();back.rotate_axis('Y',math.pi);bpy.context.view_layer.update()
body={'camera_location':list(cam.location),'camera_rotation_euler':front,'camera_matrix_evaluated':[list(r) for r in cam.matrix_world],'sun_front':front,'sun_back':list(back),'view':view}
# Numeric orbit recipes for structured MCP camera creation. The source scene
# remains unopened; only this factory-scene reference camera is used.
root=Matrix(meta['source_root_matrix_world']);bounds=view['projected_bounds_local_m'];axes=[Vector(view['local_frame'][k]) for k in ('u','v','normal')]
center=root@sum((axis*(lo+hi)/2 for axis,lo,hi in zip(axes,bounds['min'],bounds['max'])),Vector());base=cam.matrix_world.copy();orbits={}
for label,axis_key,degrees in [('yaw_minus5','v',-5),('yaw_plus5','v',5),('pitch_minus5','u',-5),('pitch_plus5','u',5)]:
    axis=(root.to_3x3()@Vector(view['local_frame'][axis_key])).normalized();cam.matrix_world=Matrix.Translation(center)@Matrix.Rotation(math.radians(degrees),4,axis)@Matrix.Translation(-center)@base
    cam.scale=(1,1,1);bpy.context.view_layer.update()
    orbits[label]={'location':list(cam.location),'rotation_euler':list(cam.rotation_euler),'matrix_world':[list(r) for r in cam.matrix_world],'axis':axis_key,'degrees':degrees,'center':list(center)}
body['orbit_poses']=orbits
Path(args[1]).write_text(json.dumps(body,indent=2));print('FROZEN_LIGHT_POSES_READ',flush=True)
