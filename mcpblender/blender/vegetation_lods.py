"""Owned near/mid botanical LODs with shared leaves and closed branch ancestry."""
import json
import math
import uuid
import bpy
from mathutils import Vector
from mcpblender import botany,vegetation_lod as solver
from . import botanical_wind as motion,botanical_foliage as foliage,botanical_trees as trees,wind_preview

META='mcpblender_vegetation_lods'
OWNER='mcpblender_vegetation_lod_owner'
TEXT='mcpblender_vegetation_lod_semantics'
COMMANDS={'inspect_botanical_lod_source','create_botanical_lods','inspect_botanical_lods','activate_botanical_lod','remove_botanical_lods'}
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','GeometryNodeTree':'node_groups','Text':'texts','Material':'materials','Image':'images','ShaderNodeTree':'node_groups'}


def plan(p):
    from .bridge import check_cancelled,report_progress
    values,wind=motion.source(p)
    count=values[-1]['foliage']['metrics']['leaves'] if values[-1]['foliage'] else 0
    if solver.mask_estimate(count,p['resolution'],len(p['views']))>p['max_mask_bytes']:raise ValueError('Vegetation LOD mask memory budget exceeded before attachment generation')
    population=motion.layout(values)
    options={k:p[k] for k in ('resolution','views','margin','silhouette_weight','max_projected_triangles','max_mask_bytes','max_gain_evaluations')}
    result=solver.plan(values[-2],population,p['levels'],source_sides=values[-1]['geometry']['radial_sides'],cancelled=check_cancelled,progress=report_progress,**options)
    wood_work=(2*solver.wood_triangles(values[-2],list(range(len(values[-2]['branches']))),values[-1]['geometry']['radial_sides'])+sum(l['triangles']['wood'] for l in result['levels']))*len(p['views'])
    if result['projected_triangles']+wood_work>p['max_projected_triangles']:raise ValueError('Combined leaf/native wood projected-triangle budget exceeded')
    summary={'source':wind,'selection_plan_sha256':result['plan_sha256'],'valid':result['valid'],
             'levels':[{'leaves':len(l['leaf_indices']),'branches':len(l['branch_indices']),'shoots':len(l['shoot_indices']),'quality':l['quality'],'triangles':l['triangles'],'passed':l['passed'],'options':l['options']} for l in result['levels']],
             'resolution':result['resolution'],'views':result['views'],'source_frame_clipped':result['source_frame_clipped'],
             'native_wood_quality_pending':True,'projected_triangles':result['projected_triangles']+wood_work,'mask_payload_estimated_bytes':result['mask_payload_estimated_bytes'],'gain_evaluations':result['gain_evaluations'],'scope':result['scope']}
    summary['plan_sha256']=botany.digest(summary)
    return values,population,result,summary


def signature(owned):
    base=wind_preview.signature(owned,metadata_key=META)
    private=[v for v in owned if isinstance(v,bpy.types.Material)]
    if not private:return base
    from . import textures
    return botany.digest({'native':base,'baked_materials':{m.name:textures.material_signature(m,source=False) for m in sorted(private,key=lambda m:m.name)}})


