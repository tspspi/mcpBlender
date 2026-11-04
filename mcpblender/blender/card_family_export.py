"""Source-preserving durable delivery of all packed family alternatives."""
import json
from pathlib import Path
from mathutils import Matrix
import bpy
from mcpblender import attribute_glb,card_family,card_family_files as files
from mcpblender.storage import require_space
from . import card_families
from .workflows import export_objects_glb

COMMANDS={'export_foliage_card_family','validate_foliage_card_family_bundle'}


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    col,owned,meta,state=card_families.inspect(p)
    if p['expected_family']!=state['family_sha256']:raise ValueError('Card family export guard is stale')
    if not state['valid']:raise ValueError('Valid unchanged card family required for export')
    destination=Path(p['directory']);job=p['_export_job'];unit=bpy.context.scene.unit_settings.scale_length
    if destination.exists():raise FileExistsError(destination)
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {};reserve=policy.get('reserve_bytes',256*1024**2)
    estimate=16*1024**2+meta['rgba8_base_bytes']*(len(meta['entries'])+1)*2+sum(len(bpy.data.objects[e['object']].data.loops)*1024 for e in meta['entries'])
    if _bridge and _bridge.active:_bridge.active['storage'].update(estimated_bytes=estimate,estimate_kind='packed_family_all_views_blend_and_corner_witness_heuristic')
    require_space(destination,estimate,reserve_bytes=reserve,estimate_kind='packed_family_all_views_blend_and_corner_witness_heuristic')
    root=bpy.data.objects[meta['root']];root_matrix=[list(row) for row in root.matrix_world]
    pose=files.placement(root_matrix,unit)
    pose['normals_world']={e['view']:pose['normals_world'][e['view']] for e in meta['entries']}
    document={'format':files.FORMAT,'family_guard':p['expected_family'],'family_collection':col.name,'scene_unit_scale':unit,
              'root_matrix_native':root_matrix,'max_angle_degrees':meta['max_angle_degrees'],'provenance':meta['provenance'],
              'optical_equivalence':False,'selector':{'method':'NEAREST_ONE_SIDED_CARD_V1','coordinates':files.COORDINATES,'tie_order':list(card_family.DIRECTIONS),
              'max_angle_degrees':meta['max_angle_degrees'],'perspective':'NEAREST_CENTRE_THEN_ALL_EIGHT_WORLD_AABB_CORNERS','automatic_playback':False,**pose},'variants':[]}
    stage=job.stage;stage.mkdir(mode=0o700);job.created();scene=None;copy=None;mesh=None;origin=None
    try:
        check_cancelled();report_progress({'phase':'writing family-only editable packed project'})
        scene=bpy.data.scenes.new('MCP_CardFamilyDelivery');scene.unit_settings.scale_length=unit;scene.collection.children.link(col)
        bpy.data.libraries.write(str(stage/'asset.blend'),{scene},fake_user=False,compress=True)
        bpy.data.scenes.remove(scene);scene=None
        origin=bpy.data.objects.new('MCP_CardFamilyOrigin',None);bpy.context.scene.collection.objects.link(origin);origin.matrix_world=root.matrix_world.copy();bpy.context.view_layer.update()
        for entry in meta['entries']:
            check_cancelled();source=bpy.data.objects[entry['object']];source_matrix=card_families.world_matrix(source,root);mesh=source.data.copy();mesh.use_fake_user=False
            copy=bpy.data.objects.new('MCP_CardAlternative',mesh);bpy.context.scene.collection.objects.link(copy);copy.parent=origin;copy.matrix_parent_inverse=origin.matrix_world.inverted()@source_matrix;copy.matrix_basis=Matrix.Identity(4);bpy.context.view_layer.update()
            view=entry['view'];number=list(card_family.DIRECTIONS).index(view)
            for a in list(mesh.attributes):
                if a.name.startswith('_'):mesh.attributes.remove(a)
            for name,values in ((attribute_glb.CORNER,list(range(len(mesh.loops)))),(files.VIEW_FIELD,[number]*len(mesh.loops))):
                a=mesh.attributes.new(name=name,type='FLOAT',domain='CORNER');a.data.foreach_set('value',values)
            mesh.update();mesh.calc_loop_triangles()
            witness={'format':attribute_glb.FORMAT,'matrix_world':[list(r) for r in source_matrix],'scene_unit_scale':unit,
                     'positions':[list(source.data.vertices[l.vertex_index].co) for l in source.data.loops],
                     'normals':[list(n.vector) for n in source.data.corner_normals],
                     'uvs':[[list(v.uv) for v in layer.data] for layer in source.data.uv_layers],
                     'triangles':[list(t.loops) for t in mesh.loop_triangles],
                     'fields':[{'semantic':files.VIEW_FIELD,'components':1,'values':[[float(number)]]*len(mesh.loops)}],
                     'required_maps':[m['map'] for m in meta['provenance']['maps']],
                     'root_matrix_native':root_matrix,'origin_node':origin.name}
            path=stage/(view.lower()+'.glb');report_progress({'phase':'exporting portable card alternative','view':view,'completed':len(document['variants']),'total':len(meta['entries'])})
            export_objects_glb({'objects':[origin.name,copy.name],'path':str(path),'animations':False,'overwrite':False,'_export_attributes':True})
            proof=files.verify_variant(path,witness,cancelled=check_cancelled)
            bpy.data.objects.remove(copy,do_unlink=True);copy=None;bpy.data.meshes.remove(mesh);mesh=None
            document['variants'].append({'view':view,'file':path.name,'triangles':entry['triangles'],'witness':witness,'proof':proof})
            size=sum(r['bytes'] for r in files.inventory(stage,check_cancelled))
            if size>p['max_bytes']:raise ValueError('Card family export exceeds max_bytes')
            storage=require_space(destination,max(0,estimate-size),reserve_bytes=reserve,estimate_kind='packed_family_remaining_bytes_heuristic')
            report_progress({'phase':'verified portable card alternative','view':view,'bytes':size,'storage':storage})
        bpy.data.objects.remove(origin,do_unlink=True);origin=None
        if card_families.inspect(p)[-1]['family_sha256']!=p['expected_family']:raise ValueError('Card family changed during export')
        document['bounds_world_m']=files.bounds([r['witness'] for r in document['variants']],unit)
        document['files']=files.inventory(stage,check_cancelled)
        payload=(json.dumps(document,sort_keys=True,allow_nan=False)+'\n').encode()
        if len(payload)>16*1024**2 or len(payload)+sum(r['bytes'] for r in document['files'])>p['max_bytes']:raise ValueError('Card family manifest/output exceeds byte budget')
        require_space(destination,len(payload),reserve_bytes=reserve,estimate_kind='serialized_card_family_manifest_bytes')
        (stage/'manifest.json').write_bytes(payload)
        proof=job.verify(check_cancelled,report_progress);check_cancelled()
        if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
        stage.rename(destination)
        return {'directory':str(destination),'proof':proof,'family_guard':p['expected_family'],'live_family_unchanged':True}
    finally:
        if copy:bpy.data.objects.remove(copy,do_unlink=True)
        if mesh:bpy.data.meshes.remove(mesh)
        if origin:bpy.data.objects.remove(origin,do_unlink=True)
        if scene:bpy.data.scenes.remove(scene)


def dispatch(command,p):
    from .bridge import check_cancelled,report_progress
    return files.validate(p['directory'],cancelled=check_cancelled,progress=report_progress)
