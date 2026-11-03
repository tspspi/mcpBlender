"""Guarded numeric base-mesh fields; evaluated inspection and reversible edits."""
from array import array
import math
import bpy
from mcpblender import attribute_values as codec,botany
from .assets import mesh_object
from .mesh_edit import geometry_digest
from .morphs import topology_digest
from . import assemblies

COMMANDS={'inspect_mesh_attributes','create_mesh_attribute','set_mesh_attribute_values','ramp_mesh_attribute','remove_mesh_attribute'}
RESERVED={'position','normal','corner_normal','material_index','sharp_edge','sharp_face','uv_seam','crease_edge','crease_vert','sculpt_face_set','radius','id'}


def protected(mesh,attribute):
    return attribute.name.startswith('.') or attribute.name in RESERVED or attribute.is_internal or attribute.is_required or attribute.name in mesh.uv_layers


def sizes(mesh):return {'POINT':len(mesh.vertices),'EDGE':len(mesh.edges),'FACE':len(mesh.polygons),'CORNER':len(mesh.loops)}


def component_count(mesh):
    total=0
    for attribute in mesh.attributes:
        count=len(attribute.data);width=1
        if count:
            item=attribute.data[0]
            prop=next((item.bl_rna.properties.get(k) for k in ('value','vector','color') if item.bl_rna.properties.get(k)),None)
            if prop and prop.is_array:width=prop.array_length
        total+=count*width
    return total


def check_size(mesh):
    if len(mesh.attributes)>256 or len(mesh.vertices)>1000000 or len(mesh.edges)>2000000 or len(mesh.polygons)>1000000 or len(mesh.loops)>4000000 or component_count(mesh)>64000000:raise ValueError('Numeric attribute mesh/inventory/component budget exceeded')


def selectors(mesh):
    return {'active_attribute':mesh.attributes.active.name if mesh.attributes.active else None,
            'active_color':mesh.color_attributes.active_color_name,'render_color':mesh.color_attributes.default_color_name,
            'active_uv':mesh.uv_layers.active.name if mesh.uv_layers.active else None,
            'render_uv':next((uv.name for uv in mesh.uv_layers if uv.active_render),None)}


def restore_selectors(mesh,old):
    if old['active_attribute'] and old['active_attribute'] in mesh.attributes:mesh.attributes.active=mesh.attributes[old['active_attribute']]
    if old['active_color'] and old['active_color'] in mesh.color_attributes:mesh.color_attributes.active_color_name=old['active_color']
    if old['render_color'] and old['render_color'] in mesh.color_attributes:mesh.color_attributes.default_color_name=old['render_color']
    if old['active_uv'] and old['active_uv'] in mesh.uv_layers:mesh.uv_layers.active=mesh.uv_layers[old['active_uv']]
    if old['render_uv'] and old['render_uv'] in mesh.uv_layers:mesh.uv_layers[old['render_uv']].active_render=True


def flat(attribute):
    prop,width,kind=codec.TYPES[attribute.data_type];result=array(kind,[0])*(len(attribute.data)*width)
    if result:attribute.data.foreach_get(prop,result)
    return result


def state(obj,mesh,evaluated=False):
    check_size(mesh);records=assemblies.attribute_records(mesh)
    header={'object':obj.name,'mesh':obj.data.name,'representation':'EVALUATED_MESH' if evaluated else 'BASE_MESH',
            'geometry_sha256':geometry_digest(mesh),'topology_sha256':topology_digest(mesh),
            'attributes':sorted(records,key=lambda v:v['name']),'selectors':selectors(mesh),'data_users':obj.data.users,
            'shape_keys':obj.data.shape_keys.name if obj.data.shape_keys else None}
    return header,botany.digest(header)


