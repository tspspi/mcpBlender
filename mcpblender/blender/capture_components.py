"""Worker-only derived leaf identity; never alter editing meshes or snapshots."""
from mcpblender import botany,component_ids as schema


def indices(mesh,instancer):
    if mesh is None and instancer is None:return []
    if mesh is None or instancer is None or instancer.type!='MESH' or instancer.data!=mesh:raise ValueError('Component instancer/point mesh changed')
    source=mesh.attributes.get('leaf_index')
    if source is None or source.domain!='POINT' or source.data_type!='INT' or len(source.data)!=len(mesh.vertices):raise ValueError('Native component leaf_index attribute changed')
    values=[int(v.value) for v in source.data];count=len(values)
    if count>250000 or len(set(values))!=count or any(not 0<=v<count for v in values):raise ValueError('Native component indices must be a full unique source inventory')
    if mesh.attributes.get(schema.ATTRIBUTE) is not None:raise ValueError('Reserved component attribute already exists')
    return values


def describe(roles,fields):
    import bpy
    mesh=roles.get('pm');obj=roles.get('po');values=indices(mesh,obj)
    for row in fields['materials']:
        mat=bpy.data.materials.get(row['material'])
        if mat is None or not mat.use_nodes:raise ValueError('Component source material missing')
        if any(n.type=='OUTPUT_AOV' and n.aov_name==schema.FIELDS[0]['name'] for n in mat.node_tree.nodes):raise ValueError('Material already uses a reserved component AOV name')
    return schema.contract(fields,len(values),mesh.name if mesh is not None else None,obj.name if obj is not None else None,botany.digest(values))


def register(scene,value,fields):
    schema.validate(value,fields)
    for layer in scene.view_layers:
        existing=next((v for v in layer.aovs if v.name==schema.FIELDS[0]['name']),None)
        if existing is not None:
            if existing.type!='VALUE':raise ValueError('Component AOV type mismatch')
        else:
            aov=layer.aovs.add();aov.name=schema.FIELDS[0]['name'];aov.type='VALUE'


def install(scene,value,fields):
    import bpy
    schema.validate(value,fields)
    roles={}
    if value['point_mesh'] is not None:
        roles={'pm':bpy.data.meshes.get(value['point_mesh']),'po':bpy.data.objects.get(value['instancer'])}
        if any(v is None for v in roles.values()):raise ValueError('Component snapshot instancer missing')
    if describe(roles,fields)!=value:raise ValueError('Component snapshot inventory changed')
    register(scene,value,fields)
    if roles:
        values=indices(roles['pm'],roles['po'])
        attr=roles['pm'].attributes.new(name=schema.ATTRIBUTE,type='INT',domain='POINT')
        attr.data.foreach_set('value',[v+1 for v in values]);roles['pm'].update()
    for row in value['materials']:
        tree=bpy.data.materials[row['material']].node_tree
        attr=tree.nodes.new('ShaderNodeAttribute');attr.attribute_type='INSTANCER';attr.attribute_name=schema.ATTRIBUTE
        node=tree.nodes.new('ShaderNodeOutputAOV');node.aov_name=schema.FIELDS[0]['name'];tree.links.new(attr.outputs['Fac'],node.inputs['Value'])
