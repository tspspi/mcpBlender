"""Owned sampled wind animation with rigid instanced foliage and native readback."""
import json
import math
import uuid
import bpy
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
from mcpblender import wind,botany
from . import botanical_wind as motion,botanical_foliage as foliage,assemblies,lods,assembly_realization as realization
from .botanical_trees import attribute

COMMANDS={'inspect_botanical_wind_preview_source','create_botanical_wind_preview','inspect_botanical_wind_preview','remove_botanical_wind_preview'}
META='mcpblender_wind_preview'
FORMAT='mcpblender-wind-preview-v1'
OWNER='mcpblender_wind_owner'
SEMANTICS='mcpblender_wind_semantics'
OPTIONS=('frame_start','frame_end','frame_step','display_offset_m','max_instances','max_coordinate_bytes','max_work',
         'max_key_error_m','max_midpoint_error_m','max_orientation_error_degrees','max_surface_edge_strain')
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','Key':'shape_keys','Action':'actions','GeometryNodeTree':'node_groups','Text':'texts'}


def frames(p):
    result=list(range(p['frame_start'],p['frame_end']+1,p['frame_step']))
    if result[-1]!=p['frame_end']:result.append(p['frame_end'])
    return result


def plan(p):
    values,info=motion.source(p);sequence=frames(p);scene=bpy.context.scene;fps=scene.render.fps/scene.render.fps_base
    if not math.isfinite(fps) or fps<=0 or max(abs(f) for f in sequence)/fps>1e6:raise ValueError('Wind preview FPS/time is outside the portable solver range')
    count=values[-1]['foliage']['metrics']['leaves'] if values[-1]['foliage'] else 0
    if count>p['max_instances']:raise ValueError('Wind preview instance budget exceeded')
    meshes=[o.data for o in values[2]]
    if values[-1]['foliage']:meshes.append(foliage.resolve_roles(values[-1]['foliage'])['sm'])
    vertices=sum(len(m.vertices) for m in meshes)+count*3;edges=sum(len(m.edges) for m in meshes)
    coordinate_bytes=vertices*(len(sequence)+1)*12
    work=(vertices+edges+len(values[-2]['branches'])+count)*(3*len(sequence)-1)
    if coordinate_bytes>p['max_coordinate_bytes'] or work>p['max_work']:raise ValueError('Wind preview coordinate/work budget exceeded')
    gap=max(b-a for a,b in zip(sequence,sequence[1:]))/fps
    cfg=info['wind'];energy=botany.length(cfg['steady_mps'])+cfg['gust_mps'];frequencies=[]
    if energy and cfg['bend_degrees_per_mps'] and cfg['max_segment_degrees']:
        frequencies.append(cfg['frequency_hz'])
        if cfg['gust_mps']:frequencies.extend(w['angular_frequency_rad_per_s']/(2*math.pi) for w in info['field']['waves'])
    if energy and cfg['flutter_degrees']:frequencies.append(cfg['flutter_hz'])
    if frequencies and max(frequencies)*gap>.125+1e-9:raise ValueError('Wind sampling needs at least eight samples per motion cycle; lower frequency/step or increase scene FPS')
    options={k:p[k] for k in OPTIONS};options['display_offset_m']=[float(x) for x in options['display_offset_m']]
    for key in ('max_key_error_m','max_midpoint_error_m','max_orientation_error_degrees','max_surface_edge_strain'):options[key]=float(options[key])
    result={'format':FORMAT,'source_collection':p['collection'],'source':info,'frames':sequence,'fps':fps,'leaf_instances':count,'prototypes':values[-1]['foliage']['metrics']['prototypes'] if count else 0,
            'coordinate_bytes':coordinate_bytes,'work':work,'options':options,
            'method':'Sampled relative shape keys; rigid leaf frames reconstructed from three animated helper points. Linear interpolation freezes at the range endpoints; no Python playback handlers.',
            'scope':'Native preview only. Display offset shifts the copy, while wind is sampled at the original frozen source placement. Surface strain and midpoint error are measured; runtime attribute export is separate.'}
    return result|{'plan_sha256':botany.digest(result)}