def inspect(p,*,ignore_users=None):
    col=bpy.data.collections.get(p['lod_collection'])
    if not col or not isinstance(col.get(META),str) or len(col[META])>8*1024**2:raise ValueError('Owned botanical LODs not found or invalid metadata')
    meta=json.loads(col[META]);owned=set()
    if meta.get('format')!=solver.FORMAT or not 1<=len(meta.get('owned',[]))<=512 or not isinstance(meta.get('owner'),str) or len(meta['owner'])!=32:raise ValueError('Invalid botanical LOD ownership')
    for entry in meta['owned']:
        table=TABLES.get(entry['type']);value=getattr(bpy.data,table).get(entry['name']) if table else None
        if value is None or value.get(OWNER)!=meta['owner']:raise ValueError('Botanical LOD owned ID missing/renamed or ownership changed')
        owned.add(value)
    if len(owned)!=len(meta['owned']) or col not in owned:raise ValueError('Duplicate botanical LOD ownership')
    blockers=[];users=bpy.data.user_map();ignored=set(ignore_users or ())
    # During staged replacement only the retiring IDs remain alive for rollback.
    # Compute the guard of the post-retirement graph without ignoring other users.
    ignored.update(v.node_tree for v in list(ignored) if isinstance(v,bpy.types.Material) and v.node_tree)
    users={v:set(u)-ignored for v,u in users.items()}
    embedded={v.node_tree for v in owned if isinstance(v,bpy.types.Material) and v.node_tree}
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Owned LOD data became linked/persistent: '+value.name)
        for user in users.get(value,set()):
            if user in owned or user in embedded or value==col and isinstance(user,(bpy.types.Scene,bpy.types.Collection)) or isinstance(value,bpy.types.Object) and isinstance(user,bpy.types.Scene):continue
            blockers.append('External reference: '+value.name)
        if isinstance(value,bpy.types.Collection) and any(v not in owned for v in [*value.objects,*value.children]):blockers.append('Foreign collection member: '+value.name)
    current=signature(owned);issues=[]
    if current!=meta['content_sha256']:issues.append('Botanical LOD contents changed')
    guard=botany.digest({'content':current,'meta':meta,'users':sorted((v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)})
    result={'lod_collection':col.name,'lods_sha256':guard,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),
            'levels':meta['levels'],'active_level':meta['active_level'],'root':meta['root'],'prototypes':meta['prototypes'],'source':meta['plan']['source'],'semantic_text':getattr(col.get(TEXT),'name',None),'plan':meta['plan'],'verification':meta['verification'],'baked_materials':meta.get('baked_materials',{})}
    return col,owned,meta,result


def shoots_mesh(name,model,population,indices,material):
    from mathutils import Vector
    vertices=[];faces=[];branches=[];lookup={b['id']:i for i,b in enumerate(model['branches'])}
    for i in indices:
        shoot=population['shoots'][i];tangent=Vector(shoot['end'])-Vector(shoot['start']);x,z=trees.frame(tangent);offset=len(vertices)
        for center,radius in ((shoot['start'],.0025),(shoot['end'],.001)):
            for j in range(4):
                vertices.append(Vector(center)+radius*(x*math.cos(j*math.pi/2)+z*math.sin(j*math.pi/2)));branches.append(lookup[shoot['parent_branch_id']])
        for j in range(4):faces.append((offset+j,offset+(j+1)%4,offset+4+(j+1)%4,offset+4+j))
        faces.extend((tuple(offset+j for j in reversed(range(4))),tuple(offset+4+j for j in range(4))))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(material);trees.attribute(mesh,'bot_branch_index','INT',branches)
    return mesh


def wood_masks(mesh,selection):
    from .bridge import check_cancelled
    from mcpblender import foliage_coverage as coverage
    resolution=selection['resolution'];mesh.calc_loop_triangles();result={}
    for view,frame in selection['frame'].items():
        rows=[0]*resolution;axes=frame['axes'];low=frame['frame_min_m'];step=frame['pixel_size_m']
        points=[tuple((v.co[a]-low[k])/step[k] for k,a in enumerate(axes)) for v in mesh.vertices]
        for i,triangle in enumerate(mesh.loop_triangles):
            if i%256==0:check_cancelled()
            coverage.raster_triangle(rows,[points[j] for j in triangle.vertices],resolution)
        result[view]=sum(row<<(r*resolution) for r,row in enumerate(rows))
    return result


def wood_quality(reference,target,resolution):
    result={}
    for view,source in reference.items():
        actual=target[view];edge=solver.boundary(source,resolution)
        result[view]={'source_pixels':source.bit_count(),'retained_pixels':(source&actual).bit_count(),
                      'coverage_loss':(source&~actual).bit_count()/max(1,source.bit_count()),
                      'silhouette_loss':(edge&~actual).bit_count()/max(1,edge.bit_count()),
                      'excess_fraction':(actual&~source).bit_count()/max(1,source.bit_count())}
    return result


