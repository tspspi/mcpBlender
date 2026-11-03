"""Source-preserving static numeric-field export with independent buffer proof."""
import json
import math
import os
from pathlib import Path
import tempfile
import bpy
from mcpblender import attribute_glb,attribute_values,botany
from mcpblender.storage import require_space
from . import attributes

COMMANDS={'inspect_attribute_export','export_attribute_bundle','validate_attribute_bundle'}


def prepare(p):
    from .bridge import check_cancelled
    obj=attributes.mesh_object(p['name'],edit=True);mesh=obj.data
    if obj.modifiers or mesh.shape_keys or obj.animation_data or mesh.animation_data or obj.constraints:raise ValueError('Attribute export requires static base geometry; realize/evaluate a separate delivery copy first')
    if bpy.context.view_layer.objects.get(obj.name)!=obj or not obj.visible_get():raise ValueError('Attribute source must be visible in the current view layer')
    if obj.matrix_world.determinant()<=0:raise ValueError('Attribute export requires a positive nonsingular placement')
    attributes.check_size(mesh)
    if len(mesh.loops)>p['max_corners'] or len(mesh.uv_layers)>8:raise ValueError('Attribute export corner/UV budget exceeded')
    mesh.calc_loop_triangles()
    if not mesh.loop_triangles or any(e.is_loose for e in mesh.edges) or {l.vertex_index for l in mesh.loops}!=set(range(len(mesh.vertices))):raise ValueError('Attribute export needs triangles and no loose vertices')
    fields=[];mapping=[]
    for slot,entry in enumerate(p['fields']):
        check_cancelled();a=mesh.attributes.get(entry['attribute'])
        if a is None or attributes.protected(mesh,a) or a.data_type not in attribute_values.TYPES or a.domain not in {'POINT','FACE','CORNER'}:raise ValueError('Field needs supported custom POINT/FACE/CORNER numeric storage; edge fields require explicit projection')
        width=attribute_values.TYPES[a.data_type][1]
        if len(mesh.loops)*(len(fields)+width)>4000000:raise ValueError('Expanded field witness exceeds four million scalar components')
        values=attributes.flat(a);face_by_loop={l:f.index for f in mesh.polygons for l in f.loop_indices} if a.domain=='FACE' else None
        expanded=[]
        for loop in mesh.loops:
            index=loop.vertex_index if a.domain=='POINT' else face_by_loop[loop.index] if a.domain=='FACE' else loop.index
            row=list(values[index*width:(index+1)*width])
            if any(not math.isfinite(v) or a.data_type=='INT' and abs(v)>16777216 for v in row):raise ValueError('Field packing needs finite float32 values and integers exactly representable within +/-2^24')
            expanded.append(row)
        # Scalar lanes keep signed vectors and linear/HDR colors as raw data.
        lanes=[]
        for component in range(width):
            semantic=f'_MCP_F{slot:02d}_C{component}';lanes.append(semantic)
            fields.append({'semantic':semantic,'components':1,'values':[[r[component]] for r in expanded]})
        mapping.append(entry|{'domain':a.domain,'data_type':a.data_type,'components':width,'lanes':lanes,'encoding':'FLOAT32_RAW_SCALAR_LANES','conversion':'BOOLEAN -> 0/1; INT -> exact float32; FLOAT/vector/linear RGBA unchanged; no unit/axis transform'})
    witness={'format':attribute_glb.FORMAT,'matrix_world':[list(r) for r in obj.matrix_world],'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'positions':[list(mesh.vertices[l.vertex_index].co) for l in mesh.loops],
             'uvs':[[list(v.uv) for v in layer.data] for layer in mesh.uv_layers],
             'triangles':[list(t.loops) for t in mesh.loop_triangles],'fields':fields}
    header,guard=attributes.state(obj,mesh)
    source={'attributes_sha256':guard,'matrix_world':[list(r) for r in obj.matrix_world],'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,
            'mapping':mapping,'uv_maps':[l.name for l in mesh.uv_layers],'profile':attribute_glb.FORMAT}
    fingerprint=botany.digest(source)
    chosen={e['attribute'] for e in p['fields']}
    result={'export_sha256':fingerprint,'source':source,'corners':len(mesh.loops),'triangles':len(mesh.loop_triangles),
            'unmapped_custom_fields':[a.name for a in mesh.attributes if not attributes.protected(mesh,a) and a.name not in chosen],
            'estimated_geometry_bytes':len(mesh.loops)*(48+4*len(fields)+8*len(mesh.uv_layers)),'scope':'Static base-mesh fields only. Named semantics and raw scalar lanes; no engine shader, skeletal/morph or unrealized instance delivery.'}
    return obj,witness,result


