"""Trusted atlas assembly inside the existing owned texture worker process."""
from array import array
from pathlib import Path
import bpy
from . import textures
from .assets import finished
from mcpblender.texture_files import read_json,write_json,manifest


def run(job,root,status):
    from .texture_atlas import guard
    info=guard(job,cancelled=lambda:None,progress=lambda v:status('verifying atlas inputs'));plan=info['atlas'];layout=plan['layout'];geometry=[];vertices=0;corners=0;defaults=None
    for entry in plan['inputs']:
        directory=Path(entry['directory']);saved=read_json(directory/'manifest.json')
        status('loading verified atlas geometry',entry=entry['id'])
        bpy.ops.wm.open_mainfile(filepath=str(directory/'asset.blend'),load_ui=False,use_scripts=False)
        # Recheck native binding in the actual file, beyond file hashes alone.
        for _ in textures.validate({'directory':str(directory)}):pass
        obj=bpy.data.objects[saved['name']];mesh=obj.data;vertices+=len(mesh.vertices);corners+=len(mesh.loops)
        if vertices>1000000 or corners>2000000 or len(mesh.vertices)>250000 or len(mesh.uv_layers)!=1 or obj.modifiers or obj.constraints or obj.matrix_world.to_3x3().determinant()<=1e-12:raise ValueError('Atlas requires bounded single-UV static baked meshes with positive nonsingular transforms')
        surface=obj.data.materials[0].node_tree.nodes['Surface'];values={}
        for index,socket in enumerate(surface.inputs):
            if not socket.is_linked and hasattr(socket,'default_value'):
                value=socket.default_value
                try:value=list(value)
                except TypeError:pass
                values[str(index)]=value
        if defaults is not None and defaults!=values:raise ValueError('Atlas entries have different untextured PBR constants')
        defaults=values;unit=bpy.context.scene.unit_settings.scale_length
        normal=obj.matrix_world.to_3x3().inverted().transposed();origin=obj.matrix_world.translation*unit
        coords=[tuple((obj.matrix_world@v.co)*unit-origin) for v in mesh.vertices]
        uv=mesh.uv_layers[0]
        if any(not -1e-6<=v<=1.000001 for loop in uv.data for v in loop.uv):raise ValueError('Atlas source UVs must fit the unit tile')
        geometry.append({'id':entry['id'],'coords':coords,'origin':list(origin),'faces':[list(p.vertices) for p in mesh.polygons],
                         'uv':[list(l.uv) for l in uv.data],'smooth':[p.use_smooth for p in mesh.polygons],'normals':[list((normal@n.vector).normalized()) for n in mesh.corner_normals]})
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.scale_length=1
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8';scene.render.image_settings.color_mode='RGBA'
    bpy.context.preferences.filepaths.save_version=0
    (root/'textures').mkdir();images={};maps=[];w=layout['width'];h=layout['height'];g=layout['gutter']
    inputs={e['id']:e for e in plan['inputs']}
    for kind in layout['maps']:
        pixels=array('f',[0])*(w*h*4);space='sRGB' if kind in {'BASE_COLOR','EMISSION'} else 'Non-Color'
        for tile in layout['tiles']:
            entry=inputs[tile['id']];path=Path(entry['directory'])/'textures'/(kind.lower()+'.png')
            status('packing atlas texture',map=kind,entry=entry['id'],completed_maps=len(maps))
            image=bpy.data.images.load(str(path),check_existing=False);image.colorspace_settings.name=space
            sw,sh=image.size;source=array('f',[0])*(sw*sh*4);image.pixels.foreach_get(source);bpy.data.images.remove(image)
            x,y,tw,th=tile['pixel_rect']
            if (sw,sh)!=(tw,th):raise ValueError('Atlas source image changed dimensions')
            for row in range(-g,sh+g):
                src=min(sh-1,max(0,row));begin=src*sw*4
                line=source[begin:begin+4]*g+source[begin:begin+sw*4]+source[begin+(sw-1)*4:begin+sw*4]*g
                offset=((y+row)*w+x-g)*4;pixels[offset:offset+len(line)]=line
        image=bpy.data.images.new('Atlas_'+kind,width=w,height=h,alpha=True);image.colorspace_settings.name=space;image.pixels.foreach_set(pixels)
        image.file_format='PNG';image.filepath_raw=str(root/'textures'/(kind.lower()+'.png'));image.save()
        path=image.filepath_raw;bpy.data.images.remove(image);image=bpy.data.images.load(path,check_existing=False);image.colorspace_settings.name=space
        image.filepath='//textures/'+kind.lower()+'.png';images[kind]=image
        maps.append({'map':kind,'path':'textures/'+kind.lower()+'.png','width':w,'height':h,'color_space':space})
    mat=bpy.data.materials.new('AtlasPBR');mat.use_nodes=True;tree=mat.node_tree;surface=tree.nodes.get('Principled BSDF');surface.name='Surface';tree.nodes.get('Material Output').name='Output'
    for index,value in defaults.items():surface.inputs[int(index)].default_value=value
    properties={'BASE_COLOR':'Base Color','ROUGHNESS':'Roughness','METALLIC':'Metallic','EMISSION':'Emission Color','ALPHA':'Alpha'}
    for kind,image in images.items():
        node=tree.nodes.new('ShaderNodeTexImage');node.name=kind;node.image=image;node.extension='EXTEND'
        if kind=='NORMAL':
            normal=tree.nodes.new('ShaderNodeNormalMap');normal.uv_map='AtlasUV';tree.links.new(node.outputs['Color'],normal.inputs['Color']);tree.links.new(normal.outputs['Normal'],surface.inputs['Normal'])
        elif kind=='AO':
            group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');group.nodes.new('NodeGroupInput');group.nodes.new('NodeGroupOutput');group['mcpblender_baked_ao']=True
            settings=tree.nodes.new('ShaderNodeGroup');settings.node_tree=group;tree.links.new(node.outputs['Color'],settings.inputs['Occlusion'])
        else:tree.links.new(node.outputs['Color'],surface.inputs[properties[kind]])
    tiles={t['id']:t for t in layout['tiles']};objects=[]
    for geo in geometry:
        mesh=bpy.data.meshes.new(geo['id']+'_Mesh');mesh.from_pydata(geo['coords'],[],geo['faces']);mesh.update()
        for polygon,smooth in zip(mesh.polygons,geo['smooth']):polygon.use_smooth=smooth
        mesh.normals_split_custom_set(geo['normals'])
        layer=mesh.uv_layers.new(name='AtlasUV');x,y,tw,th=tiles[geo['id']]['uv_rect']
        for loop,source in zip(layer.data,geo['uv']):loop.uv=(x+source[0]*tw,y+source[1]*th)
        mesh.materials.append(mat);obj=bpy.data.objects.new(geo['id'],mesh);scene.collection.objects.link(obj);obj.location=geo['origin'];obj[textures.BINDING]=job['job_id'];objects.append(obj.name)
    bpy.context.view_layer.update();status('saving editable atlas asset')
    finished(bpy.ops.wm.save_as_mainfile(filepath=str(root/'asset.blend'),check_existing=False,relative_remap=False))
    saved={'version':1,'job_id':job['job_id'],'source':job['expected_bake'],'name':objects[0],'objects':objects,'material':mat.name,'maps':maps,'projection':None,
           'atlas':plan,'object_signatures':{name:textures.output_signature(name) for name in objects},'material_adapters':info['material_adapters'],'blender_version':bpy.app.version_string}
    saved['files']=manifest(root);write_json(root/'manifest.json',saved)
    write_json(root/'result.json',{'job_id':job['job_id'],'state':'succeeded','phase':'complete','completed_maps':len(maps)})
