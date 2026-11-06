"""Owned root-relative component-column clipping; original BSDFs are retained."""
from array import array
from pathlib import Path
import bpy
from mathutils import Matrix
from mcpblender import botany,component_ids,exr_scanline

RECIPE='NATIVE_COMPONENT_COLUMN_COMPLEMENT_V1'
SCOPE='Retain all native leaf instances, making same-component fragments transparent inside their captured reference pixel columns. Private leaf materials and packed ID grid; unchanged original BSDF outside clipped columns, no depth/plane tolerance. Root-relative static captured view. Same-leaf self-occlusion is ambiguous; not face identity, optical equivalence, wind or reduced template LOD.'


def outputs(material):
    if not material.use_nodes:raise ValueError('Column complement requires node materials')
    result=[n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output and n.target in {'ALL','CYCLES'}]
    if len(result)!=1 or len(result[0].inputs['Surface'].links)!=1:raise ValueError('Column complement requires one active Cycles surface output')
    return result[0]


def plan(meta,view,row,grid):
    matrix=Matrix(meta['source_root_matrix_world']);camera=Matrix(view['matrix_world']);scale=matrix.to_3x3().col[0].length
    return {'recipe':RECIPE,'view':view,'resolution':meta['options']['resolution'],'reference_exr':{'file':row['file'],'sha256':row['sha256']},
            'grid_sha256':botany.digest(grid),'target_pixels':sum(v>0 for v in grid),'decoded_image_bytes':len(grid)*16,
            'projector':{'camera_root_local':list(matrix.inverted()@camera.translation),'u':view['local_frame']['u'],'v':view['local_frame']['v'],'span_root_local':view['ortho_scale']/scale},'scope':SCOPE}


def install(directory,prefix,root,prototypes,population,planned,*,private_materials=()):
    from .bridge import check_cancelled,report_progress
    column=planned['column_complement'];reference=column['reference_exr'];size=column['resolution']
    names=['TreeCapture.Combined.A','TreeCapture.MCP_SurfaceWeight.X',*component_ids.channels()]
    decoded=exr_scanline.decode(Path(directory)/reference['file'],names,expected_sha256=reference['sha256'],cancelled=check_cancelled,progress=report_progress)
    c=decoded['channels'];grid=[]
    for i,(alpha,weight,identity) in enumerate(zip(*(c[n] for n in names))):
        if i%8192==0:check_cancelled()
        grid.append(round(identity/weight) if alpha>planned['settings']['alpha_threshold'] and weight>0 and identity>0 else 0)
    if decoded['width']!=size or decoded['height']!=size or botany.digest(grid)!=column['grid_sha256']:raise ValueError('Column complement reference grid changed')
    image=bpy.data.images.new(prefix+'-ColumnIDs',width=size,height=size,alpha=True,float_buffer=True);image.use_half_precision=False;image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED'
    pixels=array('f',[0.])*(size*size*4)
    for y in range(size):
        for x in range(size):
            i=4*((size-1-y)*size+x);pixels[i]=grid[y*size+x];pixels[i+3]=1
    image.pixels.foreach_set(pixels);image.pack()
    mesh=population.data
    if mesh.attributes.get(component_ids.ATTRIBUTE):raise ValueError('Reserved native component attribute already exists')
    attribute=mesh.attributes.new(name=component_ids.ATTRIBUTE,type='INT',domain='POINT');attribute.data.foreach_set('value',[v.value+1 for v in mesh.attributes['leaf_index'].data]);mesh.update()
    materials={}
    for obj in prototypes.objects:
        for slot in obj.material_slots:
            source=slot.material
            if source not in materials:
                check_cancelled();mat=source if source in private_materials else source.copy()
                if mat!=source:mat.name=prefix+'-Column-'+source.name
                mat.use_fake_user=False;materials[source]=mat
                wrap(mat,root,image,column['projector'])
            slot.material=materials[source]


def wrap(material,root,image,projector):
    output=outputs(material);tree=material.node_tree;nodes=tree.nodes;links=tree.links;original=output.inputs['Surface'].links[0].from_socket
    def node(kind):return nodes.new(kind)
    def mathnode(op,a,b=0):
        n=node('ShaderNodeMath');n.operation=op
        for socket,v in zip(n.inputs,(a,b)):
            if isinstance(v,(int,float)):socket.default_value=v
            else:links.new(v,socket)
        return n.outputs[0]
    coordinates=node('ShaderNodeTexCoord');coordinates.object=root;coordinates.from_instancer=False;uv=node('ShaderNodeCombineXYZ');span=projector['span_root_local']
    for k,key in enumerate(('u','v')):
        axis=projector[key];dot=node('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';links.new(coordinates.outputs['Object'],dot.inputs[0]);dot.inputs[1].default_value=axis
        value=mathnode('ADD',mathnode('DIVIDE',dot.outputs['Value'],span),.5-sum(a*b for a,b in zip(projector['camera_root_local'],axis))/span);links.new(value,uv.inputs[k])
    tex=node('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='CLIP';links.new(uv.outputs[0],tex.inputs['Vector'])
    separate=node('ShaderNodeSeparateXYZ');links.new(tex.outputs['Color'],separate.inputs[0]);reference=separate.outputs['X']
    attribute=node('ShaderNodeAttribute');attribute.attribute_type='INSTANCER';attribute.attribute_name=component_ids.ATTRIBUTE
    same=mathnode('LESS_THAN',mathnode('ABSOLUTE',mathnode('SUBTRACT',attribute.outputs['Fac'],reference)),.25)
    matched=mathnode('MULTIPLY',same,mathnode('GREATER_THAN',reference,0))
    transparent=node('ShaderNodeBsdfTransparent');mix=node('ShaderNodeMixShader');links.new(matched,mix.inputs[0]);links.new(original,mix.inputs[1]);links.new(transparent.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],output.inputs['Surface'])
