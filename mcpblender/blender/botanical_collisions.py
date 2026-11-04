"""Native woody sleeve convex pieces with semantic selection and owned rollback."""
import json
import math
import uuid
import bpy
from mathutils import Vector
from mcpblender import botany
from mcpblender.collision_hulls import hull
from . import botanical_trees as trees,wind_preview

META='mcpblender_botanical_collisions'
OWNER='mcpblender_botanical_collision_owner'
BRANCH='mcpblender_collision_branch_index'
FORMAT='mcpblender-botanical-collision-v1'
COMMANDS={'inspect_botanical_collision_source','create_botanical_collisions','inspect_botanical_collisions','remove_botanical_collisions'}
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','Text':'texts'}
SETTINGS=('min_radius_m','max_branch_order','max_colliders','triangle_budget')


def portable(state):return {k:v for k,v in state.items() if k not in {'tree_sha256','recovery','operation_id'}}


def plan(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Botanical collision planning requires Object mode')
    bpy.context.view_layer.update()
    values=trees.inventory({'collection':p['collection']});state=values[-1];model=values[-2];root=values[1]
    if not state['valid'] or state['replacement_blockers']:raise ValueError('Collision selection requires a valid uncontrolled botanical master')
    matrix=root.matrix_world;unit=bpy.context.scene.unit_settings.scale_length;det=matrix.determinant()
    if any(not math.isfinite(v) for row in matrix for v in row) or not math.isfinite(det) or det<=1e-12 or not math.isfinite(unit) or unit<=0:raise ValueError('Collision placement requires finite positive invertible scale')
    linear=matrix.to_3x3();axes=[linear.col[i].normalized() for i in range(3)]
    if any(abs(axes[a].dot(axes[b]))>1e-6 for a,b in ((0,1),(0,2),(1,2))):raise ValueError('Collision placement does not support shear')
    branches=model['branches'];lookup={b['id']:i for i,b in enumerate(branches)}
    requested={i for i,b in enumerate(branches) if b['order']<=p['max_branch_order'] and b['radius_start']>=p['min_radius_m']}
    if not requested:raise ValueError('No branches meet the collision order/radius criteria')
    selected=set(requested)
    for index in sorted(requested):
        while branches[index]['parent_id']:
            index=lookup[branches[index]['parent_id']]
            if index in selected:break
            selected.add(index)
    if len(selected)>p['max_colliders']:raise ValueError('Botanical collision count budget exceeded')
    mesh=values[2][0].data
    if len(mesh.vertices)>200000 or len(mesh.polygons)>200000:raise ValueError('Botanical collision source geometry budget exceeded')
    attr=mesh.attributes.get('bot_branch_index')
    if not attr or attr.domain!='POINT' or attr.data_type!='INT':raise ValueError('Botanical collision requires canonical branch indices')
    labels=[v.value for v in attr.data]
    if any(i<0 or i>=len(branches) for i in labels):raise ValueError('Invalid source branch index')
    points={i:set() for i in selected}
    # Canonical indices are parent-first. A shared-ring side face belongs to its
    # downstream segment; independent-axis sleeve caps/rings carry their own ID.
    for face in mesh.polygons:
        index=max(labels[v] for v in face.vertices)
        if index in points:points[index].update(face.vertices)
    pieces=[];total=0
    for number,index in enumerate(sorted(selected)):
        check_cancelled();ids=sorted(points[index])
        if not 4<=len(ids)<=32:raise ValueError('Botanical sleeve vertex budget/topology differs from the supported source')
        shape=hull([tuple(mesh.vertices[i].co) for i in ids]);total+=shape['triangles']
        if total>p['triangle_budget']:raise ValueError('Botanical collision triangle budget exceeded')
        b=branches[index];pieces.append(shape|{'branch_index':index,'branch_id':b['id'],'parent_id':b['parent_id'],'axis_id':b['axis_id'],'order':b['order'],
                                              'radius_start_m':b['radius_start'],'radius_end_m':b['radius_end'],'source_vertex_indices':ids})
        report_progress({'phase':'planning botanical collision pieces','completed':number+1,'total':len(selected)})
    summary={'format':FORMAT,'source_collection':p['collection'],'source_tree_sha256':state['tree_sha256'],
             'source_content_sha256':botany.digest(portable(state)),'model_sha256':state['model_sha256'],'source_unit_scale':unit,
             'source_root_world_matrix':[list(row) for row in matrix],'settings':{k:p[k] for k in SETTINGS},'collider_count':len(pieces),
             'requested_branches':sorted(requested),'ancestor_added':sorted(selected-requested),'triangles':total,
             'pieces':[{k:v for k,v in s.items() if k not in {'vertices','faces','source_vertex_indices'}}|{'geometry_sha256':botany.digest({'vertices':s['vertices'],'faces':s['faces']}),'world_volume_m3':s['volume_local_m3']*det*unit**3} for s in pieces],
             'scope':'Static convex hull per selected native woody sleeve; all selected vertices checked, leaf/shoot collision omitted. Hulls may overlap or fill within-sleeve concavities; no dynamics, wind sweep, global union or engine binding.'}
    return values,pieces,summary|{'plan_sha256':botany.digest(summary)}


def inspect(p):
    bpy.context.view_layer.update()
    col=bpy.data.collections.get(p['collision_collection']);raw=col.get(META) if col else None
    if not isinstance(raw,str) or len(raw)>2*1024**2:raise ValueError('Owned botanical collisions not found or invalid metadata')
    meta=json.loads(raw);owned=set()
    if meta.get('format')!=FORMAT or not 1<=len(meta.get('owned',[]))<=1024 or not isinstance(meta.get('owner'),str) or len(meta['owner'])!=32:raise ValueError('Invalid botanical collision ownership')
    for row in meta['owned']:
        table=TABLES.get(row['type']);value=getattr(bpy.data,table).get(row['name']) if table else None
        if value is None or value.get(OWNER)!=meta['owner']:raise ValueError('Botanical collision owned ID missing/renamed or ownership changed')
        owned.add(value)
    if col not in owned or len(owned)!=len(meta['owned']):raise ValueError('Invalid botanical collision inventory')
    users=bpy.data.user_map();blockers=[];issues=[]
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Collision ID became linked/persistent: '+value.name)
        for user in users.get(value,set()):
            if user in owned or value==col and isinstance(user,(bpy.types.Scene,bpy.types.Collection)) or isinstance(value,bpy.types.Object) and isinstance(user,bpy.types.Scene):continue
            blockers.append('External collision reference: '+value.name)
        if isinstance(value,bpy.types.Collection) and (value.children or any(o not in owned for o in value.objects)):blockers.append('Foreign collision collection membership')
        if isinstance(value,bpy.types.Object) and (value.rigid_body or value.rigid_body_constraint):blockers.append('Remove attached collision physics before owned deletion: '+value.name)
    for row in meta['colliders']:
        obj=bpy.data.objects.get(row['object'])
        if obj is None or obj.get(BRANCH)!=row['branch_index']:issues.append('Collision branch mapping changed: '+row['object'])
    current=wind_preview.signature(owned,metadata_key=META)
    if current!=meta['content_sha256']:issues.append('Botanical collision native contents changed')
    if bpy.context.scene.unit_settings.scale_length!=meta['plan']['source_unit_scale']:issues.append('Scene unit scale differs from collision snapshot')
    source=bpy.data.collections.get(meta['plan']['source_collection']);fresh=None;source_error=None
    if source:
        try:fresh=botany.digest(portable(trees.inspect({'collection':source.name})))==meta['plan']['source_content_sha256']
        except (ValueError,TypeError,KeyError) as exc:source_error=str(exc);fresh=False
    guard=botany.digest({'content':current,'meta':meta,'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'branch_properties':[(r['object'],repr(bpy.data.objects[r['object']].get(BRANCH))) for r in meta['colliders']], 'users':sorted((v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)})
    offset=p.get('offset',0);limit=p.get('limit',32)
    return col,owned,meta,{'collision_collection':col.name,'collision_sha256':guard,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),
        'source_present':source is not None,'source_unchanged':fresh,'source_error':source_error,'plan':meta['plan'],'root':meta['root'],
        'objects':[v['object'] for v in meta['colliders']],'colliders':meta['colliders'][offset:offset+limit],'total':len(meta['colliders']),'offset':offset,
        'display_offset_m':meta['display_offset_m'],'parent_to_root':meta.get('parent_to_root',True),'scope':meta['plan']['scope']}


def create(p):
    from .bridge import check_cancelled,report_progress
    values,pieces,planned=plan(p)
    if p['expected_plan']!=planned['plan_sha256']:raise ValueError('Botanical collision plan is stale; inspect again')
    name=p['collision_collection']
    if name in bpy.data.collections:raise ValueError('Collision collection already exists')
    from .bridge import _bridge
    if _bridge and _bridge.active:
        from mcpblender.storage import require_space
        policy=_bridge.active['storage'];estimate=4*1024**2+sum(len(s['vertices'])*128+s['triangles']*64 for s in pieces)
        policy.update(estimated_bytes=estimate,estimate_kind='botanical_collision_checkpoint_size_heuristic')
        require_space(policy.get('path',_bridge.path.parent),estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind=policy['estimate_kind'])
    before=set(bpy.data.user_map());success=False
    try:
        check_cancelled();col=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(col)
        root=bpy.data.objects.new(name+'_Root',None);col.objects.link(root);root.matrix_world=values[1].matrix_world.copy()
        root.location+=Vector(p['display_offset_m'])/bpy.context.scene.unit_settings.scale_length
        bpy.context.view_layer.update()
        target=values[1].matrix_world.copy();target.translation+=Vector(p['display_offset_m'])/bpy.context.scene.unit_settings.scale_length
        if any(abs(root.matrix_world[i][j]-target[i][j])>max(1e-5,abs(target[i][j])*1e-6) for i in range(4) for j in range(4)):raise ValueError('Native collision placement differs from the source transform')
        rows=[]
        for number,shape in enumerate(pieces):
            check_cancelled();mesh=bpy.data.meshes.new(name+f'_B{shape["branch_index"]:04}_Mesh');mesh.from_pydata(shape['vertices'],[],shape['faces']);mesh.update()
            obj=bpy.data.objects.new(name+f'_B{shape["branch_index"]:04}',mesh);col.objects.link(obj);obj.parent=root if p['parent_to_root'] else None
            if not p['parent_to_root']:obj.matrix_world=root.matrix_world.copy()
            obj.hide_render=p['hide_render'];obj.display_type='WIRE';obj[BRANCH]=shape['branch_index']
            trees.attribute(mesh,'bot_branch_index','INT',[shape['branch_index']]*len(mesh.vertices));mesh.calc_loop_triangles()
            if len(mesh.loop_triangles)!=shape['triangles']:raise ValueError('Native botanical collision triangles differ from plan')
            rows.append(planned['pieces'][number]|{'object':obj.name,'mesh':mesh.name})
            report_progress({'phase':'building botanical collision pieces','completed':number+1,'total':len(pieces)})
        bpy.context.view_layer.update()
        if trees.inspect({'collection':p['collection']})['tree_sha256']!=planned['source_tree_sha256']:raise ValueError('Source changed during botanical collision staging')
        owner=uuid.uuid4().hex;owned=set(bpy.data.user_map())-before
        for value in owned:value[OWNER]=owner
        meta={'format':FORMAT,'owner':owner,'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))],
              'plan':planned,'root':root.name,'display_offset_m':p['display_offset_m'],'parent_to_root':p['parent_to_root'],'colliders':rows,'content_sha256':wind_preview.signature(owned,metadata_key=META)}
        col[META]=json.dumps(meta,sort_keys=True,allow_nan=False);result=inspect({'collision_collection':name})[-1]
        if not result['valid'] or not result['source_unchanged']:raise ValueError('Botanical collision publication failed verification')
        report_progress({'phase':'verified botanical collision before handoff'});check_cancelled();success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))


def dispatch(command,p):
    if command=='inspect_botanical_collision_source':return plan(p)[-1]
    if command=='create_botanical_collisions':return create(p)
    col,owned,meta,result=inspect(p)
    if command=='inspect_botanical_collisions':return result
    if p['expected_collision']!=result['collision_sha256']:raise ValueError('Botanical collision fingerprint is stale; inspect again')
    if result['ownership_blockers']:raise ValueError('; '.join(result['ownership_blockers']))
    if result['issues'] and not p.get('discard_derived_edits',False):raise ValueError('Edited botanical collisions require discard_derived_edits')
    from .bridge import check_cancelled
    check_cancelled();bpy.data.batch_remove(ids=tuple(owned));return {'removed':p['collision_collection'],'source_preserved':True}
