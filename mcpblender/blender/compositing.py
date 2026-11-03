"""Staged Blender 5 compositor graphs and guarded current-scene render settings."""
import ast
import math
import uuid

import bpy

from .compositor_profile import NODE_TYPES,PROPERTIES,PASSES,COLOR_KEYS
from .geometry import plain
from .shaders import resolve,connect,set_value as shader_value
from .lods import digest

COMMANDS={'compositor_node_catalog','inspect_compositor_graph','configure_compositor_graph',
          'inspect_render_pipeline','configure_render_passes','configure_color_management','configure_compositing'}
MARKER='mcpblender_compositor_graph'


def supported():
    if not hasattr(bpy.context.scene,'compositing_node_group'):raise ValueError('Structured compositor authoring requires the Blender 5 compositor group API')


def choices(owner,key):
    """Dynamic RNA menus do not populate enum_items; native validation lists them."""
    prop=owner.bl_rna.properties[key]
    values=[e.identifier for e in prop.enum_items]
    if values and values!=['NONE']:return values
    original=getattr(owner,key);sentinel='mcp_invalid_'+uuid.uuid4().hex
    try:
        setattr(owner,key,sentinel)
    except (TypeError,ValueError) as exc:
        tail=str(exc).partition('not found in ')[2]
        if tail:
            try:
                result=ast.literal_eval(tail)
                if isinstance(result,tuple) and all(isinstance(v,str) for v in result):return list(result)[:128]
            except (ValueError,SyntaxError):pass
        return []
    else:
        setattr(owner,key,original);return []


def socket_info(socket,index,menus=False):
    info={'index':index,'name':socket.name,'identifier':socket.identifier,'type':socket.type,
          'enabled':socket.enabled and not socket.is_unavailable,'linked':socket.is_linked,
          'default':plain(getattr(socket,'default_value',None))}
    prop=socket.bl_rna.properties.get('default_value')
    if prop:
        info['components']=prop.array_length if getattr(prop,'is_array',False) else None
        if menus and prop.type=='ENUM':info['choices']=choices(socket,'default_value')
    return info


def node_info(node,menus=False):
    # Include native primitive properties, not just editable allowlisted fields,
    # so direct UI edits such as mute/whitepoints invalidate the content guard.
    props={}
    for prop in node.bl_rna.properties:
        if prop.identifier=='rna_type' or prop.is_readonly or prop.type not in {'STRING','BOOLEAN','ENUM','INT','FLOAT'}:continue
        props[prop.identifier]=plain(getattr(node,prop.identifier))
    info={'name':node.name,'type':node.bl_idname,'properties':props,
          'inputs':[socket_info(s,i,menus) for i,s in enumerate(list(node.inputs)[:128])],
          'outputs':[socket_info(s,i,menus) for i,s in enumerate(list(node.outputs)[:128])]}
    if node.bl_idname=='CompositorNodeRLayers':
        info['render_scene']=node.scene.name if node.scene else None;info['view_layer']=node.layer
    if node.bl_idname=='ShaderNodeValToRGB':
        ramp=node.color_ramp
        info['ramp']={'mode':ramp.color_mode,'interpolation':ramp.interpolation,'hue_interpolation':ramp.hue_interpolation,
                      'stops':[(e.position,list(e.color)) for e in ramp.elements]}
    return info


def animation_paths(owner):
    from .domains import curves
    anim=owner.animation_data
    if not anim:return set()
    paths={c.data_path for c in anim.drivers}
    actions=[(anim.action,getattr(anim,'action_slot',None))] if anim.action else []
    actions.extend((strip.action,getattr(strip,'action_slot',None)) for track in anim.nla_tracks for strip in track.strips if strip.action)
    for action,slot in actions:paths.update(c.data_path for c in curves(action,slot))
    return paths


def graph(name):
    tree=bpy.data.node_groups.get(name)
    if tree is None or tree.bl_idname!='CompositorNodeTree':raise ValueError('Compositor group not found: '+name)
    return tree


