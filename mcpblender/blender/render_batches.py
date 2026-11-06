"""Short editing-side snapshot/launch phase for independent camera batches."""
import fcntl
import os
from pathlib import Path
import subprocess
import uuid
import threading

import bpy
from . import compositing
from .assets import finished
from mcpblender.render_jobs import MARKER,write_json,read_json,file_hash
from mcpblender.storage import require_space
COMMANDS={'render_camera_batch'}


def launch(p,*,scene=None,snapshot_writer=None,resource_ids=None,scene_name=None):
    from .bridge import _bridge,check_cancelled,report_progress
    scene=scene or compositing.guard(p)
    scene_name=scene_name or scene.name
    if p.get('expected_sampling') is not None:
        from . import render_sampling
        profile=render_sampling.snapshot(scene)
        if profile['sampling_sha256']!=p['expected_sampling']:raise ValueError('Render sampling guard is stale')
        if profile['animated_fields'] or scene.render.engine!='CYCLES' or p['engine']!='CYCLES':raise ValueError('Guarded sampling batches require static Cycles settings')
        p=p|{'sampling_contract':{'format':'GUARDED_CYCLES_SAMPLING_V1','source':profile}}
        from mcpblender import render_sampling as sampling_schema
        sampling_schema.expected(p['sampling_contract'],p)

    resources=set(bpy.data.user_map()) if resource_ids is None else resource_ids
    for name in p['cameras']:
        obj=scene.objects.get(name)
        if not obj or obj.type!='CAMERA':raise ValueError('Render camera not found in current scene: '+name)
    # The saved project is the immutable source. Avoid silently retaining external
    # reads or output-writing compositor nodes in this initial snapshot profile.
    # blend_paths also includes weak references to bundled brush asset files,
    # even in a factory-startup scene. Those are editing metadata, not render
    # inputs. Inspect actual render-resource datablocks instead.
    external=[i.filepath for i in resources if isinstance(i,bpy.types.Image) and i.source!='VIEWER' and (not i.packed_file or i.is_dirty)]
    external += [v.filepath for v in resources if isinstance(v,(bpy.types.Library,bpy.types.MovieClip,bpy.types.CacheFile))]
    external += [v.filepath for v in resources if isinstance(v,bpy.types.VectorFont) and v.filepath!='<builtin>' and not v.packed_file]
    external += [v.filepath for v in resources if isinstance(v,bpy.types.Sound) and not v.packed_file]
    if external:raise ValueError('Independent render snapshots require packed/self-contained inputs; external project dependencies remain')
    for tree in (v for v in resources if isinstance(v,bpy.types.NodeTree)):
        if tree.bl_idname=='CompositorNodeTree' and any(n.bl_idname in {'CompositorNodeOutputFile','CompositorNodeImage','CompositorNodeMovieClip'} for n in tree.nodes):raise ValueError('Independent renders refuse file-output/external-image compositor nodes')
    for obj in (v for v in resources if isinstance(v,bpy.types.Object)):
        if any(mod.type=='FLUID' for mod in obj.modifiers) or obj.type=='VOLUME':raise ValueError('External fluid/volume caches require a separate frozen-cache snapshot workflow')
    if scene.compositing_node_group and scene.render.use_compositing:compositing.validate(scene.compositing_node_group)
    root=Path(p['directory'])
    if root.exists() or root.is_symlink():raise FileExistsError('Render output directory already exists')
    active=_bridge.active if _bridge and _bridge.active else {}
    if active.get('command') not in {'render_camera_batch','capture_botanical_views','capture_botanical_projected_coverage'} or not active.get('operation_id') or not active.get('owner'):raise RuntimeError('Independent rendering requires broker operation ownership')
    count=len(p['cameras'])*len(range(p['frame_start'],p['frame_end']+1,p['frame_step']))
    channels=4+sum(4 for layer in scene.view_layers for key in compositing.PASSES if getattr(*compositing.pass_owner(layer,key)))
    channels+=sum(4 if aov.type=='COLOR' else 1 for layer in scene.view_layers for aov in layer.aovs)
    scene_bytes=sum(len(m.vertices)*64+len(m.loops)*64 for m in resources if isinstance(m,bpy.types.Mesh))+sum(i.packed_file.size for i in resources if isinstance(i,bpy.types.Image) and i.packed_file)
    estimate=max(16*1024**2,scene_bytes*2)+count*p['width']*p['height']*(9+4*channels*('OPEN_EXR_MULTILAYER' in p['formats']))
    if estimate>p['max_bytes']:raise ValueError('Render batch estimate exceeds max_bytes')
    policy=active.get('storage',{});reserve=policy.get('reserve_bytes',256*1024**2)
    require_space(root,estimate,reserve_bytes=reserve,estimate_kind='render_pixels_passes_and_snapshot_heuristic')
    # Slot locks are inherited by the actual worker, independent of broker/PIDs.
    slots=Path(_bridge.path).parent/'render-slots';slots.mkdir(mode=0o700,exist_ok=True);slot=None;writer=None;proc=None;created=False
    try:
        for i in range(2):
            candidate=os.open(slots/f'slot-{i}',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            try:fcntl.flock(candidate,fcntl.LOCK_EX|fcntl.LOCK_NB);slot=candidate;break
            except BlockingIOError:os.close(candidate)
        if slot is None:raise ValueError('Two independent render workers are already active; wait for a render slot')
        check_cancelled();root.mkdir(mode=0o700,parents=True,exist_ok=False);created=True;(root/'outputs').mkdir(mode=0o700)
        writer=os.open(root/'writer.lock',os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600);fcntl.flock(writer,fcntl.LOCK_EX)
        identity=root.stat();job_id=uuid.uuid4().hex
        record={'kind':'mcpblender-render-job','version':1,'id':job_id,'operation_id':active['operation_id'],'owner':active['owner'],'identity':[identity.st_dev,identity.st_ino]}
        write_json(root/MARKER,record);write_json(root/'status.json',{'job_id':job_id,'state':'running','phase':'saving source snapshot','completed':0,'total':count})
        report_progress({'phase':'saving independent render snapshot','estimated_bytes':estimate,'native_call_interruptible':False})
        if snapshot_writer:snapshot_writer(root/'source.blend')
        else:finished(bpy.ops.wm.save_as_mainfile(filepath=str(root/'source.blend'),copy=True,check_existing=False,relative_remap=False))
        job=p|{'job_id':job_id,'owner':active['owner'],'scene':scene_name,'source_sha256':file_hash(root/'source.blend'),'reserve_bytes':reserve,'estimated_bytes':estimate}
        write_json(root/'job.json',job)
        if (root/'source.blend').stat().st_size>p['max_bytes']:raise ValueError('Saved source snapshot exceeds max_bytes')
        check_cancelled()
        with (root/'worker.log').open('wb') as log:
            proc=subprocess.Popen([bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec','--threads',str(p['threads']),'--python-exit-code','1','--python',str(Path(__file__).with_name('render_worker.py')),'--',str(root/'job.json'),str(writer),str(slot)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=root,start_new_session=True,pass_fds=(writer,slot))
        # Reap only our process object; job cancellation is self-directed through a
        # bound request file, never an unverified PID signal after restart.
        threading.Thread(target=proc.wait,daemon=True).start()
        return {'_external_render':True,'directory':str(root),'render_job_id':job_id,'operation_id':active['operation_id'],'worker_pid':proc.pid,'estimated_bytes':estimate,'editing_instance_released':True}
    except BaseException as exc:
        from .bridge import OperationCancelled
        if proc and proc.poll() is None:
            write_json(root/'cancel.json', {'job_id':job_id})
        if created and (root/MARKER).is_file():
            r=read_json(root/MARKER)
            write_json(root/'status.json',{'job_id':r['id'],'state':'cancelled' if isinstance(exc,OperationCancelled) else 'failed','phase':'snapshot or launch failed; partial files preserved'})
        raise
    finally:
        if writer is not None:os.close(writer)
        if slot is not None:os.close(slot)
