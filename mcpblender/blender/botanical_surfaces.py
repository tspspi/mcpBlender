"""Editable UV botanical detail; staged node handoff preserves shared material IDs."""
import json
import math
import uuid
import bpy
from mcpblender import botany
from . import assemblies,shaders,botanical_foliage
COMMANDS={'create_botanical_surface','inspect_botanical_surface','configure_botanical_surface','remove_botanical_surface'}
META='mcpblender_botanical_surface'


def ramp_record(node):
    ramp=node.color_ramp
    return (node.name,ramp.interpolation,ramp.color_mode,ramp.hue_interpolation,[(e.position,list(e.color)) for e in ramp.elements])


def managed_digest(mat,names):
    record=assemblies.record(mat.node_tree)
    return botany.digest({'ramps':[ramp_record(n) for n in mat.node_tree.nodes if n.name in names and n.type=='VALTORGB'],'nodes':[n for n in record['nodes'] if n[0] in names], 'links':[l for l in record['links'] if l[0] in names or l[2] in names]})


def inspect(p):
    mat=shaders.material(p['material']);raw=mat.get(META);meta=json.loads(raw) if raw else None
    valid=bool(mat.use_nodes and mat.node_tree and meta and meta.get('version')==1 and all(n in mat.node_tree.nodes for n in meta['nodes']) and managed_digest(mat,set(meta['nodes']))==meta['managed_sha256'])
    mesh_users=[o for o in bpy.data.objects if o.type=='MESH' and any(slot.material==mat for slot in o.material_slots)]
    missing=[o.name for o in mesh_users if meta and not o.data.uv_layers.get(meta['settings']['uv_map'])]
    return {'mesh_uv_users_checked':len(mesh_users),'mesh_uv_users_missing':missing[:64],'mesh_uv_users_missing_count':len(missing),'material':mat.name,'material_sha256':botany.digest({'material':assemblies.record(mat),'ramps':[ramp_record(n) for n in mat.node_tree.nodes if n.type=='VALTORGB']} if mat.node_tree else assemblies.record(mat)),'use_nodes':mat.use_nodes,'managed':meta is not None,'detail_valid':valid,
            'settings':meta['settings'] if meta else None,'users':mat.users,
            'scope':'Shared UV-driven color/bump detail. Bump distance is a native shader setting, not geometry displacement or measured tissue thickness. No images or atlas generated.'}


def port(tree,item):return shaders.resolve(tree.nodes[item['node']].inputs,item['socket'])
def source_port(tree,item):return shaders.resolve(tree.nodes[item['node']].outputs,item['socket'])
def capture(socket):
    return {'default':shaders.plain(socket.default_value),'links':[{'node':l.from_node.name,'socket':l.from_socket.identifier} for l in socket.links]}
def restore(tree,socket,state):
    for link in list(socket.links):tree.links.remove(link)
    socket.default_value=state['default']
    for source in state['links']:tree.links.new(source_port(tree,source),socket)