def curve_key(obj,positions,index,sequence):
    if obj.data.shape_keys is None:obj.shape_key_add(name='Basis',from_mix=False)
    block=obj.shape_key_add(name='Wind_'+str(index),from_mix=False);block.data.foreach_set('co',[x for v in positions for x in v])
    if index:block.value=0.;block.keyframe_insert('value',frame=sequence[index-1])
    block.value=1.;block.keyframe_insert('value',frame=sequence[index])
    if index+1<len(sequence):block.value=0.;block.keyframe_insert('value',frame=sequence[index+1])
    return block


def deform(rest,indices,model,pose):
    result=[];branches=model['branches'];states=pose['branches'];base=branches[0]['start'][2]
    for v,index in zip(rest,indices):
        # Pin the generated soil ring, in addition to the model's root center.
        result.append(tuple(v) if index==0 and abs(v[2]-base)<1e-7 else wind.transform_point(branches[index],states[index],v))
    return result


def leaf_frames(population,model,pose,cfg,*,cancelled=lambda:None,progress=lambda v:None):
    points=[];poses=[]
    for leaf_index,leaf in enumerate(population['leaves']):
        if leaf_index%1024==0:
            cancelled();progress({'phase':'sampling wind leaf poses','seconds':pose['seconds'],'leaves':leaf_index,'total_leaves':len(population['leaves'])})
        i=leaf['parent_branch_index'];state=wind.leaf_local_pose(leaf,model['branches'][i],pose['branches'][i],cfg,pose['seconds'])
        center=state['position_local_m'];r=state['rotation_local'];poses.append(state)
        points.extend((center,botany.add(center,wind.mv(r,(.1,0,0))),botany.add(center,wind.mv(r,(0,0,.1)))))
    return points,poses


def leaf_graph(obj,collection):
    group=bpy.data.node_groups.new(obj.name+'_Instances','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nodes=group.nodes;links=group.links;source=nodes.new('NodeGroupInput');output=nodes.new('NodeGroupOutput')
    def named(name,kind):
        n=nodes.new('GeometryNodeInputNamedAttribute');n.data_type=kind;n.inputs['Name'].default_value=name;return n.outputs['Attribute']
    points=nodes.new('GeometryNodeMeshToPoints');points.mode='VERTICES';links.new(source.outputs['Geometry'],points.inputs['Mesh']);links.new(named('wind_center','BOOLEAN'),points.inputs['Selection'])
    position=nodes.new('GeometryNodeInputPosition');rotation=nodes.new('FunctionNodeAxesToRotation');rotation.primary_axis='X';rotation.secondary_axis='Z'
    for offset,socket in ((1,'Primary Axis'),(2,'Secondary Axis')):
        add=nodes.new('ShaderNodeMath');add.operation='ADD';links.new(named('wind_source_index','INT'),add.inputs[0]);add.inputs[1].default_value=offset
        sample=nodes.new('GeometryNodeSampleIndex');sample.data_type='FLOAT_VECTOR';sample.domain='POINT';links.new(source.outputs['Geometry'],sample.inputs['Geometry']);links.new(position.outputs['Position'],sample.inputs['Value']);links.new(add.outputs[0],sample.inputs['Index'])
        subtract=nodes.new('ShaderNodeVectorMath');subtract.operation='SUBTRACT';links.new(sample.outputs['Value'],subtract.inputs[0]);links.new(position.outputs['Position'],subtract.inputs[1]);links.new(subtract.outputs['Vector'],rotation.inputs[socket])
    prototypes=nodes.new('GeometryNodeCollectionInfo');prototypes.inputs['Collection'].default_value=collection;prototypes.inputs['Separate Children'].default_value=True;prototypes.inputs['Reset Children'].default_value=True
    instance=nodes.new('GeometryNodeInstanceOnPoints');instance.inputs['Pick Instance'].default_value=True
    links.new(points.outputs['Points'],instance.inputs['Points']);links.new(prototypes.outputs['Instances'],instance.inputs['Instance']);links.new(named('leaf_variant','INT'),instance.inputs['Instance Index']);links.new(named('leaf_scale','FLOAT_VECTOR'),instance.inputs['Scale']);links.new(rotation.outputs['Rotation'],instance.inputs['Rotation']);links.new(instance.outputs['Instances'],output.inputs['Geometry'])
    obj.modifiers.new('Wind shared leaf instances','NODES').node_group=group
    return group


def signature(owned,metadata_key=META):
    records=[]
    for value in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name)):
        if isinstance(value,bpy.types.Mesh):data=realization.mesh_record(value)
        elif isinstance(value,bpy.types.Key):
            data={'relative':value.use_relative,'animation':assemblies.animation(value),'blocks':[(k.name,k.relative_key.name,k.mute,k.vertex_group,lods.packed(k.data,'co',len(k.data)*3)) for k in value.key_blocks]}
        elif isinstance(value,bpy.types.Object):
            data={'data':value.data.name if value.data else None,'parent':value.parent.name if value.parent else None,'basis':lods.matrix(value.matrix_basis),'inverse':lods.matrix(value.matrix_parent_inverse),
                  'flags':{k:getattr(value,k) for k in ('hide_viewport','hide_render','hide_select','show_only_shape_key','use_shape_key_edit_mode','instance_type','show_instancer_for_viewport','show_instancer_for_render')},'instance_collection':value.instance_collection.name if value.instance_collection else None,'animation':assemblies.animation(value),
                  'constraints':[(c.name,c.type,assemblies.props(c),assemblies.pointers(c),assemblies.idprops(c)) for c in value.constraints],
                  'physics':{k:assemblies.props(getattr(value,k)) for k in ('rigid_body','rigid_body_constraint','soft_body') if getattr(value,k,None)},
                  'materials':[(s.link,s.material.name if s.material else None) for s in value.material_slots],
                  'modifiers':[(m.name,m.type,assemblies.props(m),assemblies.pointers(m),assemblies.idprops(m)) for m in value.modifiers]}
        elif isinstance(value,bpy.types.Collection):data={'objects':sorted(o.name for o in value.objects),'children':sorted(c.name for c in value.children),'hide_viewport':value.hide_viewport,'hide_render':value.hide_render,'instance_offset':list(value.instance_offset),'custom':{k:v for k,v in assemblies.idprops(value).items() if k!=metadata_key}}
        elif isinstance(value,bpy.types.Text):data={'content':botany.digest(value.as_string()),'use_module':value.use_module}
        else:data=assemblies.record(value)
        records.append((value.bl_rna.identifier,value.name,data))
    return botany.digest(records)


