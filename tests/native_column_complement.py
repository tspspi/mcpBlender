"""Actual first-hit column predicate and root-placement renders; guarded refusals."""
import json,sys,resource
from array import array
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mathutils import Matrix
from mcpblender import exr_scanline,component_ids
from mcpblender.blender import botanical_subsets as subsets
bpy.ops.wm.open_mainfile(filepath=args[1],use_scripts=False)
bpy.context.view_layer.update()
out=Path(args[3]);out.mkdir(parents=True,exist_ok=True)
p={'subset_collection':'ColumnComplement'};col,owned,state=subsets.inspect(p);assert state['valid']
meta=json.loads(col[subsets.META]);root=bpy.data.objects[meta['root']];original_root=root.matrix_basis.copy();plan=meta['plan'];column=plan['column_complement'];size=column['resolution']
materials=[v for v in owned if isinstance(v,bpy.types.Material)];images=[v for v in owned if isinstance(v,bpy.types.Image)]
assert materials and len(images)==1
for mat in materials:
    coordinates=[n for n in mat.node_tree.nodes if n.type=='TEX_COORD' and n.object==root];assert len(coordinates)==1
# Root placement is allowed without changing private shader/image contents.
root.matrix_world=Matrix.Translation((2,1,3))@Matrix.Rotation(.2,4,'Z')@Matrix.Scale(1.3,4)@original_root
assert subsets.inspect(p)[-1]['valid']
root.matrix_world=original_root
# Cancellation while wrapping a new private shader rolls back every new ID.
from mcpblender.botanical_subset_contracts import Source
from mcpblender.blender import subset_columns,bridge,botanical_trees
args_plan=Source(directory=args[2],selection='COLUMN_COMPLEMENT').model_dump()
fresh=subsets.plan(args_plan)[-1];before=set(bpy.data.user_map());source_guard=botanical_trees.inspect({'collection':fresh['source_collection']})['tree_sha256'];wrap=subset_columns.wrap
def cancel_wrap(*a,**k):
    wrap(*a,**k);raise bridge.OperationCancelled('native private-material staging cancellation')
subset_columns.wrap=cancel_wrap
try:
    try:subsets.create(args_plan|{'subset_collection':'CancelledColumn','expected_plan':fresh['plan_sha256']})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Staging cancellation was lost')
finally:subset_columns.wrap=wrap
assert set(bpy.data.user_map())==before and botanical_trees.inspect({'collection':fresh['source_collection']})['tree_sha256']==source_guard
# Private shader changes and foreign users refuse guarded removal.
mat=materials[0];transparent=next(n for n in mat.node_tree.nodes if n.type=='BSDF_TRANSPARENT');value=tuple(transparent.inputs['Color'].default_value);transparent.inputs['Color'].default_value=(.2,.3,.4,1)
changed=subsets.inspect(p)[-1];assert not changed['valid']
try:subsets.dispatch('remove_botanical_subset',p|{'expected_subset':changed['subset_sha256']})
except ValueError:pass
else:raise AssertionError('Edited private shader removable')
transparent.inputs['Color'].default_value=value;assert subsets.inspect(p)[-1]['valid']
mesh=bpy.data.meshes.new('Foreign');mesh.materials.append(mat);foreign=bpy.data.objects.new('Foreign',mesh);bpy.context.scene.collection.objects.link(foreign)
assert subsets.inspect(p)[-1]['ownership_blockers'];bpy.data.objects.remove(foreign,do_unlink=True);bpy.data.meshes.remove(mesh);assert subsets.inspect(p)[-1]['valid']
# Independent saved point IDs: full source retained, no semantic renumbering.
population=bpy.data.objects[state['population']];ids=[v.value for v in population.data.attributes['leaf_index'].data]
assert ids==[v.value for v in population.data.attributes['id'].data] and len(ids)==plan['source_leaf_count']
assert [v.value for v in population.data.attributes[component_ids.ATTRIBUTE].data]==[v+1 for v in ids]
reference=exr_scanline.decode(Path(args[2])/column['reference_exr']['file'],['TreeCapture.Combined.A','TreeCapture.MCP_SurfaceWeight.X',*component_ids.channels()])['channels']
expected=[int(a>0 and i>0) for a,i in zip(reference['TreeCapture.Combined.A'],reference[component_ids.channels()[0]])]
# Disable clipping only for this predicate readback: original first-hit surfaces
# remain visible and publish the actual shader match, not an averaged ID.
for mat in materials:
    tree=mat.node_tree;output=next(n for n in tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);mix=output.inputs['Surface'].links[0].from_node;matched=mix.inputs[0].links[0].from_socket
    attr=next(n for n in tree.nodes if n.type=='ATTRIBUTE' and n.attribute_name==component_ids.ATTRIBUTE)
    texture=next(n for n in tree.nodes if n.type=='TEX_IMAGE' and n.image==images[0]);split=tree.nodes.new('ShaderNodeSeparateXYZ');tree.links.new(texture.outputs['Color'],split.inputs[0])
    for label,socket in [('OwnID',attr.outputs['Fac']),('RefID',split.outputs[0])]:
        debug=tree.nodes.new('ShaderNodeOutputAOV');debug.aov_name=label;tree.links.new(socket,debug.inputs['Value'])
    aov=tree.nodes.new('ShaderNodeOutputAOV');aov.aov_name='ColumnMatch';tree.links.new(matched,aov.inputs['Value']);tree.links.remove(mix.inputs[0].links[0]);mix.inputs[0].default_value=0
