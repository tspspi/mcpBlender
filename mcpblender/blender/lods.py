"""Source-preserving static LOD chains, sampled quality and owned bundle export."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import uuid

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

from .assets import mesh_object,require_static,active_object,finished
from .mesh_edit import geometry_digest
from mcpblender.lod_files import MARKER,file_hash,glb_report,validate
from mcpblender.storage import require_space

COMMANDS={'inspect_glb_deformation','inspect_lod_export','sample_lod_chain','inspect_lod_source','generate_lod_chain','inspect_lod_chain','activate_lod_level','export_lod_chain','validate_lod_export'}
META='mcpblender_lod_chain'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def matrix(value):return [list(r) for r in value]
def packed(data,field,count,kind='f'):
    values=array(kind,[0])*count;data.foreach_get(field,values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def attributes(mesh):
    records=[]
    for attr in mesh.attributes:
        record={'name':attr.name,'domain':attr.domain,'type':attr.data_type,'count':len(attr.data)}
        if attr.data:
            item=attr.data[0];prop=next((item.bl_rna.properties.get(k) for k in ('value','vector','color') if item.bl_rna.properties.get(k)),None)
            if not prop or prop.type not in {'FLOAT','INT','BOOLEAN'}:raise ValueError('LOD snapshot cannot safely preserve attribute type: '+attr.data_type)
            record['sha256']=packed(attr.data,prop.identifier,len(attr.data)*(prop.array_length if prop.is_array else 1),'f' if prop.type=='FLOAT' else 'i')
        records.append(record)
    return records


def summary(mesh):
    if len(mesh.vertices)>250000 or len(mesh.loops)>1000000:raise ValueError('LOD geometry limits: 250000 vertices and one million corners')
    mesh.calc_loop_triangles()
    if not mesh.vertices or not mesh.loop_triangles or len(mesh.loop_triangles)>500000:raise ValueError('LOD requires 1..500000 triangles')
    if any(not math.isfinite(v) for vertex in mesh.vertices for v in vertex.co):raise ValueError('Finite LOD geometry required')
    if any(not math.isfinite(v) for normal in mesh.corner_normals for v in normal.vector):raise ValueError('Finite LOD normals required')
    uv=[]
    for layer in mesh.uv_layers:
        if any(not math.isfinite(v) for item in layer.data for v in item.uv):raise ValueError('Finite LOD UVs required')
        uv.append({'name':layer.name,'sha256':packed(layer.data,'uv',len(layer.data)*2),'render':layer.active_render})
    if any(p.material_index>=max(1,len(mesh.materials)) for p in mesh.polygons):raise ValueError('LOD material indices are invalid')
    attrs=attributes(mesh)
    used={i for triangle in mesh.loop_triangles for i in triangle.vertices}
    bounds={'min':[min(mesh.vertices[v].co[i] for v in used) for i in range(3)],'max':[max(mesh.vertices[v].co[i] for v in used) for i in range(3)]}
    content={'geometry':geometry_digest(mesh),'uv':uv,'materials':[m.name if m else None for m in mesh.materials],
             'material_indices':packed(mesh.polygons,'material_index',len(mesh.polygons),'i'),
             'smooth_faces':packed(mesh.polygons,'use_smooth',len(mesh.polygons),'i'),
             'normals':packed(mesh.corner_normals,'vector',len(mesh.corner_normals)*3),'attributes':attrs}
    return {'local_surface_bounds':bounds,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'polygons':len(mesh.polygons),
            'uv_maps':[l['name'] for l in uv],'render_uv_map':next((l['name'] for l in uv if l['render']),None),'materials':content['materials'],
            'used_material_indices':sorted({p.material_index for p in mesh.polygons}),
            'attributes':[{k:v for k,v in a.items() if k not in {'sha256','count'}} for a in attrs if not a['name'].startswith('.') and a['name'] not in {'position','material_index','sharp_face','sharp_edge'}],
            'mesh_sha256':digest(content)}


def source_snapshot(p):
    if p.get('deformation')=='MORPH':
        from .morph_lods import source_snapshot as snapshot
        return snapshot(p)
    if p.get('deformation')=='SKINNED':
        from .skin_lods import source_snapshot as snapshot
        return snapshot(p)
    obj=mesh_object(p['name']);require_static(obj)
    if obj.find_armature() or obj.data.shape_keys:raise ValueError('Static LODs require no armature or shape keys; choose deformation=SKINNED for linear skins, or MORPH for relative shape keys')
    if obj.name not in bpy.context.scene.objects or bpy.context.view_layer.objects.get(obj.name)!=obj or not obj.visible_get():raise ValueError('LOD source must be visible in the current scene/view layer')
    bpy.context.view_layer.update()
    if any(not math.isfinite(v) for row in obj.matrix_world for v in row) or abs(obj.matrix_world.determinant())<1e-12:raise ValueError('Finite invertible source transform required')
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
    try:
        # Object-linked material overrides are not mesh-data assignments.
        for i,slot in enumerate(obj.material_slots):
            if slot.link=='OBJECT' and i<len(mesh.materials):mesh.materials[i]=slot.material
        report=summary(mesh)
        binding={'name':obj.name,'matrix_world':matrix(obj.matrix_world),'frame':bpy.context.scene.frame_current,
                 'subframe':bpy.context.scene.frame_subframe,'mesh':report['mesh_sha256']}
        return obj,mesh,report,digest(binding)
    except BaseException:
        bpy.data.meshes.remove(mesh);raise


def inspect_source(p):
    obj,mesh,report,signature=source_snapshot(p)
    try:return report|{'name':obj.name,'source_sha256':signature,'frame':bpy.context.scene.frame_current,
                       'matrix_world':matrix(obj.matrix_world),'snapshot':('Raw skinned rest data and original linear binding/rig clips; morph weights follow source Key controllers.' if report.get('skin') else 'Raw relative morph basis; source actions/drivers/NLA stay authoritative.' if report.get('morph') else 'Current static viewport evaluation. Materials remain shared; external procedural dependencies are not frozen beyond this evaluated content.')}
    finally:bpy.data.meshes.remove(mesh)


def surface(mesh):
    mesh.calc_loop_triangles();coords=[v.co.copy() for v in mesh.vertices]
    triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
    return BVHTree.FromPolygons(coords,triangles,all_triangles=True),coords


def samples(mesh,count):
    # Deterministic vertex and triangle-center samples cover surfaces without claiming
    # an exhaustive Hausdorff or projected-silhouette bound.
    points=[v.co.copy() for v in mesh.vertices][::max(1,len(mesh.vertices)//max(1,count//2))][:count//2]
    mesh.calc_loop_triangles();triangles=list(mesh.loop_triangles)
    for triangle in triangles[::max(1,len(triangles)//max(1,count-len(points)))][:count-len(points)]:
        a,b,c=triangle.vertices;points.append((mesh.vertices[a].co+mesh.vertices[b].co+mesh.vertices[c].co)/3)
    return points


def quality(base,target,count):
    base_tree,coords=surface(base);target_tree,_=surface(target)
    diagonal=math.sqrt(sum((max(v[i] for v in coords)-min(v[i] for v in coords))**2 for i in range(3)))
    if diagonal<=1e-12:raise ValueError('LOD source bounds are degenerate')
    distances=[]
    for source,tree in ((base,target_tree),(target,base_tree)):
        for point in samples(source,count):
            found=tree.find_nearest(point)
            if found[0] is None:raise ValueError('Could not measure LOD surface error')
            distances.append(found[3])
    return {'sample_count':len(distances),'max_distance':max(distances),'rms_distance':math.sqrt(sum(v*v for v in distances)/len(distances)),
            'source_diagonal':diagonal,'max_relative_error':max(distances)/diagonal,
            'scope':'Deterministic bidirectional raw-vertex/triangle-center samples in asset-local coordinates; not exhaustive silhouette/density or world-scale certification.'}


def native_chain(p):
    bpy.context.view_layer.update()
    collection=bpy.data.collections.get(p['chain'])
    if not collection or not collection.get(META):raise ValueError('Managed LOD chain not found')
    encoded=collection[META]
    if not isinstance(encoded,str) or len(encoded)>2*1024**2:raise ValueError('Invalid LOD metadata')
    meta=json.loads(encoded)
    if meta.get('format') not in {MARKER,'mcpblender-skinned-lod-v1','mcpblender-morph-lod-v1'} or not 2<=len(meta.get('levels',[]))<=8:raise ValueError('Invalid LOD ownership marker')
    root=bpy.data.objects.get(meta['root']);issues=[];records=[];objects=[]
    if not root or root.type!='EMPTY' or root.name not in collection.objects:raise ValueError('LOD root missing or changed')
    if collection.library or collection.override_library or root.library or root.override_library:issues.append('LOD ownership must be local')
    for level in meta['levels']:
        obj=bpy.data.objects.get(level['object'])
        if not obj or obj.type!='MESH':issues.append('LOD object missing or changed');continue
        objects.append(obj)
        if obj.library or obj.override_library or obj.data.library or obj.data.override_library:issues.append('LOD mesh must be local')
        if obj.parent!=root or obj.name not in collection.objects or len(obj.users_collection)!=1:issues.append('LOD hierarchy/collection changed')
        if (obj.modifiers and not meta.get('skin')) or obj.constraints or obj.animation_data or (obj.data.shape_keys and not meta.get('morph')):issues.append('LOD mesh gained procedural deformation')
        if any(max(abs(value[i][j]-(1 if i==j else 0)) for i in range(4) for j in range(4))>1e-6 for value in (obj.matrix_basis,obj.matrix_parent_inverse)):issues.append('LOD relative transform changed')
        report=summary(obj.data)
        if report['mesh_sha256']!=level['mesh_sha256']:issues.append('LOD mesh/material assignments changed')
        if report['triangles']>level['triangle_budget']:issues.append('LOD triangle budget exceeded')
        records.append(level|report|{'hide_viewport':obj.hide_viewport,'hide_render':obj.hide_render})
    if {o.name for o in collection.objects}!={meta['root'],*(l['object'] for l in meta['levels'])}:issues.append('LOD collection contents changed')
    if any(o.name not in {l['object'] for l in meta['levels']} for o in root.children):issues.append('LOD root has external children')
    if meta.get('skin'):
        from .skin_lods import native_checks
        native_checks(root,objects,meta,issues)
    if meta.get('morph'):
        from .morph_lods import native_checks
        native_checks(objects,meta,issues)
    signature=digest({'metadata':meta,'levels':records,'root_matrix':matrix(root.matrix_world),'issues':issues})
    return collection,root,objects,meta,records,issues,signature


def inspect_chain(p):
    collection,root,objects,meta,records,issues,signature=native_chain(p)
    source=None
    try:source=inspect_source({'name':meta['source'],'deformation':'SKINNED' if meta.get('skin') else 'MORPH' if meta.get('morph') else 'STATIC'});stale=source['source_sha256']!=meta['source_sha256']
    except (ValueError,RuntimeError):stale=True
    return {'chain':collection.name,'root':root.name,'chain_sha256':signature,'valid':not issues,'issues':sorted(set(issues)),
            'source':meta['source'],'source_stale_or_unavailable':stale,'source_sha256':meta['source_sha256'],'levels':records,'adoption':meta.get('adoption'),
            'deformation':'SKINNED' if meta.get('skin') else 'MORPH' if meta.get('morph') else 'STATIC','skin':meta.get('skin'),'morph':meta.get('morph'),'pose_validation':meta.get('pose_validation'),'skin_profile':meta.get('skin_profile'),
            'pose_validation_inputs_changed':bool((meta.get('skin') or meta.get('morph')) and (source is None or stale or (meta.get('skin') and source['skin']['animation_sha256']!=meta['skin']['animation_sha256']) or (meta.get('morph') and source['morph']['controller_snapshot_sha256']!=meta['morph']['controller_snapshot_sha256']))),
            'note':'Independent mesh data; skin mode follows the original rig and morph mode follows the source Key controller. Source morph geometry/masks must remain intact. Visibility selects representations, not automatic distance switching. Materials remain shared.'}


def guarded(p):
    result=native_chain(p)
    if result[-1]!=p['expected_chain']:raise ValueError('LOD fingerprint is stale; inspect_lod_chain again')
    if result[-2]:raise ValueError('LOD ownership/content validation failed: '+'; '.join(sorted(set(result[-2]))))
    return result


def reduce(obj,base,recipe):
    from .bridge import check_cancelled,report_progress
    mod=obj.modifiers.new('LOD_Reduction','DECIMATE');method=recipe['method'];mod.decimate_type={'COLLAPSE':'COLLAPSE','PLANAR':'DISSOLVE','UNSUBDIVIDE':'UNSUBDIV'}[method]
    if method=='COLLAPSE':
        mod.ratio=min(.999999,recipe['triangle_budget']/base['triangles']);mod.use_collapse_triangulate=True
        if recipe.get('_skin_group'):mod.vertex_group=recipe['_skin_group'];mod.vertex_group_factor=recipe['_skin_factor'];mod.invert_vertex_group=True
    elif method=='PLANAR':mod.angle_limit=math.radians(recipe['angle_degrees']);mod.delimit={'NORMAL','MATERIAL','SEAM','SHARP','UV'};mod.use_dissolve_boundaries=False
    else:mod.iterations=recipe['iterations']
    reduced=None
    for attempt in range(8):
        check_cancelled();bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        candidate=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
        try:
            candidate.calc_loop_triangles();count=len(candidate.loop_triangles)
            report_progress({'phase':'reducing LOD geometry','object':obj.name,'attempt':attempt+1,'triangles':count,'triangle_budget':recipe['triangle_budget']})
            if count<=recipe['triangle_budget']:reduced=candidate;break
            if method!='COLLAPSE':raise ValueError('Reduction strategy did not meet triangle budget; adjust angle/iterations or use COLLAPSE')
            mod.ratio*=.98*recipe['triangle_budget']/count
        finally:
            if candidate!=reduced:bpy.data.meshes.remove(candidate)
    if reduced is None:raise ValueError(f'Collapse could not satisfy triangle budget: triangles={count}, budget={recipe["triangle_budget"]}, ratio={mod.ratio:.6g}')
    obj.modifiers.remove(mod);obj.data=reduced
    return reduced


def generate(p,adoption=None):
    from .bridge import check_cancelled,report_progress
    source,base,base_report,signature=source_snapshot(p);collection=None;root=None;created=[];meshes=[base];success=False
    try:
        if signature!=p['expected_source']:raise ValueError('LOD source fingerprint is stale; inspect_lod_source again')
        if p['levels'][0]['triangle_budget']>=base_report['triangles']:raise ValueError('First reduced budget must be below source triangles')
        names=[f"{p['chain']}_LOD{i}" for i in range(len(p['levels'])+1)];root_name=p['chain']+'_Root'
        if bpy.data.collections.get(p['chain']) or any(n in bpy.data.objects for n in names+[root_name]):raise ValueError('LOD chain/objects already exist; choose a fresh chain name')
        check_cancelled();collection=bpy.data.collections.new(p['chain']);bpy.context.scene.collection.children.link(collection)
        if collection.name!=p['chain']:raise ValueError('Native collection name changed unexpectedly')
        root=bpy.data.objects.new(root_name,None);created.append(root);collection.objects.link(root);root.matrix_world=source.matrix_world.copy()
        if base_report.get('skin'):
            from . import skin_lods
            skin_lods.setup_root(root,source)
        records=[];previous=base_report['triangles']+1
        for i,name in enumerate(names):
            check_cancelled();mesh=base if i==0 else adoption['meshes'][i-1] if adoption else base.copy()
            if i:meshes.append(mesh)
            obj=bpy.data.objects.new(name,mesh);created.append(obj);collection.objects.link(obj);obj.parent=root;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
            if obj.name!=name:raise ValueError('Native LOD object name changed unexpectedly')
            if i and adoption:
                from .lod_adoption import transfer_groups
                transfer_groups(obj,source,base,base_report)
            if base_report.get('skin'):skin_lods.setup_groups(obj,source)
            if i and not adoption:
                recipe=dict(p['levels'][i-1]);protection=None
                if base_report.get('skin') and recipe['method']=='COLLAPSE':
                    protection=skin_lods.protect_joints(obj,source,p)
                    if protection:recipe.update(_skin_group=protection,_skin_factor=p['skin_joint_importance'])
                mesh=reduce(obj,base_report,recipe);meshes.append(mesh)
                if protection:obj.vertex_groups.remove(obj.vertex_groups[protection])
                if p['transfer_normals']:
                    with active_object(obj):
                        mod=obj.modifiers.new('LOD_Normals','DATA_TRANSFER');mod.object=created[1];mod.use_loop_data=True;mod.data_types_loops={'CUSTOM_NORMAL'};mod.loop_mapping='POLYINTERP_NEAREST'
                        finished(bpy.ops.object.modifier_apply(modifier=mod.name))
            report=summary(obj.data)
            if report['triangles']>=previous:raise ValueError('Reduced LODs must actually decrease triangle count')
            previous=report['triangles']
            if report['materials']!=base_report['materials'] or report['uv_maps']!=base_report['uv_maps'] or report['render_uv_map']!=base_report['render_uv_map']:raise ValueError('LOD lost material slots or UV maps')
            if (not adoption or adoption['config']['preserve_material_regions']) and report['used_material_indices']!=base_report['used_material_indices']:raise ValueError('LOD lost used material regions')
            if (not adoption or adoption['config']['preserve_attribute_schema']) and any(a not in report['attributes'] for a in base_report['attributes']):raise ValueError('LOD lost named attribute schema')
            measurement=quality(base,obj.data,p['error_samples']) if i else {'sample_count':0,'max_relative_error':0}
            if measurement['max_relative_error']>p['max_relative_error']:raise ValueError('LOD sampled surface error exceeds max_relative_error')
            if base_report.get('skin'):report['skin_weights']=skin_lods.attach(obj,source,base_report,p,reduced=i!=0)
            records.append(report|{'object':obj.name,'level':i,'triangle_budget':p['levels'][i-1]['triangle_budget'] if i else base_report['triangles'],
                                   'recipe':({'method':'ADOPT','input':adoption['config']['inputs'][i-1]['name']} if adoption else p['levels'][i-1]) if i else {'method':'SNAPSHOT'},'quality':measurement})
            report_progress({'phase':'verified LOD level','level':i,'levels':len(names),'triangles':report['triangles'],'fraction':(i+1)/len(names)})
        if base_report.get('morph'):
            from . import morph_lods
            for i,(obj,record) in enumerate(zip(created[1:],records)):
                record['morph_transfer']=morph_lods.attach(obj,source,i==0)
                record['morph_validation']=morph_lods.measure_keys(source,obj,p)
        poses=None
        if base_report.get('skin'):
            for obj in created[1:]:obj.modifiers[0].show_viewport=True
            poses=skin_lods.measure(source,created[1:],p.get('pose_frames') or base_report['skin']['recommended_pose_frames'],p['error_samples'],p['max_pose_error'])
        elif base_report.get('morph'):
            from .skin_lods import measure
            poses=measure(source,created[1:],p.get('pose_frames') or morph_lods.frames_for(source),p['error_samples'],p['max_pose_error'])
        fresh=inspect_source({'name':source.name,'deformation':p.get('deformation','STATIC')})
        if fresh['source_sha256']!=signature:raise ValueError('Source changed during LOD generation')
        if adoption:adoption['verify']()
        for i,obj in enumerate(created[1:]):obj.hide_viewport=i!=0;obj.hide_render=i!=0
        collection[META]=json.dumps({'format':skin_lods.MARKER if base_report.get('skin') else morph_lods.MARKER if base_report.get('morph') else MARKER,'morph':base_report.get('morph'),'skin':base_report.get('skin'),'pose_validation':poses,'skin_profile':{'max_influences':p['skin_max_influences'],'joint_importance':p['skin_joint_importance']} if base_report.get('skin') else None,'id':uuid.uuid4().hex,'source':source.name,'source_sha256':signature,'root':root.name,
                                    'blender_version':bpy.app.version_string,'generation_recipe':{k:v for k,v in p.items() if k not in {'expected_management','preserve_placement','preserve_visibility'}},'levels':records},sort_keys=True,allow_nan=False)
        if adoption:
            metadata=json.loads(collection[META]);metadata['adoption']={'config':adoption['config'],'source_sha256':adoption['signature'],'inputs':adoption['records']}
            collection[META]=json.dumps(metadata,sort_keys=True,allow_nan=False)
        bpy.context.view_layer.update();check_cancelled();result=inspect_chain({'chain':p['chain']})
        if not result['valid']:raise ValueError('Created LOD chain did not pass ownership validation')
        success=True;return result
    finally:
        if not success:
            for obj in reversed(created):bpy.data.objects.remove(obj,do_unlink=True)
            if collection:bpy.data.collections.remove(collection)
        # Keep consumed temporary copies alive until this boundary, so ownership
        # never depends on dereferencing removed native RNA handles.
        for mesh in meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)


def activate(p):
    from .bridge import check_cancelled
    _,_,objects,meta,_,_,_=guarded(p)
    if p['level']>=len(objects):raise ValueError('LOD level not found')
    saved=[(o,o.hide_viewport,o.hide_render) for o in objects]
    try:
        check_cancelled()
        for i,o in enumerate(objects):o.hide_viewport=i!=p['level'];o.hide_render=i!=p['level']
        bpy.context.view_layer.update();check_cancelled()
    except BaseException:
        for o,a,b in saved:o.hide_viewport=a;o.hide_render=b
        bpy.context.view_layer.update();raise
    return inspect_chain({'chain':p['chain']})


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    from .workflows import export_objects_glb
    _,_,objects,meta,records,_,signature=guarded(p);directory=Path(p['directory'])
    if meta.get('morph'):
        from .morph_lod_export import export as export_morph
        return export_morph(p)
    if p.get('timeline_clips'):raise ValueError('timeline_clips is supported by morph-bearing bundles only')
    if meta.get('skin'):
        from .skin_lod_export import export as export_skin
        return export_skin(p)
    if directory.exists() or directory.is_symlink():raise FileExistsError('LOD output directory already exists')
    estimate=16*1024**2+sum(r['vertices']*128+r['triangles']*16 for r in records)
    images={n.image for obj in objects for mat in obj.data.materials if mat and mat.node_tree for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    estimate+=len(objects)*sum(max(1024,image.size[0]*image.size[1]*8) for image in images)
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
    require_space(directory,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='mesh_and_texture_pixel_heuristic')
    stage=(p['_export_job'].stage if p.get('_export_job') else directory.parent/('.mcpblender-lod-'+uuid.uuid4().hex));saved=[(o,o.hide_viewport,o.hide_render,o.hide_get(),o.hide_select) for o in objects];published=False;stage_created=False
    try:
        check_cancelled();stage.mkdir(mode=0o700);stage_created=True
        if p.get('_export_job'):p['_export_job'].created()
        levels=[]
        for i,(obj,record) in enumerate(zip(objects,records)):
            check_cancelled();obj.hide_viewport=False;obj.hide_render=False;obj.hide_select=False;obj.hide_set(False);bpy.context.view_layer.update()
            path=stage/f'level_{i:02}.glb'
            export_objects_glb({'objects':[obj.name],'path':str(path),'animations':False,'overwrite':False,'apply_modifiers':False})
            parsed=glb_report(path)
            if parsed['triangles']!=record['triangles']:raise ValueError('Exported GLB triangle count differs from native LOD')
            levels.append({'file':path.name,'sha256':file_hash(path),'triangles':record['triangles'],'triangle_budget':record['triangle_budget'],
                           'uv_required':bool(record['uv_maps']),'position_bounds':{'min':[record['local_surface_bounds']['min'][0],record['local_surface_bounds']['min'][2],-record['local_surface_bounds']['max'][1]],
                           'max':[record['local_surface_bounds']['max'][0],record['local_surface_bounds']['max'][2],-record['local_surface_bounds']['min'][1]]},'quality':record['quality'],'glb':parsed})
            report_progress({'phase':'exported and decoded LOD','level':i,'levels':len(objects),'bytes':path.stat().st_size,'fraction':(i+1)/len(objects)})
        for o,a,b,c,d in saved:o.hide_viewport=a;o.hide_render=b;o.hide_select=d;o.hide_set(c)
        bpy.context.view_layer.update()
        if native_chain(p)[-1]!=signature:raise ValueError('LOD chain changed during export')
        doc={'format':MARKER,'chain':p['chain'],'chain_sha256':signature,'source_sha256':meta['source_sha256'],'blender_version':bpy.app.version_string,
             'levels':levels,'switching':'Separate static representations. Runtime distance switching is a downstream choice.'}
        (stage/'manifest.json').write_text(json.dumps(doc,indent=2,allow_nan=False)+'\n')
        verified=validate(stage);check_cancelled()
        if directory.exists():raise FileExistsError(directory)
        if p.get('_export_job'):p['_export_job'].verify();check_cancelled()
        stage.rename(directory);published=True
        return verified|{'directory':str(directory),'path':str(directory/'manifest.json'),'estimated_bytes':estimate,'files':[str(directory/l['file']) for l in levels]}
    finally:
        for o,a,b,c,d in saved:o.hide_viewport=a;o.hide_render=b;o.hide_select=d;o.hide_set(c)
        bpy.context.view_layer.update()
        if stage_created and not published and stage.exists():shutil.rmtree(stage)


def dispatch(command,p):
    if command=='inspect_glb_deformation':
        from mcpblender.skin_glb import inspect_file
        from .bridge import check_cancelled,report_progress
        return inspect_file(p,check_cancelled=check_cancelled,progress=report_progress)
    if command=='inspect_lod_export':
        from .skin_lod_export import plan
        return plan(p)
    if command=='sample_lod_chain':
        if native_chain(p)[3].get('morph'):
            from .morph_lods import sample
            return sample(p)
        from .skin_lods import sample
        return sample(p)
    if command=='inspect_lod_source':return inspect_source(p)
    if command=='generate_lod_chain':return generate(p)
    if command=='inspect_lod_chain':return inspect_chain(p)
    if command=='activate_lod_level':return activate(p)
    if command=='export_lod_chain':return export(p)
    return validate(p['directory'])
