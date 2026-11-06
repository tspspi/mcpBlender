"""Guarded current-scene Cycles settings; no arbitrary RNA mutation."""
import math
import bpy
from mcpblender import render_sampling as schema
from . import compositing

COMMANDS={'inspect_render_sampling','configure_render_sampling'}


def snapshot(scene):
    if not hasattr(scene,'cycles'):raise ValueError('Cycles settings are unavailable in this Blender build')
    layers=[{'name':v.name,'enabled':v.use,'samples':v.samples,'use_denoising':v.cycles.use_denoising} for v in scene.view_layers]
    paths={scene.cycles.path_from_id()+'.'+k for k in schema.KEYS}
    paths.add('render.engine')
    for layer in scene.view_layers:
        paths.update((layer.path_from_id()+'.samples',layer.path_from_id()+'.use',layer.path_from_id()+'.cycles.use_denoising'))
    animated=sorted(compositing.animation_paths(scene).intersection(paths))
    return schema.record(scene.render.engine,{k:getattr(scene.cycles,k) for k in schema.KEYS},layers,animated,
                         {'device':scene.cycles.device,'threads_mode':scene.render.threads_mode,'threads':scene.render.threads})


def choices(scene,key):
    if key=='sampling_pattern':
        from cycles.properties import enum_sampling_pattern
        return [row[0] for row in enum_sampling_pattern(scene.cycles,bpy.context) if row[0] in {'AUTOMATIC','TABULATED_SOBOL','BLUE_NOISE'}]
    return list(scene.cycles.bl_rna.properties[key].enum_items.keys())


def inspect():
    scene=bpy.context.scene
    profile=snapshot(scene)
    return profile|{'scene':scene.name,'frame':scene.frame_current,'sample_windows':schema.windows(profile['settings'],profile['layers']),
        'choices':{key:choices(scene,key) for key in ('sampling_pattern','use_layer_samples','pixel_filter_type')},
        'scope':'Explicit Cycles sampling fields and layer overrides; not the full integrator, geometry, materials, lighting or hardware. Sample subsets clamp their length to the remaining master samples. Adaptive sampling/time limits can stop earlier. Independent workers override device, threads and master samples using their job parameters.'}


def configure(p):
    from .bridge import check_cancelled
    scene=bpy.context.scene
    if scene.library or scene.override_library:raise ValueError('Sampling edits require a local scene')
    before=snapshot(scene)
    if before['sampling_sha256']!=p['expected_sampling']:raise ValueError('Render sampling guard is stale')
    changes={k:v for k,v in p['settings'].items() if v is not None}
    if not changes or not set(changes)<=set(schema.KEYS):raise ValueError('Choose supported sampling settings')
    paths={scene.cycles.path_from_id()+'.'+k for k in changes}
    if paths.intersection(compositing.animation_paths(scene)):raise ValueError('Targeted sampling fields are keyed or driven')
    proposed=before['settings']|changes
    if proposed['use_sample_subset'] and any(row['sample_ceiling']<=0 for row in schema.windows(proposed,before['layers'])):raise ValueError('Enabled sample subset must start before master samples in each enabled layer')
    for key,value in changes.items():
        prop=scene.cycles.bl_rna.properties[key]
        if prop.type=='ENUM' and value not in choices(scene,key):raise ValueError('Sampling enum is not available in this Blender: '+key)
        if prop.type in {'INT','FLOAT'} and (not math.isfinite(value) or not prop.hard_min<=value<=prop.hard_max):raise ValueError('Sampling setting exceeds native range: '+key)
    try:
        check_cancelled()
        for key,value in changes.items():
            setattr(scene.cycles,key,value);check_cancelled()
        bpy.context.view_layer.update();check_cancelled()
        return inspect()
    except BaseException:
        for key in changes:setattr(scene.cycles,key,before['settings'][key])
        bpy.context.view_layer.update();raise


def dispatch(command,p):return inspect() if command=='inspect_render_sampling' else configure(p)
