"""Static-source fluid tools and cancellable isolated native bake workers."""
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
import uuid

import bpy

from .assets import mesh_object,finished
from .morphs import topology_digest
from .simulations import props
from mcpblender.fluid_files import MARKER,inventory,write_json,read_json,verify_steps
from mcpblender.storage import require_space

COMMANDS={"inspect_fluids","configure_fluid_domain","configure_fluid_flow","configure_fluid_effector",
          "remove_fluid_controller","bake_fluid","validate_fluid_bake","cleanup_fluid_job","inspect_fluid_job","recover_fluid_job"}
OWNED="mcpblender_fluid_controllers"
BINDING="mcpblender_fluid_binding"


def controllers():
    return [(o,m) for o in sorted(bpy.context.scene.objects,key=lambda o:o.name) for m in o.modifiers if m.type=="FLUID"]


def settings(mod):
    return getattr(mod,{"DOMAIN":"domain_settings","FLOW":"flow_settings","EFFECTOR":"effector_settings"}[mod.fluid_type])


def cached(s):
    return bool(s.has_cache_baked_any or s.is_cache_baking_any)


def inspect():
    records=[];reasons=[];total=0;domains=[]
    if not bpy.app.build_options.fluid:reasons.append("This Blender build lacks fluid support")
    for obj,mod in controllers():
        if mod.fluid_type not in {"DOMAIN","FLOW","EFFECTOR"}:
            reasons.append(f"{obj.name}: configure a domain, flow or effector role");continue
        s=settings(mod);values=props(s)
        values={k:v for k,v in values.items() if not k.startswith(("has_cache_","is_cache_","cache_"))}
        record={"name":obj.name,"modifier":mod.name,"role":mod.fluid_type,"settings":values,
                "matrix":[list(row) for row in obj.matrix_world],"enabled":[mod.show_viewport,mod.show_render],
                "visible":obj.visible_get()}
        if obj.type!="MESH" or obj.library or obj.override_library or obj.data.library or obj.data.override_library:
            reasons.append(f"{obj.name}: local mesh data required")
        elif obj.parent or obj.constraints or obj.animation_data or obj.data.animation_data or obj.data.shape_keys or obj.rigid_body:
            reasons.append(f"{obj.name}: static, unparented, unconstrained source geometry required")
        elif len(obj.modifiers)!=1 or not obj.data.polygons:
            reasons.append(f"{obj.name}: a dedicated face mesh with one fluid modifier is required")
        elif len(obj.data.vertices)>50000:
            reasons.append(f"{obj.name}: source vertex budget exceeded")
        else:
            total+=len(obj.data.vertices);coords=array("f",[0])*(3*len(obj.data.vertices));obj.data.vertices.foreach_get("co",coords)
            if any(not math.isfinite(v) for v in coords):reasons.append(f"{obj.name}: nonfinite source geometry")
            record["mesh_sha256"]=hashlib.sha256(bytes.fromhex(topology_digest(obj.data))+coords.tobytes()).hexdigest()
        if not obj.visible_get() or not mod.show_viewport or not mod.show_render:reasons.append(f"{obj.name}: viewport/render-enabled sources required")
        if any(not math.isfinite(v) for row in obj.matrix_world for v in row):reasons.append(f"{obj.name}: nonfinite transform")
        if any(abs(v-1)>1e-6 for v in obj.scale):reasons.append(f"{obj.name}: apply source scale first")
        if mod.fluid_type=="DOMAIN":
            domains.append(record);record["range"]=[s.cache_frame_start,s.cache_frame_end];record["cache_type"]=s.cache_type
            record["effector_weights"]=props(s.effector_weights)
            if s.cache_type!="MODULAR" or s.use_noise or s.use_spray_particles or s.use_foam_particles or s.use_bubble_particles or s.use_tracer_particles:
                reasons.append(f"{obj.name}: modular data/liquid mesh without noise/secondary particles required")
            if getattr(s,"fluid_group",None) or getattr(s,"effector_group",None):reasons.append(f"{obj.name}: collection-filtered dependencies unsupported")
            if s.force_collection or s.effector_weights.collection:reasons.append(f"{obj.name}: force collections unsupported")
            if s.use_guide or s.guide_parent:reasons.append(f"{obj.name}: fluid guiding dependencies unsupported")
            if s.resolution_max>128 or not 1<=s.cache_frame_start<=s.cache_frame_end<=10000 or s.cache_frame_end-s.cache_frame_start>499:
                reasons.append(f"{obj.name}: fluid resolution/frame budget exceeded")
        elif mod.fluid_type=="FLOW":
            if s.flow_source!="MESH" or getattr(s,"use_texture",False) or getattr(s,"noise_texture",None):reasons.append(f"{obj.name}: untextured mesh fluid sources required")
            if any(v for k,v in values.items() if k.startswith("vertex_group_")):reasons.append(f"{obj.name}: vertex-group fluid dependencies unsupported")
        elif s.effector_type!="COLLISION":reasons.append(f"{obj.name}: only collision effectors supported")
        records.append(record)
    if len(domains)>1:reasons.append("One fluid domain per scene is supported")
    if len(records)>64 or total>200000:reasons.append("Fluid source budget exceeded")
    scene=bpy.context.scene
    if scene.animation_data:reasons.append("Animated scene properties unsupported")
    if any(o.field and o.field.type!="NONE" for o in scene.objects):reasons.append("Force-field dependencies are not yet supported by fluid bundles")
    if domains:
        liquid=domains[0]["settings"]["domain_type"]=="LIQUID"
        if any((r["settings"]["flow_type"]=="LIQUID")!=liquid for r in records if r["role"]=="FLOW"):
            reasons.append("Flow type must match the liquid/gas domain")
    content={"controllers":records,"gravity":list(scene.gravity),"use_gravity":scene.use_gravity,
             "fps":scene.render.fps,"fps_base":scene.render.fps_base,"unit_scale":scene.unit_settings.scale_length}
    digest=hashlib.sha256(json.dumps(content,sort_keys=True,allow_nan=False).encode()).hexdigest() if not reasons else None
    return content|{"fluid_sha256":digest,"complete":not reasons,"unsupported_reasons":reasons,
                    "native_caches":[{"name":o.name,"baked":cached(settings(m)),"directory":settings(m).cache_directory}
                                     for o,m in controllers() if m.fluid_type=="DOMAIN"]}


