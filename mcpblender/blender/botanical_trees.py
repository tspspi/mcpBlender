"""Managed woody botanical masters; canonical model is independent of bpy."""
import json
import math
import os
import tempfile
from pathlib import Path
import uuid

import bpy
from mathutils import Vector

from mcpblender import botany
from mcpblender.storage import require_space
from . import assemblies,assembly_realization as realization,lods
from .lod_management import parents,flags

COMMANDS={'botanical_species_catalog','plan_botanical_tree','create_botanical_tree','inspect_botanical_tree',
 'list_botanical_elements','regenerate_botanical_tree','remove_botanical_tree','export_botanical_model'}
META='mcpblender_botanical_tree'
MODEL='mcpblender_botanical_model'
MARKER='mcpblender-botanical-master-v1'


def build_model(p):
    from .bridge import check_cancelled,report_progress
    # Pure growth checks are frequent; avoid an RPC for every candidate point.
    ticks=[0]
    def cancelled():
        ticks[0]+=1
        if ticks[0]%256==0:check_cancelled()
    check_cancelled();return botany.generate(p['recipe'],progress=report_progress,cancelled=cancelled)


def plan(p):
    model=build_model(p)
    return {'model_sha256':botany.digest(model),'generator':model['generator'],'recipe':model['recipe'],
            'metrics':botany.metrics(model),'crown':model['crown'],'scope':model['scope'],
            'geometry_scope':'Woody centerlines and bud anchors. No foliage/leaf coverage, wind motion, unioned branch junctions or engine export qualification.'}


def frame(direction,previous=None):
    tangent=Vector(direction).normalized()
    if previous is None:
        reference=Vector((1,0,0)) if abs(tangent.x)<.9 else Vector((0,1,0))
        normal=(reference-tangent*reference.dot(tangent)).normalized()
    else:
        normal=previous-tangent*previous.dot(tangent)
        if normal.length<1e-8:return frame(direction)
        normal.normalize()
    return normal,tangent.cross(normal).normalized()


def attribute(mesh,name,kind,values):
    item=mesh.attributes.new(name=name,type=kind,domain='POINT')
    if kind=='FLOAT_VECTOR':item.data.foreach_set('vector',[x for v in values for x in v])
    else:item.data.foreach_set('value',values)


