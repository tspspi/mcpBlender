"""Guarded rigid-body workflows. Native embedded caches are verified, not assumed."""
from array import array
import hashlib
import json
import math
from pathlib import Path

import bpy

from .assets import active_object, finished, mesh_object
from .morphs import topology_digest
from mcpblender.storage import require_space

COMMANDS = {"inspect_physics", "configure_rigid_world", "configure_rigid_body", "remove_rigid_body",
            "sample_rigid_bodies", "bake_rigid_bodies", "validate_rigid_bake", "clear_rigid_bake"}
FIELDS = ("type", "collision_shape", "mesh_source", "mass", "friction", "restitution", "enabled", "kinematic",
          "linear_damping", "angular_damping", "use_margin", "collision_margin", "use_deactivation", "use_deform",
          "use_start_deactivated", "deactivate_linear_velocity", "deactivate_angular_velocity", "collision_collections")
BINDING = "mcpblender_rigid_bake"


def actors():
    world = bpy.context.scene.rigidbody_world
    if not world or not world.collection:
        return []
    return sorted((o for o in world.collection.all_objects if o.rigid_body and o.name in bpy.context.scene.objects), key=lambda o:o.name)


def cache_info(cache):
    return {key: getattr(cache, key) for key in ("frame_start", "frame_end", "frame_step", "is_baked", "is_baking", "is_outdated", "is_frame_skip", "use_disk_cache", "use_external", "info")}


def source_issues(obj):
    issues = []
    if obj.type != "MESH" or obj.library or obj.override_library or obj.data.library:
        return ["local mesh required"]
    if obj.parent or obj.constraints or obj.animation_data:
        issues.append("parented/constrained/animated transforms require a specialized workflow")
    if obj.modifiers or obj.data.shape_keys or obj.data.animation_data:
        issues.append("bake modifiers/deformation explicitly into a static collider mesh")
    if not obj.data.vertices or not obj.data.polygons:
        issues.append("collider mesh must have vertices and faces")
    if any(not math.isfinite(v) or v <= 0 for v in obj.scale):
        issues.append("positive finite object scales required")
    if obj.rigid_body and (obj.rigid_body.mesh_source != "BASE" or obj.rigid_body.kinematic or obj.rigid_body.use_deform):
        issues.append("only static BASE collision geometry is currently qualified")
    if obj.rigid_body and obj.rigid_body.collision_shape == "COMPOUND":
        issues.append("compound colliders require child-dependency tracking")
    return issues