def inspect(p):
    col=bpy.data.collections.get(p['preview_collection'])
    if not col or not isinstance(col.get(META),str):raise ValueError('Owned wind preview not found')
    if len(col[META])>8*1024**2:raise ValueError('Wind preview metadata exceeds limit')
    meta=json.loads(col[META])
    if meta.get('format')!=FORMAT or not 1<=len(meta.get('owned',[]))<=128 or not isinstance(meta.get('owner'),str) or len(meta['owner'])!=32 or any(c not in '0123456789abcdef' for c in meta['owner']):raise ValueError('Invalid wind preview inventory')
    owned=set()
    for entry in meta['owned']:
        table=TABLES.get(entry['type']);value=getattr(bpy.data,table).get(entry['name']) if table else None
        if value is None:raise ValueError('Wind preview owned ID is missing/renamed: '+entry['name'])
        if value.get(OWNER)!=meta.get('owner'):raise ValueError('Wind preview ID ownership marker differs: '+entry['name'])
        owned.add(value)
    if col not in owned or len(owned)!=len(meta['owned']):raise ValueError('Invalid duplicate wind ownership')
    users=bpy.data.user_map();blockers=[]
    objects={v for v in owned if isinstance(v,bpy.types.Object)};collections={v for v in owned if isinstance(v,bpy.types.Collection)}
    if set(col.objects)!=objects.intersection(col.objects) or set(col.children):blockers.append('Wind preview collection gained foreign members/children')
    if set(col.objects)!={v for v in objects if v.name not in meta['prototype_objects']}:blockers.append('Wind preview main membership changed')
    proto=bpy.data.collections.get(meta.get('prototype_collection')) if meta.get('prototype_collection') else None
    if proto and (set(proto.objects)!={v for v in objects if v.name in meta['prototype_objects']} or proto.children):blockers.append('Wind prototype membership changed')
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Wind preview owned data became persistent/linked: '+value.name)
        for user in users.get(value,set()):
            if user in owned:continue
            if value==col and isinstance(user,(bpy.types.Scene,bpy.types.Collection)):continue
            if isinstance(value,bpy.types.Object) and isinstance(user,bpy.types.Scene):continue
            blockers.append('External reference to wind preview: '+value.name)
    current=signature(owned);issues=[]
    if current!=meta['content_sha256']:issues.append('Wind preview native contents changed')
    fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    if abs(fps-meta['plan']['fps'])>1e-9:issues.append('Scene FPS differs from baked wind timing')
    result={'preview_collection':col.name,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),
            'preview_sha256':botany.digest({'content':current,'users':sorted((v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned),'meta':meta}),
            'plan':meta['plan'],'verification':meta['verification'],'objects':meta['render_objects'],'root':meta['root'],
            'roles':meta['roles'],'prototype_objects':meta['prototype_objects'],'semantic_text':getattr(col.get(SEMANTICS),'name',None),
            'leaf_instances':meta['plan']['leaf_instances'],'prototypes':meta['plan']['prototypes']}
    return col,owned,meta,result