def inspect(p):
    bpy.context.view_layer.update();obj=mesh_object(p['name']);evaluated=None
    try:
        if p.get('evaluated',False):
            deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
        else:mesh=obj.data
        header,digest=state(obj,mesh,p.get('evaluated',False));schemas=[]
        for attribute in sorted(mesh.attributes,key=lambda a:a.name):
            schemas.append({'name':attribute.name,'data_type':attribute.data_type,'domain':attribute.domain,'count':len(attribute.data),
                            'protected':bool(protected(mesh,attribute)),'editable':not p.get('evaluated',False) and not protected(mesh,attribute) and attribute.data_type in codec.TYPES and attribute.domain in codec.DOMAINS})
        result={'name':obj.name,'mesh_data':obj.data.name,'representation':header['representation'],'attributes_sha256':digest,
                'geometry_sha256':header['geometry_sha256'],'topology_sha256':header['topology_sha256'],
                'data_users':obj.data.users,'selectors':header['selectors'],'domain_sizes':sizes(mesh),'attributes':schemas,
                'scope':'Base storage or evaluated mesh component only. Numeric values use native local coordinates/float32 storage; no unit, axis, normalization or shader conversion. Unrealized INSTANCE fields require Geometry Nodes realization for mesh readback.'}
        if p.get('attribute') is not None:
            attribute=mesh.attributes.get(p['attribute'])
            if attribute is None:raise ValueError('Mesh attribute not found')
            result.update(attribute=attribute.name,total_values=len(attribute.data),offset=p.get('offset',0),values_supported=attribute.data_type in codec.TYPES)
            if attribute.data_type in codec.TYPES:
                buffer=flat(attribute);width=codec.TYPES[attribute.data_type][1];start=p.get('offset',0);stop=min(len(attribute.data),start+p.get('limit',32));rows=[]
                for i in range(start,stop):
                    values=list(buffer[i*width:(i+1)*width]);value=values if width>1 else (bool(values[0]) if attribute.data_type=='BOOLEAN' else values[0])
                    rows.append({'index':i,'value':value if all(math.isfinite(v) for v in values) else None,'finite':all(math.isfinite(v) for v in values)})
                result.update(values=rows,next_offset=stop if stop<len(attribute.data) else None)
        return result
    finally:
        if evaluated:evaluated.to_mesh_clear()


def coordinates(mesh,domain,axis):
    if domain=='POINT':return [v.co[axis] for v in mesh.vertices]
    if domain=='CORNER':return [mesh.vertices[l.vertex_index].co[axis] for l in mesh.loops]
    if domain=='EDGE':return [sum(mesh.vertices[i].co[axis] for i in e.vertices)/2 for e in mesh.edges]
    return [sum(mesh.vertices[i].co[axis] for i in f.vertices)/len(f.vertices) for f in mesh.polygons]