def guard(p):
    info=inspect()
    if not info["complete"]:raise ValueError("Unsupported fluid sources: "+"; ".join(info["unsupported_reasons"][:8]))
    if info["fluid_sha256"]!=p["expected_fluid"]:raise ValueError("Fluid fingerprint is stale; inspect_fluids first")
    return info


def domain(p):
    obj=mesh_object(p["name"]);mod=obj.modifiers.get(p["modifier"])
    if not mod or mod.type!="FLUID" or mod.fluid_type!="DOMAIN":raise ValueError("Named fluid domain not found")
    return obj,mod


def editable(p,role):
    guard(p)
    if any(cached(settings(m)) for _,m in controllers() if m.fluid_type=="DOMAIN"):
        raise ValueError("Baked fluid projects are immutable here; edit the original unbaked source project")
    obj=mesh_object(p["name"],edit=True);mod=obj.modifiers.get(p["modifier"])
    owned=json.loads(obj.get(OWNED,"[]"))
    if mod and (mod.type!="FLUID" or mod.fluid_type!=role or mod.name not in owned):raise ValueError("Expected an owned fluid controller with matching role")
    if obj.parent or obj.constraints or obj.animation_data or obj.rigid_body or obj.data.shape_keys or obj.data.animation_data or any(m!=mod for m in obj.modifiers):
        raise ValueError("Fluid authoring requires a dedicated static source mesh")
    if not obj.data.polygons or len(obj.data.vertices)>50000 or any(abs(v-1)>1e-6 for v in obj.scale):raise ValueError("Use a bounded face mesh with applied scale")
    if any(not math.isfinite(v) for vertex in obj.data.vertices for v in vertex.co) or any(not math.isfinite(v) for row in obj.matrix_world for v in row):raise ValueError("Finite fluid source geometry/transforms required")
    if role=="DOMAIN" and any(max(v.co[k] for v in obj.data.vertices)-min(v.co[k] for v in obj.data.vertices)<=1e-6 for k in range(3)):
        raise ValueError("Fluid domain needs nonzero volume in every axis")
    if role=="DOMAIN" and any(m.fluid_type=="DOMAIN" and m!=mod for _,m in controllers()):raise ValueError("Only one domain per scene is supported")
    return obj,mod,owned


