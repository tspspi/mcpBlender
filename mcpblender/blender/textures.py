"""Guarded image baking with isolated workers and persistent owned bundles."""
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
from .mesh_edit import geometry_digest
from .morphs import topology_digest
from .simulations import props
from . import shaders,uv
from .fluids import alive
from mcpblender.texture_files import MARKER,inventory,write_json,read_json,verify_steps,file_hash,projected_map_policy,validate_map_policy
from mcpblender.storage import require_space

COMMANDS={'inspect_texture_bake','bake_textures','validate_texture_bake','inspect_texture_job','recover_texture_job','cleanup_texture_job'}
BINDING='mcpblender_texture_binding'
NODE_UI={'select','location','width','height','hide','label','color','use_custom_color','show_options','show_preview','show_texture'}


def packed_array(values,property,count,kind='f'):
    data=array(kind,[0])*count;values.foreach_get(property,data)
    return hashlib.sha256(data.tobytes()).hexdigest()


THIN_NODES={'Surface Side':'ShaderNodeNewGeometry','Leaf Sides':'ShaderNodeMixRGB','Leaf Surface':'ShaderNodeBsdfPrincipled',
            'Thin Backlighting':'ShaderNodeBsdfTranslucent','Optical Mix':'ShaderNodeMixShader','Culled Backface':'ShaderNodeBsdfTransparent',
            'Backface Enabled':'ShaderNodeMath','Backface Cull':'ShaderNodeMixShader','Output':'ShaderNodeOutputMaterial'}