def originals(mat,profile,meta):
    if meta:
        if meta['settings']['profile']!=profile:raise ValueError('Botanical surface profile cannot change in place; remove detail first')
        return meta['originals']
    tree=mat.node_tree
    if profile=='OAK_LEAF':
        botanical_foliage.inspect_material({'material':mat.name})
        surface=tree.nodes['Leaf Surface'];targets=[('COLOR',surface.inputs['Base Color']),('NORMAL',surface.inputs['Normal']),('BACK_NORMAL',tree.nodes['Thin Backlighting'].inputs['Normal'])]
    else:
        outputs=[n for n in tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
        if len(outputs)!=1 or outputs[0].inputs['Volume'].is_linked or not outputs[0].inputs['Surface'].is_linked:raise ValueError('Bark detail requires a surface-only Principled material')
        surface=outputs[0].inputs['Surface'].links[0].from_node
        if surface.type!='BSDF_PRINCIPLED':raise ValueError('Bark detail requires direct Principled surface')
        targets=[('COLOR',surface.inputs['Base Color']),('NORMAL',surface.inputs['Normal'])]
    return [{'role':role,'node':socket.node.name,'socket':socket.identifier,'state':capture(socket)} for role,socket in targets]


def build(mat,p,original):
    tree=mat.node_tree;names=[];prefix='Botanical_'+uuid.uuid4().hex[:12]+'_'
    def node(kind,name):
        value=tree.nodes.new(kind);value.name=prefix+name;value.label=name;names.append(value.name);return value
    def link(a,b):tree.links.new(a,b)
    def math_node(name,op,a,b=None):
        value=node('ShaderNodeMath',name);value.operation=op
        for socket,input in zip(value.inputs,(a,b)):
            if input is None:continue
            if isinstance(input,(int,float)):socket.default_value=input
            else:link(input,socket)
        return value.outputs[0]
    coords=node('ShaderNodeUVMap','Surface UV');coords.uv_map=p['uv_map']
    bump=node('ShaderNodeBump','Surface Relief');bump.inputs['Distance'].default_value=p['bump_distance'];bump.inputs['Strength'].default_value=p['bump_strength']
    if p['profile']=='OAK_BARK':
        scale=node('ShaderNodeVectorMath','Longitudinal Scale');scale.operation='MULTIPLY';scale.inputs[1].default_value=(p['cross_scale'],p['length_scale'],1);link(coords.outputs['UV'],scale.inputs[0])
        noise=node('ShaderNodeTexNoise','Bark Fissures');noise.inputs['Scale'].default_value=1;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7;noise.inputs['Distortion'].default_value=.25;link(scale.outputs['Vector'],noise.inputs['Vector'])
        cells=node('ShaderNodeTexVoronoi','Longitudinal Fissures');cells.feature='DISTANCE_TO_EDGE';cells.inputs['Scale'].default_value=1;link(scale.outputs['Vector'],cells.inputs['Vector'])
        ramp=node('ShaderNodeValToRGB','Bark Tones');ramp.color_ramp.elements[0].position=.025;ramp.color_ramp.elements[0].color=p['dark_color'];ramp.color_ramp.elements[1].position=.13;ramp.color_ramp.elements[1].color=p['light_color'];link(cells.outputs['Distance'],ramp.inputs[0])
        plates=math_node('Bark Plateaus','MINIMUM',math_node('Fissure Height','MULTIPLY',cells.outputs['Distance'],8),1)
        height=math_node('Fine Bark Relief','ADD',plates,math_node('Grain Height','MULTIPLY',noise.outputs['Fac'],.12));link(height,bump.inputs['Height'])
        tint=node('ShaderNodeMixRGB','Bark Mottling');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.25;link(ramp.outputs['Color'],tint.inputs[1]);link(noise.outputs['Color'],tint.inputs[2]);color=tint.outputs[0]
    else:
        channels=node('ShaderNodeSeparateXYZ','Blade Coordinates');link(coords.outputs['UV'],channels.inputs[0])
        lateral=math_node('Lateral Distance','ABSOLUTE',math_node('Centered U','SUBTRACT',channels.outputs['X'],.5))
        slant=math_node('Vein Slant','SUBTRACT',math_node('Vein Count','MULTIPLY',channels.outputs['Y'],p['vein_pairs']),math_node('Vein Angle','MULTIPLY',lateral,p['vein_slope']))
        phase=math_node('Vein Phase','MULTIPLY',math_node('Vein Offset','ADD',slant,.5),math.pi)
        waves=math_node('Vein Waves','ABSOLUTE',math_node('Vein Sine','SINE',phase))
        side=math_node('Secondary Veins','MAXIMUM',math_node('Vein Width','SUBTRACT',1,math_node('Vein Profile','DIVIDE',waves,p['vein_width'])),0)
        midrib=math_node('Midrib','MAXIMUM',math_node('Midrib Width','SUBTRACT',1,math_node('Midrib Profile','DIVIDE',lateral,p['midrib_width'])),0)
        height=math_node('Combined Veins','MAXIMUM',side,midrib);link(height,bump.inputs['Height'])
        tint=node('ShaderNodeMixRGB','Vein Color');tint.inputs[2].default_value=p['vein_color'];link(math_node('Vein Contrast','MULTIPLY',height,p['color_strength']),tint.inputs[0])
        base=next(v for v in original if v['role']=='COLOR')['state']
        if base['links']:link(source_port(tree,base['links'][0]),tint.inputs[1])
        else:tint.inputs[1].default_value=base['default']
        color=tint.outputs[0]
    return names,color,bump


def configure(p):
    from .bridge import check_cancelled
    state=inspect(p);mat=shaders.material(p['material'],edit=True);tree=mat.node_tree
    if tree is None or not mat.use_nodes:raise ValueError('Botanical surface requires an enabled node material')
    if len(tree.nodes)>192:raise ValueError('Botanical detail requires at most 192 existing shader nodes')
    if state['material_sha256']!=p['expected_material']:raise ValueError('Botanical surface material guard is stale')
    if state['managed'] and not state['detail_valid']:raise ValueError('Managed botanical detail was edited; preserve/reconcile those edits before rebuilding')
    previous=mat.get(META);meta=json.loads(previous) if previous else None;original=originals(mat,p['settings']['profile'],meta)
    before=set(tree.nodes);current=[capture(port(tree,item)) for item in original];success=False
    try:
        check_cancelled();names,color,bump=build(mat,p['settings'],original)
        normal=next(v for v in original if v['role']=='NORMAL')['state']
        if normal['links']:tree.links.new(source_port(tree,normal['links'][0]),bump.inputs['Normal'])
        for item in original:tree.links.new(color if item['role']=='COLOR' else bump.outputs['Normal'],port(tree,item))
        # Output handoff is reversible until the final old-node deletion.
        check_cancelled();record={'version':1,'settings':p['settings'],'nodes':names,'originals':original,'managed_sha256':managed_digest(mat,set(names))}
        mat[META]=json.dumps(record,sort_keys=True,allow_nan=False)
        if meta:
            for name in meta['nodes']:tree.nodes.remove(tree.nodes[name])
        success=True;return inspect(p)
    finally:
        if not success:
            for item,saved in zip(original,current):restore(tree,port(tree,item),saved)
            for value in set(tree.nodes)-before:tree.nodes.remove(value)
            if previous is None:
                if META in mat:del mat[META]
            else:mat[META]=previous


def remove(p):
    from .bridge import check_cancelled
    state=inspect(p);mat=shaders.material(p['material'],edit=True);tree=mat.node_tree
    if state['material_sha256']!=p['expected_material']:raise ValueError('Botanical surface material guard is stale')
    if not state['detail_valid']:raise ValueError('Unchanged managed botanical detail required')
    meta=json.loads(mat[META]);current=[capture(port(tree,i)) for i in meta['originals']];success=False
    try:
        check_cancelled()
        for item in meta['originals']:restore(tree,port(tree,item),item['state'])
        check_cancelled()
        for name in meta['nodes']:tree.nodes.remove(tree.nodes[name])
        del mat[META];success=True;return inspect(p)
    finally:
        if not success:
            for item,saved in zip(meta['originals'],current):restore(tree,port(tree,item),saved)


def dispatch(command,p):
    if command=='inspect_botanical_surface':return inspect(p)
    if command=='configure_botanical_surface':return configure(p)
    if command=='remove_botanical_surface':return remove(p)
    from .bridge import check_cancelled
    if bpy.data.materials.get(p['material']):raise ValueError('Material already exists')
    before=set(bpy.data.user_map());success=False
    try:
        check_cancelled()
        if p['settings']['profile']=='OAK_LEAF':mat=botanical_foliage.material(p['material'])
        else:mat=bpy.data.materials.new(p['material']);mat.use_nodes=True;mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.85
        if mat.name!=p['material']:raise ValueError('Botanical material name collision/truncation')
        state=inspect(p);result=configure(p|{'expected_material':state['material_sha256']});check_cancelled();success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))
