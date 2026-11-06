"""Independent owned render process; no MCP bridge or user script execution."""
import os
from pathlib import Path
import resource
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import bpy
from mcpblender import render_jobs as files
from mcpblender.storage import require_space


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    args=sys.argv[sys.argv.index('--')+1:];root=Path(args[0]).parent;job=files.read_json(root/'job.json')
    writer,slot=map(int,args[1:]);os.fstat(writer);os.fstat(slot)
    lock=threading.Lock();stop=threading.Event();started=time.monotonic();current={'job_id':job['job_id'],'state':'running','completed':0,'total':len(job['cameras'])*len(range(job['frame_start'],job['frame_end']+1,job['frame_step']))}
    def status(**values):
        with lock:
            current.update(values);files.write_json(root/'status.json',current)
    def abort(state,message,code):
        try:status(state=state,phase=message)
        finally:os._exit(code)
    def watch():
        while not stop.wait(.2):
            try:
                if (root/'cancel.json').exists() and files.read_json(root/'cancel.json').get('job_id')==job['job_id']:abort('cancelled','cancelled owned render worker',130)
                if time.monotonic()-started>job['timeout_seconds']:abort('failed','render timeout exceeded',124)
                used=sum(v['bytes'] for v in files.inventory(root))
                if used>job['max_bytes']:abort('failed','render byte budget exceeded',123)
                space=require_space(root,max(0,job['estimated_bytes']-used),reserve_bytes=job['reserve_bytes'],estimate_kind='render_pixels_passes_and_snapshot_heuristic')
                status(bytes_written=used,estimated_bytes=job['estimated_bytes'],storage=space)
            except Exception as exc:abort('failed',str(exc),122)
    threading.Thread(target=watch,daemon=True).start()
    try:
        status(phase='loading source snapshot')
        if files.file_hash(root/'source.blend')!=job['source_sha256']:raise ValueError('Source snapshot hash mismatch')
        bpy.ops.wm.open_mainfile(filepath=str(root/'source.blend'),load_ui=False,use_scripts=False)
        if bpy.app.autoexec_fail:raise ValueError('Source requires disabled script/driver execution')
        scene=bpy.data.scenes[job['scene']];bpy.context.window.scene=scene
        if capture:=job.get('botanical_capture'):
            from mcpblender import tree_capture
            tree_capture.validate(capture,job)
            if capture.get('material_fields'):
                from mcpblender.blender import capture_material_fields
                capture_material_fields.install(scene,capture['material_fields'])
            if capture.get('component_ids'):
                from mcpblender.blender import capture_components
                capture_components.install(scene,capture['component_ids'],capture['material_fields'])
            # Source editing visibility is preserved in source.blend; canonical
            # reference owners are enabled only in this isolated process.
            for name in capture['render_visible_objects']:bpy.data.objects[name].hide_render=False
            for name in capture['render_visible_collections']:bpy.data.collections[name].hide_render=False
            for name in capture['render_visible_objects']:
                obj=bpy.data.objects[name]
                while obj.parent:obj=obj.parent;obj.hide_render=False
        scene.render.engine=job['engine'];scene.render.use_sequencer=False;scene.render.use_border=False
        scene.render.resolution_x=job['width'];scene.render.resolution_y=job['height'];scene.render.resolution_percentage=100
        scene.render.use_file_extension=True;scene.render.threads_mode='FIXED';scene.render.threads=job['threads']
        scene.render.compositor_device='CPU'
        if hasattr(scene,'cycles'):scene.cycles.samples=job['samples'];scene.cycles.device='CPU'
        if job['engine']=='BLENDER_EEVEE_NEXT':scene.eevee.taa_render_samples=job['samples']
        outputs=[];last=[0.]
        def stats(*values):
            if time.monotonic()-last[0]>.5:
                status(native_stats=' '.join(str(v) for v in values)[-1024:]);last[0]=time.monotonic()
        bpy.app.handlers.render_stats.append(stats)
        for ci,camera in enumerate(job['cameras']):
            scene.camera=bpy.data.objects[camera]
            for fi,frame in enumerate(range(job['frame_start'],job['frame_end']+1,job['frame_step'])):
                status(phase='rendering camera/frame',camera=camera,frame=frame,native_call_interruptible=False,worker_cancel_supported=True)
                scene.frame_set(frame)
                if 'FINISHED' not in bpy.ops.render.render(write_still=False):raise ValueError('Native render failed')
                for fmt in job['formats']:
                    scene.render.image_settings.media_type='MULTI_LAYER_IMAGE' if fmt=='OPEN_EXR_MULTILAYER' else 'IMAGE'
                    scene.render.image_settings.file_format=fmt;scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='16' if fmt=='PNG' else '32'
                    scene.render.image_settings.exr_codec='ZIP'
                    name=f"outputs/c{ci:02}_f{fi:04}.{'png' if fmt=='PNG' else 'exr'}";path=root/name
                    bpy.data.images['Render Result'].save_render(str(path),scene=scene)
                    outputs.append({'camera':camera,'camera_index':ci,'frame':frame,'frame_index':fi,'format':fmt,'file':name,'bytes':path.stat().st_size,'sha256':files.file_hash(path),'header':files.image_header(path)})
                status(completed=current['completed']+1)
        files.write_json(root/'manifest.json',{'version':1,'job_id':job['job_id'],'source_sha256':job['source_sha256'],'blender_version':bpy.app.version_string,'outputs':outputs,**({'botanical_capture':job['botanical_capture']} if 'botanical_capture' in job else {})})
        files.validate(root,job['owner'])
        if sum(v['bytes'] for v in files.inventory(root))>job['max_bytes']:raise ValueError('Completed render exceeds byte budget')
        status(state='succeeded',phase='complete')
    except BaseException as exc:
        status(state='failed',phase='render failed',error=f'{type(exc).__name__}: {exc}');raise
    finally:stop.set()

if __name__=='__main__':main()
