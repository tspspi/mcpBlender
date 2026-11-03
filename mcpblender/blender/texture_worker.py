"""Trusted image-bake worker; no MCP bridge and no user-script execution."""
import os
from pathlib import Path
import resource
import sys
import threading
import time
from array import array

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import bpy
from mathutils import Matrix
from mcpblender.blender import textures
from mcpblender.blender.assets import finished
from mcpblender.texture_files import write_json,read_json,manifest

PROPERTIES={'BASE_COLOR':'Base Color','ROUGHNESS':'Roughness','METALLIC':'Metallic','EMISSION':'Emission Color','ALPHA':'Alpha'}


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    job_path=Path(sys.argv[sys.argv.index('--')+1]);job=read_json(job_path);root=job_path.parent
    def parent_watch():
        while True:
            if os.getppid()!=job['parent_pid']:os._exit(125)
            time.sleep(.2)
    threading.Thread(target=parent_watch,daemon=True).start()
    if os.getppid()!=job['parent_pid']:raise RuntimeError('Texture parent is gone')
    def status(phase,**kw):write_json(root/'result.json',{'job_id':job['job_id'],'state':'running','phase':phase}|kw)
    if job.get('_texture_pipeline')=='ATLAS':
        from mcpblender.blender.atlas_worker import run
        return run(job,root,status)
    status('loading isolated texture source')
    bpy.ops.wm.open_mainfile(filepath=str(root/'source.blend'),load_ui=False,use_scripts=False)
    bpy.context.preferences.filepaths.save_version=0;source_info=textures.guard(job)
    names=[job['name'],*job['sources']]+([job['cage']] if job.get('cage') else [])
    # Capture all evaluated meshes before replacing any dependency.
    frozen=[];deps=bpy.context.evaluated_depsgraph_get()
    for name in names:
        obj=bpy.data.objects[name];ev=obj.evaluated_get(deps)
        data=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        frozen.append((obj,data,ev.matrix_world.copy()))
    # A plain matrix_world assignment decomposes and loses inherited shear.
    # Preserve each evaluated affine transform under an independent identity anchor.
    anchor=bpy.data.objects.new('MCP_BakePlacement',None);bpy.context.scene.collection.objects.link(anchor)
    for obj,data,matrix in frozen:
        obj.modifiers.clear();obj.constraints.clear();obj.animation_data_clear();obj.parent=anchor;obj.data=data
        obj.matrix_parent_inverse=matrix;obj.matrix_basis=Matrix.Identity(4)
        obj.hide_render=False;obj.hide_viewport=False;obj.hide_set(False);obj.hide_select=False
    for obj in list(bpy.data.objects):
        if obj.name not in names and obj!=anchor:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.view_layer.update()
    low=bpy.data.objects[job['name']]
    low.data.uv_layers.active=low.data.uv_layers[job['uv_map']];low.data.uv_layers[job['uv_map']].active_render=True
    source_objects=[bpy.data.objects[n] for n in job['sources']] or [low]
    source_materials={mat for obj in source_objects for mat in obj.data.materials}
    # Saved edits happen only in this disposable child. Keep source materials for
    # self baking until all maps are complete, with image targets on every slot.
    if job['sources']:
        recipient=bpy.data.materials.new('MCP_BakeRecipient');recipient.use_nodes=True
        low.data.materials.clear();low.data.materials.append(recipient)
        for face in low.data.polygons:face.material_index=0
    target_materials=set(low.data.materials)
    source_nodes={m:textures.bake_surface_node(m,job.get('thin_foliage_mode','REFUSE'))[0].name for m in source_materials}
    for mat in source_materials:
        if any(a['material']==mat.name for a in source_info.get('material_adapters',[])):
            front=mat.node_tree.nodes['Leaf Sides'].inputs[0]
            for link in list(front.links):mat.node_tree.links.remove(link)
            front.default_value=0
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=job['samples'];scene.cycles.device='CPU'
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8';scene.render.image_settings.color_mode='RGBA'
    scene.render.bake.use_clear=True
    (root/'textures').mkdir()
    maps=[];images={};projection=None
    if job['sources']:
        scene.cycles.samples=1
        status('checking projection coverage')
        # Geometry projection must be measurable independently of source color,
        # alpha, map padding and target UV gutters.
        for mat in source_materials|target_materials:
            output=next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
            emission=mat.node_tree.nodes.new('ShaderNodeEmission');emission.name='MCP_BakeEmission'
            emission.inputs['Color'].default_value=(1,1,1,1);emission.inputs['Strength'].default_value=1
            mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
        masks={}
        for mask,project in (('uv_mask',False),('coverage',True)):
            image=bpy.data.images.new('MCP_'+mask,width=job['width'],height=job['height'],alpha=True)
            image.colorspace_settings.name='Non-Color'
            for mat in target_materials:
                node=mat.node_tree.nodes.get('MCP_BakeImage') or mat.node_tree.nodes.new('ShaderNodeTexImage')
                node.name='MCP_BakeImage';node.image=image;mat.node_tree.nodes.active=node
            bpy.ops.object.select_all(action='DESELECT');low.select_set(True)
            if project:
                for obj in source_objects:obj.select_set(True)
            bpy.context.view_layer.objects.active=low
            kwargs={'type':'EMIT','use_selected_to_active':project,'margin':0,'use_cage':bool(job.get('cage') or project and job['cage_extrusion']>0),'cage_extrusion':job['cage_extrusion'],'max_ray_distance':job['max_ray_distance'],'uv_layer':job['uv_map']}
            if job.get('cage') and project:kwargs['cage_object']=job['cage']
            finished(bpy.ops.object.bake(**kwargs))
            pixels=array('f',[0])*(job['width']*job['height']*4);image.pixels.foreach_get(pixels)
            masks[mask]=pixels[0::4]
            image.file_format='PNG';image.filepath_raw=str(root/'textures'/f'{mask}.png');image.save();bpy.data.images.remove(image)
        target_pixels=sum(v>.5 for v in masks['uv_mask'])
        hit_pixels=sum(a>.5 and b>.5 for a,b in zip(masks['uv_mask'],masks['coverage']))
        if not target_pixels:raise ValueError('Target UV raster has no covered pixels')
        projection={'target_pixels':target_pixels,'hit_pixels':hit_pixels,'fraction':hit_pixels/target_pixels,'threshold':job['min_projection_coverage'],'mask_paths':['textures/uv_mask.png','textures/coverage.png']}
        if projection['fraction']<job['min_projection_coverage']:raise ValueError(f"Projection coverage {projection['fraction']:.6f} is below required {job['min_projection_coverage']}; adjust cage/ray distance or sources")
    scene.cycles.samples=job['samples']
    for index,kind in enumerate(job['maps']):
        status('baking texture map',map=kind,completed_maps=index)
        # Restore the source output between passes; source inputs stay intact.
        for mat,source_name in source_nodes.items():
            # Rewire only the surface output; source sockets and bump/normal graph
            # remain available for subsequent passes.
            output=next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
            for link in list(output.inputs['Surface'].links):mat.node_tree.links.remove(link)
            source=mat.node_tree.nodes[source_name]
            previous=mat.node_tree.nodes.get('MCP_BakeEmission')
            if previous:mat.node_tree.nodes.remove(previous)
            if kind in {'AO','NORMAL'}:
                diffuse=mat.node_tree.nodes.new('ShaderNodeBsdfDiffuse');diffuse.name='MCP_BakeEmission'
                diffuse.inputs['Color'].default_value=(1,1,1,1)
                if kind=='NORMAL' and source.inputs['Normal'].is_linked:mat.node_tree.links.new(source.inputs['Normal'].links[0].from_socket,diffuse.inputs['Normal'])
                mat.node_tree.links.new(diffuse.outputs[0],output.inputs['Surface'])
            elif kind in PROPERTIES:
                port=source.inputs[PROPERTIES[kind]];emission=mat.node_tree.nodes.new('ShaderNodeEmission');emission.name='MCP_BakeEmission'
                if port.is_linked:mat.node_tree.links.new(port.links[0].from_socket,emission.inputs['Color'])
                else:
                    value=port.default_value
                    emission.inputs['Color'].default_value=list(value) if port.type=='RGBA' else (value,value,value,1)
                emission.inputs['Strength'].default_value=1
                mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
            else:mat.node_tree.links.new(source.outputs['BSDF'],output.inputs['Surface'])
        image=bpy.data.images.new('Baked_'+kind,width=job['width'],height=job['height'],alpha=True,float_buffer=False)
        image.colorspace_settings.name='sRGB' if kind in {'BASE_COLOR','EMISSION'} else 'Non-Color'
        for mat in target_materials:
            node=mat.node_tree.nodes.get('MCP_BakeImage') or mat.node_tree.nodes.new('ShaderNodeTexImage')
            node.name='MCP_BakeImage';node.image=image;mat.node_tree.nodes.active=node
        bpy.ops.object.select_all(action='DESELECT')
        low.select_set(True)
        for obj in source_objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=low
        kwargs={'type':kind if kind in {'NORMAL','AO'} else 'EMIT','use_selected_to_active':bool(job['sources']),
                'use_cage':bool(job.get('cage') or job['sources'] and job['cage_extrusion']>0),
                'cage_extrusion':job['cage_extrusion'],'max_ray_distance':job['max_ray_distance'],
                'normal_space':'TANGENT','normal_r':'POS_X','normal_g':'POS_Y','normal_b':'POS_Z',
                'margin':job['margin'],'margin_type':'EXTEND','target':'IMAGE_TEXTURES','save_mode':'INTERNAL','uv_layer':job['uv_map']}
        if job.get('cage'):kwargs['cage_object']=job['cage']
        finished(bpy.ops.object.bake(**kwargs))
        image.file_format='PNG';image.filepath_raw=str(root/'textures'/f'{kind.lower()}.png');image.save()
        # Use the exact saved PNG as the final asset's texture and validation input.
        path=image.filepath_raw;bpy.data.images.remove(image);image=bpy.data.images.load(path,check_existing=False)
        image.colorspace_settings.name='sRGB' if kind in {'BASE_COLOR','EMISSION'} else 'Non-Color'
        pixels=array('f',[0])*(job['width']*job['height']*4);image.pixels.foreach_get(pixels)
        stats={'min':[min(pixels[c::4]) for c in range(4)],'max':[max(pixels[c::4]) for c in range(4)],'mean':[sum(pixels[c::4])/(job['width']*job['height']) for c in range(4)]}
        image.filepath='//textures/'+kind.lower()+'.png';images[kind]=image
        maps.append({'map':kind,'path':'textures/'+kind.lower()+'.png','width':job['width'],'height':job['height'],'color_space':image.colorspace_settings.name,'statistics':stats})
    status('assembling baked PBR asset',completed_maps=len(maps))
    mat=bpy.data.materials.new('BakedPBR');mat.use_nodes=True;tree=mat.node_tree;surface=tree.nodes.get('Principled BSDF');surface.name='Surface';tree.nodes.get('Material Output').name='Output'
    for kind,image in images.items():
        node=tree.nodes.new('ShaderNodeTexImage');node.name=kind;node.image=image
        if kind=='NORMAL':
            normal=tree.nodes.new('ShaderNodeNormalMap');normal.uv_map=job['uv_map'];tree.links.new(node.outputs['Color'],normal.inputs['Color']);tree.links.new(normal.outputs['Normal'],surface.inputs['Normal'])
        elif kind=='AO':
            group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');group.nodes.new('NodeGroupInput');group.nodes.new('NodeGroupOutput');group['mcpblender_baked_ao']=True
            settings=tree.nodes.new('ShaderNodeGroup');settings.node_tree=group;tree.links.new(node.outputs['Color'],settings.inputs['Occlusion'])
        else:tree.links.new(node.outputs['Color'],surface.inputs[PROPERTIES[kind]])
    if 'EMISSION' in images:surface.inputs['Emission Strength'].default_value=1
    low.data.materials.clear();low.data.materials.append(mat)
    for face in low.data.polygons:face.material_index=0
    for obj in list(bpy.data.objects):
        if obj!=low and obj!=anchor:bpy.data.objects.remove(obj,do_unlink=True)
    low[textures.BINDING]=job['job_id']
    finished(bpy.ops.wm.save_as_mainfile(filepath=str(root/'asset.blend'),check_existing=False,relative_remap=False))
    saved={'version':1,'job_id':job['job_id'],'source':job['expected_bake'],'name':low.name,'material':mat.name,'maps':maps,'projection':projection,'blender_version':bpy.app.version_string,'asset_sha256':textures.output_signature(low.name),'material_adapters':source_info.get('material_adapters',[])}
    saved['files']=manifest(root);write_json(root/'manifest.json',saved)
    write_json(root/'result.json',{'job_id':job['job_id'],'state':'succeeded','phase':'complete','completed_maps':len(maps)})


if __name__=='__main__':
    try:main()
    except Exception as exc:
        path=Path(sys.argv[sys.argv.index('--')+1]);job=read_json(path)
        write_json(path.parent/'result.json',{'job_id':job['job_id'],'state':'failed','phase':'failed','error':str(exc)[:2000]})
        raise
