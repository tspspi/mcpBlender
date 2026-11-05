"""Worker-only unit normal-input moments with strict shared-closure admission."""
from mcpblender import botany,normal_moments as schema
from . import textures
from .capture_material_fields import binding


def describe(materials,base_rows):
    rows=[];lookup={v.name:v for v in materials}
    for row in base_rows:
        mat=lookup[row['material']];surface,thin=textures.bake_surface_node(mat,'FRONT_PBR')
        normal=binding(surface,'Normal');back=binding(mat.node_tree.nodes['Thin Backlighting'],'Normal') if thin else None
        if back is not None and back['source']!=normal['source']:raise ValueError('Normal moments require shared reflective/translucent normal inputs')
        if any(n.type=='OUTPUT_AOV' and n.aov_name in {f['name'] for f in schema.FIELDS} for n in mat.node_tree.nodes):raise ValueError('Material already uses a reserved normal-moment AOV name')
        rows.append({'material':row['material'],'id':row['id'],'normal':normal,'thin_normal':back})
    value={'format':schema.FORMAT,'fields':schema.FIELDS,'materials':rows,'coordinate_space':'WORLD','normalization':'PER_HIT_SAFE_UNIT_INPUT','zero_length_fallback':'GEOMETRY_NORMAL',
           'scope':'Renderer-safe normalized linked inputs with geometry-normal fallback at zero squared length, or implicit geometry normals when unlinked. Managed closures must share the same normal source. First/second moments do not identify a unique distribution; validate native Normal agreement and unit/covariance bounds.'}
    value['moments_sha256']=botany.digest(value);schema.validate(value,base_rows);return value


def install(contract):
    import bpy
    for row in contract['materials']:
        tree=bpy.data.materials[row['material']].node_tree;source=row['normal']['source']
        geometry=tree.nodes.new('ShaderNodeNewGeometry').outputs['Normal']
        if source:
            socket=next(s for s in tree.nodes[source['node']].outputs if s.identifier==source['socket'])
        else:socket=geometry
        unit=tree.nodes.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';tree.links.new(socket,unit.inputs[0])
        # Match Cycles safe_normalize_fallback(N, sd->N), not an inferred repair.
        squared=tree.nodes.new('ShaderNodeVectorMath');squared.operation='DOT_PRODUCT';tree.links.new(socket,squared.inputs[0]);tree.links.new(socket,squared.inputs[1])
        valid=tree.nodes.new('ShaderNodeMath');valid.operation='GREATER_THAN';tree.links.new(squared.outputs['Value'],valid.inputs[0]);valid.inputs[1].default_value=0
        inverse=tree.nodes.new('ShaderNodeMath');inverse.operation='SUBTRACT';inverse.inputs[0].default_value=1;tree.links.new(valid.outputs[0],inverse.inputs[1])
        a=tree.nodes.new('ShaderNodeVectorMath');a.operation='SCALE';tree.links.new(unit.outputs[0],a.inputs[0]);tree.links.new(valid.outputs[0],a.inputs['Scale'])
        b=tree.nodes.new('ShaderNodeVectorMath');b.operation='SCALE';tree.links.new(geometry,b.inputs[0]);tree.links.new(inverse.outputs[0],b.inputs['Scale'])
        safe=tree.nodes.new('ShaderNodeVectorMath');safe.operation='ADD';tree.links.new(a.outputs[0],safe.inputs[0]);tree.links.new(b.outputs[0],safe.inputs[1])
        xyz=tree.nodes.new('ShaderNodeSeparateXYZ');tree.links.new(safe.outputs[0],xyz.inputs[0])
        outputs=dict(zip('XYZ',xyz.outputs))
        for field in schema.FIELDS:
            key=field['key']
            if len(key)==1:value=outputs[key]
            else:
                node=tree.nodes.new('ShaderNodeMath');node.operation='MULTIPLY';tree.links.new(outputs[key[0]],node.inputs[0]);tree.links.new(outputs[key[1]],node.inputs[1]);value=node.outputs[0]
            node=tree.nodes.new('ShaderNodeOutputAOV');node.aov_name=field['name'];tree.links.new(value,node.inputs['Value'])
