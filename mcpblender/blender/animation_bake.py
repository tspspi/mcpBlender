"""Transactional visual pose baking into independent, constraint-free assets."""
import math

import bpy

from .rigging import armature_object
from .assets import mesh_object


def bake(p):
    from .bridge import check_cancelled, report_progress
    from .domains import curves
    rig = armature_object(p['name'])
    scene = bpy.context.scene
    frames = list(range(p['frame_start'], p['frame_end'] + 1))
    bones = list(rig.pose.bones)
    meshes = [mesh_object(item['source']) for item in p['meshes']]
    names = [p['output_rig']] + [item['output'] for item in p['meshes']]
    if any(len(n.encode()) > 63 or n in bpy.data.objects for n in names):
        raise ValueError('Output object names must be unused and fit 63 UTF-8 bytes')
    if p['clip'] in bpy.data.actions or len(p['clip'].encode()) > 63:
        raise ValueError('Output clip name must be unused and fit 63 UTF-8 bytes')
    if rig.mode != 'OBJECT' or not bones or len(bones) > 256 or len(bones) * len(frames) > 32768:
        raise ValueError('Bake requires Object mode, 1..256 bones and at most 32768 bone-frame samples')
    if rig.data.pose_position != 'POSE' or any(b.bone.bbone_segments != 1 for b in bones):
        raise ValueError('Bake requires pose evaluation and single-segment bones')
    vertex_count = sum(len(m.data.vertices) for m in meshes)
    if vertex_count * len(frames) > 2000000:
        raise ValueError('Mesh verification is limited to 2000000 vertex-frame samples')
    for mesh in meshes:
        mods = list(mesh.modifiers)
        if (mesh.mode != 'OBJECT' or mesh.data.shape_keys or mesh.constraints or mesh.animation_data
                or len(mods) != 1 or mods[0].type != 'ARMATURE' or mods[0].object != rig
                or not mods[0].show_viewport or not mods[0].show_render or mods[0].use_bone_envelopes
                or mesh.parent not in (None, rig) or (mesh.parent and mesh.parent_type != 'OBJECT')):
            raise ValueError('Bake meshes require one enabled vertex-group armature modifier, no shape keys, animation, constraints or external/bone parent')
    saved = scene.frame_current, scene.frame_subframe
    created = []; data = []; action = None; success = False
    reference_world = rig.matrix_world.copy()
    mesh_world = [m.matrix_world.copy() for m in meshes]
    tolerance = p['tolerance']

    def matrix_error(a, b):
        values = [abs(x-y) for ra, rb in zip(a, b) for x, y in zip(ra, rb)]
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Non-finite evaluated animation matrix')
        return max(values)

    def check_static():
        if matrix_error(rig.matrix_world, reference_world) > 1e-6 or any(
                matrix_error(m.matrix_world, world) > 1e-6 for m, world in zip(meshes, mesh_world)):
            raise ValueError('This bake requires stationary rig and mesh object transforms; bake object motion separately')

    try:
        output = rig.copy(); created.append(output)
        output.data = rig.data.copy(); data.append(output.data)
        output.name = p['output_rig']; output.data.name = p['output_rig'] + '_Skeleton'
        scene.collection.objects.link(output)
        output.animation_data_clear(); output.data.animation_data_clear()
        output.parent = None; output.matrix_world = reference_world
        for constraint in list(output.constraints): output.constraints.remove(constraint)
        for bone in output.pose.bones:
            for constraint in list(bone.constraints): bone.constraints.remove(constraint)
            bone.rotation_mode = 'QUATERNION'
        duplicates = []
        for mesh, spec, world in zip(meshes, p['meshes'], mesh_world):
            duplicate = mesh.copy(); created.append(duplicate)
            duplicate.data = mesh.data.copy(); data.append(duplicate.data)
            duplicate.name = spec['output']; scene.collection.objects.link(duplicate)
            duplicate.parent = output if mesh.parent else None; duplicate.matrix_world = world
            duplicate.modifiers[0].object = output
            duplicates.append(duplicate)
        action = bpy.data.actions.new(p['clip'])
        action['mcpblender_target'] = output.name
        action['mcpblender_bake_source'] = rig.name
        action.use_fake_user = True
        output.animation_data_create().action = action
        slot = action.slots.new(id_type='OBJECT', name=output.name) if hasattr(action, 'slots') else None
        if slot is not None: output.animation_data.action_slot = slot
        previous = {}
        for index, frame in enumerate(frames):
            check_cancelled(); scene.frame_set(frame); bpy.context.view_layer.update(); check_static()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            for bone in output.pose.bones:
                source = evaluated.pose.bones[bone.name]
                kwargs = {'parent_matrix': source.parent.matrix, 'parent_matrix_local': source.parent.bone.matrix_local} if source.parent else {}
                basis = bone.bone.convert_local_to_pose(source.matrix, bone.bone.matrix_local, invert=True, **kwargs)
                location, rotation, scale = basis.decompose()
                if bone.name in previous: rotation.make_compatible(previous[bone.name])
                previous[bone.name] = rotation.copy()
                bone.location = location; bone.rotation_quaternion = rotation; bone.scale = scale
                for key in ('location', 'rotation_quaternion', 'scale'):
                    if not bone.keyframe_insert(data_path=key, frame=frame, group=bone.name):
                        raise RuntimeError('Blender refused a baked pose keyframe')
            report_progress({'phase':'baking visual pose', 'frame':frame, 'fraction': .5*(index+1)/len(frames)})
        for channel in curves(action, slot):
            for key in channel.keyframe_points: key.interpolation = 'LINEAR'
        max_pose_error = max_vertex_error = 0.0
        # Independently evaluate the keyed output rather than trusting inserted keys.
        for index, frame in enumerate(frames):
            check_cancelled(); scene.frame_set(frame); bpy.context.view_layer.update(); check_static()
            deps = bpy.context.evaluated_depsgraph_get()
            source = rig.evaluated_get(deps); result = output.evaluated_get(deps)
            max_pose_error = max(max_pose_error, matrix_error(source.matrix_world, result.matrix_world))
            for bone in source.pose.bones:
                error = matrix_error(source.matrix_world @ bone.matrix, result.matrix_world @ result.pose.bones[bone.name].matrix)
                max_pose_error = max(max_pose_error, error)
            for original, duplicate in zip(meshes, duplicates):
                a = original.evaluated_get(deps); b = duplicate.evaluated_get(deps)
                am = bm = None
                try:
                    am = a.to_mesh(); bm = b.to_mesh()
                    if len(am.vertices) != len(bm.vertices): raise ValueError('Baked mesh topology changed')
                    for av, bv in zip(am.vertices, bm.vertices):
                        distance = (a.matrix_world @ av.co - b.matrix_world @ bv.co).length
                        if not math.isfinite(distance): raise ValueError('Non-finite baked deformation')
                        max_vertex_error = max(max_vertex_error, distance)
                finally:
                    if am is not None: a.to_mesh_clear()
                    if bm is not None: b.to_mesh_clear()
            if max_pose_error > tolerance or max_vertex_error > tolerance:
                raise ValueError('Visual bake verification exceeded tolerance; no baked assets retained')
            report_progress({'phase':'verifying visual bake', 'frame':frame, 'fraction': .5+.5*(index+1)/len(frames)})
        check_cancelled(); success = True
        return {'source':rig.name, 'name':output.name, 'clip':action.name,
                'meshes':[{'source':m.name,'output':d.name} for m,d in zip(meshes,duplicates)],
                'frame_count':len(frames), 'frame_start':frames[0], 'frame_end':frames[-1],
                'max_pose_matrix_error':max_pose_error,'max_vertex_world_error':max_vertex_error,
                'tolerance':tolerance, 'restored_frame':saved[0],
                'scope':'Every integer frame verified; subframe interpolation is not guaranteed'}
    finally:
        if not success:
            for obj in reversed(created): bpy.data.objects.remove(obj, do_unlink=True)
            for block in reversed(data):
                collection = bpy.data.armatures if isinstance(block, bpy.types.Armature) else bpy.data.meshes
                collection.remove(block)
            if action is not None: bpy.data.actions.remove(action)
        scene.frame_set(saved[0], subframe=saved[1]); bpy.context.view_layer.update()
