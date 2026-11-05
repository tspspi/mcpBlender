"""Guarded shader-input AOV wiring confined to the independent render worker."""
import bpy
from mcpblender import botany,capture_material_fields as schema
from . import textures,shaders

PORTS={'base_color':'Base Color','roughness':'Roughness','metallic':'Metallic','alpha':'Alpha','emission_color':'Emission Color',
       'emission_strength':'Emission Strength','ior':'IOR','transmission_weight':'Transmission Weight'}


def binding(node,socket):
    port=node.inputs[socket]
    if len(port.links)>1:raise ValueError('Material input has ambiguous links')
    return {'node':node.name,'socket':port.identifier,'source':{'node':port.links[0].from_node.name,'socket':port.links[0].from_socket.identifier} if port.links else None,'default':shaders.plain(port.default_value)}


def describe(materials,*,normal_moments=False):
    rows=[]
    for index,mat in enumerate(sorted(set(materials),key=lambda v:v.name)):
        if not mat.use_nodes or mat.animation_data or mat.node_tree.animation_data:raise ValueError('Material fields require static enabled node shaders')
        node,adapter=textures.bake_surface_node(mat,'FRONT_PBR')
        # Only use the existing managed-topology verifier to find this node.
        # Do not apply the FRONT_PBR bake adapter: retain side/backlight/cull graph.
        if node.mute or adapter is not None and any(mat.node_tree.nodes[name].mute for name in textures.THIN_NODES):raise ValueError('Material fields require unmuted surface/managed optical nodes')
        if any(n.type=='OUTPUT_AOV' and n.aov_name in {r['name'] for r in schema.FIELDS} for n in mat.node_tree.nodes):raise ValueError('Material already uses a reserved capture AOV name')
        bindings={key:binding(node,port) for key,port in PORTS.items()};thin=adapter is not None
        bindings.update(thin_color=binding(mat.node_tree.nodes['Thin Backlighting'],'Color') if thin else {'constant':[0.,0.,0.,1.]},
                        thin_weight=binding(mat.node_tree.nodes['Optical Mix'],0) if thin else {'constant':0.},thin_mode={'constant':1. if thin else 0.},
                        cull_weight=binding(mat.node_tree.nodes['Backface Enabled'],1) if thin else {'constant':float(mat.use_backface_culling)},
                        surface_weight={'constant':1.},material_id={'constant':float(index+1)})
        rows.append({'material':mat.name,'id':index+1,'model':'MANAGED_THIN_FOLIAGE' if thin else 'PRINCIPLED','bindings':bindings,
                     'omitted_principled_inputs':[binding(node,i) for i,p in enumerate(node.inputs) if p.name not in PORTS.values()],
                     'thickness_m':None,'thin_model':'ARTISTIC_DIFFUSE_BACKLIGHT' if thin else 'NONE'})
    result={'format':schema.FORMAT,'fields':schema.FIELDS,'materials':rows,
            'normal_source':'Native world-space Normal pass; no normalization or inferred replacement.',
            'weighting':'Raw shader AOVs with separate constant-one surface_weight. Divide by this weight only where valid, never by beauty alpha. Values may average different source surfaces/materials within one pixel.',
            'scope':'View-evaluated native shader inputs, not beauty colors. Managed thin-leaf backfacing, procedural/texture links and backlighting inputs are retained; no front forcing. No physical thickness, complete BSDF reconstruction, transport/optical equivalence or dynamic side recovery from one view.'}
    if normal_moments:
        from . import capture_normal_moments
        result['normal_moments']=capture_normal_moments.describe(materials,rows)
    result['fields_sha256']=botany.digest(result);schema.validate(result);return result


def register(scene,contract):
    schema.validate(contract)
    for layer in scene.view_layers:
        existing={v.name:v.type for v in layer.aovs}
        fields=list(schema.FIELDS)
        if contract.get('normal_moments'):fields+=contract['normal_moments']['fields']
        for field in fields:
            if field['name'] in existing:
                if existing[field['name']]!=field['type']:raise ValueError('Capture AOV type mismatch')
            else:
                aov=layer.aovs.add();aov.name=field['name'];aov.type=field['type']


def install(scene,contract):
    materials=[]
    for row in contract['materials']:
        mat=bpy.data.materials.get(row['material'])
        if mat is None:raise ValueError('Capture material missing from snapshot')
        materials.append(mat)
    if describe(materials,normal_moments=bool(contract.get('normal_moments')))!=contract:raise ValueError('Snapshot material field bindings changed')
    register(scene,contract)
    fields={f['key']:f for f in schema.FIELDS}
    for row,mat in zip(contract['materials'],materials):
        tree=mat.node_tree
        for key,b in row['bindings'].items():
            field=fields[key];node=tree.nodes.new('ShaderNodeOutputAOV');node.name=field['name'];node.aov_name=field['name'];port=node.inputs['Color' if field['type']=='COLOR' else 'Value']
            if b.get('source'):
                source=b['source'];socket=next(s for s in tree.nodes[source['node']].outputs if s.identifier==source['socket']);tree.links.new(socket,port)
            else:port.default_value=b['constant'] if 'constant' in b else b['default']

    if contract.get('normal_moments'):
        from . import capture_normal_moments
        capture_normal_moments.install(contract['normal_moments'])
