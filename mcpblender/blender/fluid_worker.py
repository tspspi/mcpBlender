"""Trusted isolated fluid bake entrypoint; never starts an MCP bridge."""
import os
from pathlib import Path
import sys
import threading
import time
import resource

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import bpy
from mcpblender.fluid_files import write_json,read_json,manifest
from mcpblender.blender import fluids
from mcpblender.blender.assets import active_object,finished


def main():
    # A failed native bake must not fill the filesystem with an unbudgeted core.
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    job_path=Path(sys.argv[sys.argv.index("--")+1]);job=read_json(job_path);root=job_path.parent
    def parent_watch():
        while True:
            if os.getppid()!=job["parent_pid"]:os._exit(125)
            time.sleep(.2)
    threading.Thread(target=parent_watch,daemon=True).start()
    if os.getppid()!=job["parent_pid"]:raise RuntimeError("Fluid parent is gone")
    def status(phase,**values):write_json(root/"result.json",{"job_id":job["job_id"],"state":"running","phase":phase}|values)
    status("loading isolated source")
    bpy.ops.wm.open_mainfile(filepath=str(root/"source.blend"),load_ui=False,use_scripts=False)
    bpy.context.preferences.filepaths.save_version=0
    fluids.guard({"expected_fluid":job["source"]})
    obj,mod=fluids.domain(job);s=mod.domain_settings;s.cache_directory="//cache"
    with active_object(obj):
        status("baking native fluid data")
        finished(bpy.ops.fluid.bake_data())
        if not s.has_cache_baked_data:raise RuntimeError("Native fluid data did not become baked")
        if s.domain_type=="LIQUID":
            status("baking native liquid surface")
            finished(bpy.ops.fluid.bake_mesh())
            if not s.has_cache_baked_mesh:raise RuntimeError("Native liquid surface did not become baked")
    fluids.guard({"expected_fluid":job["source"]})
    frames=sorted({s.cache_frame_start,(s.cache_frame_start+s.cache_frame_end)//2,s.cache_frame_end});checkpoints=[]
    status("sampling fluid checkpoints")
    for frame in frames:
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        checkpoints.append({"frame":frame,"value":fluids.capture(obj,mod)})
    if s.domain_type=="LIQUID" and not any(c["value"]["vertices"]>0 for c in checkpoints):raise RuntimeError("Liquid bake produced no surface geometry")
    if s.domain_type=="GAS" and not any(c["value"]["sampled_density_max"]>0 for c in checkpoints):raise RuntimeError("Gas bake produced no sampled density")
    status("saving baked project and hashing cache files")
    obj[fluids.BINDING]=job["job_id"]
    finished(bpy.ops.wm.save_as_mainfile(filepath=str(root/"asset.blend"),check_existing=False))
    write_json(root/"manifest.json",{"version":1,"job_id":job["job_id"],"source":job["source"],"name":obj.name,"modifier":mod.name,
               "blender_version":bpy.app.version_string,"checkpoints":checkpoints,"files":manifest(root)})
    write_json(root/"result.json",{"job_id":job["job_id"],"state":"succeeded","phase":"complete"})


if __name__=="__main__":
    main()