def inspect(p):return prepare(p)[2]


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    from .workflows import export_objects_glb
    obj,witness,info=prepare(p)
    if info['export_sha256']!=p['expected_export']:raise ValueError('Attribute export fingerprint is stale; inspect again')
    output=Path(p['directory'])
    if output.exists():raise FileExistsError(output)
    encoded=json.dumps(witness,sort_keys=True,allow_nan=False).encode()
    if len(encoded)>p['max_bytes']:raise ValueError('Field witness exceeds max_bytes')
    # Geometry heuristic does not bound embedded material images; recheck actual files.
    estimate=len(encoded)*2+info['estimated_geometry_bytes']+16*1024**2
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
    if _bridge and _bridge.active:_bridge.active['storage'].update(estimated_bytes=estimate,estimate_kind='field_witness_and_geometry_heuristic_excludes_material_images')
    storage=require_space(output,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='field_witness_and_geometry_heuristic_excludes_material_images')
    report_progress({'phase':'staging verified attribute bundle','storage':storage});check_cancelled()
    stage=Path(tempfile.mkdtemp(prefix='.mcpblender-fields-',dir=output.parent));mesh=None;copy=None
    try:
        mesh=obj.data.copy();mesh.use_fake_user=False;copy=bpy.data.objects.new('MCP_FieldDelivery',mesh);bpy.context.scene.collection.objects.link(copy);copy.matrix_world=obj.matrix_world
        # Remove all underscore names on the disposable copy to prevent collisions.
        for a in list(mesh.attributes):
            if a.name.startswith('_') and not attributes.protected(mesh,a):mesh.attributes.remove(a)
        for field in witness['fields']:
            a=mesh.attributes.new(name=field['semantic'],type='FLOAT',domain='CORNER');a.data.foreach_set('value',[v[0] for v in field['values']])
        a=mesh.attributes.new(name=attribute_glb.CORNER,type='FLOAT',domain='CORNER');a.data.foreach_set('value',list(range(len(mesh.loops))));mesh.update()
        check_cancelled();export_objects_glb({'objects':[copy.name],'path':str(stage/'asset.glb'),'animations':False,'overwrite':False,'_export_attributes':True})
        if (stage/'asset.glb').stat().st_size+len(encoded)>p['max_bytes']:raise ValueError('Attribute bundle exceeds max_bytes')
        report_progress({'phase':'decoding exported attribute buffers'});proof=attribute_glb.verify(stage/'asset.glb',witness,cancelled=check_cancelled)
        manifest=info|{'format':attribute_glb.FORMAT,'witness':witness,'proof':proof,'losses':['Only explicitly mapped custom fields are qualified. Material/shader fidelity is outside numeric correspondence proof.'],'asset':'asset.glb'}
        serialized=(json.dumps(manifest,sort_keys=True,allow_nan=False)+'\n').encode()
        if len(serialized)+(stage/'asset.glb').stat().st_size>p['max_bytes']:raise ValueError('Attribute manifest/bundle exceeds max_bytes')
        storage=require_space(output,len(serialized),reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='serialized_attribute_manifest_bytes')
        (stage/'manifest.json').write_bytes(serialized)
        report_progress({'phase':'verified attribute bundle before publication','storage':storage});check_cancelled()
        # mkdir is an exclusive reservation, protecting preexisting/foreign paths.
        output.mkdir(mode=0o700)
        try:
            os.replace(stage/'asset.glb',output/'asset.glb');os.replace(stage/'manifest.json',output/'manifest.json')
        except BaseException:
            for path in (output/'asset.glb',output/'manifest.json'):path.unlink(missing_ok=True)
            output.rmdir();raise
        return info|{'directory':str(output),'proof':proof,'bytes':len(serialized)+(output/'asset.glb').stat().st_size}
    finally:
        if copy:bpy.data.objects.remove(copy,do_unlink=True)
        if mesh and mesh.users==0:bpy.data.meshes.remove(mesh)
        # Only this invocation's private staging files are removable.
        for name in ('asset.glb','manifest.json'):(stage/name).unlink(missing_ok=True)
        stage.rmdir()


def validate(p):
    from .bridge import check_cancelled
    root=Path(p['directory']);path=root/'manifest.json'
    if root.is_symlink() or any((root/name).is_symlink() or not (root/name).is_file() for name in ('manifest.json','asset.glb')):raise ValueError('Attribute bundle requires regular local files, not symlinks')
    if path.stat().st_size>256*1024**2:raise ValueError('Attribute manifest exceeds validation budget')
    manifest=json.loads(path.read_text())
    if manifest.get('format')!=attribute_glb.FORMAT or manifest.get('asset')!='asset.glb':raise ValueError('Unsupported attribute bundle')
    proof=attribute_glb.verify(root/'asset.glb',manifest['witness'],cancelled=check_cancelled)
    if proof!=manifest['proof']:raise ValueError('Attribute bundle file/proof changed')
    return {'directory':str(root),'proof':proof,'mapping':manifest['source']['mapping']}


def dispatch(command,p):
    return {'inspect_attribute_export':inspect,'export_attribute_bundle':export,'validate_attribute_bundle':validate}[command](p)
