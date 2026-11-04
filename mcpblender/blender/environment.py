"""Scene-local static world authoring, bounded image admission and staged rollback."""
import hashlib
import json
import math
from pathlib import Path
import uuid
import bpy
from mcpblender import environment_files
from mcpblender.storage import require_space
from . import assemblies,compositing
from .lods import digest

COMMANDS={'environment_catalog','inspect_environment','configure_environment'}
META='mcpblender_environment'
IMAGE_OWNER='mcpblender_environment_image_owner'
FORMAT='mcpblender-environment-v1'
NODES={'ShaderNodeBackground','ShaderNodeOutputWorld','ShaderNodeTexSky','ShaderNodeTexEnvironment','ShaderNodeTexImage',
       'ShaderNodeTexCoord','ShaderNodeMapping','ShaderNodeRGB','ShaderNodeValue','ShaderNodeMath','ShaderNodeVectorMath',
       'ShaderNodeMixRGB','ShaderNodeMix','ShaderNodeMixShader','ShaderNodeAddShader','ShaderNodeLightPath','ShaderNodeGroup',
       'ShaderNodeTexNoise','ShaderNodeTexVoronoi','ShaderNodeTexGradient','ShaderNodeTexWave','ShaderNodeTexChecker',
       'ShaderNodeValToRGB','ShaderNodeMapRange','ShaderNodeSeparateXYZ','ShaderNodeCombineXYZ','ShaderNodeSeparateColor',
       'ShaderNodeCombineColor','NodeGroupInput','NodeGroupOutput','NodeReroute','NodeFrame'}


def catalog():
    prop=bpy.types.ShaderNodeTexSky.bl_rna.properties['sky_type']
    return {'modes':['COLOR','SKY','HDRI'],'sky_models':[v.identifier for v in prop.enum_items],
            'hdri_profile':'Static 2:1 equirectangular PNG/JPEG/Radiance HDR or single-part scanline RGB(A) HALF/FLOAT EXR with equal windows. Packed private image; 64 KiB header admission before decode.',
            'default_hdri_limits':{'encoded_bytes':128*1024**2,'pixels':16*1024**2},
            'scope':'Native world lighting; no calibrated exposure/photometry, weather/cloud generation or automatic scene SUN/exposure edits.'}


def content(world):
    if world.animation_data:raise ValueError('Animated worlds require explicit animation editing')
    trees=set();pending=[world.node_tree] if world.node_tree else [];rows=[];images=set();nodes=0;links=0
    while pending:
        tree=pending.pop()
        if tree in trees:continue
        trees.add(tree);nodes+=len(tree.nodes);links+=len(tree.links)
        if len(trees)>64 or nodes>1024 or links>4096 or len(tree.interface.items_tree)>256:raise ValueError('World graph exceeds environment inspection budget')
        if tree.animation_data:raise ValueError('Animated world node groups are unsupported')
        described=[]
        for node in tree.nodes:
            if node.bl_idname not in NODES or len(node.inputs)>128 or len(node.outputs)>128:raise ValueError('Unsupported world node or socket budget: '+node.bl_idname)
            if getattr(node,'object',None) is not None:raise ValueError('Object-dependent world coordinates are unsupported')
            row=compositing.node_info(node)
            if node.type=='GROUP' and node.node_tree:pending.append(node.node_tree);row['group']=node.node_tree.name
            if getattr(node,'image',None):images.add(node.image);row['image']=node.image.name;row['image_user']=assemblies.props(node.image_user)
            described.append(row)
        rows.append({'name':tree.name,'nodes':described,'links':[(v.from_node.name,v.from_socket.identifier,v.to_node.name,v.to_socket.identifier) for v in tree.links],
                     'interface':[(v.item_type,v.name,assemblies.props(v)) for v in tree.interface.items_tree]})
    if len(images)>8:raise ValueError('Environment inspection supports at most eight image dependencies')
    if sum(v.packed_file.size for v in images if v.packed_file)>512*1024**2:raise ValueError('Environment packed image inspection budget exceeded')
    encoded=0;image_rows=[]
    for image in sorted(images,key=lambda v:v.name):
        if getattr(image,'animation_data',None):raise ValueError('Animated environment image is unsupported')
        row,size,issue=assemblies.image_record(image)
        if issue:raise ValueError(issue)
        encoded+=size
        if encoded>512*1024**2:raise ValueError('Environment encoded image inspection budget exceeded')
        image_rows.append(row)
    value={'name':world.name,'properties':assemblies.props(world),'custom':{k:v for k,v in assemblies.idprops(world).items() if k!=META},
           'fake_user':world.use_fake_user,'library':world.library.filepath if world.library else None,'groups':sorted(rows,key=lambda v:v['name']),'images':image_rows}
    for name in ('cycles','cycles_visibility','mist_settings'):
        if hasattr(world,name):value[name]=assemblies.props(getattr(world,name))
    if len(json.dumps(value,allow_nan=False))>16*1024**2:raise ValueError('Environment signature record exceeds 16 MiB')
    return value