s=bpy.context.scene
for c in list(s.collection.children):c.hide_render=c!=col
col.hide_render=False;col.hide_viewport=False
layer=s.view_layers[0];layer.name='ColumnProbe';aov=layer.aovs.add();aov.name='ColumnMatch';aov.type='VALUE'
for label in ('OwnID','RefID'):
    aov=layer.aovs.add();aov.name=label;aov.type='VALUE'
s.view_layers[0].use_pass_position=True
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.cycles.use_sample_subset=False;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.sampling_pattern='AUTOMATIC';s.cycles.seed=0;s.cycles.use_animated_seed=False;s.render.resolution_x=s.render.resolution_y=size;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.use_compositing=False;s.render.use_sequencer=False
camera=bpy.data.objects.new('ColumnProbeCamera',bpy.data.cameras.new('ColumnProbeCamera'));s.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.ortho_scale=column['view']['ortho_scale'];camera.data.clip_start=column['view']['clip_start'];camera.data.clip_end=column['view']['clip_end'];s.camera=camera
camera_original=Matrix(column['view']['matrix_world']);rows=[]
for name,placement in [('original',original_root),('moved',Matrix.Translation((7,-2,3))@Matrix.Rotation(.7,4,'Z')@Matrix.Scale(1.6,4)@original_root)]:
    root.matrix_world=placement;delta=placement@original_root.inverted();camera.matrix_world=delta@camera_original;camera.data.ortho_scale=column['view']['ortho_scale']*(1 if name=='original' else 1.6);camera.data.clip_start=column['view']['clip_start']*(1 if name=='original' else 1.6);camera.data.clip_end=column['view']['clip_end']*(1 if name=='original' else 1.6)
    print('PROBE_POSE',name,[list(r) for r in root.matrix_world],[list(r) for r in camera.matrix_world],camera.data.ortho_scale,s.render.pixel_aspect_x,s.render.pixel_aspect_y,flush=True)
    bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_depth='32';s.render.image_settings.color_mode='RGBA';s.render.image_settings.exr_codec='ZIP';file=out/(name+'.exr');bpy.data.images['Render Result'].save_render(str(file),scene=s)
    debug=exr_scanline.decode(file,['ColumnProbe.OwnID.X','ColumnProbe.RefID.X'])['channels'];(out/(name+'-debug.json')).write_text(json.dumps([{'pixel':i,'sourceID':reference[component_ids.channels()[0]][i],**{k:v[i] for k,v in debug.items()}} for i,e in enumerate(expected) if e],indent=2))
    own=debug['ColumnProbe.OwnID.X'];sampled=debug['ColumnProbe.RefID.X'];source_ids=reference[component_ids.channels()[0]]
    assert sum(v>0 for v in own)>=.9*sum(expected),'Moved view lost native leaf observations'
    if name=='original':assert own==source_ids,'Saved native first-hit identity differs from reference'
    # Moving all native geometry/camera can change edge hits through float32
    # rounding. Check the projector and predicate independently at the actual
    # new first-hit IDs, and report changes rather than claiming exact pixels.
    assert max(abs(sampled[i]-source_ids[i]) for i,v in enumerate(own) if v>0)<1e-6,'Root-relative projector selected a different reference cell'
    wanted=expected if name=='original' else [int(v>0 and v==source_ids[i]) for i,v in enumerate(own)]
    data=exr_scanline.decode(file,['ColumnProbe.ColumnMatch.X'])['channels']['ColumnProbe.ColumnMatch.X'];errors=[abs(a-b) for a,b in zip(data,wanted)];assert max(errors)<1e-6,(name,max(errors),sum(data),sum(wanted));rows.append({'placement':name,'matched_leaf_pixels':sum(data),'max_error':max(errors),'source_first_hit_changes':sum(a!=b for a,b in zip(own,source_ids))})
# Reopen the unchanged saved fixture: image tampering must fail independently
# of the temporary AOV nodes and moved placement used by the render probe.
bpy.ops.wm.open_mainfile(filepath=args[1],use_scripts=False)
col,owned,state=subsets.inspect(p);assert state['valid']
image=next(v for v in owned if isinstance(v,bpy.types.Image));pixels=array('f',[0.])*len(image.pixels);image.pixels.foreach_get(pixels);pixels[0]+=1;image.pixels.foreach_set(pixels);image.pack()
changed=subsets.inspect(p)[-1];assert not changed['valid']
try:subsets.dispatch('remove_botanical_subset',p|{'expected_subset':changed['subset_sha256']})
except ValueError:pass
else:raise AssertionError('Edited packed image removable')
(out/'proof.json').write_text(json.dumps(rows,indent=2));print('COLUMN_COMPLEMENT_NATIVE_COMPLETE',rows,flush=True)