def wood_mesh(model,p):
    from .bridge import check_cancelled,report_progress
    sides=p['radial_sides'];vertices=[];faces=[];face_uv=[];indices=[];branches=model['branches'];ends={};axis_lengths={};frames={}
    lookup={b['id']:b for b in branches}
    def ring(center,radius,normal,binormal,index,flare=False):
        ids=[]
        for j in range(sides):
            angle=2*math.pi*j/sides;factor=1+(.1*math.cos(5*angle+model['recipe']['seed']) if flare else 0)
            ids.append(len(vertices));vertices.append(Vector(center)+radius*factor*(normal*math.cos(angle)+binormal*math.sin(angle)));indices.append(index)
        return ids
    for i,b in enumerate(branches):
        if i%64==0:check_cancelled();report_progress({'phase':'meshing botanical wood','branches':i,'total_branches':len(branches)})
        direction=Vector(b['end'])-Vector(b['start']);normal,binormal=frame(direction,frames.get(b['axis_id']))
        parent=lookup.get(b['parent_id']);same_axis=parent and parent['axis_id']==b['axis_id']
        if same_axis:start_ring=ends[parent['id']]
        else:
            center=Vector(b['start'])
            if parent:center-=direction.normalized()*parent['radius_end']*.25
            if parent is None:normal,binormal=Vector((1,0,0)),Vector((0,1,0))
            start_ring=ring(center,b['radius_start'],normal,binormal,i,parent is None)
        v0=axis_lengths.get(b['parent_id'],0.) if same_axis else 0.
        v1=v0+direction.length/p['bark_tile_length'];axis_lengths[b['id']]=v1
        normal,binormal=frame(direction,normal);end_ring=ring(b['end'],b['radius_end'],normal,binormal,i)
        for j in range(sides):
            k=(j+1)%sides;faces.append((start_ring[j],start_ring[k],end_ring[k],end_ring[j]));face_uv.append(((j/sides,v0),((j+1)/sides,v0),((j+1)/sides,v1),(j/sides,v1)))
        if not same_axis:
            faces.append(tuple(reversed(start_ring)));face_uv.append(tuple((.5+.5*math.cos(2*math.pi*j/sides),.5+.5*math.sin(2*math.pi*j/sides)) for j in reversed(range(sides))))
        ends[b['id']]=end_ring;frames[b['axis_id']]=normal
    continued={b['parent_id'] for b in branches if b['parent_id'] and lookup[b['parent_id']]['axis_id']==b['axis_id']}
    for b in branches:
        if b['id'] not in continued:
            faces.append(tuple(ends[b['id']]));face_uv.append(tuple((.5+.5*math.cos(2*math.pi*j/sides),.5+.5*math.sin(2*math.pi*j/sides)) for j in range(sides)))
    mesh=bpy.data.meshes.new(p['collection']+'_WoodMesh')
    try:
        mesh.from_pydata(vertices,[],faces);mesh.update()
        layer=mesh.uv_layers.new(name='BarkUV')
        for polygon,coords in zip(mesh.polygons,face_uv):
            polygon.use_smooth=polygon.loop_total==4
            for loop,value in zip(polygon.loop_indices,coords):layer.data[loop].uv=value
        attribute(mesh,'bot_branch_index','INT',indices)
        for name,key in (('bot_branch_order','order'),('bot_age','age_years'),('branch_stiffness','stiffness'),('branch_phase','phase')):
            attribute(mesh,name,'INT' if key=='order' else 'FLOAT',[branches[i][key] for i in indices])
        attribute(mesh,'branch_anchor','FLOAT_VECTOR',[branches[i]['anchor'] for i in indices])
        attribute(mesh,'bend_weight','FLOAT',[min(1,max(0,v.z/model['recipe']['height'])) for v in vertices])
        return mesh
    except BaseException:bpy.data.meshes.remove(mesh);raise