def configure(p,role):
    obj,mod,owned=editable(p,role)
    values={}
    if role=="DOMAIN":
        rna=bpy.types.FluidDomainSettings.bl_rna
        values={"resolution_max":p["resolution"],"time_scale":p["time_scale"],"mesh_scale":p["mesh_scale"]}
    elif role=="FLOW":
        rna=bpy.types.FluidFlowSettings.bl_rna
        values={key:p[key] for key in ("density","temperature","fuel_amount","surface_distance","subframes")}
        values["velocity_coord"]=p["velocity"]
    else:
        rna=bpy.types.FluidEffectorSettings.bl_rna
        values={key:p[key] for key in ("surface_distance","subframes")}
    for key,value in values.items():
        prop=rna.properties[key]
        if not all(prop.hard_min<=v<=prop.hard_max for v in (value if prop.is_array else [value])):
            raise ValueError(f"{key} outside installed Blender range")
    # Check type compatibility before creating a modifier, preserving the source.
    domains=[settings(m) for _,m in controllers() if m.fluid_type=="DOMAIN"]
    if role=="FLOW" and domains and (p["type"]=="LIQUID")!=(domains[0].domain_type=="LIQUID"):
        raise ValueError("Flow type must match the domain")
    if role=="DOMAIN" and any((settings(m).flow_type=="LIQUID")!=(p["type"]=="LIQUID") for _,m in controllers() if m.fluid_type=="FLOW"):
        raise ValueError("Domain type must match existing flows")
    mod=mod or obj.modifiers.new(p["modifier"],"FLUID");mod.fluid_type=role;s=settings(mod)
    if role=="DOMAIN":
        s.cache_type="MODULAR";s.domain_type=p["type"];s.resolution_max=p["resolution"]
        s.cache_frame_start=p["frame_start"];s.cache_frame_end=p["frame_end"];s.time_scale=p["time_scale"]
        s.effector_weights.gravity=p["gravity_weight"]
        s.use_mesh=p["type"]=="LIQUID";s.mesh_scale=p["mesh_scale"];s.use_noise=False
        # Liquid domains create an auxiliary legacy FLIP particle modifier by
        # default. Surface baking uses the solver particles without that display.
        s.use_flip_particles=False
        s.cache_data_format="UNI";s.cache_mesh_format="BOBJECT"
        for key,value in p.items():
            if key.startswith("use_collision_border_"):setattr(s,key,value)
    elif role=="FLOW":
        s.flow_type=p["type"];s.flow_behavior=p["behavior"];s.flow_source="MESH"
        for key in ("density","temperature","fuel_amount","surface_distance","subframes"):setattr(s,key,p[key])
        s.use_initial_velocity=any(p["velocity"]);s.velocity_coord=p["velocity"];s.velocity_normal=0;s.velocity_factor=0
    else:
        s.effector_type="COLLISION"
        for key in ("surface_distance","use_effector","subframes"):setattr(s,key,p[key])
    if mod.name not in owned:owned.append(mod.name)
    obj[OWNED]=json.dumps(owned);obj.update_tag();bpy.context.view_layer.update();return inspect()