def bake_surface_node(mat,thin_foliage_mode='REFUSE'):
    tree=mat.node_tree;outputs=[n for n in tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if len(outputs)!=1 or outputs[0].inputs['Volume'].is_linked:raise ValueError('One surface-only material output required')
    surface=outputs[0].inputs['Surface']
    if not surface.is_linked:raise ValueError('Material surface must connect directly to Principled BSDF')
    if surface.links[0].from_node.type=='BSDF_PRINCIPLED':return surface.links[0].from_node,None
    if thin_foliage_mode!='FRONT_PBR':raise ValueError('Material surface must connect directly to Principled BSDF; managed thin leaves require explicit thin_foliage_mode=FRONT_PBR')
    try:marker=json.loads(mat.get('mcpblender_thin_foliage','null'))
    except (ValueError,TypeError):marker=None
    if not isinstance(marker,dict) or marker.get('version')!=1 or marker.get('alpha_mode')!='OPAQUE_GEOMETRY':raise ValueError('FRONT_PBR requires a managed opaque-geometry thin-leaf material')
    for name,kind in THIN_NODES.items():
        node=tree.nodes.get(name)
        if not node or node.bl_idname!=kind:raise ValueError('Unsupported managed leaf shader node: '+name)
    if outputs[0]!=tree.nodes['Output'] or tree.nodes['Leaf Sides'].blend_type!='MIX' or tree.nodes['Backface Enabled'].operation!='MULTIPLY':raise ValueError('Unsupported managed leaf shader topology')
    required=[('Output','Surface','Backface Cull',0),('Backface Cull',0,'Backface Enabled',0),('Backface Cull',1,'Optical Mix',0),
              ('Backface Cull',2,'Culled Backface',0),('Backface Enabled',0,'Surface Side','Backfacing'),
              ('Leaf Sides',0,'Surface Side','Backfacing'),('Optical Mix',1,'Leaf Surface',0),('Optical Mix',2,'Thin Backlighting',0)]
    for target,socket,source,output in required:
        port=tree.nodes[target].inputs[socket];expected=tree.nodes[source].outputs[output]
        if len(port.links)!=1 or port.links[0].from_socket!=expected:raise ValueError('Unsupported managed leaf shader link: '+target)
    return tree.nodes['Leaf Surface'],{'kind':'MANAGED_THIN_LEAF_FRONT_PBR_V1','material':mat.name,
       'omitted_features':['native back color','translucent lobe and transmission color','native backface transparency/double-sided shader'],
       'scope':'Bake selected Principled front inputs with Leaf Sides forced to front in the isolated child. This is a lossy PBR approximation, not native thin-surface optical equivalence.'}


def material_signature(mat,*,source=True,thin_foliage_mode='REFUSE'):
    if not mat or mat.library or mat.override_library or not mat.use_nodes or mat.animation_data or mat.node_tree.animation_data:
        raise ValueError('Local static node materials required')
    tree=mat.node_tree
    if len(tree.nodes)>128 or len(tree.links)>512:raise ValueError('Material graph budget exceeded')
    selected,adapter=bake_surface_node(mat,thin_foliage_mode if source else 'REFUSE')
    records=[]
    for node in tree.nodes:
        if node.bl_idname not in shaders.NODE_TYPES or node.type in {'ATTRIBUTE','VOLUME_INFO','PRINCIPLED_VOLUME'}:
            if not (adapter and THIN_NODES.get(node.name)==node.bl_idname or node.type=='GROUP' and baked_ao_group(node.node_tree)):
                raise ValueError(f'Unsupported bake material node: {node.bl_idname}')
        if node.type=='TEX_COORD' and node.object:raise ValueError('External texture-coordinate objects are unsupported')
        record={'name':node.name,'type':node.bl_idname,'properties':{k:v for k,v in props(node).items() if k not in NODE_UI},
                'inputs':[shaders.socket_info(s,i) for i,s in enumerate(node.inputs)],
                'outputs':[shaders.socket_info(s,i) for i,s in enumerate(node.outputs)]}
        if node.type=='GROUP':record['group_name']=node.node_tree.name
        if node.type=='VALTORGB':record['ramp']={'interpolation':node.color_ramp.interpolation,'color_mode':node.color_ramp.color_mode,'hue_interpolation':node.color_ramp.hue_interpolation,'elements':[(e.position,list(e.color)) for e in node.color_ramp.elements]}
        if node.type=='TEX_IMAGE':
            image=node.image
            if not image or image.source not in {'FILE','GENERATED'} or image.size[0]*image.size[1]>4*1024**2:
                raise ValueError('Bounded single-image texture inputs required')
            if image.is_dirty or (source and not image.packed_file):raise ValueError('Bake source images must be saved and packed without unsaved pixel edits')
            content=hashlib.sha256(image.packed_file.data).hexdigest() if image.packed_file else file_hash(bpy.path.abspath(image.filepath))
            record['image']={'name':image.name,'size':list(image.size),'color_space':image.colorspace_settings.name,'alpha_mode':image.alpha_mode,'content':content}
        records.append(record)
    return {'nodes':records,'links':[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in tree.links],
            'material':mat.name,'properties':props(mat)}|({'bake_adapter':adapter} if adapter else {})


def mesh_signature(obj,mesh):
    if len(mesh.vertices)>250000 or len(mesh.loops)>1000000:raise ValueError('Evaluated bake geometry budget exceeded')
    if any(not math.isfinite(v) for row in obj.matrix_world for v in row) or any(not math.isfinite(v) for vertex in mesh.vertices for v in vertex.co):raise ValueError('Finite bake geometry/transforms required')
    return {'name':obj.name,'geometry':geometry_digest(mesh),'matrix':[list(row) for row in obj.matrix_world],
            'uv':[(layer.name,packed_array(layer.data,'uv',len(mesh.loops)*2)) for layer in mesh.uv_layers],
            'render_uv':next((l.name for l in mesh.uv_layers if l.active_render),None),
            'corner_normals':packed_array(mesh.corner_normals,'vector',len(mesh.corner_normals)*3),
            'materials':packed_array(mesh.polygons,'material_index',len(mesh.polygons),'i'),
            'texspace':{'auto':mesh.use_auto_texspace,'location':list(mesh.texspace_location),'size':list(mesh.texspace_size)}}


def inspect(p):
    bpy.context.view_layer.update();records=[];reasons=[];total=0;target_topology=None
    if not hasattr(bpy.context.scene,'cycles'):reasons.append('Cycles rendering support is required')
    roles=[(p['name'],'target')]+[(n,'source') for n in p.get('sources',[])]+([(p['cage'],'cage')] if p.get('cage') else [])
    for name,role in roles:
        evaluated=None
        try:
            obj=mesh_object(name,edit=True)
            if obj.data.override_library:raise ValueError('Local mesh data required')
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
            if not mesh.polygons:raise ValueError('Bake objects require faces')
            record=mesh_signature(evaluated,mesh);record['role']=role;total+=len(mesh.vertices)
            if role=='target':
                target_topology=topology_digest(mesh);layer=mesh.uv_layers.get(p['uv_map'])
                if not layer:raise ValueError('Target UV map not found')
                coords,islands,triangles=uv.layout(mesh,layer,evaluated.matrix_world,1024,1024)
                if any(i['uv_area']<=1e-20 or i['world_area']<=1e-20 for i in islands):raise ValueError('Target has degenerate UV/world islands')
                if any(v< -1e-6 or v>1.000001 for co in coords for v in co):raise ValueError('Target UVs must fit the unit tile')
                overlap=uv.overlaps(triangles,200000)
                if not overlap['complete'] or overlap['face_pair_count']:raise ValueError('Target UV overlap check must be complete and clear')
                record['uv_islands']=len(islands)
                if p.get('quality'):
                    from .texture_quality import measure
                    record['texture_quality']=measure(evaluated,mesh,p['uv_map'],p['quality'])
                    if not record['texture_quality']['passed']:reasons.append(name+': texture quality gate did not pass')
            elif role=='cage' and topology_digest(mesh)!=target_topology:raise ValueError('Cage topology/order must match the evaluated target')
            if role=='source' or role=='target' and not p.get('sources'):
                if not mesh.materials or any(m is None for m in mesh.materials):raise ValueError('Every source slot needs a material')
                record['shaders']=[material_signature(m,thin_foliage_mode=p.get('thin_foliage_mode','REFUSE')) for m in mesh.materials]
            records.append(record)
        except (ValueError,RuntimeError) as exc:reasons.append(f'{name}: {exc}')
        finally:
            if evaluated:evaluated.to_mesh_clear()
    if total>500000:reasons.append('Total evaluated source vertex budget exceeded')
    content={'objects':records,'uv_map':p['uv_map'],'frame':bpy.context.scene.frame_current,'subframe':bpy.context.scene.frame_subframe}
    if p.get('thin_foliage_mode','REFUSE')!='REFUSE':content['thin_foliage_mode']=p['thin_foliage_mode']
    adapters={s['material']:s['bake_adapter'] for r in records for s in r.get('shaders',[]) if s.get('bake_adapter')}
    from mcpblender.texture_files import bake_fingerprint
    digest=bake_fingerprint(content) if not reasons else None
    return content|{'material_adapters':[adapters[k] for k in sorted(adapters)],'complete':not reasons,'bake_sha256':digest,'unsupported_reasons':reasons}


def guard(p):
    if p.get('_texture_pipeline')=='ATLAS':
        from .texture_atlas import guard as atlas_guard
        return atlas_guard(p)
    info=inspect(p)
    if not info['complete']:raise ValueError('Unsupported bake sources: '+'; '.join(info['unsupported_reasons'][:8]))
    if info['bake_sha256']!=p['expected_bake']:raise ValueError('Texture bake fingerprint is stale; inspect_texture_bake first')
    return info


def output_signature(name):
    obj=mesh_object(name);mesh=obj.data
    content={'mesh':mesh_signature(obj,mesh),'materials':[material_signature(m,source=False) for m in mesh.materials]}
    return hashlib.sha256(json.dumps(content,sort_keys=True,allow_nan=False).encode()).hexdigest()


def validate(p):
    root=Path(p['directory']);record=read_json(root/MARKER);saved=read_json(root/'manifest.json')
    if record.get('kind')!='mcpblender-texture-job' or record.get('state')!='succeeded':raise ValueError('Texture job is not a successful bundle')
    if saved.get('job_id')!=record['job_id'] or saved.get('source')!=record['source'] or saved.get('material_adapters',[])!=record.get('material_adapters',[]) or saved.get('atlas')!=record.get('atlas'):raise ValueError('Texture manifest binding mismatch')
    map_policy=validate_map_policy(record,saved,read_json(root/'job.json'))
    size=yield from verify_steps(root,saved['files'])
    names=saved['objects'] if saved.get('atlas') is not None else [saved['name']]
    if saved.get('atlas') is not None and (names!=[t['id'] for t in saved['atlas']['layout']['tiles']] or set(saved['object_signatures'])!=set(names)):raise ValueError('Atlas object inventory differs from tiles')
    for name in names:
        obj=mesh_object(name)
        signature=saved['object_signatures'][name] if saved.get('atlas') is not None else saved['asset_sha256']
        if obj.get(BINDING)!=record['job_id'] or output_signature(obj.name)!=signature:raise ValueError('Texture asset binding mismatch; open the unchanged baked asset')
        for image in (n.image for m in obj.data.materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE'):
            if Path(bpy.path.abspath(image.filepath)).resolve().parent!=(root/'textures').resolve():raise ValueError('Baked image path does not reference this bundle')
    return {'validated':True,'bytes':size,'map_policy':map_policy,'maps':saved['maps'],'material':saved['material'],'projection':saved['projection'],'material_adapters':saved.get('material_adapters',[]),**({'atlas':saved['atlas'],'objects':names} if saved.get('atlas') is not None else {}),'validation_scope':'file hashes and native low geometry/UV/material/image binding'}


def bake(p):
    from . import bridge
    info=guard(p);root=Path(p['directory'])
    if root.exists():raise FileExistsError('Texture output directory already exists')
    scene_bytes=sum(len(m.vertices)*64+len(m.loops)*64 for m in bpy.data.meshes)+sum(i.packed_file.size for i in bpy.data.images if i.packed_file)
    previous=Path(bpy.data.filepath).stat().st_size if bpy.data.filepath and Path(bpy.data.filepath).is_file() else 0
    estimate=(info['estimated_output_bytes'] if p.get('_texture_pipeline')=='ATLAS' else p['width']*p['height']*32*(len(p['maps'])+(2 if p['sources'] else 0)))+max(16*1024**2,scene_bytes*2,previous*2)
    if estimate>p['max_bytes']:raise ValueError('Texture bake estimate exceeds max_bytes')
    policy=bridge._bridge.active['storage'];policy.update(estimated_bytes=estimate,estimate_kind='atlas_png_geometry_snapshot_heuristic' if p.get('_texture_pipeline')=='ATLAS' else 'texture_pixels_maps_and_snapshot_heuristic')
    reserve=policy.get('reserve_bytes',256*1024**2);require_space(root,estimate,reserve_bytes=reserve,estimate_kind=policy['estimate_kind'])
    root.mkdir(parents=True,exist_ok=False)
    record={'kind':'mcpblender-texture-job','version':1,'job_id':uuid.uuid4().hex,'state':'running','source':info['bake_sha256'],'parent_pid':os.getpid(),'worker_pid':None,'material_adapters':info.get('material_adapters',[])}
    if projected_map_policy(p) is not None:record['map_policy']=projected_map_policy(p)
    if 'atlas' in info:record['atlas']=info['atlas']
    write_json(root/MARKER,record);proc=None;success=False;cancelled=False;started=time.monotonic()
    try:
        yield {'phase':'saving isolated texture source','native_call_interruptible':False}
        finished(bpy.ops.wm.save_as_mainfile(filepath=str(root/'source.blend'),copy=True,check_existing=False))
        write_json(root/'job.json',p|{'parent_pid':os.getpid(),'job_id':record['job_id'],**({'map_policy':record['map_policy']} if 'map_policy' in record else {})})
        with (root/'worker.log').open('wb') as log:
            proc=subprocess.Popen([bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec','--threads',str(p['threads']),'--python-exit-code','1','--python',str(Path(__file__).with_name('texture_worker.py')),'--',str(root/'job.json')],cwd=str(root),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        record['worker_pid']=proc.pid;write_json(root/MARKER,record)
        while proc.poll() is None:
            if time.monotonic()-started>p['timeout_seconds']:raise TimeoutError('Texture worker exceeded timeout; partial bundle preserved')
            rows,_=inventory(root);used=sum(r['bytes'] for r in rows)
            if used>p['max_bytes']:raise ValueError('Texture bundle exceeded max_bytes; stopping owned worker')
            require_space(root,max(0,estimate-used),reserve_bytes=reserve,estimate_kind=policy['estimate_kind'])
            status=read_json(root/'result.json') if (root/'result.json').exists() else {}
            yield {'phase':status.get('phase','native texture bake'),'map':status.get('map'),'completed_maps':status.get('completed_maps',0),'worker_pid':proc.pid,'bytes_written':used,'worker_cancel_supported':True}
        if proc.returncode:
            status=read_json(root/'result.json') if (root/'result.json').exists() else {}
            raise RuntimeError(f"Texture worker exited {proc.returncode}: {status.get('error','inspect worker.log')}; partial bundle preserved")
        result=read_json(root/'result.json');saved=read_json(root/'manifest.json')
        if result.get('state')!='succeeded' or result.get('job_id')!=record['job_id'] or saved.get('source')!=record['source'] or saved.get('job_id')!=record['job_id'] or saved.get('material_adapters',[])!=record.get('material_adapters',[]) or saved.get('atlas')!=record.get('atlas'):raise ValueError('Texture worker result binding mismatch')
        validate_map_policy(record,saved,read_json(root/'job.json'))
        if sum(r['bytes'] for r in inventory(root)[0])>p['max_bytes']:raise ValueError('Completed texture bundle exceeds max_bytes')
        guard(p);yield from verify_steps(root,saved['files'])
        record['state']='succeeded';write_json(root/MARKER,record);success=True
        return {'directory':str(root),'path':str(root/'asset.blend'),'map_policy':saved.get('map_policy'),'maps':saved['maps'],'material':saved['material'],'projection':saved['projection'],'material_adapters':saved.get('material_adapters',[]),**({'atlas':saved['atlas'],'objects':saved['objects']} if 'atlas' in saved else {}),'live_scene_unchanged':True,'bytes':sum(r['bytes'] for r in inventory(root)[0])}
    except GeneratorExit:cancelled=True;raise
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
        if not success:record['state']='cancelled' if cancelled else 'failed';write_json(root/MARKER,record)


def job_info(p):
    root=Path(p['directory']);rows,_=inventory(root);record=read_json(root/MARKER)
    if record.get('kind')!='mcpblender-texture-job' or record.get('version')!=1:raise ValueError('Not an owned texture job')
    return {'record':record,'worker_alive':alive(record.get('worker_pid')),'parent_alive':alive(record.get('parent_pid')),'bytes':sum(r['bytes'] for r in rows),'file_count':len(rows)}


def recover(p):
    info=job_info(p);record=info['record'];root=Path(p['directory'])
    if record['state']!='running':return info|{'reconciled':False}
    if info['worker_alive'] or info['parent_alive']:raise ValueError('Recorded texture processes may still be alive; refuse recovery')
    result=read_json(root/'result.json') if (root/'result.json').is_file() else {}
    if result.get('state')=='succeeded' and result.get('job_id')==record['job_id']:
        saved=read_json(root/'manifest.json')
        if saved.get('source')!=record['source'] or saved.get('job_id')!=record['job_id'] or saved.get('material_adapters',[])!=record.get('material_adapters',[]) or saved.get('atlas')!=record.get('atlas'):raise ValueError('Abandoned texture manifest binding mismatch')
        validate_map_policy(record,saved,read_json(root/'job.json'))
        yield from verify_steps(root,saved['files']);record['state']='succeeded'
    else:record['state']='interrupted'
    write_json(root/MARKER,record)
    return job_info(p)|{'reconciled':True,'replayed':False,'native_validation_required':record['state']=='succeeded'}


def cleanup(p):
    root=Path(p['directory']);record=read_json(root/MARKER)
    states={'failed','cancelled'}|({'interrupted'} if p['include_interrupted'] else set())
    if record.get('kind')!='mcpblender-texture-job' or record.get('version')!=1 or record.get('state') not in states:raise ValueError('Cleanup requires an owned failed/cancelled or explicitly included interrupted texture job; success is protected')
    if alive(record.get('worker_pid')):raise ValueError('Recorded texture worker may still be alive')
    paths=([bpy.data.filepath] if bpy.data.filepath else [])+[bpy.path.abspath(i.filepath) for i in bpy.data.images if i.filepath]
    if any(Path(path).resolve().is_relative_to(root.resolve()) for path in paths):raise ValueError('Current project references this texture job')
    rows,dirs=inventory(root);result={'dry_run':p['dry_run'],'files':rows,'bytes':sum(r['bytes'] for r in rows)}
    if not p['dry_run']:
        for row in rows:(root/row['path']).unlink()
        for path in reversed(dirs):path.rmdir()
        root.rmdir()
    return result


def dispatch(command,p):
    return {'inspect_texture_bake':inspect,'bake_textures':bake,'validate_texture_bake':validate,'inspect_texture_job':job_info,'recover_texture_job':recover,'cleanup_texture_job':cleanup}[command](p)


def baked_material(images,uv_map):
    """Build the shared explicit-UV PBR recipe from already verified images."""
    properties={'BASE_COLOR':'Base Color','ROUGHNESS':'Roughness','METALLIC':'Metallic','EMISSION':'Emission Color','ALPHA':'Alpha'}
    mat=bpy.data.materials.new('BakedPBR');mat.use_nodes=True;tree=mat.node_tree;surface=tree.nodes.get('Principled BSDF');surface.name='Surface';tree.nodes.get('Material Output').name='Output'
    for kind,image in images.items():
        node=tree.nodes.new('ShaderNodeTexImage');node.name=kind;node.image=image
        coords=tree.nodes.new('ShaderNodeUVMap');coords.uv_map=uv_map;tree.links.new(coords.outputs['UV'],node.inputs['Vector'])
        if kind=='NORMAL':
            normal=tree.nodes.new('ShaderNodeNormalMap');normal.uv_map=uv_map;tree.links.new(node.outputs['Color'],normal.inputs['Color']);tree.links.new(normal.outputs['Normal'],surface.inputs['Normal'])
        elif kind=='AO':
            group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');group.nodes.new('NodeGroupInput');group.nodes.new('NodeGroupOutput');group['mcpblender_baked_ao']=True
            settings=tree.nodes.new('ShaderNodeGroup');settings.node_tree=group;tree.links.new(node.outputs['Color'],settings.inputs['Occlusion'])
        else:tree.links.new(node.outputs['Color'],surface.inputs[properties[kind]])
    if 'EMISSION' in images:surface.inputs['Emission Strength'].default_value=1
    return mat


def baked_ao_group(group):
    return bool(group and not group.animation_data and group.get('mcpblender_baked_ao') and len(group.nodes)==2 and {n.bl_idname for n in group.nodes}=={'NodeGroupInput','NodeGroupOutput'} and not group.links and [(s.name,s.in_out,s.socket_type) for s in group.interface.items_tree if s.item_type=='SOCKET']==[('Occlusion','INPUT','NodeSocketFloat')])