def inspect(p=None):
    p = p or {}
    scene, bodies = bpy.context.scene, actors()
    world = scene.rigidbody_world
    config = {"gravity": list(scene.gravity), "use_gravity": scene.use_gravity,
              "fps": scene.render.fps, "fps_base": scene.render.fps_base,
              "world": {key:getattr(world,key) for key in ("enabled", "time_scale", "substeps_per_frame", "solver_iterations", "use_split_impulse")} if world else None}
    if world:
        config["cache_range"] = [world.point_cache.frame_start, world.point_cache.frame_end, world.point_cache.frame_step]
        config["cache_backend"] = {key:getattr(world.point_cache,key) for key in ("use_disk_cache","use_external")}
        config["effector_weights"] = {prop.identifier:getattr(world.effector_weights,prop.identifier)
                                      for prop in world.effector_weights.bl_rna.properties if prop.type in {"FLOAT","BOOLEAN"}}
    records, reasons, total_vertices = [], [], 0
    if len(bodies) > 500:
        reasons.append("over 500 rigid bodies")
    if scene.animation_data:
        reasons.append("animated/driven scene properties require a specialized workflow")
    for obj in bodies:
        issues = source_issues(obj)
        reasons.extend(f"{obj.name}: {issue}" for issue in issues)
        body = {"name":obj.name,"settings":{key:list(getattr(obj.rigid_body,key)) if key=="collision_collections" else getattr(obj.rigid_body,key) for key in FIELDS},
                "source_matrix":[list(row) for row in obj.matrix_basis]}
        if not issues:
            total_vertices += len(obj.data.vertices)
            if total_vertices <= 2_000_000:
                coords = array("f", [0]) * (3 * len(obj.data.vertices))
                obj.data.vertices.foreach_get("co", coords)
                if any(not math.isfinite(v) for v in coords):
                    reasons.append(f"{obj.name}: nonfinite source coordinates")
                body["mesh_sha256"] = hashlib.sha256(bytes.fromhex(topology_digest(obj.data)) + coords.tobytes()).hexdigest()
        records.append(body)
    if total_vertices > 2_000_000:
        reasons.append("over 2000000 source vertices")
    if world and world.constraints and world.constraints.all_objects:
        reasons.append("rigid-body constraints require a specialized workflow")
    if world and world.effector_weights.collection:
        reasons.append("effector collection dependencies require a specialized workflow")
    if any(obj.field and obj.field.type != "NONE" for obj in scene.objects):
        reasons.append("force-field dependencies require a specialized workflow")
    fingerprint = hashlib.sha256(json.dumps(config | {"bodies":records},sort_keys=True,allow_nan=False).encode()).hexdigest() if not reasons else None
    offset, limit = p.get("offset",0), p.get("limit",32)
    binding = json.loads(scene.get(BINDING,"{}"))
    return config | {"physics_sha256":fingerprint,"complete":not reasons,"unsupported_reasons":reasons,
                     "bodies":records[offset:offset+limit],"total_bodies":len(records),
                     "next_offset":offset+limit if offset+limit<len(records) else None,
                     "cache":cache_info(world.point_cache) if world else None,
                     "bake_binding":{"present":bool(binding),"source_matches":bool(binding and binding.get("physics_sha256")==fingerprint),
                                     "checkpoint_frames":[v["frame"] for v in binding.get("checkpoints",[])]}}


def guard(p, require_world=True):
    info = inspect()
    if not info["complete"]:
        raise ValueError("Unsupported physics sources: " + "; ".join(info["unsupported_reasons"][:8]))
    if info["physics_sha256"] != p["expected_physics"]:
        raise ValueError("Physics fingerprint is stale; inspect_physics before editing/evaluation")
    world = bpy.context.scene.rigidbody_world
    if require_world and world is None:
        raise ValueError("Configure a rigid-body world first")
    return world


def free_cache():
    scene = bpy.context.scene
    world = scene.rigidbody_world
    with bpy.context.temp_override(point_cache=world.point_cache):
        finished(bpy.ops.ptcache.free_bake())
    if BINDING in scene:
        del scene[BINDING]
    scene.frame_set(world.point_cache.frame_start)
    bpy.context.view_layer.update()


def editable_cache(world, reset):
    if world is None:
        return
    cache = world.point_cache
    if cache.is_baked:
        raise ValueError("Clear the baked rigid cache explicitly before editing")
    # Unknown/localized cache descriptions are treated conservatively rather
    # than parsing a translated native frame-count string.
    populated = cache.info not in {"", "No valid data to read!"}
    if populated and not reset:
        raise ValueError("Evaluated cache exists; pass reset_unbaked=true to invalidate it")
    if reset:
        free_cache()


