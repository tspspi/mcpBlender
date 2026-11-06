"""Source-preserving preparation and isolated geometric coverage measurement."""
from array import array
import math
import bpy
from mathutils import Matrix
from mcpblender import botany,capture_data,component_ids,exr_scanline,projected_coverage as schema
from . import botanical_capture as capture,botanical_trees as trees,render_batches,capture_components

COMMANDS={'inspect_botanical_projected_coverage','capture_botanical_projected_coverage'}


def plan(p):
    from .bridge import check_cancelled,report_progress
    root,proof,meta,rows=capture_data.source({'directory':p['reference_directory'],'views':[p['view']],'max_pixels':1048576,'max_total_pixels':1048576},report_progress,check_cancelled)
    if not meta.get('component_ids'):raise ValueError('Projected coverage requires recapture with component_ids=true')
    values,deps,fresh=capture.source(meta['options'])
    binding='source_content_sha256' if meta.get('source_content_sha256') else 'source_tree_sha256'
    for key in (binding,'resource_sha256','frame','source_root_matrix_world','scene_unit_scale','component_ids'):
        if fresh[key]!=meta[key]:raise ValueError('Projected coverage source changed: '+key)
    if not meta['component_ids']['leaf_count']:raise ValueError('Projected coverage requires native leaves')
    if bpy.data.images.get(schema.IMAGE):raise ValueError('Reserved projected coverage image already exists')
    view,row=rows[0];names=['TreeCapture.Combined.A','TreeCapture.MCP_SurfaceWeight.X',*component_ids.channels()]
    decoded=exr_scanline.decode(root/row['file'],names,expected_sha256=row['sha256'],cancelled=check_cancelled,progress=report_progress)
    channels=decoded['channels'];mask,_=component_ids.filter_mask(decoded,channels[names[1]],channels[names[2]],meta['component_ids'],'LEAVES',.001,cancelled=check_cancelled)
    grid=[round(channels[names[2]][i]/channels[names[1]][i]) if keep else 0 for i,keep in enumerate(mask)]
    if not any(grid):raise ValueError('Reference view contains no leaf samples')
    result={'format':schema.FORMAT,'reference':meta,'reference_snapshot_sha256':proof['source_sha256'],'reference_exr_sha256':row['sha256'],
            'source_tree_sha256':fresh['source_tree_sha256'],'view':view,'resolution':decoded['width'],'image':schema.IMAGE,'grid_sha256':botany.digest(grid),'target_pixels':sum(mask),
            'sampling':schema.sampling(p['samples']),'scope':schema.SCOPE}
    return values,deps,grid,result|{'plan_sha256':botany.digest(result)}


def launch(p):
    values,deps,grid,planned=plan(p)
    if planned['plan_sha256']!=p['expected_plan']:raise ValueError('Projected coverage plan is stale')
    scene=None;created=[]
    def cleanup():
        nonlocal scene
        if scene is not None:bpy.data.scenes.remove(scene);scene=None
        for table,value in reversed(created):getattr(bpy.data,table).remove(value)
        created.clear()
    try:
        scene=bpy.data.scenes.new('MCP Projected Coverage');scene.collection.children.link(values[0]);scene.unit_settings.scale_length=planned['reference']['scene_unit_scale'];scene.frame_current=planned['reference']['frame']
        scene.render.film_transparent=True;scene.render.use_compositing=False;scene.view_layers[0].name=schema.LAYER
        scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
        world=bpy.data.worlds.new('MCP Coverage Black');created.append(('worlds',world));world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Strength'].default_value=0;scene.world=world
        view=planned['view'];data=bpy.data.cameras.new(view['camera']);created.append(('cameras',data));obj=bpy.data.objects.new(view['camera'],data);created.append(('objects',obj));scene.collection.objects.link(obj)
        if obj.name!=view['camera']:raise ValueError('Projected coverage camera allocation changed')
        obj.matrix_basis=Matrix(view['matrix_world']);data.type='ORTHO';data.ortho_scale=view['ortho_scale'];data.clip_start=view['clip_start'];data.clip_end=view['clip_end']
        size=planned['resolution'];image=bpy.data.images.new(schema.IMAGE,width=size,height=size,alpha=True,float_buffer=True);created.append(('images',image));image.use_fake_user=True;image.use_half_precision=False;image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED'
        pixels=array('f',[0.])*(size*size*4)
        for y in range(size):
            for x in range(size):
                i=4*((size-1-y)*size+x);pixels[i]=grid[y*size+x];pixels[i+3]=1
        image.pixels.foreach_set(pixels);image.pack()
        params={k:p[k] for k in ('directory','threads','max_bytes','timeout_seconds')}
        params.update(samples=planned['sampling']['master_samples'],cameras=[obj.name],frame_start=scene.frame_current,frame_end=scene.frame_current,frame_step=1,width=size,height=size,engine='CYCLES',formats=['OPEN_EXR_MULTILAYER'],projected_coverage=planned)
        scene_name=scene.name
        def snapshot(path):
            bpy.data.libraries.write(str(path),{scene,image},fake_user=False,compress=True)
            cleanup()
            if trees.inventory(planned['reference']['options'])[-1]['tree_sha256']!=planned['source_tree_sha256']:raise ValueError('Source changed during projected coverage snapshot')
        return render_batches.launch(params,scene=scene,snapshot_writer=snapshot,resource_ids=deps|{image},scene_name=scene_name)
    finally:cleanup()