def capture(obj,mod):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if mod.domain_settings.domain_type=="LIQUID":
        mesh=evaluated.to_mesh()
        try:
            coords=[evaluated.matrix_world@v.co for v in mesh.vertices]
            return {"kind":"LIQUID","vertices":len(coords),"bounds":{"min":[min(v[k] for v in coords) for k in range(3)],"max":[max(v[k] for v in coords) for k in range(3)]} if coords else None}
        finally:evaluated.to_mesh_clear()
    s=evaluated.modifiers[mod.name].domain_settings;grid=s.density_grid;n=len(grid)
    indices=range(0,n,max(1,n//32768));values=[grid[i] for i in indices]
    return {"kind":"GAS","grid_values":n,"sampled_values":len(values),"sampled_density_sum":sum(values),"sampled_density_max":max(values,default=0)}


def validate(p):
    root=Path(p["directory"]);record=read_json(root/MARKER)
    if record.get("kind")!="mcpblender-fluid-job" or record.get("state")!="succeeded":raise ValueError("Fluid job is not a successful bundle")
    manifest=read_json(root/"manifest.json")
    if manifest.get("job_id")!=record["job_id"] or manifest.get("source")!=record["source"]:raise ValueError("Fluid manifest binding mismatch")
    size=yield from verify_steps(root,manifest["files"])
    info=inspect()
    if not info["complete"] or info["fluid_sha256"]!=manifest["source"]:raise ValueError("Fluid source binding mismatch; open the bundle's asset.blend")
    obj,mod=domain(manifest);s=mod.domain_settings
    if obj.get(BINDING)!=record["job_id"] or Path(bpy.path.abspath(s.cache_directory)).resolve()!=(root/"cache").resolve() or not s.has_cache_baked_data:
        raise ValueError("Fluid native cache binding mismatch")
    scene=bpy.context.scene;old=scene.frame_current,scene.frame_subframe
    from .simulations import close_numbers
    try:
        for checkpoint in manifest["checkpoints"]:
            scene.frame_set(checkpoint["frame"]);bpy.context.view_layer.update()
            if not close_numbers(checkpoint["value"],capture(obj,mod)):raise ValueError("Fluid native checkpoint mismatch")
            yield {"phase":"validating native fluid checkpoint","frame":checkpoint["frame"]}
        return {"validated":True,"bytes":size,"files":len(manifest["files"]),"checkpoint_frames":[c["frame"] for c in manifest["checkpoints"]],"validation_scope":"file hashes, source binding and bounded native geometry/grid checkpoints"}
    finally:scene.frame_set(old[0],subframe=old[1]);bpy.context.view_layer.update()


def bake(p):
    from . import bridge
    info=guard(p);obj,mod=domain(p);s=mod.domain_settings
    if cached(s):raise ValueError("Bake from the original unbaked source project")
    root=Path(p["directory"])
    if root.exists():raise FileExistsError("Fluid output directory already exists")
    if not any(m.fluid_type=="FLOW" and settings(m).flow_behavior!="OUTFLOW" for _,m in controllers()):raise ValueError("At least one fluid source is required")
    scene_bytes=sum(len(m.vertices)*64+len(m.loops)*64 for m in bpy.data.meshes)+sum(i.packed_file.size for i in bpy.data.images if i.packed_file)
    previous_size=Path(bpy.data.filepath).stat().st_size if bpy.data.filepath and Path(bpy.data.filepath).is_file() else 0
    estimate=s.resolution_max**3*(s.cache_frame_end-s.cache_frame_start+1)*128*(s.mesh_scale**3 if s.use_mesh else 1)+max(16*1024**2,2*scene_bytes,2*previous_size)
    if estimate>p["max_bytes"]:raise ValueError("Fluid cache estimate exceeds max_bytes; reduce resolution/frames or explicitly raise the budget")
    policy=bridge._bridge.active["storage"];policy.update(estimated_bytes=estimate,estimate_kind="fluid_cells_frames_heuristic")
    require_space(root,estimate,reserve_bytes=policy.get("reserve_bytes",256*1024**2),estimate_kind=policy["estimate_kind"])
    root.mkdir(parents=True,exist_ok=False)
    record={"kind":"mcpblender-fluid-job","version":1,"job_id":uuid.uuid4().hex,"state":"running","source":info["fluid_sha256"],"parent_pid":os.getpid(),"worker_pid":None}
    write_json(root/MARKER,record);proc=None;success=False;cancelled=False;started=time.monotonic()
    try:
        yield {"phase":"saving isolated fluid source","native_call_interruptible":False}
        finished(bpy.ops.wm.save_as_mainfile(filepath=str(root/"source.blend"),copy=True,check_existing=False))
        job=p|{"parent_pid":os.getpid(),"job_id":record["job_id"],"source":info["fluid_sha256"],"reserve_bytes":policy.get("reserve_bytes",256*1024**2)}
        write_json(root/"job.json",job)
        with (root/"worker.log").open("wb") as log:
            proc=subprocess.Popen([bpy.app.binary_path,"--background","--factory-startup","--disable-autoexec","--threads",str(p["threads"]),"--python-exit-code","1","--python",str(Path(__file__).with_name("fluid_worker.py")),"--",str(root/"job.json")],cwd=str(root),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        record["worker_pid"]=proc.pid;write_json(root/MARKER,record)
        while proc.poll() is None:
            if time.monotonic()-started>p["timeout_seconds"]:raise TimeoutError("Fluid worker exceeded timeout; partial bundle preserved")
            rows,_=inventory(root);used=sum(row["bytes"] for row in rows)
            if used>p["max_bytes"]:raise ValueError("Fluid bundle exceeded max_bytes; stopping owned worker")
            require_space(root,max(0,estimate-used),reserve_bytes=job["reserve_bytes"],estimate_kind=policy["estimate_kind"])
            status=read_json(root/"result.json") if (root/"result.json").exists() else {}
            yield {"phase":status.get("phase","native fluid bake"),"worker_pid":proc.pid,"bytes_written":used,"file_count":len(rows),"worker_cancel_supported":True}
        if proc.returncode:raise RuntimeError(f"Fluid worker exited {proc.returncode}; inspect worker.log; partial bundle preserved")
        result=read_json(root/"result.json")
        if result.get("state")!="succeeded" or result.get("job_id")!=record["job_id"]:raise ValueError("Fluid worker did not return a bound success result")
        if sum(r["bytes"] for r in inventory(root)[0])>p["max_bytes"]:raise ValueError("Completed fluid bundle exceeds max_bytes")
        guard(p);manifest=read_json(root/"manifest.json");yield from verify_steps(root,manifest["files"])
        record["state"]="succeeded";write_json(root/MARKER,record);success=True
        return {"directory":str(root),"path":str(root/"asset.blend"),"manifest_path":str(root/"manifest.json"),"checkpoint_frames":[c["frame"] for c in manifest["checkpoints"]],"live_scene_unchanged":True,"bytes":sum(r["bytes"] for r in inventory(root)[0])}
    except GeneratorExit:
        cancelled=True;raise
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
        if not success:
            record["state"]="cancelled" if cancelled else "failed";write_json(root/MARKER,record)


def alive(pid):
    if not pid:return False
    from mcpblender.broker import process_alive
    return process_alive(pid)


def job_info(p):
    root=Path(p["directory"]);rows,_=inventory(root);record=read_json(root/MARKER)
    if record.get("kind")!="mcpblender-fluid-job" or record.get("version")!=1:raise ValueError("Not an owned fluid job")
    return {"record":record,"worker_alive":alive(record.get("worker_pid")),"parent_alive":alive(record.get("parent_pid")),
            "bytes":sum(r["bytes"] for r in rows),"file_count":len(rows)}


def recover(p):
    info=job_info(p);record=info["record"];root=Path(p["directory"])
    if record["state"]!="running":return info|{"reconciled":False}
    if info["worker_alive"] or info["parent_alive"]:raise ValueError("Recorded fluid processes may still be alive; refuse recovery")
    result=read_json(root/"result.json") if (root/"result.json").is_file() else {}
    if result.get("state")=="succeeded" and result.get("job_id")==record["job_id"]:
        saved=read_json(root/"manifest.json")
        if saved.get("source")!=record["source"] or saved.get("job_id")!=record["job_id"]:raise ValueError("Abandoned fluid manifest binding mismatch")
        yield from verify_steps(root,saved["files"]);record["state"]="succeeded"
    else:record["state"]="interrupted"
    write_json(root/MARKER,record)
    return job_info(p)|{"reconciled":True,"replayed":False,"native_validation_required":record["state"]=="succeeded"}


def cleanup(p):
    root=Path(p["directory"]);record=read_json(root/MARKER)
    states={"failed","cancelled"}|({"interrupted"} if p["include_interrupted"] else set())
    if record.get("kind")!="mcpblender-fluid-job" or record.get("version")!=1 or record.get("state") not in states:raise ValueError("Cleanup accepts failed/cancelled jobs, or explicitly included interrupted jobs; successful deliverables are protected")
    pid=record.get("worker_pid")
    if pid:
        try:os.kill(pid,0)
        except ProcessLookupError:pass
        else:raise ValueError("Recorded fluid worker may still be alive; refuse cleanup")
    paths=[bpy.data.filepath] if bpy.data.filepath else []
    paths += [bpy.path.abspath(settings(m).cache_directory) for _,m in controllers() if m.fluid_type=="DOMAIN"]
    if any(Path(path).resolve().is_relative_to(root.resolve()) for path in paths):raise ValueError("Current project references this fluid job")
    rows,dirs=inventory(root);result={"dry_run":p["dry_run"],"files":rows,"bytes":sum(r["bytes"] for r in rows)}
    if not p["dry_run"]:
        for row in rows:(root/row["path"]).unlink()
        for path in sorted(dirs,key=lambda p:len(p.parts),reverse=True):path.rmdir()
        root.rmdir()
    return result


def dispatch(command,p):
    if command=="inspect_fluids":return inspect()
    if command=="bake_fluid":return bake(p)
    if command=="validate_fluid_bake":return validate(p)
    if command=="cleanup_fluid_job":return cleanup(p)
    if command=="inspect_fluid_job":return job_info(p)
    if command=="recover_fluid_job":return recover(p)
    if command.startswith("configure_fluid_"):return configure(p,{"configure_fluid_domain":"DOMAIN","configure_fluid_flow":"FLOW","configure_fluid_effector":"EFFECTOR"}[command])
    guard(p);obj=mesh_object(p["name"],edit=True);mod=obj.modifiers.get(p["modifier"])
    if not mod or mod.type!="FLUID" or mod.name not in json.loads(obj.get(OWNED,"[]")):raise ValueError("Owned fluid controller not found")
    if any(cached(settings(m)) for _,m in controllers() if m.fluid_type=="DOMAIN"):raise ValueError("Cached fluid projects are protected")
    owned=json.loads(obj[OWNED]);owned.remove(mod.name);obj.modifiers.remove(mod);obj[OWNED]=json.dumps(owned);return inspect()
