"""Source-preserving native instanced-tree capture preparation."""
from array import array
import itertools
import math
import bpy
from mathutils import Euler,Matrix,Vector
from mcpblender import botany,card_views,tree_capture
from . import assemblies,botanical_trees as trees,botanical_foliage as foliage,render_batches
from .vegetation_bake import static_matrix

COMMANDS={'inspect_botanical_view_capture','capture_botanical_views'}
OPTIONS=('collection','views','resolution','margin','world_strength','samples','max_leaves','max_render_triangles','max_bounds_work')


def corners(low,high):return [Vector(v) for v in itertools.product(*zip(low,high))]


def shader_state(tree):
    """Include nested ramp/curve/mapping RNA omitted by generic ID records."""
    from .botanical_surfaces import ramp_record
    from .simulations import props
    if len(tree.nodes)>4096 or len(tree.links)>16384:raise ValueError('Capture shader graph budget exceeded')
    result=[]
    for node in tree.nodes:
        if node.bl_idname=='ShaderNodeOutputMaterial' and node.inputs['Displacement'].is_linked:raise ValueError('Capture framing requires no material-output displacement; normal/bump detail is supported')
        row={'node':node.name}
        if hasattr(node,'color_ramp'):row['ramp']=ramp_record(node)
        for key in ('texture_mapping','color_mapping','image_user','mapping'):
            value=getattr(node,key,None)
            if value is None:continue
            extra=props(value)
            if hasattr(value,'color_ramp'):
                ramp=value.color_ramp
                extra['ramp']=[props(ramp),[(e.position,list(e.color)) for e in ramp.elements]]
            if hasattr(value,'curves'):extra['curves']=[[(list(p.location),p.handle_type) for p in curve.points] for curve in value.curves]
            row[key]=extra
        result.append(row)
    return result