def create(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for botanical creation')
    model=build_model(p)
    if botany.digest(model)!=p['expected_model']:raise ValueError('Botanical model guard is stale; plan_botanical_tree with the same recipe')
    name=p['collection'];names=[name+'_Root',name+'_Wood',name+'_Buds'];text_name=name+'_Model.json'
    if bpy.data.collections.get(name) or any(n in bpy.data.objects for n in names) or bpy.data.texts.get(text_name):raise ValueError('Botanical names already exist; choose a fresh collection')
    before=set(bpy.data.user_map());success=False
    try:
        check_cancelled();collection=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(collection)
        root=bpy.data.objects.new(names[0],None);collection.objects.link(root);root.location=p['location'];root.scale=(1/bpy.context.scene.unit_settings.scale_length,)*3
        text=bpy.data.texts.new(text_name);text.write(json.dumps(model,sort_keys=True,separators=(',',':'),allow_nan=False));text.use_module=False;text.use_fake_user=False;collection[MODEL]=text
        mesh=wood_mesh(model,p);wood=bpy.data.objects.new(names[1],mesh);collection.objects.link(wood);wood.parent=root
        if p.get('bark_material'):
            mat=bpy.data.materials.get(p['bark_material'])
            if mat is None:raise ValueError('Bark material not found')
        else:
            mat=bpy.data.materials.new(name+'_Bark');mat.use_nodes=True
            shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.12,.065,.027,1);shader.inputs['Roughness'].default_value=.85
        mesh.materials.append(mat)
        buds_mesh=bpy.data.meshes.new(name+'_BudPoints');buds_mesh.from_pydata([o['position'] for o in model['organs']],[],[]);buds_mesh.update()
        bud_lookup={b['id']:i for i,b in enumerate(model['branches'])}
        attribute(buds_mesh,'bot_branch_index','INT',[bud_lookup[o['parent_id']] for o in model['organs']]);attribute(buds_mesh,'bud_direction','FLOAT_VECTOR',[o['direction'] for o in model['organs']])
        buds=bpy.data.objects.new(names[2],buds_mesh);collection.objects.link(buds);buds.parent=root;buds.hide_render=True;buds.hide_viewport=True
        meta={'format':MARKER,'id':uuid.uuid4().hex,'model_sha256':p['expected_model'],'model_text':text.name,'root':root.name,
              'members':[{'role':role,'object':o.name,'mesh_sha256':botany.digest(realization.mesh_record(o.data))} for role,o in (('WOOD',wood),('BUDS',buds))],
              'geometry':{'radial_sides':p['radial_sides'],'bark_tile_length':p['bark_tile_length'],'bark_material':mat.name,'junctions':'OVERLAPPING_SLEEVES','units':'METRE_LOCAL'},
              'blender_version':bpy.app.version_string}
        if p.get('foliage'):
            from .botanical_foliage import create_component
            meta['foliage']=create_component(name,collection,root,model,p['foliage'],mat,p.get('_foliage_material'))
        collection[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        bpy.context.view_layer.update();report_progress({'phase':'verified botanical master','branches':len(model['branches'])});check_cancelled()
        result=inspect({'collection':name})
        if not result['valid']:raise ValueError('Botanical master did not pass content validation: '+'; '.join(result['issues']+result['ownership_blockers']))
        success=True;return result
    finally:
        if not success:
            created=set(bpy.data.user_map())-before
            if created:bpy.data.batch_remove(ids=tuple(created))


def inventory(p):
    col=bpy.data.collections.get(p['collection'])
    if col is None:raise ValueError('Botanical collection not found')
    raw=col.get(META)
    if not isinstance(raw,str) or len(raw)>1024**2:raise ValueError('Invalid botanical ownership metadata')
    meta=json.loads(raw)
    if meta.get('format')!=MARKER or not isinstance(meta.get('members'),list) or len(meta['members'])!=2:raise ValueError('Invalid botanical ownership inventory')
    root=bpy.data.objects.get(meta.get('root'));text=col.get(MODEL);members=[bpy.data.objects.get(m['object']) for m in meta['members']]
    if not root or root.type!='EMPTY' or not isinstance(text,bpy.types.Text) or text.name!=meta['model_text'] or any(not o or o.type!='MESH' for o in members):raise ValueError('Botanical owned IDs are missing/changed')
    owned={col,root,text,*members,*(o.data for o in members)};users=bpy.data.user_map();links=parents(col);blockers=[];issues=[]
    foliage_report=None;fol_roles={};fol_model_error=None
    if meta.get('foliage'):
        from .botanical_foliage import component
        fol_roles,fol_issues,fol_blockers,fol_model_error=component(col,root,meta['foliage']);owned.update(fol_roles.values());issues.extend(fol_issues);blockers.extend(fol_blockers);foliage_report=meta['foliage']
    if set(col.children)!=({fol_roles['fc']} if fol_roles else set()) or set(col.objects)!={root,*members}:blockers.append('Botanical collection membership changed')
    if any(o.parent!=root or len(o.users_collection)!=1 for o in members) or len(root.users_collection)!=1 or set(root.children)!=set(members)|({fol_roles['po'],fol_roles['so']} if fol_roles else set()):blockers.append('Botanical hierarchy/links changed')
    for item in owned:
        if item.library or item.override_library or item.use_fake_user:blockers.append('Botanical ownership is linked/overridden/persistent: '+item.name)
        external=[u for u in users.get(item,set()) if u not in owned and not (item==col and (u in links or isinstance(u,bpy.types.Scene))) and not (isinstance(item,(bpy.types.Object,bpy.types.Collection)) and isinstance(u,bpy.types.Scene))]
        if external:blockers.append('External native reference: '+item.name)
    if any(c.library or c.override_library for c in links):blockers.append('Botanical parent collection is not editable')
    records=[]
    for entry,obj in zip(meta['members'],members):
        unsupported=[a.name for a in obj.data.attributes if a.data_type=='STRING'];record=realization.mesh_record(obj.data)
        if botany.digest(record)!=entry['mesh_sha256'] or unsupported:issues.append('Derived mesh content changed: '+obj.name)
        if obj.modifiers or obj.constraints or obj.animation_data or obj.data.animation_data or obj.data.shape_keys:issues.append('Derived object gained deformation: '+obj.name)
        if obj.data.shape_keys or obj.rigid_body or obj.rigid_body_constraint:blockers.append('Derived controls/physics prevent owned removal: '+obj.name)
        if any(max(abs(m[i][j]-(i==j)) for i in range(4) for j in range(4))>1e-6 for m in (obj.matrix_basis,obj.matrix_parent_inverse)):issues.append('Derived relative transform changed: '+obj.name)
        records.append({'role':entry['role'],'record':record,'native':assemblies.record(obj),'unsupported_attributes':unsupported})
    content=text.as_string()
    if len(content)>8*1024**2:raise ValueError('Botanical model text exceeds profile limit')
    model=None;model_error=None
    try:
        model=json.loads(content);botany.validate(model)
        if botany.digest(model)!=meta['model_sha256']:raise ValueError('Canonical botanical model was edited')
    except (ValueError,TypeError,KeyError) as exc:model_error=str(exc);issues.append(model_error)
    if root.rigid_body or root.rigid_body_constraint:blockers.append('Root physics prevents owned removal')
    root_blockers=[fol_model_error] if fol_model_error else []
    if root.instance_type!='NONE' or root.constraints or root.animation_data or root.rigid_body or root.rigid_body_constraint:root_blockers.append('Root instancing/animation/constraints/physics prevent replacement')
    state={'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'meta':meta,'root':assemblies.record(root),'native_ids':sorted((type(i).__name__,i.name,i.as_pointer()) for i in owned),
           'foliage':foliage_report,'records':records,'local_hidden':[(o.name,o.hide_get() if bpy.context.view_layer.objects.get(o.name)==o else None) for o in [root,*members]],'model_content_sha256':botany.digest(content),'users':sorted((item.name,[(type(u).__name__,u.name) for u in sorted(users.get(item,set()),key=lambda u:(type(u).__name__,u.name))]) for item in owned),
           'collection_flags':{'hide_viewport':col.hide_viewport,'hide_render':col.hide_render},'blockers':sorted(set(blockers)),'issues':sorted(set(issues))}
    report={'collection':col.name,'id':meta['id'],'root':root.name,'model_text':text.name,'model_sha256':meta['model_sha256'],'tree_sha256':botany.digest(state),
            'valid':not issues and not blockers,'issues':sorted(set(issues)),'ownership_blockers':sorted(set(blockers)),'replacement_blockers':root_blockers,
            'can_remove':not blockers,'can_regenerate':not blockers and not root_blockers and not issues,'model_error':model_error,
            'foliage':foliage_report,'geometry':meta['geometry'],'root_world_matrix':lods.matrix(root.matrix_world),'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'members':[{'role':e['role'],'object':o.name,'mesh':r['record']} for e,o,r in zip(meta['members'],members,records)],
            'metrics':botany.metrics(model) if model is not None and not model_error else None,'recipe':model['recipe'] if model is not None and not model_error else None,
            'scope':'Owned woody mesh and semantic bud points; materials remain shared. Sleeve junctions intersect but are not welded/unioned. Attributes are native semantic inputs, not qualified wind animation/export packing.'}
    return col,root,members,text,owned,links,model,report


def inspect(p):return inventory(p)[-1]
def guarded(p):
    values=inventory(p);report=values[-1]
    if report['tree_sha256']!=p['expected_tree']:raise ValueError('Botanical tree fingerprint is stale; inspect_botanical_tree again')
    if report['ownership_blockers']:raise ValueError('; '.join(report['ownership_blockers']))
    return values


def remove(p):
    from .bridge import check_cancelled
    values=guarded(p);report=values[-1];check_cancelled();bpy.data.batch_remove(ids=tuple(values[4]))
    return {'removed':p['collection'],'materials_preserved':True,'id':report['id']}


def regenerate(p):
    from .bridge import check_cancelled,report_progress
    col,root,objects,text,owned,links,model,state=guarded(p)
    if state['replacement_blockers'] or state['model_error']:raise ValueError('Cannot regenerate root controls or edited/invalid canonical model')
    if state['issues'] and not p['discard_derived_edits']:raise ValueError('Derived edits require discard_derived_edits=true explicitly')
    old_meta=json.loads(col[META]);old_fol=old_meta.get('foliage')
    from . import botanical_foliage as fol
    def role_map(c,r,obs,t,metadata):
        result=dict(zip(('c','r','w','b','t','wm','bm'),[c,r,*obs,t,*(o.data for o in obs)]))
        if metadata.get('foliage'):result.update({'f_'+k:v for k,v in fol.resolve_roles(metadata['foliage']).items()})
        return result
    old_roles=role_map(col,root,objects,text,old_meta);roles=list(old_roles.values());old_names=[o.name for o in roles]
    before=set(bpy.data.user_map());staged_roles=[];success=False
    selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    try:
        private='BotanicalStage_'+uuid.uuid4().hex[:16]
        foliage_cfg=p.get('foliage',old_fol['recipe'] if old_fol else False)
        fresh=create(p|{'collection':private,'bark_material':p.get('bark_material') or state['geometry']['bark_material'],
                        'foliage':foliage_cfg,'_foliage_material':bpy.data.materials.get(old_fol['material']) if old_fol and foliage_cfg else None})
        new_col,new_root,new_objects,new_text,_,_,_,_=inventory({'collection':private});new_roles=role_map(new_col,new_root,new_objects,new_text,json.loads(new_col[META]));staged_roles=list(new_roles.values())
        if p['preserve_placement']:
            new_root.parent=root.parent;new_root.parent_type=root.parent_type;new_root.parent_bone=root.parent_bone;new_root.parent_vertices=tuple(root.parent_vertices)
            new_root.matrix_parent_inverse=root.matrix_parent_inverse.copy();new_root.rotation_mode=root.rotation_mode
            # Matrix assignment decomposes through float32 and loses delta/mode
            # information. Identical channels retain the actual authored placement.
            for channel in ('location','rotation_euler','rotation_quaternion','rotation_axis_angle','scale','delta_location','delta_rotation_euler','delta_rotation_quaternion','delta_scale'):
                setattr(new_root,channel,getattr(root,channel)[:])
        if inspect({'collection':col.name})['tree_sha256']!=p['expected_tree']:raise ValueError('Original botanical tree changed during staging')
        check_cancelled()
        for i,item in enumerate(roles):item.name='BotanicalOld_'+uuid.uuid4().hex[:16]+str(i)
        name_map={}
        for key,item in new_roles.items():
            public=old_names[roles.index(old_roles[key])] if key in old_roles else item.name.replace(private,p['collection'],1)
            previous=item.name;item.name=public
            if item.name!=public:raise ValueError('Botanical component public-name collision')
            name_map[previous]=item.name
        def remap(value):
            if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
            if isinstance(value,list):return [remap(v) for v in value]
            return name_map.get(value,value) if isinstance(value,str) else value
        staged_meta=json.loads(new_col[META])
        if staged_meta.get('foliage'):
            mat=bpy.data.materials[staged_meta['foliage']['material']]
            if mat not in before and mat.name.startswith(private):
                previous=mat.name;mat.name=p['collection']+'_LeafSurface';name_map[previous]=mat.name
        meta=remap(staged_meta);meta['root']=new_root.name;meta['model_text']=new_text.name
        for entry,obj in zip(meta['members'],new_objects):entry['object']=obj.name
        meta['replaces']=state['id'];new_col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        for parent in parents(new_col):parent.children.unlink(new_col)
        for parent in links:parent.children.link(new_col)
        new_col.hide_viewport=col.hide_viewport;new_col.hide_render=col.hide_render
        for old,new in zip([root,*objects],[new_root,*new_objects]):
            for key,value in flags(old).items():setattr(new,key,value)
        bpy.context.view_layer.update()
        for old,new in zip([root,*objects],[new_root,*new_objects]):
            if bpy.context.view_layer.objects.get(old.name)==old and bpy.context.view_layer.objects.get(new.name)==new:new.hide_set(old.hide_get())
        if p['preserve_placement'] and any(abs(root.matrix_world[i][j]-new_root.matrix_world[i][j])>1e-6 for i in range(4) for j in range(4)):raise ValueError('Botanical root placement could not be preserved')
        if meta.get('foliage'):
            meta['foliage']['content_sha256']=fol.component_signature(fol.resolve_roles(meta['foliage']));new_col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        result=inspect({'collection':new_col.name})
        if not result['valid']:raise ValueError('Replacement botanical tree failed validation')
        replacements={value:new_roles[key] for key,value in old_roles.items() if key in new_roles and isinstance(value,bpy.types.Object)}
        for obj in selected:
            target=replacements.get(obj,obj)
            if target.visible_get() and not target.hide_select:target.select_set(True)
        if active:bpy.context.view_layer.objects.active=replacements.get(active,active)
        report_progress({'phase':'verified botanical handoff before deletion','collection':new_col.name});check_cancelled()
        bpy.data.batch_remove(ids=tuple(owned));success=True;return result
    finally:
        if not success:
            for i,item in enumerate(staged_roles):item.name='BotanicalFailed_'+uuid.uuid4().hex[:16]+str(i)
            for item,name in zip(roles,old_names):item.name=name
            created=set(bpy.data.user_map())-before
            if created:bpy.data.batch_remove(ids=tuple(created))
            bpy.context.view_layer.update()
            for obj in selected:
                if obj.visible_get() and not obj.hide_select:obj.select_set(True)
            if active:bpy.context.view_layer.objects.active=active


def export_model(p):
    from .bridge import check_cancelled
    *_,model,report=guarded(p)
    if not report['valid']:raise ValueError('Export requires an unchanged valid botanical master')
    path=Path(p['path'])
    if path.exists() and not p['overwrite']:raise FileExistsError(path)
    from .bridge import _bridge
    encoded=(json.dumps(model,sort_keys=True,allow_nan=False)+'\n').encode()
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
    require_space(path,len(encoded),reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='serialized_botanical_model_bytes')
    temporary=None
    try:
        check_cancelled()
        with tempfile.NamedTemporaryFile(prefix='.mcpblender-model-',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        check_cancelled()
        if p['overwrite']:temporary.replace(path);temporary=None
        else:os.link(temporary,path)
    finally:
        if temporary is not None:temporary.unlink()
    return {'path':str(path),'model_sha256':report['model_sha256'],'generator':model['generator'],'scope':'Canonical local-metre branch/bud JSON only; mesh placement and engine export adapters are separate.'}


def dispatch(command,p):
    if command=='botanical_species_catalog':return botany.species_catalog()
    if command=='plan_botanical_tree':return plan(p)
    if command=='create_botanical_tree':return create(p)
    if command=='inspect_botanical_tree':return inspect(p)
    if command=='regenerate_botanical_tree':return regenerate(p)
    if command=='remove_botanical_tree':return remove(p)
    if command=='export_botanical_model':return export_model(p)
    *_,model,report=inventory(p)
    if report['model_error']:raise ValueError(report['model_error'])
    elements=model['branches'] if p['kind']=='BRANCH' else model['organs']
    return {'kind':p['kind'],'total':len(elements),'offset':p['offset'],'items':elements[p['offset']:p['offset']+p['limit']],'model_sha256':report['model_sha256']}
