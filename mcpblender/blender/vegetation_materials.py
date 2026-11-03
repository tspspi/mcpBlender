"""Frozen native material source profiles and explicit bake requirements."""
import bpy
from mcpblender import botany,vegetation_materials as schema
from . import textures,botanical_foliage,botanical_surfaces,shaders

COMMANDS={'inspect_vegetation_materials'}
PORTS=schema.PORTS


def profile(material):
    signature=textures.material_signature(material,thin_foliage_mode='FRONT_PBR')
    front,adapter=textures.bake_surface_node(material,'FRONT_PBR');tree=material.node_tree
    thin=adapter is not None
    if thin and any(tree.nodes[n].inputs[s].is_linked for n,s in (('Leaf Sides',1),('Leaf Sides',2),('Thin Backlighting','Color'),('Optical Mix',0),('Backface Enabled',1))):raise ValueError('Linked optical parameters require baking; source-parameter metadata cannot treat them as constants')
    optics=botanical_foliage.optical_settings(material) if thin else None
    if thin and (front.inputs['Alpha'].is_linked or front.inputs['Alpha'].default_value!=1 or material.use_backface_culling==optics['double_sided']):raise ValueError('Managed thin-leaf opaque/culling profile changed; inspect the source shader before material delivery')
    detail=botanical_surfaces.inspect({'material':material.name}) if material.get(botanical_surfaces.META) else None
    if detail and not detail['detail_valid']:raise ValueError('Managed botanical material detail changed')
    inputs={};bake=[]
    for name in PORTS:
        socket=front.inputs[name];source='NODE_GRAPH' if socket.is_linked else 'GEOMETRY_NORMAL' if name=='Normal' else 'UNLINKED';value=None if socket.is_linked or name=='Normal' else shaders.plain(socket.default_value)
        if thin and name=='Base Color' and len(socket.links)==1 and socket.links[0].from_node==tree.nodes['Leaf Sides']:
            source='CONSTANT_FRONT';value=optics['front_color']
        image_binding=None
        if socket.is_linked and len(socket.links)==1 and socket.links[0].from_node.type=='TEX_IMAGE':
            image_node=socket.links[0].from_node;vector=image_node.inputs['Vector']
            if len(vector.links)==1 and vector.links[0].from_node.type=='UVMAP' and vector.links[0].from_node.uv_map:
                frozen=next(n['image'] for n in signature['nodes'] if n['name']==image_node.name)
                source='TEXTURE_IMAGE';image_binding={'image_sha256':frozen['content'],'size':frozen['size'],'color_space':frozen['color_space'],'uv_map':vector.links[0].from_node.uv_map,'output':socket.links[0].from_socket.identifier}
        inputs[name]={'source':source,'value':value}
        if image_binding:inputs[name]['image_binding']=image_binding
        if source=='NODE_GRAPH':bake.append(name)
    alpha={'mode':'OPAQUE' if inputs['Alpha']['value']==1 else 'UNRESOLVED','cutoff':None,'factor':inputs['Alpha']['value']}
    transmission={'model':'ARTISTIC_DIFFUSE_BACKLIGHT' if thin else 'PRINCIPLED_SURFACE' if inputs['Transmission Weight']['value']!=0 else 'NONE','weight':optics['translucent_mix'] if thin else inputs['Transmission Weight']['value'],
                  'color_linear_rgba':optics['transmission_color'] if thin else None,'thickness_m':None}
    return {'name':material.name,'source_sha256':botany.digest(signature),'model':'MANAGED_THIN_FOLIAGE' if thin else 'PRINCIPLED',
       'double_sided':optics['double_sided'] if thin else not material.use_backface_culling,'alpha':alpha,'transmission':transmission,
       'source_base_colors':{'front':optics['front_color'],'back':optics['back_color']} if thin else None,
       'front_inputs':inputs,'maps':{kind:None for kind in schema.MAPS},'detail':detail['settings'] if detail else None,
       'bake_required_inputs':bake,'bake_adapter':adapter,'delivery':'NATIVE_PARAMETERS','portable_optical_equivalence':False,
       'omitted_from_native_gltf_qualification':['native back color','artistic translucent backlighting','physical thickness/transmission calibration','procedural graph/texture fidelity'] if thin else ['procedural graph/texture fidelity'],
       'bake_hint':{'thin_foliage_mode':'FRONT_PBR' if thin else 'REFUSE','maps':['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AO','ALPHA']}}


def contract(objects):
    slots={};materials={};used={};uv={}
    for role,obj in objects.items():
        row=list(obj.data.materials)
        if not row or any(mat is None for mat in row):raise ValueError('Every vegetation material slot needs a material')
        uv[role]=[u.name for u in obj.data.uv_layers];slots[role]=[mat.name for mat in row];used[role]=sorted({f.material_index for f in obj.data.polygons})
        for mat in row:materials[mat.name]=mat
    return schema.finish([profile(mat) for mat in materials.values()],slots,used,uv)


def inspect(p):
    if p.get('collection'):
        from . import botanical_trees,botanical_foliage
        values=botanical_trees.inventory(p)
        if not values[-1]['valid']:raise ValueError('Material inspection requires a valid botanical source')
        objects={'wood':values[2][0]};meta=values[-1]['foliage']
        if meta and meta['metrics']['leaves']:
            roles=botanical_foliage.resolve_roles(meta);objects['shoots']=roles['so'];objects.update({f'leaf-{i}':roles['lo'+str(i)] for i in range(meta['recipe']['variants'])})
        result=contract(objects);return {'contract':result,'materials_sha256':result['materials_sha256']}
    if p.get('lod_collection'):
        from . import vegetation_lods
        col,owned,meta,state=vegetation_lods.inspect(p)
        if not state['valid']:raise ValueError('Material inspection requires a valid owned LOD profile')
        result=contract(lod_objects(col,meta));return {'contract':result,'materials_sha256':result['materials_sha256']}
    materials=[]
    for name in p['materials']:
        material=bpy.data.materials.get(name)
        if material is None:raise ValueError('Vegetation material not found: '+name)
        materials.append(profile(material))
    result=schema.finish(materials,{})
    return {'contract':result,'materials_sha256':result['materials_sha256'],'scope':'Frozen source parameters and bake requirements. No textures generated, native glTF fidelity, alpha-card or physical thickness calibration.'}


def dispatch(command,p):return inspect(p)


def lod_objects(col,meta):
    objects={f"lod-{l['level']}-{role}":bpy.data.objects[l['objects'][i]] for l in meta['levels'] for i,role in enumerate(('wood','shoots'))}
    objects.update({f'leaf-{i}':obj for i,obj in enumerate(sorted(col['mcpblender_leaf_sources'].objects,key=lambda o:o.name))})
    return objects