def describe(tree):
    nodes=[node_info(n) for n in list(tree.nodes)[:128]]
    links=[{'from_node':l.from_node.name,'from_socket':l.from_socket.identifier,'to_node':l.to_node.name,
            'to_socket':l.to_socket.identifier,'valid':l.is_valid,
            'available':l.from_socket.enabled and not l.from_socket.is_unavailable and l.to_socket.enabled and not l.to_socket.is_unavailable} for l in list(tree.links)[:256]]
    native_users=bpy.data.user_map(subset={tree}).get(tree,set())
    indirect_animation=any(isinstance(u,bpy.types.Scene) and any(path.startswith('compositing_node_group.') for path in animation_paths(u)) for u in native_users)
    users=sorted(({'type':u.bl_rna.identifier,'name':u.name,'library':u.library.filepath if u.library else None} for u in native_users),key=lambda x:(x['type'],x['name']))
    interface=[{'name':s.name,'identifier':s.identifier,'direction':s.in_out,'type':s.socket_type} for s in list(tree.interface.items_tree)[:64] if s.item_type=='SOCKET']
    complete=not tree.animation_data and not indirect_animation and len(tree.nodes)<=128 and len(tree.links)<=256 and len(tree.interface.items_tree)<=64 and all(n.bl_idname in NODE_TYPES and len(n.inputs)<=128 and len(n.outputs)<=128 for n in tree.nodes)
    content={'nodes':nodes,'links':links,'interface':interface,'users':users,'fake_user':tree.use_fake_user,
             'animation':bool(tree.animation_data) or indirect_animation,'managed':bool(tree.get(MARKER))}
    return content|{'group':tree.name,'complete':complete,'graph_sha256':digest(content) if complete else None,
                    'editable':complete and bool(tree.get(MARKER)) and not content['animation'] and not tree.library and not tree.override_library}


def new_tree(name):
    supported();tree=bpy.data.node_groups.new(name,'CompositorNodeTree')
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    return tree


def catalog(p):
    if not p.get('node_type'):return {'node_types':list(NODE_TYPES),'profile':'Blender 5 Image group output; request a type for installed sockets and menus.'}
    tree=new_tree('mcp_compositor_catalog')
    try:
        n=tree.nodes.new(p['node_type'])
        if n.bl_idname=='CompositorNodeRLayers':n.scene=bpy.context.scene;n.layer=bpy.context.view_layer.name
        info=node_info(n,True)
        info['editable_properties']={k:{'type':n.bl_rna.properties[k].type,'choices':choices(n,k) if n.bl_rna.properties[k].type=='ENUM' else None} for k in PROPERTIES.get(n.bl_idname,()) if k in n.bl_rna.properties}
        return info
    finally:bpy.data.node_groups.remove(tree)


def set_value(socket,value):
    prop=socket.bl_rna.properties.get('default_value')
    if socket.type=='MENU':
        if not isinstance(value,str):raise ValueError('Menu socket requires an installed choice string')
        socket.default_value=value;return
    if socket.type=='VECTOR' and prop and prop.is_array and prop.array_length==2:
        if not isinstance(value,list) or len(value)!=2 or any(not math.isfinite(v) or not prop.hard_min<=v<=prop.hard_max for v in value):raise ValueError('This socket requires two finite components within native limits')
        socket.default_value=value;return
    shader_value(socket,value)


def validate(tree):
    if len(tree.nodes)>128 or len(tree.links)>256:raise ValueError('Compositor graph limits exceeded')
    outputs=[n for n in tree.nodes if n.bl_idname=='NodeGroupOutput']
    if len(outputs)!=1 or not outputs[0].inputs['Image'].is_linked:raise ValueError('Exactly one linked Image group output is required')
    if any(not l.is_valid or not l.from_socket.enabled or l.from_socket.is_unavailable or not l.to_socket.enabled or l.to_socket.is_unavailable for l in tree.links):raise ValueError('Compositor link uses an invalid/unavailable socket or disabled render pass')
    # connect() validates cycle freedom during authoring; inspect native UI edits too.
    edges={n.name:[] for n in tree.nodes}
    for link in tree.links:edges[link.from_node.name].append(link.to_node.name)
    done=set();active=set()
    def visit(name):
        if name in active:raise ValueError('Compositor links must not create cycles')
        if name in done:return
        active.add(name)
        for target in edges[name]:visit(target)
        active.remove(name);done.add(name)
    for name in edges:visit(name)
    if any(n.bl_idname not in NODE_TYPES for n in tree.nodes):raise ValueError('Graph contains unsupported nodes; imported graphs are read-only')


