"""Separate renderer normal correction from geometric facet representation."""
from pathlib import Path
exec(compile(Path(__file__).with_name('native_normal_quadrature.py').read_text(), str(Path(__file__).with_name('native_normal_quadrature.py')), 'exec'))
from mcpblender import projected_microfacets
transport={};row=reference['controls']['box-mixed-world'];w=row['Calibration.Probe_W.X'];keys=('NX','NY','NZ','XX','XY','XZ','YY','YZ','ZZ');fitted=normal_quadrature.fit([row['Calibration.Probe_'+k+'.X']/w for k in keys]);s.cycles.pixel_filter_type='BOX';s.render.filter_size=1
# Reuse the exact flat closure-mixture material from the earlier box control.
material=bpy.data.materials['Reconstructedbox']
for mode in ('flat_default','flat_no_bump_correction','facets'):
 mesh=bpy.data.meshes.new(mode)
 if mode=='facets':
  vertices=[];faces=[];geometry=[]
  for pixel in range(32):
   left=-1+pixel/16
   piece=projected_microfacets.build((left,-2,left+1/16,2),fitted['atoms'],depth=5,near=.1,far=10)
   offset=len(vertices);vertices.extend((x,y,z+5) for x,y,z in piece['vertices']);faces.extend(tuple(offset+i for i in face) for face in piece['faces']);geometry.append({k:v for k,v in piece.items() if k not in ('vertices','faces','uvs')})
  mesh.from_pydata(vertices,[],faces);mat=bpy.data.materials.new('ImplicitFacets');mat.use_nodes=True;tree=mat.node_tree;tree.nodes.clear();d=tree.nodes.new('ShaderNodeBsdfDiffuse');d.inputs['Color'].default_value=(.2,.2,.2,1);d.inputs['Roughness'].default_value=0;o=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(d.outputs[0],o.inputs['Surface']);mesh.materials.append(mat)
 else:mesh.from_pydata([(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0)],[],[(0,1,2,3)]);mesh.materials.append(material)
 obj=bpy.data.objects.new(mode,mesh);s.collection.objects.link(obj)
 for key in ('visible_shadow','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter'):setattr(obj,key,False)
 properties=[p.identifier for p in obj.cycles.bl_rna.properties]
 if mode=='flat_no_bump_correction':material.cycles.use_bump_map_correction=False
 for lighting in ('world','sun'):
  s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5 if lighting=='world' else 0;sun=None
  if lighting=='sun':
   light=bpy.data.lights.new('Sun','SUN');light.energy=2;light.angle=0;sun=bpy.data.objects.new('Sun',light);s.collection.objects.link(sun)
  bpy.context.view_layer.update();bpy.ops.render.render(write_still=False);s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP';path=out/(mode+'-'+lighting+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s);data=exr_scanline.decode(path,['Calibration.Combined.'+a for a in 'RGBA'])['channels'];i=16*32+16;actual=[data['Calibration.Combined.'+a][i] for a in 'RGBA'];expected=[reference['controls']['box-mixed-'+lighting]['Calibration.Combined.'+a] for a in 'RGBA'];transport[mode+'-'+lighting]={'rgba':actual,'reference':expected,'relative_red_bias':actual[0]/expected[0]-1,'triangles':2*len(mesh.polygons),'bump_correction':mesh.materials[0].cycles.use_bump_map_correction,'cycles_properties':properties,'geometry':geometry if mode=='facets' else None};(out/'transport-proof.json').write_text(json.dumps(transport,indent=2));print('TRANSPORT_DONE',mode,lighting,transport[mode+'-'+lighting]['relative_red_bias'],flush=True)
  if sun:light=sun.data;bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(light)
 bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
print('TRANSPORT_COMPLETE')