def verify(objects,rest,indices,model,population,info,plan_data,root,prototype_objects):
    from .bridge import check_cancelled,report_progress
    scene=bpy.context.scene;unit=scene.unit_settings.scale_length;sequence=plan_data['frames'];cfg=info['wind'];offset=Vector(plan_data['options']['display_offset_m'])
    result={'max_key_position_error_m':0.,'max_midpoint_position_error_m':0.,'max_leaf_orientation_error_degrees':0.,'max_leaf_scale_relative_error':0.,'max_leaf_axis_dot':0.,'max_surface_edge_strain':0.,'checked_frames':[]}
    checks=sorted(set(sequence+[ (a+b)/2 for a,b in zip(sequence,sequence[1:]) ]));roles=[k for k in rest];leaf_obj=objects.get('leaves')
    for frame in checks:
        check_cancelled();scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));bpy.context.view_layer.update()
        pose=wind.solve(model,cfg,frame/plan_data['fps'],info['placement'],cancelled=check_cancelled)
        key=frame in sequence;maximum=0.
        for role in roles:
            obj=objects[role];expected=deform(rest[role],indices[role],model,pose);evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            try:
                if len(mesh.vertices)!=len(expected):raise ValueError('Wind evaluated topology differs from source')
                maximum=max(maximum,max(((v.co-Vector(p)).length*info['placement']['scale'] for v,p in zip(mesh.vertices,expected)),default=0.))
                for edge in mesh.edges:
                    a,b=edge.vertices;before=(Vector(rest[role][a])-Vector(rest[role][b])).length
                    if before>1e-8:result['max_surface_edge_strain']=max(result['max_surface_edge_strain'],abs((mesh.vertices[a].co-mesh.vertices[b].co).length/before-1))
            finally:evaluated.to_mesh_clear()
        if leaf_obj:
            _,leaves=leaf_frames(population,model,pose,cfg,cancelled=check_cancelled,progress=report_progress);tree=KDTree(len(leaves));used=set()
            for i,leaf in enumerate(leaves):tree.insert(Vector(wind.world(info['placement'],leaf['position_local_m']))+offset,i)
            tree.balance();count=0;graph=bpy.context.evaluated_depsgraph_get()
            tolerance=plan_data['options']['max_key_error_m'] if key else plan_data['options']['max_midpoint_error_m']
            for instance_index,item in enumerate(graph.object_instances):
                if instance_index%1024==0:check_cancelled()
                if instance_index>=1000000:raise ValueError('Native wind instance inspection budget exceeded')
                if not item.is_instance or not item.parent or item.parent.original!=leaf_obj or not item.show_self:continue
                count+=1;actual=item.matrix_world;position=actual.translation*unit
                candidates=tree.find_range(position,max(tolerance,1e-5));best=None
                for _,i,distance in candidates:
                    leaf=leaves[i]
                    if i in used or item.object.original!=prototype_objects[leaf['variant']]:continue
                    desired=Matrix(info['placement']['rotation'])@Matrix(leaf['rotation_local'])
                    normalized=actual.to_3x3().normalized();angle=math.degrees(normalized.to_quaternion().rotation_difference(desired.to_quaternion()).angle)
                    angle=min(angle,360-angle)
                    score=(angle,distance,i)
                    if best is None or score<best:best=score
                if best is None:raise ValueError('Wind leaf instance missing, duplicated or outside pose tolerance')
                angle,distance,i=best;used.add(i);maximum=max(maximum,distance);result['max_leaf_orientation_error_degrees']=max(result['max_leaf_orientation_error_degrees'],angle)
                linear=actual.to_3x3();expected_scale=info['placement']['scale']*leaves[i]['scale']
                result['max_leaf_scale_relative_error']=max(result['max_leaf_scale_relative_error'],max(abs(linear.col[a].length*unit/expected_scale-1) for a in range(3)))
                result['max_leaf_axis_dot']=max(result['max_leaf_axis_dot'],max(abs(normalized.col[a].dot(normalized.col[b])) for a,b in ((0,1),(0,2),(1,2))))
            if count!=len(leaves) or len(used)!=len(leaves):raise ValueError('Wind leaf instance count differs from layout')
        metric='max_key_position_error_m' if key else 'max_midpoint_position_error_m';result[metric]=max(result[metric],maximum)
        if maximum>plan_data['options']['max_key_error_m' if key else 'max_midpoint_error_m']:raise ValueError('Native wind pose error exceeds tolerance; reduce step/frequency or adjust tolerance')
        if result['max_leaf_orientation_error_degrees']>plan_data['options']['max_orientation_error_degrees']:raise ValueError('Native wind leaf orientation error exceeds tolerance')
        if result['max_leaf_scale_relative_error']>1e-5 or result['max_leaf_axis_dot']>1e-5:raise ValueError('Native wind leaf instance lost rigid scale/orientation')
        if result['max_surface_edge_strain']>plan_data['options']['max_surface_edge_strain']:raise ValueError('Native wind surface edge strain exceeds budget')
        result['checked_frames'].append(frame);report_progress({'phase':'verified native wind frame','frame':frame,'checked_frames':len(result['checked_frames']),'total_frames':len(checks)})
    return result