def metadata(world):
    try:
        raw=world.get(META,'') if world else ''
        return json.loads(raw) if isinstance(raw,str) and len(raw)<65536 else {}
    except (ValueError,TypeError):return {}


def inspect(p=None):
    scene=bpy.context.scene;world=scene.world;issues=[];row=None
    if scene.library or scene.override_library:issues.append('Make the scene local before structured environment replacement')
    if world and (world.library or world.override_library):issues.append('Make the scene world local before structured replacement')
    paths=compositing.animation_paths(scene)
    if any(v=='world' or v.startswith(('world.','world[')) for v in paths):issues.append('Scene world binding/settings are keyed or driven')
    try:row=content(world) if world else None
    except (ValueError,TypeError) as exc:issues.append(str(exc))
    meta=metadata(world);managed=isinstance(meta,dict) and meta.get('format')==FORMAT
    current=digest(row) if row is not None else None
    state={'scene':scene.name,'world':row,'world_users':world.users if world else 0,'metadata':world.get(META) if world else None,'film_transparent':scene.render.film_transparent}
    guard=digest(state) if not issues else None
    suns=[{'name':o.name,'energy':o.data.energy,'hide_render':o.hide_render} for o in scene.objects if o.type=='LIGHT' and o.data.type=='SUN']
    return {'environment_sha256':guard,'scene':scene.name,'world':world.name if world else None,'world_users':world.users if world else 0,
            'managed':managed,'managed_unchanged':managed and meta.get('content_sha256')==current,
            'settings':meta.get('settings') if managed else None,'content':row,'issues':issues,'can_configure':not issues,
            'film_transparent':scene.render.film_transparent,'exposure':scene.view_settings.exposure,'sun_lights':suns[:128],'sun_lights_truncated':len(suns)>128,
            'scope':'Current scene world/film guard and bounded static graph/image signatures. Scene geometry, exposure and SUN light contents are independently controlled.'}


def native_set(owner,key,value):
    setattr(owner,key,value);actual=getattr(owner,key)
    if isinstance(value,(float,int)) and not isinstance(value,bool) and not math.isclose(actual,value,rel_tol=1e-5,abs_tol=1e-6):raise ValueError('Environment setting exceeds native limits: '+key)