def install(scene,value):
    """Worker-only matte: exact semantic ID predicates, never averaged IDs."""
    ref=value['reference'];contract=ref['component_ids'];mesh=bpy.data.meshes.get(contract['point_mesh']);instancer=bpy.data.objects.get(contract['instancer'])
    ids=capture_components.indices(mesh,instancer)
    if botany.digest(ids)!=contract['leaf_indices_sha256']:raise ValueError('Projected coverage native leaf inventory changed')
    attr=mesh.attributes.new(name=component_ids.ATTRIBUTE,type='INT',domain='POINT');attr.data.foreach_set('value',[v+1 for v in ids]);mesh.update()
    image=bpy.data.images[value['image']];size=value['resolution']
    if list(image.size)!=[size,size] or not image.is_float or not image.packed_file:raise ValueError('Projected coverage packed grid changed')
    pixels=image.pixels[:];grid=[]
    for y in range(size):
        for x in range(size):
            v=pixels[4*((size-1-y)*size+x)]
            if not math.isfinite(v) or v!=round(v) or not 0<=v<=len(ids):raise ValueError('Projected coverage reference ID changed')
            grid.append(int(v))
    if botany.digest(grid)!=value['grid_sha256']:raise ValueError('Projected coverage grid hash mismatch')
    matrix=Matrix(value['view']['matrix_world']);span=value['view']['ortho_scale'];camera=matrix.translation
    for item in contract['materials']:
        material=bpy.data.materials[item['material']];tree=material.node_tree;nodes=tree.nodes;nodes.clear();links=tree.links
        def node(name):return nodes.new(name)
        def mathnode(op,a,b):
            n=node('ShaderNodeMath');n.operation=op
            for socket,v in zip(n.inputs,(a,b)):
                if isinstance(v,(float,int)):socket.default_value=v
                else:links.new(v,socket)
            return n.outputs[0]
        geometry=node('ShaderNodeNewGeometry');uv=node('ShaderNodeCombineXYZ')
        for k in (0,1):
            axis=matrix.col[k].to_3d();dot=node('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';links.new(geometry.outputs['Position'],dot.inputs[0]);dot.inputs[1].default_value=axis
            projected=mathnode('ADD',mathnode('DIVIDE',dot.outputs['Value'],span),.5-camera.dot(axis)/span);links.new(projected,uv.inputs[k])
        texture=node('ShaderNodeTexImage');texture.image=image;texture.interpolation='Closest';texture.extension='CLIP';links.new(uv.outputs[0],texture.inputs['Vector'])
        split=node('ShaderNodeSeparateXYZ');links.new(texture.outputs['Color'],split.inputs[0]);reference=split.outputs['X']
        attribute=node('ShaderNodeAttribute');attribute.attribute_type='INSTANCER';attribute.attribute_name=component_ids.ATTRIBUTE
        same=mathnode('LESS_THAN',mathnode('ABSOLUTE',mathnode('SUBTRACT',attribute.outputs['Fac'],reference),0),.25)
        matched=mathnode('MULTIPLY',same,mathnode('GREATER_THAN',reference,0))
        emission=node('ShaderNodeEmission');emission.inputs['Color'].default_value=(1,1,1,1);emission.inputs['Strength'].default_value=1
        transparent=node('ShaderNodeBsdfTransparent');mix=node('ShaderNodeMixShader');links.new(matched,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);output=node('ShaderNodeOutputMaterial');links.new(mix.outputs[0],output.inputs['Surface'])
    for name in ref['render_visible_objects']:bpy.data.objects[name].hide_render=False
    for name in ref['render_visible_collections']:bpy.data.collections[name].hide_render=False
    for name in ref['render_visible_objects']:
        obj=bpy.data.objects[name]
        while obj.parent:obj=obj.parent;obj.hide_render=False
    configure_sampling(scene,value['sampling'])


def configure_sampling(scene,profile):
    scene.cycles.samples=profile['master_samples'];scene.cycles.device='CPU'
    for key,v in profile.items():
        if key not in {'effective_samples','master_samples'}:setattr(scene.cycles,key,v)


def dispatch(command,p):return plan(p)[-1] if command=='inspect_botanical_projected_coverage' else launch(p)