def configure_node(tree,spec):
    n=tree.nodes.new(spec['type']);n.name=spec['name'];n.label=spec.get('label','')
    if n.name!=spec['name']:raise ValueError('Native node name changed unexpectedly')
    if n.bl_idname=='CompositorNodeRLayers':
        layer=spec.get('view_layer',bpy.context.view_layer.name)
        if layer not in bpy.context.scene.view_layers:raise ValueError('Render view layer not found')
        n.scene=bpy.context.scene;n.layer=layer
    for key,value in spec.get('properties',{}).items():
        if key not in PROPERTIES.get(n.bl_idname,()) or key not in n.bl_rna.properties:raise ValueError('Unsupported compositor node property: '+key)
        prop=n.bl_rna.properties[key]
        if prop.type=='BOOLEAN' and not isinstance(value,bool):raise ValueError('Boolean node property requires a boolean')
        if prop.type=='ENUM' and (not isinstance(value,str) or value not in choices(n,key)):raise ValueError('Invalid installed node property choice: '+key)
        setattr(n,key,value)
    for item in spec.get('inputs',[]):set_value(resolve(n.inputs,item['socket']),item['value'])
    if spec.get('output_value') is not None:set_value(n.outputs[0],spec['output_value'])
    if spec.get('ramp'):
        stops=sorted(spec['ramp'],key=lambda s:s['position']);ramp=n.color_ramp
        for element,stop in zip(ramp.elements,stops[:2]):element.position=stop['position'];element.color=stop['color']
        for stop in stops[2:]:ramp.elements.new(stop['position']).color=stop['color']
    return n


def configure_graph(p):
    from .bridge import check_cancelled,report_progress
    supported();old=bpy.data.node_groups.get(p['group']);old_name=p['group'];users=[]
    if old:
        state=describe(graph(p['group']))
        if not p.get('replace') or not state['editable']:raise ValueError('Replacement requires a managed local unanimated graph and replace=true')
        if state['graph_sha256']!=p.get('expected_graph'):raise ValueError('Compositor graph fingerprint is stale')
        users=list(bpy.data.user_map(subset={old}).get(old,set()))
        if any(not isinstance(u,bpy.types.Scene) or u.library or u.override_library for u in users):raise ValueError('Replacement supports local scene bindings only; nested/external graph users must be detached explicitly')
        if len(users)>1 and not p.get('allow_shared'):raise ValueError('Multiple scene users require allow_shared=true')
    elif p.get('expected_graph'):raise ValueError('Expected compositor graph no longer exists')
    staged=new_tree('mcp_compositor_stage_'+uuid.uuid4().hex[:16]);swapped=False;success=False
    try:
        for i,spec in enumerate(p['nodes']):
            check_cancelled();configure_node(staged,spec)
            report_progress({'phase':'staged compositor node','nodes':i+1,'total_nodes':len(p['nodes'])})
        connect(staged,p.get('links',[]),False);validate(staged)
        staged[MARKER]=True;staged.use_fake_user=True
        if old and describe(old)['graph_sha256']!=p['expected_graph']:raise ValueError('Original compositor graph changed during staging')
        check_cancelled()
        if old:old.name='mcp_compositor_old_'+uuid.uuid4().hex[:16]
        staged.name=old_name
        if staged.name!=old_name:raise ValueError('Compositor group name collision')
        if old:old.user_remap(staged)
        swapped=True
        report_progress({'phase':'verified compositor handoff','group':staged.name});check_cancelled()
        result=describe(staged)
        if old:bpy.data.node_groups.remove(old)
        success=True;return result
    finally:
        if not success:
            if old and swapped:staged.user_remap(old)
            bpy.data.node_groups.remove(staged)
            if old:old.name=old_name


def color_values(scene):
    return {key:plain(getattr(scene.display_settings if key=='display_device' else scene.view_settings,key)) for key in COLOR_KEYS}


def pass_owner(layer,key):
    path=PASSES[key]
    return (layer.cycles,path.split('.')[1]) if '.' in path else (layer,path)


def pipeline():
    supported();scene=bpy.context.scene;tree=scene.compositing_node_group
    layers=[]
    for layer in scene.view_layers:
        layers.append({'name':layer.name,'enabled':layer.use,'passes':{key:getattr(*pass_owner(layer,key)) for key in PASSES}})
    content={'scene':scene.name,'engine':scene.render.engine,'compositing':scene.render.use_compositing,
             'group':tree.name if tree else None,'graph_sha256':describe(tree)['graph_sha256'] if tree else None,
             'layers':layers,'color':color_values(scene)}
    return content|{'settings_sha256':digest(content),'scope':'Current scene compositor binding, pass flags and scalar color settings; not geometry, custom color curves, animation or external OCIO file contents.'}


