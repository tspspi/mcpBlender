"""Owned batch snapshots, dependency guards and independently verified publication."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import uuid

import bpy

from . import assemblies,lods,proxies,assembly_realization as realization
from .workflows import export_objects_glb
from mcpblender.proxy_contracts import Source as ProxySource
from mcpblender.storage import require_space
from mcpblender.package_files import MARKER,triangle_hash,surface_digest,inspect_static_glb,validate
from mcpblender.lod_files import file_hash

COMMANDS={'inspect_asset_package','export_asset_package','validate_asset_package'}


def native_proof(meshes):
    points=[];hashes=[];triangles=0
    for mesh in meshes:
        mesh.calc_loop_triangles()
        for triangle in mesh.loop_triangles:
            coords=[]
            for index in triangle.vertices:
                v=mesh.vertices[index].co;coords.append((v.x,v.z,-v.y))
            hashes.append(triangle_hash(coords));points.extend(coords);triangles+=1
    if not points:raise ValueError('Asset package members require triangle surfaces')
    return {'surface_sha256':surface_digest(hashes),'triangles':triangles,'mesh_instances':len(meshes),
            'gltf_world_bounds':{key:[fn(p[a] for p in points) for a in range(3)] for key,fn in (('min',min),('max',max))}}


def dependencies(meshes,check_cancelled):
    materials={m for mesh in meshes for m in mesh.materials if m}
    ids,_,issues=assemblies.dependencies(materials,assemblies.references(),nested_leaf=False)
    blockers=list(issues);images=[];records=[];warnings=[];pixel_bytes=0
    if any(isinstance(d,bpy.types.Object) for d in ids):blockers.append('Material references scene objects; bake object-coordinate/driver dependencies before packaging')
    for block in sorted(ids,key=lambda d:(type(d).__name__,d.name)):
        check_cancelled()
        if isinstance(block,bpy.types.Image):
            if block.source not in {'FILE','GENERATED'}:blockers.append('Unsupported image source for static packaging: '+block.name);continue
            external=None
            if block.source=='FILE' and not block.packed_file:
                path=Path(bpy.path.abspath(block.filepath,library=block.library))
                if not path.is_file() or path.stat().st_size>512*1024**2:blockers.append('Missing/oversized external image: '+block.name);continue
                external=file_hash(path)
            count=len(block.pixels)
            if not 0<count<=64*1024**2:blockers.append('Missing/oversized loaded image pixels: '+block.name);continue
            pixel_bytes+=count*4
            if pixel_bytes>1024**3:raise ValueError('Package dependency pixels exceed one GiB')
            pixels=array('f',[0])*count;block.pixels.foreach_get(pixels)
            if any(not math.isfinite(v) for v in pixels):raise ValueError('Nonfinite image pixels: '+block.name)
            images.append({'name':block.name,'size':list(block.size),'source':block.source,'packed':bool(block.packed_file),
                           'color_space':block.colorspace_settings.name,'pixel_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'external_sha256':external})
            del pixels
        elif isinstance(block,bpy.types.NodeTree):
            if any(n.bl_idname=='ShaderNodeScript' for n in block.nodes):blockers.append('Script shader dependencies must be baked before packaging: '+block.name)
            records.append(assemblies.record(block))
        elif isinstance(block,bpy.types.Material):
            if block.node_tree:
                for node in block.node_tree.nodes:
                    if node.type=='OUTPUT_MATERIAL' and node.is_active_output and node.inputs.get('Volume') and node.inputs['Volume'].is_linked:blockers.append('Volume material must use a separate delivery workflow: '+block.name)
                warnings.append('GLB shader conversion requires visual review: '+block.name)
            records.append(assemblies.record(block))
        elif isinstance(block,(bpy.types.Scene,bpy.types.World)):blockers.append('Context-dependent material must be baked: '+block.name)
        else:records.append(assemblies.record(block))
    return {'sha256':lods.digest({'records':records,'images':images}),'images':images,'materials':sorted(m.name for m in materials),
            'pixel_bytes':pixel_bytes,'blockers':sorted(set(blockers)),'warnings':sorted(set(warnings))}


def collect(p,check_cancelled=lambda:None):
    owned=[];parts=[];assets=[];blockers=[];warnings=[];estimated=16*1024**2
    try:
        for asset in p['assets']:
            check_cancelled();identifier=asset['id'];asset_parts=[]
            # Reuse the qualified evaluated-source snapshot path. Its collision
            # volume blockers do not apply to primary triangle surfaces.
            raw=ProxySource(objects=asset['objects'],method='BOX',grouping='COMBINED').model_dump()
            meshes,_,snapshot=proxies.source(raw,check_cancelled=check_cancelled);owned.extend(meshes)
            asset_parts.append({'role':'PRIMARY','meshes':meshes,'source_sha256':snapshot['source_sha256']})
            for purpose,key in (('COLLISION','collision_proxies'),('SHADOW','shadow_proxies')):
                for collection in asset.get(key,[]):
                    info=proxies.inspect({'collection':collection,'limit':128})
                    if not info['valid'] or not info['source_matches']:raise ValueError('Proxy is invalid/stale: '+collection)
                    if info['purpose']!=purpose or not set(info['settings']['objects'])<=set(asset['objects']):raise ValueError('Proxy role/source association differs from asset inputs: '+collection)
                    meta=json.loads(bpy.data.collections[collection][proxies.META]);meshes=[]
                    for member in meta['members']:
                        obj=bpy.data.objects[member['name']]
                        mesh=realization.copy_evaluated_mesh(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()),obj.matrix_world.copy());owned.append(mesh);meshes.append(mesh)
                    asset_parts.append({'role':purpose,'meshes':meshes,'proxy_collection':collection,'proxy_sha256':info['proxy_sha256'],'source_objects':info['settings']['objects'],'proxy_method':info['method'],'proxy_members':meta['members']})
            lod_entries=[]
            for options in asset.get('lods',[]):
                check_cancelled();chain=lods.inspect_chain(options)
                if not chain['valid'] or chain['source_stale_or_unavailable'] or chain['source'] not in asset['objects']:raise ValueError('LOD chain invalid/stale or not associated with an asset input: '+options['chain'])
                export_plan=lods.dispatch('inspect_lod_export',options)
                if not export_plan['can_export']:raise ValueError('LOD export blocked: '+'; '.join(export_plan['blockers']))
                _,_,lod_objects,_,_,_,_=lods.native_chain(options)
                dep=dependencies([o.data for o in lod_objects],check_cancelled);blockers.extend(dep['blockers']);warnings.extend(dep['warnings'])
                lod_entries.append({'options':options,'chain_sha256':chain['chain_sha256'],'source_sha256':chain['source_sha256'],'export_profile':export_plan,'dependencies':dep['sha256']})
                estimated+=sum(len(o.data.vertices)*192+len(o.data.polygons)*32 for o in lod_objects)+dep['pixel_bytes']*len(lod_objects)
            entries=[]
            role_counts={}
            for part in asset_parts:
                check_cancelled();role=part['role'];i=role_counts.get(role,0);role_counts[role]=i+1
                part['file']=identifier+'/'+('primary.glb' if role=='PRIMARY' else f'{role.lower()}_{i:02}.glb');part['asset']=identifier
                dep=dependencies(part['meshes'],check_cancelled);part['dependencies']=dep;part['native']=native_proof(part['meshes'])
                blockers.extend(dep['blockers']);warnings.extend(dep['warnings'])
                estimated+=sum(len(m.vertices)*192+len(m.polygons)*32 for m in part['meshes'])+dep['pixel_bytes']
                entries.append({k:v for k,v in part.items() if k not in {'meshes','dependencies'}}|{'dependencies':dep})
                parts.append(part)
            assets.append({'id':identifier,'objects':asset['objects'],'members':entries,'lods':lod_entries})
        result={'assets':assets,'frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe,'estimated_bytes':estimated,
                'blockers':sorted(set(blockers)),'warnings':sorted(set(warnings))}
        result['source_sha256']=lods.digest(result);result['can_export']=not blockers
        result['scope']='Primary and proxy GLBs are static current-viewport world-space snapshots. LOD bundles retain their own supported static/skin/morph profiles. Shader fidelity and engine integration require review.'
        return owned,parts,result
    except BaseException:
        for mesh in owned:bpy.data.meshes.remove(mesh)
        raise


def plan(p):
    owned,_,result=collect(p)
    try:return result
    finally:
        for mesh in owned:bpy.data.meshes.remove(mesh)


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    directory=Path(p['directory'])
    if directory.exists() or directory.is_symlink():raise FileExistsError('Asset package output directory already exists')
    owned=[];parts=[];temporary_objects=[];scene=None;stage=None;stage_created=False;published=False
    try:
        owned,parts,planned=collect(p,check_cancelled=check_cancelled)
        if planned['source_sha256']!=p['expected_source']:raise ValueError('Asset package source fingerprint is stale; inspect again')
        if planned['blockers']:raise ValueError('; '.join(planned['blockers']))
        policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
        require_space(directory,planned['estimated_bytes'],reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='native_mesh_and_loaded_image_pixel_heuristic')
        if _bridge and _bridge.active:_bridge.active['storage']['estimated_bytes']=planned['estimated_bytes']
        check_cancelled();stage=directory.parent/('.mcpblender-package-'+uuid.uuid4().hex);stage.mkdir(mode=0o700);stage_created=True
        scene=bpy.data.scenes.new('MCP_PackageExport');manifest_assets=[]
        for asset in planned['assets']:
            (stage/asset['id']).mkdir(mode=0o700);members=[];lod_entries=[]
            for part in [item for item in parts if item['asset']==asset['id']]:
                check_cancelled();objects=[]
                for i,mesh in enumerate(part['meshes']):
                    obj=bpy.data.objects.new(f"MCP_Package_{asset['id']}_{i:04}",mesh);temporary_objects.append(obj);objects.append(obj);scene.collection.objects.link(obj)
                path=stage/part['file']
                try:
                    window=bpy.context.window
                    if window is None:raise ValueError('Native GLB export requires a window context (background Blender normally supplies one)')
                    previous_scene=window.scene;previous_layer=window.view_layer
                    try:
                        # The native exporter dereferences the window's scene;
                        # a scene-only temp_override can crash this Blender build.
                        window.scene=scene;scene.frame_set(previous_scene.frame_current,subframe=previous_scene.frame_subframe)
                        bpy.context.view_layer.update()
                        export_objects_glb({'objects':[o.name for o in objects],'path':str(path),'animations':False,'overwrite':False,'apply_modifiers':False})
                    finally:
                        window.scene=previous_scene;window.view_layer=previous_layer
                        bpy.context.view_layer.update()
                    parsed=inspect_static_glb(path,check_cancelled)
                    if parsed['surface_sha256']!=part['native']['surface_sha256'] or parsed['triangles']!=part['native']['triangles'] or parsed['mesh_instances']!=part['native']['mesh_instances']:raise ValueError('Exported triangle surface differs from native asset snapshot')
                    member={'file':part['file'],'role':part['role'],'sha256':file_hash(path),'scene':parsed,'native':part['native'],
                            'dependencies':part['dependencies'],'source_sha256':part.get('source_sha256')}
                    if part['role']!='PRIMARY':
                        member.update(for_asset=asset['id'],proxy_sha256=part['proxy_sha256'],proxy_collection=part['proxy_collection'],source_objects=part['source_objects'],proxy_method=part['proxy_method'],
                                      proxy_nodes=[{'node':obj.name,'source_proxy':origin['name'],'native':native_proof([obj.data]),
                                                    'suggested_collision_shape':origin['suggested_collision_shape'],'quality':origin['quality'],'volume':origin['volume']} for obj,origin in zip(objects,part['proxy_members'])])
                    members.append(member)
                    report_progress({'phase':'verified package mesh and embedded dependencies','asset':asset['id'],'role':part['role'],'bytes':path.stat().st_size})
                finally:
                    for obj in objects:temporary_objects.remove(obj);bpy.data.objects.remove(obj,do_unlink=True)
            for i,lod_entry in enumerate(asset['lods']):
                check_cancelled();relative=asset['id']+f'/lod_{i:02}';options=lod_entry['options']
                lods.export(options|{'expected_chain':lod_entry['chain_sha256'],'expected_animation':lod_entry['export_profile'].get('animation_sha256'),'directory':str(stage/relative)})
                files={path.name:file_hash(path) for path in sorted((stage/relative).iterdir())}
                lod_entries.append({'directory':relative,'chain':options['chain'],'chain_sha256':lod_entry['chain_sha256'],'source_sha256':lod_entry['source_sha256'],'animation_sha256':lod_entry['export_profile'].get('animation_sha256'),'files':files})
                report_progress({'phase':'verified package LOD bundle','asset':asset['id'],'chain':options['chain']})
            manifest_assets.append({'id':asset['id'],'objects':asset['objects'],'members':members,'lods':lod_entries})
        check_cancelled()
        if plan(p)['source_sha256']!=p['expected_source']:raise ValueError('Asset package source changed during export')
        document={'format':MARKER,'source_sha256':p['expected_source'],'frame':planned['frame'],'blender_version':bpy.app.version_string,
                  'assets':manifest_assets,'warnings':planned['warnings'],'scope':planned['scope']}
        (stage/'manifest.json').write_text(json.dumps(document,indent=2,allow_nan=False)+'\n')
        verified=validate(stage,check_cancelled);report_progress({'phase':'verified asset package inventory','assets':len(manifest_assets),'files':len(verified['files'])});check_cancelled()
        if directory.exists() or directory.is_symlink():raise FileExistsError('Asset package output directory already exists')
        stage.rename(directory);published=True
        return verified|{'directory':str(directory),'path':str(directory/'manifest.json'),'estimated_bytes':planned['estimated_bytes']}
    finally:
        for obj in temporary_objects:bpy.data.objects.remove(obj,do_unlink=True)
        if scene:bpy.data.scenes.remove(scene)
        for mesh in owned:bpy.data.meshes.remove(mesh)
        if stage_created and not published and stage.exists():shutil.rmtree(stage)


def dispatch(command,p):
    if command=='inspect_asset_package':return plan(p)
    if command=='export_asset_package':return export(p)
    from .bridge import check_cancelled
    return validate(p['directory'],check_cancelled)