def create(p):
    from .bridge import check_cancelled,report_progress
    values,population,selection,planned=plan(p)
    if p['expected_plan']!=planned['plan_sha256']:raise ValueError('Botanical LOD plan fingerprint is stale')
    if not planned['valid']:raise ValueError('Botanical LOD coverage/triangle quality budgets failed; inspect and revise explicitly')
    name=p['lod_collection']
    if name in bpy.data.collections:raise ValueError('Botanical LOD collection already exists')
    before=set(bpy.data.user_map());success=False;scene=bpy.context.scene
    try:
        col=bpy.data.collections.new(name);scene.collection.children.link(col)
        root=bpy.data.objects.new(name+'_Root',None);col.objects.link(root);root.matrix_world=values[1].matrix_world.copy()
        root.location+=Vector(p.get('display_offset_m',[0,0,0]))/scene.unit_settings.scale_length
        roles=foliage.resolve_roles(values[-1]['foliage']);prototypes=bpy.data.collections.new(name+'_LeafSources');prototype_objects=[]
        for i in range(population['recipe']['variants']):
            mesh=roles['lo'+str(i)].data.copy();mesh.use_fake_user=False;obj=bpy.data.objects.new(name+'_Leaf'+str(i),mesh);prototypes.objects.link(obj);prototype_objects.append(obj)
        col['mcpblender_leaf_sources']=prototypes
        source_model=values[-2];levels=[];bark=values[2][0].data.materials[0];reference_wood=wood_masks(values[2][0].data,selection)
        full={'leaf_indices':list(range(len(population['leaves']))),'branch_indices':list(range(len(source_model['branches']))),'shoot_indices':list(range(len(population['shoots']))),'options':{'radial_sides':values[-1]['geometry']['radial_sides']}}
        for number,level in enumerate([full,*selection['levels']]):
            check_cancelled();prefix=f'{name}_LOD{number}';objects=[]
            selected=level['branch_indices'];model=source_model|{'branches':[source_model['branches'][i] for i in selected]}
            mesh=trees.wood_mesh(model,{'collection':prefix,'radial_sides':level['options']['radial_sides'],'bark_tile_length':values[-1]['geometry']['bark_tile_length']});mesh.materials.append(bark)
            for v in mesh.attributes['bot_branch_index'].data:v.value=selected[v.value]
            wood=bpy.data.objects.new(prefix+'_Wood',mesh);col.objects.link(wood);wood.parent=root;objects.append(wood)
            mesh=shoots_mesh(prefix+'_ShootMesh',source_model,population,level['shoot_indices'],bark);shoots=bpy.data.objects.new(prefix+'_Shoots',mesh);col.objects.link(shoots);shoots.parent=root;objects.append(shoots)
            leaves=[population['leaves'][i] for i in level['leaf_indices']];mesh=bpy.data.meshes.new(prefix+'_LeafPoints');mesh.from_pydata([v['position'] for v in leaves],[],[]);mesh.update()
            leaf_obj=bpy.data.objects.new(prefix+'_Leaves',mesh);col.objects.link(leaf_obj);leaf_obj.parent=root;objects.append(leaf_obj)
            foliage.instance_population(prefix,leaf_obj,mesh,prototypes,population|{'leaves':leaves},level['leaf_indices'])
            native_triangles=[]
            for obj in (wood,shoots):obj.data.calc_loop_triangles();native_triangles.append(len(obj.data.loop_triangles))
            if number and native_triangles!=[level['triangles']['wood'],level['triangles']['shoots']]:raise ValueError('Native LOD wood/shoot triangle counts differ from plan')
            quality=wood_quality(reference_wood,wood_masks(wood.data,selection),selection['resolution'])
            if number and any(q['coverage_loss']>level['options']['max_coverage_loss'] or q['silhouette_loss']>level['options']['max_silhouette_loss'] or q['excess_fraction']>level['options']['max_coverage_loss'] for q in quality.values()):raise ValueError('Native LOD wood silhouette/coverage budgets failed; revise radial sides/radius thresholds or explicit quality limits')
            for obj in objects:obj.hide_viewport=number!=0;obj.hide_render=number!=0
            levels.append({'level':number,'objects':[o.name for o in objects],'leaves':len(leaves),'branches':len(selected),'native_triangles':native_triangles,'wood_quality':quality})
            report_progress({'phase':'building native botanical LOD','completed':number+1,'total':len(selection['levels'])+1})
        from .vegetation_export import native_instances
        verification=[];where=dict(planned['source']['placement']);where['translation_m']=[a+b for a,b in zip(where['translation_m'],p.get('display_offset_m',[0,0,0]))]
        for number,level in enumerate([full,*selection['levels']]):
            for current in levels:
                for object_name in current['objects']:
                    obj=bpy.data.objects[object_name];obj.hide_viewport=current['level']!=number;obj.hide_render=current['level']!=number
            bpy.context.view_layer.update()
            native_roles={'po':bpy.data.objects[levels[number]['objects'][2]]}|{'lo'+str(i):o for i,o in enumerate(prototype_objects)}
            verified=native_instances(values,population|{'leaves':[population['leaves'][i] for i in level['leaf_indices']]},native_roles,{'wind':{'placement':where}})
            verification.append(verified)
        for current in levels:
            for object_name in current['objects']:
                obj=bpy.data.objects[object_name];obj.hide_viewport=current['level']!=0;obj.hide_render=current['level']!=0
        bpy.context.view_layer.update()
        if trees.inspect({'collection':p['collection']})['tree_sha256']!=planned['source']['tree_sha256']:raise ValueError('Source changed during botanical LOD creation')
        text=bpy.data.texts.new(name+'_Semantics.json');text.use_fake_user=False;text.use_module=False;text.write(json.dumps({'model':source_model,'foliage':population,'selection':selection,'wind':planned['source']},sort_keys=True,allow_nan=False));col[TEXT]=text
        owned=set(bpy.data.user_map())-before;owner=uuid.uuid4().hex
        for value in owned:value[OWNER]=owner
        meta={'format':solver.FORMAT,'owner':owner,'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))],
              'verification':verification,'plan':planned,'root':root.name,'levels':levels,'prototypes':population['recipe']['variants'],'active_level':0,'content_sha256':None}
        col[META]=json.dumps(meta,sort_keys=True);bpy.context.view_layer.update();meta['content_sha256']=signature(owned);col[META]=json.dumps(meta,sort_keys=True)
        report_progress({'phase':'verified botanical LODs before handoff'});check_cancelled();result=inspect({'lod_collection':col.name})[-1]
        if not result['valid']:raise ValueError('Owned botanical LODs failed native validation')
        success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))