def poses(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    return {obj.name:[list(row) for row in obj.evaluated_get(graph).matrix_world] for obj in objects}


def sample(p):
    world = guard(p)
    bodies = {o.name:o for o in actors()}
    if any(name not in bodies for name in p["objects"]):
        raise ValueError("Sample targets must be rigid bodies in the current world")
    frames = sorted(p["sample_frames"])
    cache = world.point_cache
    if frames[0] < cache.frame_start or frames[-1] > cache.frame_end:
        raise ValueError("Sample frames must be inside the rigid cache range")
    original = bpy.context.scene.frame_current, bpy.context.scene.frame_subframe
    samples = []
    try:
        for frame in range(cache.frame_start,frames[-1]+1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            if frame in frames:
                samples.append({"frame":frame,"poses":poses([bodies[n] for n in p["objects"]])})
            yield {"phase":"evaluating rigid bodies","frame":frame,"frame_start":cache.frame_start,"frame_end":frames[-1],
                   "completed":frame-cache.frame_start+1,"total":frames[-1]-cache.frame_start+1}
        guard(p)
        return {"samples":samples,"physics_sha256":p["expected_physics"],"restored_frame":True,"cache":cache_info(cache)}
    finally:
        bpy.context.scene.frame_set(original[0], subframe=original[1])
        bpy.context.view_layer.update()


def compare_checkpoints(checkpoints, bodies):
    for checkpoint in checkpoints:
        bpy.context.scene.frame_set(checkpoint["frame"])
        bpy.context.view_layer.update()
        current = poses(bodies)
        for name, matrix in checkpoint["poses"].items():
            if name not in current or any(abs(a-b)>1e-4 for row_a,row_b in zip(matrix,current[name]) for a,b in zip(row_a,row_b)):
                raise ValueError(f"Baked pose mismatch at frame {checkpoint['frame']}: {name}")


def validate(p):
    world = guard(p)
    binding = json.loads(bpy.context.scene.get(BINDING,"{}"))
    if not world.point_cache.is_baked or binding.get("version") != 1 or binding.get("physics_sha256") != p["expected_physics"]:
        raise ValueError("No baked cache with a matching source binding")
    original = bpy.context.scene.frame_current, bpy.context.scene.frame_subframe
    try:
        compare_checkpoints(binding["checkpoints"], actors())
        return {"validated":True,"validation_scope":"source binding and saved pose checkpoints, not every cached frame",
                "physics_sha256":p["expected_physics"],"checkpoint_frames":[v["frame"] for v in binding["checkpoints"]],
                "cache":cache_info(world.point_cache),"restored_frame":True}
    finally:
        bpy.context.scene.frame_set(original[0],subframe=original[1])
        bpy.context.view_layer.update()


def bake(p):
    from . import bridge
    world = guard(p)
    cache, scene, bodies = world.point_cache, bpy.context.scene, actors()
    if cache.is_baked:
        raise ValueError("Clear the existing bake explicitly first")
    if cache.use_disk_cache or cache.use_external:
        raise ValueError("Embedded bake requires native disk/external cache flags disabled")
    if not world.enabled or not any(o.rigid_body.type=="ACTIVE" for o in bodies):
        raise ValueError("Enabled world with an active rigid body required")
    if cache.frame_step != 1 or not 1 <= cache.frame_start <= cache.frame_end <= 10000:
        raise ValueError("Bake requires a step-one cache range inside frames 1..10000")
    path = Path(p["path"])
    if path.exists():
        raise FileExistsError(path)
    existing_size = Path(bpy.data.filepath).stat().st_size if bpy.data.filepath and Path(bpy.data.filepath).is_file() else 0
    mesh_bytes = sum(len(mesh.vertices)*64+len(mesh.edges)*16+len(mesh.loops)*64+len(mesh.polygons)*64 for mesh in bpy.data.meshes)
    packed_bytes = sum(image.packed_file.size for image in bpy.data.images if image.packed_file)
    estimate = max(16*1024**2,existing_size*2,2*(mesh_bytes+packed_bytes)) + len(bodies)*(cache.frame_end-cache.frame_start+1)*256
    policy = bridge._bridge.active["storage"]
    policy.update(estimated_bytes=estimate,estimate_kind="project_plus_rigid_cache_heuristic")
    require_space(path,estimate,reserve_bytes=policy.get("reserve_bytes",256*1024**2),estimate_kind=policy["estimate_kind"])
    original = scene.frame_current, scene.frame_subframe
    checkpoints = []
    selected = {cache.frame_start,(cache.frame_start+cache.frame_end)//2,cache.frame_end}
    try:
        for frame in range(cache.frame_start,cache.frame_end+1):
            require_space(path,estimate,reserve_bytes=policy.get("reserve_bytes",256*1024**2),estimate_kind=policy["estimate_kind"])
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            if frame in selected:
                checkpoints.append({"frame":frame,"poses":poses(bodies)})
            yield {"phase":"baking rigid bodies","frame":frame,"completed":frame-cache.frame_start+1,"total":cache.frame_end-cache.frame_start+1}
        if path.exists():
            raise FileExistsError(path)
        guard(p)
        yield {"phase":"finalizing embedded bake","native_call_interruptible":False}
        with bpy.context.temp_override(point_cache=cache):
            finished(bpy.ops.ptcache.bake_from_cache())
        if not cache.is_baked:
            raise RuntimeError("Blender did not mark the cache baked")
        compare_checkpoints(checkpoints,bodies)
        guard(p)
        scene[BINDING] = json.dumps({"version":1,"physics_sha256":p["expected_physics"],"checkpoints":checkpoints})
        yield {"phase":"saving embedded bake copy","native_call_interruptible":False}
        if path.exists():
            raise FileExistsError(path)
        guard(p)
        require_space(path,estimate,reserve_bytes=policy.get("reserve_bytes",256*1024**2),estimate_kind=policy["estimate_kind"])
        finished(bpy.ops.wm.save_as_mainfile(filepath=str(path),check_existing=False,copy=True))
        return {"path":str(path),"bytes":path.stat().st_size,"physics_sha256":p["expected_physics"],
                "checkpoint_frames":sorted(selected),"cache":cache_info(cache),"snapshot_contains":"entire scene and embedded rigid cache","restored_frame":True}
    finally:
        scene.frame_set(original[0],subframe=original[1])
        bpy.context.view_layer.update()


def dispatch(command,p):
    if command == "inspect_physics":
        return inspect(p)
    if command == "sample_rigid_bodies":
        return sample(p)
    if command == "bake_rigid_bodies":
        return bake(p)
    if command == "validate_rigid_bake":
        return validate(p)
    world = guard(p, require_world=command!="configure_rigid_world")
    if command == "clear_rigid_bake":
        free_cache()
        return inspect()
    obj = None
    if command in {"configure_rigid_body","remove_rigid_body"}:
        obj = mesh_object(p["name"],edit=True)
        if source_issues(obj):
            raise ValueError("Unsupported collider: " + "; ".join(source_issues(obj)))
        if command=="remove_rigid_body" and obj.rigid_body is None:
            raise ValueError("Object has no rigid body")
    editable_cache(world,p.get("reset_unbaked",False))
    if command=="configure_rigid_world":
        if world is None:
            finished(bpy.ops.rigidbody.world_add())
            world=bpy.context.scene.rigidbody_world
        scene=bpy.context.scene
        scene.gravity=p["gravity"];scene.use_gravity=True
        scene.render.fps=p["fps"];scene.render.fps_base=1
        world.enabled=True
        for key in ("substeps_per_frame","solver_iterations","time_scale"):
            setattr(world,key,p[key])
        world.point_cache.frame_start=p["frame_start"];world.point_cache.frame_end=p["frame_end"];world.point_cache.frame_step=1
        scene.frame_set(p["frame_start"])
    elif command=="configure_rigid_body":
        if obj.rigid_body is None:
            with active_object(obj):
                finished(bpy.ops.rigidbody.object_add())
        for key in ("type","collision_shape","mass","friction","restitution","linear_damping","angular_damping","use_margin","collision_margin"):
            setattr(obj.rigid_body,key,p[key])
        obj.rigid_body.mesh_source="BASE"
    elif command=="remove_rigid_body":
        with active_object(obj):
            finished(bpy.ops.rigidbody.object_remove())
    bpy.context.view_layer.update()
    return inspect()
