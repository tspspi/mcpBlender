"""Guarded LOD inventory, shared-data-preserving removal and staged replacement."""
import json
import math
import uuid

import bpy

from . import lods,assemblies
from mcpblender.lod_recipe import suggested_recipe

COMMANDS={'configure_lod_source_visibility','inspect_lod_management','remove_lod_chain','rebuild_lod_chain'}


def finite_state(value):
    if isinstance(value,float) and not math.isfinite(value):return {'nonfinite':repr(value)}
    if isinstance(value,dict):return {k:finite_state(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [finite_state(v) for v in value]
    return value


def parents(collection):
    return [scene.collection for scene in bpy.data.scenes if collection.name in scene.collection.children]+[c for c in bpy.data.collections if collection.name in c.children]


def flags(obj):
    return {k:getattr(obj,k) for k in ('hide_render','hide_viewport','hide_select','display_type',
                                       'visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow')}


def inventory(p):
    collection=bpy.data.collections.get(p['chain'])
    if collection is None:raise ValueError('Managed LOD chain not found')
    text=collection.get(lods.META)
    if not isinstance(text,str) or len(text)>2*1024**2:raise ValueError('Invalid LOD ownership metadata')
    meta=json.loads(text)
    if not isinstance(meta,dict) or meta.get('format') not in {lods.MARKER,'mcpblender-skinned-lod-v1','mcpblender-morph-lod-v1'} or not isinstance(meta.get('levels'),list) or not 2<=len(meta['levels'])<=8:raise ValueError('Invalid LOD ownership marker')
    names=[m['object'] for m in meta['levels']];root_name=meta['root']
    if not all(isinstance(n,str) and n for n in [root_name,*names]) or len({root_name,*names})!=len(names)+1:raise ValueError('Invalid LOD member inventory')
    if not isinstance(meta.get('source'),str) or not meta['source'] or meta['source'] in {root_name,*names}:raise ValueError('LOD source cannot be owned chain content')
    root=bpy.data.objects.get(root_name);levels=[bpy.data.objects.get(n) for n in names];objects=[o for o in [root,*levels] if o]
    owned=set(objects);blockers=[];preserved=[];deletable=[];links=parents(collection);users=bpy.data.user_map()
    if collection.library or collection.override_library:blockers.append('LOD collection must be local')
    if collection.children or {o.name for o in collection.objects}!={root_name,*names}:blockers.append('LOD collection membership/hierarchy changed')
    if not root or root.type!='EMPTY' or any(not o or o.type!='MESH' for o in levels):blockers.append('LOD root/mesh inventory is missing or changed')
    if not links:blockers.append('LOD collection is not linked into a scene/collection')
    if any(parent.library or parent.override_library for parent in links):blockers.append('LOD parent collection links must be local and unoverridden')
    if any(parent.get(assemblies.META) for parent in links):blockers.append('LOD collection is inside a managed assembly')
    external_collection=[u for u in users.get(collection,set()) if not isinstance(u,(bpy.types.Scene,bpy.types.Collection))]
    if external_collection:blockers.append('LOD collection has external native references')
    for obj in objects:
        if obj.library or obj.override_library:blockers.append('LOD object must be local: '+obj.name)
        if set(obj.users_collection)!={collection}:blockers.append('LOD object has foreign collection membership: '+obj.name)
        if obj.rigid_body:blockers.append('Detach rigid-body physics before LOD management: '+obj.name)
        external=[u for u in users.get(obj,set()) if u not in owned and u!=collection and not isinstance(u,bpy.types.Scene)]
        if external:blockers.append('LOD object has external native references: '+obj.name)
    meshes={o.data for o in levels if o and o.type=='MESH'}
    for mesh in meshes:
        if mesh.library or mesh.override_library or mesh.use_fake_user or any(u not in owned for u in users.get(mesh,set())):
            preserved.append(mesh.name);continue
        deletable.append(mesh)
        key=mesh.shape_keys
        if key:
            if any(u!=mesh and u not in owned for u in users.get(key,set())):blockers.append('LOD shape-key data has external references: '+key.name)
            elif key.library or key.override_library or key.use_fake_user:blockers.append('LOD shape-key persistence/ownership prevents deletion: '+key.name)
            else:deletable.append(key)
    native=None;content_issues=[]
    try:native=lods.inspect_chain(p);content_issues=native['issues']
    except (ValueError,RuntimeError,ReferenceError,KeyError,TypeError) as exc:content_issues=[str(exc)]
    deformation='SKINNED' if meta.get('skin') else 'MORPH' if meta.get('morph') else 'STATIC'
    source=None;source_error=None;suggested=None
    try:
        source=lods.inspect_source({'name':meta['source'],'deformation':deformation})
        recipe=meta.get('generation_recipe')
        if not recipe:
            recipe={'levels':[{k:v for k,v in level['recipe'].items() if k in {'triangle_budget','method','angle_degrees','iterations'}} for level in meta['levels'][1:]]}
            profile=meta.get('skin_profile') or {}
            if 'max_influences' in profile:recipe['skin_max_influences']=profile['max_influences']
            if 'joint_importance' in profile:recipe['skin_joint_importance']=profile['joint_importance']
        suggested=suggested_recipe(recipe|{'name':meta['source'],'chain':collection.name,'deformation':deformation,'expected_source':source['source_sha256']})
    except (ValueError,RuntimeError,ReferenceError,KeyError,TypeError) as exc:source_error=str(exc)
    records=[]
    for obj in objects:
        records.append({'id':obj.as_pointer(),'native':assemblies.record(obj),'collections':sorted(c.name for c in obj.users_collection),
                        'flags':flags(obj),'hidden_in_view_layer':obj.hide_get() if bpy.context.view_layer.objects.get(obj.name)==obj else None,
                        'users':sorted((type(u).__name__,u.name) for u in users.get(obj,set()))})
    for mesh in meshes:
        records.append({'id':mesh.as_pointer(),'native':assemblies.record(mesh),'users':sorted((type(u).__name__,u.name) for u in users.get(mesh,set())),
                        'key':assemblies.record(mesh.shape_keys) if mesh.shape_keys else None,
                        'key_users':sorted((type(u).__name__,u.name) for u in users.get(mesh.shape_keys,set())) if mesh.shape_keys else []})
    source_obj=bpy.data.objects.get(meta['source'])
    source_visibility={'hide_viewport':source_obj.hide_viewport,'hide_render':source_obj.hide_render,'scenes':sorted(scene.name for scene in source_obj.users_scene)} if source_obj else None
    state=finite_state({'source_visibility':source_visibility,'source_id':source_obj.as_pointer() if source_obj else None,'metadata':meta,'records':records,'parents':sorted((c.as_pointer(),type(c).__name__,c.name) for c in links),
                        'collection_flags':{'hide_viewport':collection.hide_viewport,'hide_render':collection.hide_render},
                        'collection_users':sorted((type(u).__name__,u.name) for u in users.get(collection,set())),
                        'source':source['source_sha256'] if source else None,'blockers':sorted(set(blockers))})
    signature=lods.digest(state)
    root_anim=root.animation_data if root else None
    rebuild_blockers=['LOD root has authored instancing/constraints/animation that replacement cannot preserve'] if root and (root.instance_type!='NONE' or root.constraints or root_anim and (root_anim.action or root_anim.drivers or root_anim.nla_tracks)) else []
    report={'chain':collection.name,'id':meta.get('id'),'management_sha256':signature,'can_remove':not blockers,
            'can_rebuild':not blockers and not rebuild_blockers and suggested is not None,'rebuild_blockers':rebuild_blockers,'blockers':sorted(set(blockers)),'content_issues':content_issues,
            'source':meta['source'],'source_visibility':source_visibility,'source_error':source_error,'source_sha256':source['source_sha256'] if source else None,
            'source_stale_or_unavailable':source is None or source['source_sha256']!=meta['source_sha256'],
            'preserved_shared_meshes':sorted(preserved),'suggested_rebuild':suggested,'adoption':meta.get('adoption'),
            'note':'Native ID references and membership are checked. Shared/fake-user meshes remain; materials, source meshes, rigs and clips are not purged. String-name references in scripts/recipes cannot be inferred. Legacy recipes without recorded generation settings use explicit defaults.'}
    return collection,root,levels,meta,deletable,links,report


def guarded(p):
    result=inventory(p)
    if result[-1]['management_sha256']!=p['expected_management']:raise ValueError('LOD management fingerprint is stale; inspect_lod_management again')
    if result[-1]['blockers']:raise ValueError('; '.join(result[-1]['blockers']))
    return result


def remove(p):
    from .bridge import check_cancelled
    collection,root,levels,meta,data,_,report=guarded(p)
    result={'removed':collection.name,'source_preserved':meta['source'],'preserved_shared_meshes':report['preserved_shared_meshes'],
            'removed_objects':[o.name for o in [root,*levels]]}
    check_cancelled()
    # Final noninterruptible native deletion: all refusals/checks precede it.
    bpy.data.batch_remove(ids=tuple({collection,root,*levels,*data}))
    return result



def source_visibility(p):
    from .bridge import check_cancelled
    from .assets import local_object
    from .domains import curves
    state=inventory(p)[-1]
    if state['management_sha256']!=p['expected_management']:raise ValueError('LOD management fingerprint is stale; inspect_lod_management again')
    obj=local_object(state['source']);changes={k:p[k] for k in ('hide_viewport','hide_render') if p.get(k) is not None}
    anim=obj.animation_data;paths=set()
    if anim:
        paths.update(c.data_path for c in anim.drivers)
        actions=[(anim.action,getattr(anim,'action_slot',None))] if anim.action else []
        actions.extend((strip.action,getattr(strip,'action_slot',None)) for track in anim.nla_tracks for strip in track.strips if strip.action)
        for action,slot in actions:paths.update(c.data_path for c in curves(action,slot))
    if paths.intersection(changes):raise ValueError('Targeted source visibility is keyed/driven; edit its animation explicitly')
    original={k:getattr(obj,k) for k in changes};selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    try:
        check_cancelled()
        for k,v in changes.items():setattr(obj,k,v)
        bpy.context.view_layer.update();check_cancelled();return inventory(p)[-1]
    except BaseException:
        for k,v in original.items():setattr(obj,k,v)
        bpy.context.view_layer.update()
        for selected_obj in selected:
            if bpy.context.view_layer.objects.get(selected_obj.name)==selected_obj and selected_obj.visible_get():selected_obj.select_set(True)
        if active and bpy.context.view_layer.objects.get(active.name)==active:bpy.context.view_layer.objects.active=active
        raise

def remap(value,names):
    if isinstance(value,dict):return {k:names.get(v,v) if k in {'object','root','chain'} and isinstance(v,str) else remap(v,names) for k,v in value.items()}
    if isinstance(value,list):return [remap(v,names) for v in value]
    return value


def rebuild(p,generator=None):
    from .bridge import check_cancelled,report_progress
    collection,root,levels,meta,data,links,report=guarded(p)
    if report['rebuild_blockers']:raise ValueError('; '.join(report['rebuild_blockers']))
    if p['name'] in {root.name,*(o.name for o in levels)}:raise ValueError('Rebuild source cannot be a replaced LOD object')
    if any(i['name'] in {root.name,*(o.name for o in levels)} for i in p.get('inputs',[])):raise ValueError('Adoption inputs cannot belong to the replaced LOD chain')
    before=set(bpy.data.user_map());old_names=[(collection,collection.name),(root,root.name),*((o,o.name) for o in levels)]
    old_flags=[flags(o) for o in [root,*levels]];old_hidden=[o.hide_get() if bpy.context.view_layer.objects.get(o.name)==o else None for o in [root,*levels]]
    selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    stage=None;new_names=[];success=False
    try:
        stage_name='mcp_LOD_rebuild_'+uuid.uuid4().hex[:16]
        if stage_name in bpy.data.collections:raise ValueError('Private rebuild collection name collision')
        generated=(generator or lods.generate)(p|{'chain':stage_name})
        stage=bpy.data.collections[generated['chain']];new_root=bpy.data.objects[generated['root']];new_levels=[bpy.data.objects[r['object']] for r in generated['levels']]
        new_meta=json.loads(stage[lods.META]);new_names=[(stage,stage.name),(new_root,new_root.name),*((o,o.name) for o in new_levels)]
        if p.get('preserve_placement',True):
            if new_meta.get('skin'):
                if any(abs(root.matrix_world[i][j]-new_root.matrix_world[i][j])>1e-6 for i in range(4) for j in range(4)):raise ValueError('Preserving placement conflicts with new rig binding; use preserve_placement=false explicitly')
            else:
                new_root.parent=root.parent;new_root.parent_type=root.parent_type;new_root.parent_bone=root.parent_bone;new_root.parent_vertices=tuple(root.parent_vertices)
                new_root.matrix_parent_inverse=root.matrix_parent_inverse.copy();new_root.matrix_basis=root.matrix_basis.copy()
        if inventory({'chain':collection.name})[-1]['management_sha256']!=p['expected_management']:raise ValueError('Original LOD chain changed during replacement generation')
        report_progress({'phase':'verified replacement before LOD handoff','chain':p['chain'],'levels':len(new_levels)});check_cancelled()
        token=uuid.uuid4().hex[:16]
        for i,(item,_) in enumerate(old_names):item.name=f'mcp_LOD_old_{token}_{i}'
        public_names={new_root.name:old_names[1][1]}|{o.name:(old_names[i+2][1] if i<len(levels) else f"{p['chain']}_LOD{i}") for i,o in enumerate(new_levels)}
        stage.name=p['chain'];new_root.name=public_names[new_root.name]
        for obj in new_levels:obj.name=public_names[obj.name]
        new_meta=remap(new_meta,public_names|{stage_name:p['chain']})
        new_meta['rebuild_of']=meta.get('id');stage[lods.META]=json.dumps(new_meta,sort_keys=True,allow_nan=False)
        for parent in parents(stage):parent.children.unlink(stage)
        for parent in links:parent.children.link(stage)
        if p.get('preserve_visibility',True):
            stage.hide_render=collection.hide_render;stage.hide_viewport=collection.hide_viewport
            for i,obj in enumerate([new_root,*new_levels]):
                if i<len(old_flags):
                    for key,value in old_flags[i].items():setattr(obj,key,value)
        bpy.context.view_layer.update()
        if p.get('preserve_visibility',True):
            for i,obj in enumerate([new_root,*new_levels]):
                if i<len(old_hidden) and old_hidden[i] is not None and bpy.context.view_layer.objects.get(obj.name)==obj:obj.hide_set(old_hidden[i])
        if p.get('preserve_visibility',True):
            for key in ('hide_viewport','hide_render'):
                visible=[i for i,o in enumerate(levels) if not old_flags[i+1][key]]
                if visible and all(getattr(o,key) for o in new_levels):setattr(new_levels[min(visible[0],len(new_levels)-1)],key,False)
        if p.get('preserve_placement',True) and any(abs(root.matrix_world[i][j]-new_root.matrix_world[i][j])>1e-6+abs(root.matrix_world[i][j])*1e-7 for i in range(4) for j in range(4)):raise ValueError('Replacement could not preserve root world placement')
        result=lods.inspect_chain({'chain':p['chain']})
        if not result['valid'] or result['source_stale_or_unavailable']:raise ValueError('Replacement LOD verification failed')
        replacements={root:new_root}|{old:new for old,new in zip(levels,new_levels)}
        next_selected=[replacements.get(o,o) for o in selected if o not in levels[len(new_levels):]]
        next_active=replacements.get(active,active) if active not in levels[len(new_levels):] else None
        result=result|{'replaced_id':meta.get('id'),'preserved_shared_meshes':report['preserved_shared_meshes']}
        for obj in next_selected:
            if bpy.context.view_layer.objects.get(obj.name)==obj and obj.visible_get() and not obj.hide_select:obj.select_set(True)
        if next_active and bpy.context.view_layer.objects.get(next_active.name)==next_active:bpy.context.view_layer.objects.active=next_active
        report_progress({'phase':'verified LOD handoff before deletion','chain':p['chain'],'levels':len(new_levels)});check_cancelled()
        bpy.data.batch_remove(ids=tuple({collection,root,*levels,*data}))
        success=True;return result
    finally:
        if not success:
            # Free the public slots before restoring the original IDs/names.
            for item,name in new_names:item.name=name
            for item,name in old_names:item.name=name
            created=set(bpy.data.user_map())-before
            if created:bpy.data.batch_remove(ids=tuple(created))
            bpy.context.view_layer.update()
            for obj in selected:
                if bpy.context.view_layer.objects.get(obj.name)==obj and obj.visible_get() and not obj.hide_select:obj.select_set(True)
            if active and bpy.context.view_layer.objects.get(active.name)==active:bpy.context.view_layer.objects.active=active


def dispatch(command,p):
    if command=='inspect_lod_management':return inventory(p)[-1]
    if command=='remove_lod_chain':return remove(p)
    if command=='configure_lod_source_visibility':return source_visibility(p)
    return rebuild(p)
