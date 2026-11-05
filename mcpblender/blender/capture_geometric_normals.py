"""Worker-only face-normal AOV; preserve the surface and its shading inputs."""
from mcpblender import geometric_normals as schema


def describe(materials,rows):
    reserved={f['name'] for f in schema.FIELDS}
    if any(n.type=='OUTPUT_AOV' and n.aov_name in reserved for mat in materials for n in mat.node_tree.nodes):raise ValueError('Material already uses a reserved geometric-normal AOV name')
    return schema.contract(rows)


def install(contract):
    import bpy
    for row in contract['materials']:
        tree=bpy.data.materials[row['material']].node_tree
        geometry=tree.nodes.new('ShaderNodeNewGeometry')
        node=tree.nodes.new('ShaderNodeOutputAOV');node.aov_name=schema.FIELDS[0]['name']
        tree.links.new(geometry.outputs['True Normal'],node.inputs['Color'])