def create(p):
    from .bridge import check_cancelled,report_progress
    from .bridge import _bridge
    if bpy.context.mode!='OBJECT':raise ValueError('Wind preview creation requires Object mode')
    planned=plan(p)
    if planned['plan_sha256']!=p['expected_plan']:raise ValueError('Wind preview plan fingerprint is stale')
    if p['preview_collection'] in bpy.data.collections:raise ValueError('Wind preview collection already exists')
    if _bridge and _bridge.active:_bridge.active['storage'].update(estimated_bytes=planned['coordinate_bytes']*2+16*1024**2,estimate_kind='wind_animation_checkpoint_size_heuristic')
    values,info=motion.source(p);model=values[-2];population=motion.layout(values);prefix=p['preview_collection'];scene=bpy.context.scene
    before=set(bpy.data.user_map());frame=scene.frame_current;subframe=scene.frame_subframe;success=False
    try:
        check_cancelled();col=bpy.data.collections.new(prefix);scene.collection.children.link(col)
        root=bpy.data.objects.new(prefix+'_Root',None);col.objects.link(root)
        matrix=Matrix(info['placement']['rotation']).to_4x4()
        for i in range(3):
            for j in range(3):matrix[i][j]*=info['placement']['scale']/scene.unit_settings.scale_length
        matrix.translation=(Vector(info['placement']['translation_m'])+Vector(p['display_offset_m']))/scene.unit_settings.scale_length;root.matrix_world=matrix
        objects={};rest={};indices={}
        sources={'wood':values[2][0],'buds':values[2][1]}
        source_roles=foliage.resolve_roles(values[-1]['foliage']) if population else None
        if source_roles:sources['shoots']=source_roles['so']
        for role,source in sources.items():
            mesh=source.data.copy();obj=bpy.data.objects.new(prefix+'_'+role,mesh);col.objects.link(obj);obj.parent=root;objects[role]=obj
            rest[role]=[tuple(v.co) for v in mesh.vertices];indices[role]=[v.value for v in mesh.attributes['bot_branch_index'].data]
            attribute(mesh,'wind_segment_anchor','FLOAT_VECTOR',[model['branches'][i]['start'] for i in indices[role]])
        prototypes=[];prototype_col=None
        if population:
            prototype_col=bpy.data.collections.new(prefix+'_LeafSources')
            for i in range(population['recipe']['variants']):
                original=source_roles['lo'+str(i)];obj=bpy.data.objects.new(prefix+'_Leaf'+str(i),original.data.copy());prototype_col.objects.link(obj);prototypes.append(obj)
            mesh=bpy.data.meshes.new(prefix+'_LeafFrames');base=[]
            for leaf in population['leaves']:
                r=wind.euler_rotation(leaf['rotation']);center=leaf['position'];base.extend((center,botany.add(center,wind.mv(r,(.1,0,0))),botany.add(center,wind.mv(r,(0,0,.1)))))
            mesh.from_pydata(base,[],[]);mesh.update();obj=bpy.data.objects.new(prefix+'_Leaves',mesh);col.objects.link(obj);obj.parent=root;objects['leaves']=obj
            leafs=population['leaves']
            for name,kind,data in [('wind_center','BOOLEAN',[i%3==0 for i in range(len(base))]),('wind_source_index','INT',[i//3*3 for i in range(len(base))]),
               ('leaf_variant','INT',[leaf['variant'] for leaf in leafs for _ in range(3)]),('leaf_scale','FLOAT_VECTOR',[(leaf['scale'],)*3 for leaf in leafs for _ in range(3)]),
               ('bot_branch_index','INT',[leaf['parent_branch_index'] for leaf in leafs for _ in range(3)]),('leaf_orientation','FLOAT_VECTOR',[leaf['rotation'] for leaf in leafs for _ in range(3)]),
               ('leaf_flutter','FLOAT',[leaf['flutter'] for leaf in leafs for _ in range(3)]),('leaf_phase','FLOAT',[leaf['phase'] for leaf in leafs for _ in range(3)])]:attribute(mesh,name,kind,data)
            leaf_graph(obj,prototype_col)
        for index,at in enumerate(planned['frames']):
            check_cancelled();pose=wind.solve(model,info['wind'],at/planned['fps'],info['placement'],cancelled=check_cancelled)
            for role in rest:curve_key(objects[role],deform(rest[role],indices[role],model,pose),index,planned['frames'])
            if population:curve_key(objects['leaves'],leaf_frames(population,model,pose,info['wind'],cancelled=check_cancelled,progress=report_progress)[0],index,planned['frames'])
            report_progress({'phase':'baking native wind coordinates','sample':index+1,'samples':len(planned['frames'])})
        from .domains import curves
        for obj in objects.values():
            key=obj.data.shape_keys;anim=key.animation_data
            for curve in curves(anim.action,getattr(anim,'action_slot',None)):
                curve.extrapolation='CONSTANT'
                for point in curve.keyframe_points:point.interpolation='LINEAR'
                curve.update()
        verified=verify(objects,rest,indices,model,population,info,planned,root,prototypes)
        scene.frame_set(frame,subframe=subframe);bpy.context.view_layer.update()
        if motion.source(p)[1]['wind_sha256']!=info['wind_sha256']:raise ValueError('Wind source changed during preview creation')
        text=bpy.data.texts.new(prefix+'_Wind.json');text.use_fake_user=False;text.use_module=False;text.write(json.dumps({'plan':planned,'model':model,'foliage_recipe':population['recipe'] if population else None},sort_keys=True,allow_nan=False))
        col[SEMANTICS]=text
        owned=set(bpy.data.user_map())-before
        owner=uuid.uuid4().hex
        for value in owned:value.use_fake_user=False;value[OWNER]=owner
        meta={'format':FORMAT,'owner':owner,'plan':planned,'root':root.name,'prototype_collection':prototype_col.name if prototype_col else None,'prototype_objects':[o.name for o in prototypes],
              'render_objects':[objects[k].name for k in ('wood','shoots','leaves') if k in objects],
              'roles':{k:v.name for k,v in objects.items()},
              'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))],
              'verification':verified,'content_sha256':signature(owned)}
        col[META]=json.dumps(meta,sort_keys=True,allow_nan=False);result=inspect({'preview_collection':col.name})[-1]
        if not result['valid']:raise ValueError('Wind preview inventory verification failed: '+str(result))
        report_progress({'phase':'verified wind preview before handoff'});check_cancelled();success=True;return result
    finally:
        scene.frame_set(frame,subframe=subframe)
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))
        bpy.context.view_layer.update()


def remove(p):
    from .bridge import check_cancelled
    col,owned,meta,result=inspect(p)
    if result['preview_sha256']!=p['expected_preview']:raise ValueError('Wind preview guard is stale; inspect again')
    if result['ownership_blockers']:raise ValueError('; '.join(result['ownership_blockers']))
    check_cancelled();bpy.data.batch_remove(ids=tuple(owned))
    return {'removed':p['preview_collection'],'materials_preserved':True}


def dispatch(command,p):
    if command=='inspect_botanical_wind_preview_source':return plan(p)
    if command=='create_botanical_wind_preview':return create(p)
    if command=='remove_botanical_wind_preview':return remove(p)
    return inspect(p)[-1]