def source(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for botanical captures')
    values=trees.inventory(p);col,root,members=values[:3];state=values[-1]
    if not state['valid'] or state['replacement_blockers']:raise ValueError('Capture requires a valid static managed botanical tree')
    scene=bpy.context.scene
    if scene.frame_subframe:raise ValueError('Capture requires an integer source frame')
    matrix=static_matrix(root);unit=scene.unit_settings.scale_length;linear=matrix.to_3x3();sizes=[linear.col[i].length for i in range(3)]
    if any(not math.isfinite(v) for row in matrix for v in row) or not all(math.isfinite(v) for v in sizes) or not math.isfinite(matrix.determinant()) or not math.isfinite(unit) or unit<=0 or min(sizes)<=1e-8 or matrix.determinant()<=0:raise ValueError('Capture requires finite positive uniform root placement')
    axes=[linear.col[i]/sizes[i] for i in range(3)]
    if max(sizes)-min(sizes)>max(sizes)*1e-6 or any(abs(axes[a].dot(axes[b]))>1e-6 for a,b in ((0,1),(0,2),(1,2))):raise ValueError('Capture requires uniform root scale without shear/reflection')
    roles=foliage.resolve_roles(state['foliage']) if state['foliage'] else {}
    count=len(roles['pm'].vertices) if roles else 0
    if count>p['max_leaves']:raise ValueError('Capture leaf budget exceeded')
    mesh_objects=[members[0]]+([roles['so']] if roles else [])
    prototypes=[roles['lo'+str(i)] for i in range(state['foliage']['recipe']['variants'])] if roles else []
    work=sum(len(o.data.vertices) for o in mesh_objects)+count*8+sum(len(o.data.vertices) for o in prototypes)
    if work>p['max_bounds_work']:raise ValueError('Capture analytical bounds work budget exceeded')
    deps,_,blockers=assemblies.dependencies({col},assemblies.references(),nested_leaf=False)
    if blockers:raise ValueError('Capture dependencies are not self-contained: '+'; '.join(blockers))
    for obj in (v for v in deps if isinstance(v,bpy.types.Object) and v not in values[4]):
        if obj.type!='EMPTY':raise ValueError('Capture source has an external object dependency')
        static_matrix(obj)
    resources=[]
    for value in sorted(deps,key=lambda v:(type(v).__name__,v.name)):
        check_cancelled()
        if value.library or value.override_library or getattr(value,'animation_data',None):raise ValueError('Capture requires local static dependencies: '+value.name)
        if isinstance(value,bpy.types.Image):
            row,_,error=assemblies.image_record(value,check_cancelled)
            if error or row.get('storage')!='PACKED':raise ValueError(error or 'Capture requires packed image inputs')
            resources.append(row)
        elif isinstance(value,(bpy.types.Material,bpy.types.NodeTree)):
            record=assemblies.record(value)
            tree=value.node_tree if isinstance(value,bpy.types.Material) else value
            if tree:record['nested_shader_state']=shader_state(tree)
            resources.append(record)
        elif isinstance(value,bpy.types.Object):
            resources.append({'object_dependency':value.name,'static_matrix':[list(r) for r in static_matrix(value)],'properties':assemblies.props(value,exclude={'matrix_world','matrix_local','matrix_basis','dimensions'})})
    low=Vector((math.inf,)*3);high=Vector((-math.inf,)*3)
    def include(v):
        if any(not math.isfinite(x) for x in v):raise ValueError('Non-finite capture geometry')
        for j in range(3):low[j]=min(low[j],v[j]);high[j]=max(high[j],v[j])
    for obj in mesh_objects:
        for vertex in obj.data.vertices:include(vertex.co)
    tris=lambda mesh:sum(max(0,len(f.vertices)-2) for f in mesh.polygons)
    total= sum(tris(o.data) for o in mesh_objects);variant_counts=[0]*len(prototypes)
    boxes=[]
    for obj in prototypes:
        mesh=obj.data
        boxes.append(corners([min(v.co[j] for v in mesh.vertices) for j in range(3)],[max(v.co[j] for v in mesh.vertices) for j in range(3)]))
    if roles:
        mesh=roles['pm'];positions=array('f',[0.])*(3*count);mesh.vertices.foreach_get('co',positions)
        def attr(key,kind,width,field):
            values=array(kind,[0])*(count*width);mesh.attributes[key].data.foreach_get(field,values);return values
        rotations=attr('leaf_rotation','f',3,'vector');scales=attr('leaf_scale','f',3,'vector');variants=attr('leaf_variant','i',1,'value')
        for i in range(count):
            if i%2048==0:check_cancelled();report_progress({'phase':'bounding native tree instances','completed':i,'total':count})
            variant=variants[i]
            if not 0<=variant<len(boxes):raise ValueError('Invalid native leaf variant index')
            variant_counts[variant]+=1;k=3*i;rotation=Euler(rotations[k:k+3],'XYZ').to_matrix();position=Vector(positions[k:k+3]);scale=scales[k:k+3]
            for corner in boxes[variant]:include(position+rotation@Vector([corner[j]*scale[j] for j in range(3)]))
        total+=sum(n*tris(o.data) for n,o in zip(variant_counts,prototypes))
    if total>p['max_render_triangles']:raise ValueError('Capture expanded render triangle budget exceeded')
    if not total or any(high[i]<=low[i] for i in range(3)):raise ValueError('Capture requires a nondegenerate whole-tree volume')
    rotation=Matrix(axes).transposed();scale=sizes[0];centre=(low+high)/2;worldcentre=matrix@centre;box=corners(low,high);views=[]
    for name in p['views']:
        u,v=map(Vector,card_views.FRAMES[name]);n=Vector(card_views.DIRECTIONS[name]);projected=[[point.dot(a) for point in box] for a in (u,v,n)]
        spans=[max(r)-min(r) for r in projected];distance=max((high-low).length*scale,.001);location=worldcentre+(rotation@n)*(distance+spans[2]*scale/2)
        basis=Matrix((rotation@u,rotation@v,rotation@n)).transposed().to_4x4();basis.translation=location
        camera='TreeCapture_'+name;index=0
        while camera in bpy.data.objects:
            index+=1;camera='TreeCapture_'+name+f'_{index}'
        views.append({'view':name,'camera':camera,'matrix_world':[list(r) for r in basis],'ortho_scale':max(spans[:2])*scale*p['margin'],
                      'clip_start':max(distance*.001,1e-6),'clip_end':distance+spans[2]*scale+max(distance*.1,.001),
                      'local_frame':{'u':list(u),'v':list(v),'normal':list(n)},'projected_bounds_local_m':{'min':[min(r) for r in projected],'max':[max(r) for r in projected]}})
    for view in views:
        if any(not math.isfinite(v) for row in view['matrix_world'] for v in row):raise ValueError('Capture camera placement exceeds finite native range')
        for key in ('ortho_scale','clip_start','clip_end'):
            prop=bpy.types.Camera.bl_rna.properties[key];value=view[key]
            if not math.isfinite(value) or not prop.hard_min<=value<=prop.hard_max:raise ValueError('Capture camera setting exceeds native range: '+key)
    summary={'format':tree_capture.FORMAT,'options':{k:p[k] for k in OPTIONS},'frame':scene.frame_current,'collection':col.name,'root':root.name,
             'source_tree_sha256':state['tree_sha256'],'model_sha256':state['model_sha256'],'resource_sha256':botany.digest(resources),
             'source_root_matrix_world':[list(r) for r in matrix],'scene_unit_scale':unit,'root_pivot_world_m':[x*unit for x in matrix.translation],
             'bounds_root_local_m':{'min':list(low),'max':list(high)},'bounds_method':'canonical wood/shoot vertices and transformed eight-corner leaf prototype boxes; conservative, no realization',
             'leaf_instances':count,'variant_counts':variant_counts,'expanded_render_triangles':total,'bounds_work':work,'views':views,
             'render_visible_objects':[root.name,*(o.name for o in mesh_objects),*([roles['po'].name] if roles else [])],
             'render_visible_collections':[col.name,*([roles['fc'].name] if roles else [])],
             'passes':dict(tree_capture.PASSES),'lighting':{'type':'UNIFORM_WHITE_WORLD','strength':p['world_strength'],'ground':False},
             'pixel_contract':{'PNG':'16-bit RGBA, Standard view, sRGB display reference','EXR':'32-bit float native multilayer data; Combined scene-linear, Normal/Position world scene coordinates, Depth native camera Z, background/no-hit and pass AA follow Blender'},
             'scope':'Static native full-density reference/data capture. Native leaf instances and materials retained. No far mesh, reconstructed PBR, depth compositing, view blending, wind, shadow proxy or optical-equivalence claim.'}
    return values,deps,summary|{'capture_sha256':botany.digest(summary)}


def capture(p):
    values,deps,plan=source(p)
    if plan['capture_sha256']!=p['expected_capture']:raise ValueError('Botanical capture plan is stale')
    scene=None;created=[]
    def cleanup():
        nonlocal scene
        if scene is not None:bpy.data.scenes.remove(scene);scene=None
        for value in reversed(created):
            table=bpy.data.objects if isinstance(value,bpy.types.Object) else bpy.data.cameras if isinstance(value,bpy.types.Camera) else bpy.data.worlds
            table.remove(value)
        created.clear()
    try:
        scene=bpy.data.scenes.new('MCP Tree Capture');scene.collection.children.link(values[0]);scene.unit_settings.scale_length=plan['scene_unit_scale'];scene.frame_current=plan['frame']
        scene.render.film_transparent=True;scene.render.use_compositing=False
        scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
        layer=scene.view_layers[0];layer.name='TreeCapture'
        for key in tree_capture.PASSES:setattr(layer,'use_pass_'+key,True)
        world=bpy.data.worlds.new('MCP Tree Capture World');created.append(world);world.use_nodes=True;scene.world=world
        world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=p['world_strength']
        for view in plan['views']:
            data=bpy.data.cameras.new(view['camera']);created.append(data);obj=bpy.data.objects.new(view['camera'],data);created.append(obj);scene.collection.objects.link(obj)
            if obj.name!=view['camera']:raise ValueError('Capture camera name allocation changed')
            obj.matrix_basis=Matrix(view['matrix_world']);data.type='ORTHO';data.ortho_scale=view['ortho_scale'];data.clip_start=view['clip_start'];data.clip_end=view['clip_end']
        params={k:p[k] for k in ('directory','samples','threads','max_bytes','timeout_seconds')}
        params.update(cameras=[v['camera'] for v in plan['views']],frame_start=plan['frame'],frame_end=plan['frame'],frame_step=1,width=p['resolution'],height=p['resolution'],engine='CYCLES',formats=['PNG','OPEN_EXR_MULTILAYER'],botanical_capture=plan)
        scene_name=scene.name
        def snapshot(path):
            bpy.data.libraries.write(str(path),{scene},fake_user=False,compress=True)
            cleanup()
            if trees.inventory(p)[-1]['tree_sha256']!=plan['source_tree_sha256']:raise ValueError('Source tree changed during capture snapshot')
        return render_batches.launch(params,scene=scene,snapshot_writer=snapshot,resource_ids=deps,scene_name=scene_name)
    finally:cleanup()


def dispatch(command,p):return source(p)[-1] if command=='inspect_botanical_view_capture' else capture(p)