def configure(p):
    from .bridge import check_cancelled,report_progress,_bridge
    scene=bpy.context.scene;old=scene.world;before=inspect()
    if not before['can_configure']:raise ValueError('Environment cannot be safely configured: '+', '.join(before['issues']))
    if p['expected_environment']!=before['environment_sha256']:raise ValueError('Environment fingerprint is stale; inspect_environment again')
    if old and (old.library or old.override_library):raise ValueError('Make the scene world local before structured replacement')
    if p.get('film_transparent') is not None:compositing.unanimated(scene,{'render.film_transparent'})
    settings=p['settings'];world=None;image=None;owner=uuid.uuid4().hex;success=False;old_fake=old.use_fake_user if old else False;old_film=scene.render.film_transparent
    retire=bool(old and before['managed_unchanged'] and old.users==1 and not old_fake)
    previous_meta=metadata(old)
    try:
        check_cancelled();world=bpy.data.worlds.new(scene.name+'_Environment');world.use_nodes=True;tree=world.node_tree;tree.nodes.clear()
        if old:
            for key,value in assemblies.props(old).items():
                if key!='use_nodes':setattr(world,key,value)
            for name in ('cycles','cycles_visibility','mist_settings'):
                if hasattr(old,name) and hasattr(world,name):
                    for key,value in assemblies.props(getattr(old,name)).items():setattr(getattr(world,name),key,value)
        bg=tree.nodes.new('ShaderNodeBackground');bg.name='Background';bg.inputs['Strength'].default_value=settings['strength']
        output=tree.nodes.new('ShaderNodeOutputWorld');output.name='Output';tree.links.new(bg.outputs['Background'],output.inputs['Surface'])
        recipe=dict(settings);mode=settings['mode']
        if mode=='COLOR':bg.inputs['Color'].default_value=(*settings['color'],1.)
        elif mode=='SKY':
            node=tree.nodes.new('ShaderNodeTexSky');node.name='Sky';available=catalog()['sky_models'];chosen=settings['sky_model']
            if chosen=='AUTO':chosen=next((v for v in ('MULTIPLE_SCATTERING','SINGLE_SCATTERING','NISHITA') if v in available),None)
            if chosen not in available:raise ValueError('Requested atmospheric sky model is unavailable')
            node.sky_type=chosen;recipe['resolved_sky_model']=chosen
            values={'sun_elevation':math.radians(settings['sun_elevation_degrees']),'sun_rotation':math.radians(settings['sun_rotation_degrees']),
                    'sun_disc':settings['sun_disc'],'sun_size':math.radians(settings['sun_size_degrees']),'sun_intensity':settings['sun_intensity'],
                    'altitude':settings['altitude_m'],'air_density':settings['air_density'],'ozone_density':settings['ozone_density'],
                    'aerosol_density' if hasattr(node,'aerosol_density') else 'dust_density':settings['aerosol_density']}
            for key,value in values.items():native_set(node,key,value)
            tree.links.new(node.outputs['Color'],bg.inputs['Color'])
        elif mode=='HDRI':
            path=Path(settings['image_path']);info=environment_files.inspect(path,settings['max_image_bytes'],settings['max_image_pixels'],check_cancelled)
            if info['width']!=2*info['height']:raise ValueError('Equirectangular environment images require a 2:1 aspect ratio')
            policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
            storage=require_space(path,info['bytes']+2*1024**2,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='packed_environment_checkpoint_heuristic')
            report_progress({'phase':'loading bounded environment image','storage':storage,'image':info});check_cancelled()
            image=bpy.data.images.load(str(path),check_existing=False);image.use_fake_user=False
            if list(image.size)!=[info['width'],info['height']] or image.source!='FILE':raise ValueError('Decoded environment differs from admitted image header')
            if settings.get('color_space'):image.colorspace_settings.name=settings['color_space']
            image.pack()
            if not image.packed_file or hashlib.sha256(image.packed_file.data).hexdigest()!=info['sha256']:raise ValueError('Environment image changed between admission and packing')
            image[IMAGE_OWNER]=owner;image.filepath='';image.name=world.name+'_Image'
            node=tree.nodes.new('ShaderNodeTexEnvironment');node.name='Environment';node.image=image;node.projection='EQUIRECTANGULAR';node.interpolation='Linear'
            coord=tree.nodes.new('ShaderNodeTexCoord');coord.name='Coordinates';mapping=tree.nodes.new('ShaderNodeMapping');mapping.name='Rotation';mapping.vector_type='VECTOR'
            mapping.inputs['Rotation'].default_value.z=math.radians(settings['rotation_degrees'])
            tree.links.new(coord.outputs['Generated'],mapping.inputs['Vector']);tree.links.new(mapping.outputs['Vector'],node.inputs['Vector']);tree.links.new(node.outputs['Color'],bg.inputs['Color'])
            recipe.pop('image_path');recipe.update(source_file=path.name,source_sha256=info['sha256'],image_size=[info['width'],info['height']],color_space=image.colorspace_settings.name,is_float=image.is_float)
        else:raise ValueError('Unsupported environment mode')
        # No scene binding has changed while constructing and validating the new graph.
        signature=digest(content(world));meta={'format':FORMAT,'id':owner,'settings':recipe,'content_sha256':signature,'owned_image':image.name if image else None}
        world[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        if inspect()['environment_sha256']!=p['expected_environment']:raise ValueError('Environment changed during staging')
        check_cancelled()
        if old and not retire and old.users==1:old.use_fake_user=True
        scene.world=world
        if p.get('film_transparent') is not None:scene.render.film_transparent=p['film_transparent']
        result=inspect()
        if not result['managed_unchanged'] or result['issues']:raise ValueError('Published environment failed verification')
        report_progress({'phase':'verified environment before handoff','mode':mode,'world':world.name});check_cancelled()
        retained=bool(old and not retire)
        if retire:
            old_image=bpy.data.images.get(previous_meta.get('owned_image') or '')
            bpy.data.worlds.remove(old)
            if old_image and old_image.users==0 and not old_image.use_fake_user and not old_image.library and old_image.get(IMAGE_OWNER)==previous_meta.get('id'):bpy.data.images.remove(old_image)
        success=True;return result|{'previous_world_retained':retained,'previous_world':before['world'],'retired_previous_managed':retire}
    finally:
        if not success:
            scene.world=old;scene.render.film_transparent=old_film
            if old:old.use_fake_user=old_fake
            if world:bpy.data.worlds.remove(world)
            if image and image.users==0:bpy.data.images.remove(image)


def dispatch(command,p):
    if command=='environment_catalog':return catalog()
    if command=='inspect_environment':return inspect(p)
    return configure(p)