def inspect_pipeline():
    result=pipeline();scene=bpy.context.scene;scratch=scene.copy()
    try:
        result['color_choices']={key:choices(scratch.display_settings if key=='display_device' else scratch.view_settings,key) for key in ('display_device','view_transform','look')}
        return result
    finally:bpy.data.scenes.remove(scratch)


def guard(p):
    scene=bpy.context.scene
    if scene.library or scene.override_library:raise ValueError('Render settings require a local scene')
    if pipeline()['settings_sha256']!=p['expected_settings']:raise ValueError('Render pipeline fingerprint is stale; inspect_render_pipeline again')
    return scene


def unanimated(scene,targets):
    if animation_paths(scene).intersection(targets):raise ValueError('Targeted render settings are keyed/driven; edit their animation explicitly')


def configure_passes(p):
    from .bridge import check_cancelled
    scene=guard(p);layer=scene.view_layers.get(p.get('view_layer',bpy.context.view_layer.name))
    if layer is None:raise ValueError('Render view layer not found')
    bindings=[(pass_owner(layer,key),value) for key,value in p['passes'].items()]
    if p['passes'].get('combined') is False:raise ValueError('Keep the Combined pass enabled for managed compositor output')
    unanimated(scene,{layer.path_from_id()+'.'+PASSES[key] for key in p['passes']})
    original=[((owner,key),getattr(owner,key)) for (owner,key),value in bindings]
    try:
        check_cancelled()
        for (owner,key),value in bindings:setattr(owner,key,value)
        layer.update_render_passes();bpy.context.view_layer.update()
        for candidate in bpy.data.scenes:
            tree=candidate.compositing_node_group
            if tree and candidate.render.use_compositing and tree.get(MARKER) and any(n.bl_idname=='CompositorNodeRLayers' and n.scene==scene and n.layer==layer.name for n in tree.nodes):validate(tree)
        check_cancelled();return pipeline()
    except BaseException:
        for (owner,key),value in original:setattr(owner,key,value)
        layer.update_render_passes();bpy.context.view_layer.update();raise


def configure_color(p):
    from .bridge import check_cancelled
    scene=guard(p);changes={key:p[key] for key in COLOR_KEYS if p.get(key) is not None}
    if not changes:raise ValueError('Supply color management settings')
    unanimated(scene,{(scene.display_settings if key=='display_device' else scene.view_settings).path_from_id(key) for key in changes})
    original=color_values(scene);scratch=scene.copy()
    def apply(target,values):
        for key in COLOR_KEYS:
            if key in values:setattr(target.display_settings if key=='display_device' else target.view_settings,key,values[key])
    try:
        apply(scratch,changes)
        for key,value in changes.items():
            actual=color_values(scratch)[key]
            if isinstance(value,(int,float)) and not isinstance(value,bool) and not math.isclose(actual,value,rel_tol=1e-6,abs_tol=1e-6):raise ValueError('Color setting exceeds native supported limits: '+key)
    finally:bpy.data.scenes.remove(scratch)
    check_cancelled()
    try:apply(scene,changes);check_cancelled();return pipeline()
    except BaseException:apply(scene,original);raise


def attach(p):
    from .bridge import check_cancelled
    scene=guard(p);tree=graph(p['group']) if p.get('group') else scene.compositing_node_group
    unanimated(scene,{'compositing_node_group','render.use_compositing'})
    if tree:
        state=describe(tree)
        if p.get('group') and state['graph_sha256']!=p.get('expected_graph'):raise ValueError('Compositor graph fingerprint is stale')
        if p['enabled']:
            if not state['editable']:raise ValueError('Enabling requires a managed local unanimated supported graph')
            validate(tree)
    elif p['enabled']:raise ValueError('No compositor group is bound; supply group and expected_graph')
    old=scene.compositing_node_group;enabled=scene.render.use_compositing
    try:
        check_cancelled();scene.compositing_node_group=tree;scene.render.use_compositing=p['enabled'];check_cancelled();return pipeline()
    except BaseException:scene.compositing_node_group=old;scene.render.use_compositing=enabled;raise


def dispatch(command,p):
    if command=='compositor_node_catalog':return catalog(p)
    if command=='inspect_compositor_graph':return describe(graph(p['group']))
    if command=='configure_compositor_graph':return configure_graph(p)
    if command=='inspect_render_pipeline':return inspect_pipeline()
    if command=='configure_render_passes':return configure_passes(p)
    if command=='configure_color_management':return configure_color(p)
    return attach(p)