def dispatch(command,p):
    if command=='inspect_botanical_lod_source':return plan(p)[-1]
    if command=='create_botanical_lods':return create(p)
    col,owned,meta,result=inspect(p)
    if command=='inspect_botanical_lods':return result
    if result['lods_sha256']!=p['expected_lods']:raise ValueError('Botanical LOD fingerprint is stale')
    if result['ownership_blockers']:raise ValueError('Botanical LOD external ownership references prevent mutation/removal')
    if command=='remove_botanical_lods':
        if result['issues'] and not p.get('discard_derived_edits',False):raise ValueError('Edited derived LODs need explicit discard_derived_edits')
        name=col.name;private_materials=sum(isinstance(v,bpy.types.Material) for v in owned);bpy.data.batch_remove(ids=tuple(owned));return {'removed':name,'materials_preserved':True,'shared_source_materials_preserved':True,'owned_baked_materials_removed':private_materials}
    if not result['valid']:raise ValueError('Cannot activate modified botanical LODs')
    if not 0<=p['level']<len(meta['levels']):raise ValueError('Botanical LOD level out of range')
    for level in meta['levels']:
        for name in level['objects']:
            obj=bpy.data.objects[name];obj.hide_viewport=level['level']!=p['level'];obj.hide_render=level['level']!=p['level']
    meta['active_level']=p['level'];meta['content_sha256']=signature(owned);col[META]=json.dumps(meta,sort_keys=True);bpy.context.view_layer.update()
    return inspect(p)[-1]
