"""Typed point-cache controllers, dependencies and embedded-cache verification."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct

import bpy

from .assets import active_object,finished,mesh_object,local_object
from .morphs import topology_digest
from .physics import cache_info
from mcpblender.storage import require_space

COMMANDS={"inspect_simulations","configure_deform_simulation","configure_collision","configure_particles",
          "configure_force_field","remove_simulation_controller","remove_force_field","sample_simulation",
          "bake_simulation","validate_simulation_bake","clear_simulation_cache"}
KINDS={"CLOTH","SOFT_BODY","PARTICLE_SYSTEM"}
FIELDS={"WIND","FORCE","VORTEX","TURBULENCE","DRAG","MAGNET","HARMONIC","CHARGE"}
OWNED="mcpblender_simulation_controllers"
BINDINGS="mcpblender_simulation_bakes"
FIELD="mcpblender_force_field"
PARTICLE_DATA="mcpblender_particle_settings"


def plain(value):
    if value is None or isinstance(value,(str,bool,int,float)):return value
    if isinstance(value,set):return sorted(value)
    return [plain(item) for item in value]


def props(value):
    return {p.identifier:plain(getattr(value,p.identifier)) for p in value.bl_rna.properties
            if p.type in {"BOOLEAN","INT","FLOAT","ENUM","STRING"} and not p.is_readonly
            # Solver estimates are outputs. Legacy trail_count is rendering-only
            # and Blender normalizes its default 0 to 1 when loading a project.
            and p.identifier not in {"name","tag","use_fake_user","location_mass_center","rotation_estimate","scale_estimate","trail_count"}}


def targets():
    return [(obj,mod) for obj in sorted(bpy.context.scene.objects,key=lambda o:o.name)
            for mod in obj.modifiers if mod.type in KINDS]


def point_cache(mod):
    return mod.particle_system.point_cache if mod.type=="PARTICLE_SYSTEM" else mod.point_cache


def mapping(obj,key):
    return json.loads(obj.get(key,"{}"))


def basic(obj):
    issues=[]
    if obj.library or obj.override_library or (obj.data and obj.data.library):issues.append("local data required")
    if obj.parent or obj.constraints or obj.animation_data:issues.append("static unparented/unconstrained transforms required")
    if obj.rigid_body:issues.append("use a separate static collision proxy, not a rigid-body object")
    if any(not math.isfinite(v) for row in obj.matrix_basis for v in row):issues.append("nonfinite transform")
    if obj.type=="MESH":
        if obj.data.shape_keys or obj.data.animation_data:issues.append("deforming source geometry is unsupported")
        if len(obj.data.vertices)>50000:issues.append("per-source vertex limit is 50000")
        if not obj.data.vertices or not obj.data.polygons:issues.append("mesh faces required")
        if any(m.type not in KINDS|{"COLLISION"} for m in obj.modifiers):issues.append("bake upstream/visual modifiers explicitly")
        sims=[m for m in obj.modifiers if m.type in KINDS]
        if len(sims)>1:issues.append("one simulation controller per source mesh")
        if sims and any(m.type=="COLLISION" for m in obj.modifiers):issues.append("dynamic collider dependencies are not qualified")
    return issues


def source():
    scene=bpy.context.scene
    records=[];objects={};reasons=[]
    for obj,mod in targets():
        objects[obj.name]=obj
        cache=point_cache(mod)
        record={"name":obj.name,"modifier":mod.name,"kind":mod.type,
                "enabled":[mod.show_viewport,mod.show_render],
                "cache_range":[cache.frame_start,cache.frame_end,cache.frame_step],
                "cache_backend":[cache.use_disk_cache,cache.use_external],
                "settings":props(mod.particle_system.settings if mod.type=="PARTICLE_SYSTEM" else mod.settings)}
        settings=mod.particle_system.settings if mod.type=="PARTICLE_SYSTEM" else mod.settings
        if not obj.visible_get() or not mod.show_viewport:reasons.append(f"{obj.name}: controller must be enabled/visible for viewport simulation")
        if hasattr(settings,"effector_weights"):
            record["effector_weights"]=props(settings.effector_weights)
            if settings.effector_weights.collection:reasons.append(f"{obj.name}: effector collection unsupported")
        if mod.type=="CLOTH":
            record["collisions"]=props(mod.collision_settings)
            if mod.collision_settings.collection or settings.rest_shape_key:reasons.append(f"{obj.name}: collision collections/rest-shape dependencies unsupported")
        if mod.type=="SOFT_BODY" and settings.collision_collection:
            reasons.append(f"{obj.name}: collision collection unsupported")
        if mod.type=="PARTICLE_SYSTEM":
            ps=mod.particle_system
            if settings.animation_data:reasons.append(f"{obj.name}: animated particle settings unsupported")
            record["system"]=props(ps)
            record["force_fields"]=[props(settings.force_field_1),props(settings.force_field_2)]
            if settings.count>10000 or (settings.type=="HAIR" and settings.count*(settings.hair_step+1)>650000):reasons.append(f"{obj.name}: particle/hair budget exceeded")
            if (settings.type=="EMITTER" and settings.physics_type!="NEWTON") or ps.use_hair_dynamics or settings.child_type!="NONE":
                reasons.append(f"{obj.name}: only Newtonian emitters/static hair without children are qualified")
            if any(slot for slot in settings.texture_slots) or settings.use_clump_curve or settings.use_roughness_curve:
                reasons.append(f"{obj.name}: particle texture/curve dependencies unsupported")
            if settings.instance_collection or ps.parent:reasons.append(f"{obj.name}: particle collection/parent dependency unsupported")
            if settings.instance_object:
                objects[settings.instance_object.name]=settings.instance_object
                record["instance_object"]=settings.instance_object.name
        records.append(record)
    for obj in scene.objects:
        if any(m.type=="COLLISION" for m in obj.modifiers):objects[obj.name]=obj
        if obj.field and obj.field.type!="NONE":objects[obj.name]=obj
    headers=[]
    if len(records)>64 or len(objects)>128:reasons.append("controller/dependency count limit exceeded")
    if scene.animation_data:reasons.append("animated scene properties unsupported")
    total=0
    for obj in sorted(objects.values(),key=lambda o:o.name):
        issues=basic(obj)
        header={"name":obj.name,"matrix":[list(row) for row in obj.matrix_basis],
                "visibility":[obj.hide_viewport,obj.hide_render,obj.visible_get()]}
        if obj.field and obj.field.type!="NONE":
            header["field"]=props(obj.field)
            if obj.type!="EMPTY" or obj.field.type not in FIELDS:issues.append("only supported Empty force fields are qualified")
        collisions=[m for m in obj.modifiers if m.type=="COLLISION"]
        if collisions:
            header["collision"]=props(obj.collision)
            header["collision_modifiers"]=[{"name":m.name,"enabled":[m.show_viewport,m.show_render]} for m in collisions]
        if obj.type=="MESH" and not issues:
            total+=len(obj.data.vertices)
            coords=array("f",[0])*(3*len(obj.data.vertices));obj.data.vertices.foreach_get("co",coords)
            if any(not math.isfinite(v) for v in coords):issues.append("nonfinite source geometry")
            digest=hashlib.sha256(bytes.fromhex(topology_digest(obj.data))+coords.tobytes())
            for vertex in obj.data.vertices:
                for assignment in vertex.groups:digest.update(struct.pack("!IIf",vertex.index,assignment.group,assignment.weight))
            header["mesh_sha256"]=digest.hexdigest();header["vertex_groups"]=[g.name for g in obj.vertex_groups]
        reasons.extend(f"{obj.name}: {issue}" for issue in issues)
        headers.append(header)
    if total>200000:reasons.append("total source vertex budget exceeded")
    content={"gravity":list(scene.gravity),"use_gravity":scene.use_gravity,"fps":scene.render.fps,
             "fps_base":scene.render.fps_base,"controllers":records,"dependencies":headers}
    digest=hashlib.sha256(json.dumps(content,sort_keys=True,allow_nan=False).encode()).hexdigest() if not reasons else None
    return content,digest,reasons


def inspect(p=None):
    content,digest,reasons=source();p=p or {};offset=p.get("offset",0);limit=p.get("limit",32)
    controllers=[]
    for obj,mod in targets()[offset:offset+limit]:
        binding=mapping(obj,BINDINGS).get(mod.name,{})
        controllers.append({"name":obj.name,"modifier":mod.name,"kind":mod.type,"managed":mod.name in mapping(obj,OWNED),
                            "cache":cache_info(point_cache(mod)),"bake_binding":{"present":bool(binding),
                            "source_matches":binding.get("source")==digest if binding else False}})
    return {"simulation_sha256":digest,"complete":not reasons,"unsupported_reasons":reasons,
            "controllers":controllers,"total_controllers":len(content["controllers"]),
            "next_offset":offset+limit if offset+limit<len(content["controllers"]) else None,
            "dependencies":content["dependencies"],"controller_settings":content["controllers"]}


def guard(p):
    info=inspect()
    if not info["complete"]:raise ValueError("Unsupported simulation dependencies: "+"; ".join(info["unsupported_reasons"][:8]))
    if info["simulation_sha256"]!=p["expected_simulation"]:raise ValueError("Simulation fingerprint is stale; inspect_simulations first")


def selected(p):
    obj=mesh_object(p["name"],edit=True);mod=obj.modifiers.get(p["modifier"])
    if mod is None or mod.type not in KINDS:raise ValueError("Simulation controller not found")
    return obj,mod


def free(obj,mod):
    with active_object(obj),bpy.context.temp_override(point_cache=point_cache(mod)):
        finished(bpy.ops.ptcache.free_bake())
    bindings=mapping(obj,BINDINGS);bindings.pop(mod.name,None);obj[BINDINGS]=json.dumps(bindings)


def editing(p):
    guard(p)
    all_targets=targets()
    if any(point_cache(m).is_baked for _,m in all_targets):raise ValueError("Clear baked simulation caches explicitly before configuration edits")
    if any(point_cache(m).info not in {"","No valid data to read!"} for _,m in all_targets) and not p.get("reset_unbaked"):
        raise ValueError("Evaluated cache exists; pass reset_unbaked=true")
    if p.get("reset_unbaked"):
        for obj,mod in all_targets:free(obj,mod)
    starts=[point_cache(m).frame_start for _,m in all_targets]
    if starts:bpy.context.scene.frame_set(min(starts))


def valid_values(rna,values):
    for key,value in values.items():
        prop=rna.properties[key]
        if prop.type in {"FLOAT","INT"} and not prop.hard_min<=value<=prop.hard_max:raise ValueError(f"{key} outside installed Blender range")


def owned_modifier(obj,p,kind):
    mod=obj.modifiers.get(p["modifier"])
    if mod and (mod.type!=kind or mod.name not in mapping(obj,OWNED)):raise ValueError("Existing modifier must be an owned controller with matching type")
    return mod


def mesh_preflight(p,kind):
    obj=mesh_object(p["name"],edit=True)
    issues=basic(obj)
    if issues:raise ValueError("Unsupported simulation source: "+"; ".join(issues))
    mod=owned_modifier(obj,p,kind)
    if any(m!=mod for m in obj.modifiers):raise ValueError("Use a dedicated source mesh with one controller")
    return obj,mod


def remember(obj,mod,pin=None):
    owned=mapping(obj,OWNED);owned[mod.name]={"kind":mod.type,"pin_group":pin};obj[OWNED]=json.dumps(owned)


def configure_deform(p):
    settings=dict(p["settings"]);kind=settings.pop("type");obj,mod=mesh_preflight(p,kind)
    pins=settings.pop("pins",[]);collision={key:settings.pop(key) for key in list(settings) if key in {"use_collision","distance_min","collision_quality","use_self_collision","self_distance_min"}}
    if p.get("expected_topology") and topology_digest(obj.data)!=p["expected_topology"]:raise ValueError("Source topology is stale")
    if pins and max(pins)>=len(obj.data.vertices):raise ValueError("Pin index outside source mesh")
    rna=bpy.types.ClothSettings.bl_rna if kind=="CLOTH" else bpy.types.SoftBodySettings.bl_rna
    valid_values(rna,settings);valid_values(bpy.types.ClothCollisionSettings.bl_rna,collision)
    pin_name="MCP_Pin_"+hashlib.sha256(p["modifier"].encode()).hexdigest()[:12]
    old=mapping(obj,OWNED).get(p["modifier"],{}).get("pin_group")
    if pins and obj.vertex_groups.get(pin_name) and old!=pin_name:raise ValueError("Pin group name already belongs to user data")
    if obj.data.users>1 and not p["make_single_user"]:raise ValueError("Deform mesh data is shared; pass make_single_user=true to isolate pin/weight edits")
    editing(p)
    if obj.data.users>1:obj.data=obj.data.copy()
    mod=mod or obj.modifiers.new(p["modifier"],kind)
    if old and obj.vertex_groups.get(old):obj.vertex_groups.remove(obj.vertex_groups[old])
    if kind=="CLOTH":
        mod.settings.vertex_group_mass=""
        if pins:
            group=obj.vertex_groups.new(name=pin_name);group.add(pins,1,"REPLACE");mod.settings.vertex_group_mass=group.name
        for key,value in collision.items():setattr(mod.collision_settings,key,value)
    else:
        mod.settings.use_goal=False;mod.settings.use_edges=True
    for key,value in settings.items():setattr(mod.settings,key,value)
    cache=point_cache(mod);cache.frame_start=p["frame_start"];cache.frame_end=p["frame_end"];cache.frame_step=1
    remember(obj,mod,pin_name if pins else None);obj.update_tag();bpy.context.view_layer.update()
    return inspect()


def configure_particles(p):
    obj,mod=mesh_preflight(p,"PARTICLE_SYSTEM")
    instance=mesh_object(p["instance_object"]) if p.get("instance_object") else None
    if instance and (instance==obj or basic(instance) or instance.modifiers):raise ValueError("Particle instance must be a separate static local mesh without modifiers")
    if mod and (mod.particle_system.settings.users>1 or mod.particle_system.settings.library or mod.particle_system.settings.override_library) and not p["make_single_user"]:raise ValueError("Particle settings are shared/linked; pass make_single_user=true")
    keys=("type","count","particle_size","size_random")+(("hair_length","hair_step") if p["type"]=="HAIR" else ("frame_start","frame_end","lifetime","normal_factor","factor_random"))
    # Native hair_length aliases normal_factor; setting both would silently
    # replace an emitter's requested initial velocity.
    values={key:p[key] for key in keys}
    valid_values(bpy.types.ParticleSettings.bl_rna,values)
    editing(p)
    if mod is None:
        with active_object(obj):finished(bpy.ops.object.particle_system_add())
        mod=next(m for m in obj.modifiers if m.type=="PARTICLE_SYSTEM");mod.name=p["modifier"]
        mod.particle_system.settings[PARTICLE_DATA]=True
    ps=mod.particle_system
    if ps.settings.users>1 or ps.settings.library or ps.settings.override_library:
        ps.settings=ps.settings.copy();ps.settings[PARTICLE_DATA]=True
    for key,value in values.items():setattr(ps.settings,key,value)
    ps.name=p["modifier"];ps.seed=p["seed"]
    # Static hair still needs the native NEWTON setting to generate its strands;
    # NO collapses all hair keys onto their roots. Hair dynamics stays disabled.
    ps.settings.physics_type="NEWTON"
    ps.settings.render_type="PATH" if p["type"]=="HAIR" else "OBJECT" if instance else "NONE"
    ps.settings.instance_object=instance;ps.settings.child_type="NONE";ps.settings.display_percentage=100
    cache=ps.point_cache;cache.frame_start=p["frame_start"];cache.frame_end=p["cache_end"];cache.frame_step=1
    remember(obj,mod);obj.update_tag();bpy.context.view_layer.update()
    return inspect()


def configure_collision(p):
    obj,mod=mesh_preflight(p,"COLLISION")
    values={key:p[key] for key in ("thickness_outer","damping_factor","friction_factor","permeability","use_particle_kill")}
    valid_values(bpy.types.CollisionSettings.bl_rna,values);editing(p)
    mod=mod or obj.modifiers.new(p["modifier"],"COLLISION")
    for key,value in values.items():setattr(obj.collision,key,value)
    remember(obj,mod);obj.update_tag();bpy.context.view_layer.update();return inspect()


def configure_field(p):
    obj=bpy.data.objects.get(p["name"])
    if obj and (not obj.get(FIELD) or obj.type!="EMPTY" or basic(obj)):raise ValueError("Existing object must be an owned static force helper")
    world=bpy.context.scene.rigidbody_world
    if world and world.point_cache.is_baked:raise ValueError("Clear the rigid bake before changing force-field dependencies")
    values={key:p[key] for key in ("strength","flow","noise","seed","falloff_power")}
    valid_values(bpy.types.FieldSettings.bl_rna,values);editing(p)
    if obj is None:
        selected_objects=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
        try:
            finished(bpy.ops.object.effector_add(type=p["type"]))
            obj=bpy.context.object;obj.name=p["name"];obj[FIELD]=True
        finally:
            for item in bpy.context.selected_objects:item.select_set(False)
            for item in selected_objects:item.select_set(True)
            bpy.context.view_layer.objects.active=active
    obj.location=p["location"];obj.rotation_mode="XYZ";obj.rotation_euler=p["rotation_euler"];obj.field.type=p["type"]
    obj.field.shape=p.get("shape") or ("PLANE" if p["type"]=="WIND" else "POINT")
    for key,value in values.items():setattr(obj.field,key,value)
    obj.field.use_max_distance=p.get("distance_max") is not None
    if p.get("distance_max") is not None:obj.field.distance_max=p["distance_max"]
    bpy.context.view_layer.update();return inspect()


def capture(obj,mod,limit):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if mod.type=="PARTICLE_SYSTEM":
        ps=evaluated.particle_systems[mod.particle_system.name];particles=ps.particles;rows=[];states={}
        for particle in particles:states[particle.alive_state]=states.get(particle.alive_state,0)+1
        for i in range(min(limit,len(particles))):
            particle=particles[i];row={"index":i,"state":particle.alive_state}
            if ps.settings.type=="HAIR":
                keys=particle.hair_keys;row["hair_key_count"]=len(keys)
                if keys:row.update(root=list(keys[0].co),tip=list(keys[-1].co))
            elif particle.alive_state in {"ALIVE","DYING"}:row.update(location=list(particle.location),velocity=list(particle.velocity))
            rows.append(row)
        return {"kind":ps.settings.type,"count":len(particles),"states":states,"samples":rows,
                "coordinate_space":"OBJECT" if ps.settings.type=="HAIR" else "WORLD"}
    mesh=evaluated.to_mesh()
    try:
        points=[evaluated.matrix_world@v.co for v in mesh.vertices]
        indices=sorted({round(i*(len(points)-1)/max(1,min(limit,len(points))-1)) for i in range(min(limit,len(points)))})
        return {"kind":mod.type,"vertices":len(points),"bounds":{"min":[min(v[k] for v in points) for k in range(3)],"max":[max(v[k] for v in points) for k in range(3)]} if points else None,
                "samples":[{"index":i,"location":list(points[i])} for i in indices]}
    finally:evaluated.to_mesh_clear()


def close_numbers(a,b):
    if isinstance(a,(float,int)) and not isinstance(a,bool):return isinstance(b,(float,int)) and math.isfinite(b) and abs(a-b)<=1e-4
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(close_numbers(a[k],b[k]) for k in a)
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(close_numbers(x,y) for x,y in zip(a,b))
    return a==b


def validate(p):
    guard(p);obj,mod=selected(p);cache=point_cache(mod);binding=mapping(obj,BINDINGS).get(mod.name,{})
    if not cache.is_baked or binding.get("version")!=1 or binding.get("source")!=p["expected_simulation"]:raise ValueError("No baked cache with matching source binding")
    scene=bpy.context.scene;old=scene.frame_current,scene.frame_subframe
    try:
        for checkpoint in binding["checkpoints"]:
            scene.frame_set(checkpoint["frame"]);bpy.context.view_layer.update()
            if not close_numbers(checkpoint["value"],capture(obj,mod,16)):raise ValueError("Baked geometry/particle checkpoint mismatch")
        guard(p)
        return {"validated":True,"validation_scope":"source binding and bounded geometry/particle checkpoints",
                "checkpoint_frames":[v["frame"] for v in binding["checkpoints"]],"restored_frame":True,"cache":cache_info(cache)}
    finally:scene.frame_set(old[0],subframe=old[1]);bpy.context.view_layer.update()


def evaluate(p,baking=False):
    from . import bridge
    guard(p);obj,mod=selected(p);cache=point_cache(mod);scene=bpy.context.scene
    frames=sorted(p.get("sample_frames",[]));path=Path(p["path"]) if baking else None
    if baking:
        if cache.is_baked:raise ValueError("Clear the existing bake explicitly first")
        if mod.type=="PARTICLE_SYSTEM" and mod.particle_system.settings.type=="HAIR":raise ValueError("Static hair does not use a frame-based bake; save the project normally")
        if cache.use_disk_cache or cache.use_external:raise ValueError("Embedded baking requires disk/external cache flags disabled")
        if path.exists():raise FileExistsError(path)
        frames=sorted({cache.frame_start,(cache.frame_start+cache.frame_end)//2,cache.frame_end})
    if not frames or frames[0]<cache.frame_start or frames[-1]>cache.frame_end or cache.frame_step!=1 or not 1<=cache.frame_start<=cache.frame_end<=10000:
        raise ValueError("Samples require a step-one cache range inside frames 1..10000")
    policy=bridge._bridge.active["storage"]
    cache_bytes=(mod.particle_system.settings.count if mod.type=="PARTICLE_SYSTEM" else len(obj.data.vertices))*(frames[-1]-cache.frame_start+1)*128
    if cache_bytes>p["max_cache_bytes"]:raise ValueError("Point-cache estimate exceeds max_cache_bytes; reduce frames/points or explicitly raise the budget")
    mesh_bytes=sum(len(m.vertices)*64+len(m.edges)*16+len(m.loops)*64+len(m.polygons)*64 for m in bpy.data.meshes)
    packed_bytes=sum(image.packed_file.size for image in bpy.data.images if image.packed_file)
    size=max(16*1024**2,2*(mesh_bytes+packed_bytes),Path(bpy.data.filepath).stat().st_size*2 if bpy.data.filepath and Path(bpy.data.filepath).is_file() else 0)+cache_bytes
    if baking:policy.update(estimated_bytes=size,estimate_kind="project_plus_point_cache_heuristic")
    old=scene.frame_current,scene.frame_subframe;samples=[]
    try:
        for frame in range(cache.frame_start,frames[-1]+1):
            if baking:require_space(path,size,reserve_bytes=policy.get("reserve_bytes",256*1024**2),estimate_kind=policy["estimate_kind"])
            scene.frame_set(frame);bpy.context.view_layer.update()
            if frame in frames:samples.append({"frame":frame,"value":capture(obj,mod,16 if baking else p["sample_limit"])})
            yield {"phase":"baking simulation" if baking else "sampling simulation","kind":mod.type,"frame":frame,"completed":frame-cache.frame_start+1,"total":frames[-1]-cache.frame_start+1,"estimated_cache_bytes":cache_bytes}
        guard(p)
        if not baking:return {"samples":samples,"restored_frame":True,"simulation_sha256":p["expected_simulation"]}
        if path.exists():raise FileExistsError(path)
        yield {"phase":"finalizing native cache","native_call_interruptible":False}
        with active_object(obj),bpy.context.temp_override(point_cache=cache):finished(bpy.ops.ptcache.bake_from_cache())
        if not cache.is_baked:raise RuntimeError("Native cache did not become baked")
        bindings=mapping(obj,BINDINGS);bindings[mod.name]={"version":1,"source":p["expected_simulation"],"checkpoints":samples};obj[BINDINGS]=json.dumps(bindings)
        validate(p)
        yield {"phase":"saving embedded simulation snapshot","native_call_interruptible":False}
        if path.exists():raise FileExistsError(path)
        guard(p);require_space(path,size,reserve_bytes=policy.get("reserve_bytes",256*1024**2),estimate_kind=policy["estimate_kind"])
        finished(bpy.ops.wm.save_as_mainfile(filepath=str(path),check_existing=False,copy=True))
        return {"path":str(path),"bytes":path.stat().st_size,"cache":cache_info(cache),"checkpoint_frames":frames,"restored_frame":True,"snapshot_contains":"entire scene and selected embedded simulation cache"}
    finally:scene.frame_set(old[0],subframe=old[1]);bpy.context.view_layer.update()


def dispatch(command,p):
    if command=="inspect_simulations":return inspect(p)
    if command=="configure_deform_simulation":return configure_deform(p)
    if command=="configure_collision":return configure_collision(p)
    if command=="configure_particles":return configure_particles(p)
    if command=="configure_force_field":return configure_field(p)
    if command=="sample_simulation":return evaluate(p)
    if command=="bake_simulation":return evaluate(p,True)
    if command=="validate_simulation_bake":return validate(p)
    guard(p)
    if command=="clear_simulation_cache":
        obj,mod=selected(p);free(obj,mod);bpy.context.scene.frame_set(point_cache(mod).frame_start);return inspect()
    if command=="remove_simulation_controller":
        obj=mesh_object(p["name"],edit=True);mod=obj.modifiers.get(p["modifier"]);owned=mapping(obj,OWNED)
        if mod is None or mod.name not in owned:raise ValueError("Owned controller not found")
        pin=owned[mod.name].get("pin_group")
        if pin and obj.data.users>1 and not p["make_single_user"]:raise ValueError("Pinned mesh data is shared; pass make_single_user=true before removing pin weights")
        editing(p)
        if pin and obj.data.users>1:obj.data=obj.data.copy()
        if mod.type=="PARTICLE_SYSTEM":
            ps=mod.particle_system;settings=ps.settings
            with active_object(obj):
                obj.particle_systems.active_index=list(obj.particle_systems).index(ps);finished(bpy.ops.object.particle_system_remove())
            if settings.users==0 and settings.get(PARTICLE_DATA) and not settings.library:bpy.data.particles.remove(settings)
        else:obj.modifiers.remove(mod)
        if pin and obj.vertex_groups.get(pin):obj.vertex_groups.remove(obj.vertex_groups[pin])
        owned.pop(p["modifier"]);obj[OWNED]=json.dumps(owned);return inspect()
    obj=local_object(p["name"])
    if not obj.get(FIELD) or obj.children or len(obj.users_scene)!=1:raise ValueError("Expected an owned standalone force helper without children/shared scenes")
    editing(p);bpy.data.objects.remove(obj,do_unlink=True);return inspect()