def edit(command,p):
    from .bridge import check_cancelled,report_progress
    obj=mesh_object(p['name'],edit=True);original=obj.data
    if original.override_library:raise ValueError('Numeric attribute editing needs local mesh data')
    animation=original.animation_data
    if animation and (animation.action or animation.drivers or animation.nla_tracks):raise ValueError('Animated/driven mesh data requires a specialized attribute workflow')
    animation=obj.animation_data
    if animation:
        from .domains import curves
        channels=list(animation.drivers);actions=[(animation.action,getattr(animation,'action_slot',None))] if animation.action else []
        actions.extend((strip.action,getattr(strip,'action_slot',None)) for track in animation.nla_tracks for strip in track.strips if strip.action)
        for action,slot in actions:channels.extend(curves(action,slot))
        if any(c.data_path.startswith(('data.attributes','data.color_attributes')) for c in channels):raise ValueError('Object animation/drivers target mesh attributes; use a specialized workflow')
    check_cancelled();header,digest=state(obj,original)
    if digest!=p['expected_attributes']:raise ValueError('Mesh attribute fingerprint is stale; inspect base attributes again')
    attribute=original.attributes.get(p['attribute']);creating=command=='create_mesh_attribute';removing=command=='remove_mesh_attribute'
    if creating:
        if attribute is not None:raise ValueError('Attribute already exists')
        if p['attribute'] in RESERVED:raise ValueError('Protected mesh attribute name')
        data_type=p['data_type'];domain=p['domain'];count=sizes(original)[domain]
        if len(original.attributes)>=256 or component_count(original)+count*codec.TYPES[data_type][1]>64000000:raise ValueError('New attribute exceeds inventory/component budget')
        value=codec.row(data_type,p['value']);width=codec.TYPES[data_type][1];values=array(codec.TYPES[data_type][2],value if width>1 else [value])*count
    else:
        if attribute is None:raise ValueError('Custom mesh attribute not found')
        if protected(original,attribute) or attribute.data_type not in codec.TYPES or attribute.domain not in codec.DOMAINS:raise ValueError('Protected or unsupported mesh attribute; use UV/geometry/color-specific tools where applicable')
        data_type=attribute.data_type;domain=attribute.domain;count=len(attribute.data);width=codec.TYPES[data_type][1];values=flat(attribute)
        if command=='ramp_mesh_attribute':
            if data_type!='FLOAT':raise ValueError('Coordinate ramps require a FLOAT attribute')
            coords=coordinates(original,domain,'XYZ'.index(p['axis']))
            if not coords or any(not math.isfinite(v) for v in coords):raise ValueError('Ramp requires nonempty finite local coordinates')
            low=p.get('input_min');high=p.get('input_max');low=min(coords) if low is None else low;high=max(coords) if high is None else high
            if high<=low:raise ValueError('Ramp input interval is degenerate')
            for i,v in enumerate(coords):
                t=(v-low)/(high-low);t=max(0.,min(1.,t)) if p['clamp'] else t
                values[i]=codec.row('FLOAT',p['output_min']+(p['output_max']-p['output_min'])*t)
        elif not removing:
            supplied=p.get('values');indices=p.get('indices')
            if indices is None:indices=range(p.get('offset',0),p.get('offset',0)+len(supplied)) if supplied is not None else range(count)
            if any(i>=count for i in indices):raise ValueError('Attribute index/range is outside its domain')
            uniform=codec.row(data_type,p['value']) if supplied is None else None
            rows=[codec.row(data_type,v) for v in supplied] if supplied is not None else None
            for j,i in enumerate(indices):
                value=uniform if rows is None else rows[j];values[i*width:(i+1)*width]=array(codec.TYPES[data_type][2],value if width>1 else [value])
        if not removing and any(not math.isfinite(v) for v in values):raise ValueError('Updated attribute contains nonfinite values; fill the complete field to repair it')
    shared=original.users-int(original.use_fake_user)>1
    if shared and not p['make_single_user']:raise ValueError('Mesh data is shared; pass make_single_user=true to isolate this object')
    if shared and original.shape_keys:raise ValueError('Isolating a shared shape-key mesh requires a separate duplication workflow')
    old_selectors=selectors(original);backup=flat(attribute) if attribute else None;mesh=original;success=False;created_name=None
    try:
        check_cancelled()
        if shared:mesh=original.copy();mesh.use_fake_user=False
        target=mesh.attributes.get(p['attribute'])
        if creating:
            target=mesh.attributes.new(name=p['attribute'],type=data_type,domain=domain);created_name=target.name
            if target.name!=p['attribute']:raise ValueError('Native attribute name differs from request')
        if removing:mesh.attributes.remove(target)
        elif values:target.data.foreach_set(codec.TYPES[data_type][0],values)
        restore_selectors(mesh,old_selectors);mesh.update()
        if not removing and flat(target)!=values:raise ValueError('Native numeric attribute readback differs from requested float32 storage')
        report_progress({'phase':'verified numeric attribute edit','attribute':p['attribute'],'elements':count,'isolated':shared});check_cancelled()
        if shared:obj.data=mesh
        result=inspect({'name':obj.name,'attribute':None if removing else p['attribute'],'offset':0,'limit':32})
        result.update(isolated=shared,modified_attribute=p['attribute'],removed=removing)
        success=True;return result
    finally:
        if not success:
            if shared and mesh!=original:
                obj.data=original;bpy.data.meshes.remove(mesh)
            elif mesh==original:
                if creating and created_name and mesh.attributes.get(created_name):mesh.attributes.remove(mesh.attributes[created_name])
                elif attribute is not None:
                    target=mesh.attributes.get(p['attribute']) or mesh.attributes.new(name=p['attribute'],type=data_type,domain=domain)
                    if backup:target.data.foreach_set(codec.TYPES[data_type][0],backup)
                restore_selectors(mesh,old_selectors);mesh.update()


def dispatch(command,p):return inspect(p) if command=='inspect_mesh_attributes' else edit(command,p)
