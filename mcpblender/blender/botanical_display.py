"""Transactional display changes for source and owned botanical collections."""
import bpy
from mcpblender import botany
from . import botanical_trees,botanical_subsets,depth_assets

COMMANDS={'inspect_botanical_display','configure_botanical_display'}
FIELDS=('hide_viewport','hide_render')


def animated(value):
    paths=set();animation=getattr(value,'animation_data',None)
    if animation:
        from .domains import curves
        paths.update(c.data_path for c in animation.drivers if c.data_path in FIELDS)
        actions=[(animation.action,getattr(animation,'action_slot',None))] if animation.action else []
        actions.extend((strip.action,getattr(strip,'action_slot',None)) for track in animation.nla_tracks for strip in track.strips if strip.action)
        for action,slot in actions:paths.update(c.data_path for c in curves(action,slot) if c.data_path in FIELDS)
    return sorted(paths)


def contexts(collections):
    """Bound every scene/layer occurrence, including hidden ancestor paths."""
    from .bridge import check_cancelled
    reports={col:[] for col in collections};work=0
    if len(bpy.data.scenes)>128:raise ValueError('Display scene budget exceeded')
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            stack=[(layer.layer_collection,[])]
            while stack:
                node,path=stack.pop();work+=1
                if work%128==0:check_cancelled()
                if work>16384 or len(path)>128:raise ValueError('Display visibility-context work budget exceeded')
                col=node.collection
                here=path+[{'collection':col.name,'hide_viewport':col.hide_viewport,'hide_render':col.hide_render,'layer_hide_viewport':node.hide_viewport,'exclude':node.exclude,'holdout':node.holdout,'indirect_only':node.indirect_only}]
                if col in reports:
                    reports[col].append({'scene':scene.name,'view_layer':layer.name,'layer_use':layer.use,'path':here,
                                         'collection_viewport_enabled':not any(r['hide_viewport'] or r['layer_hide_viewport'] or r['exclude'] for r in here),
                                         'collection_render_enabled':layer.use and not any(r['hide_render'] or r['exclude'] for r in here)})
                stack.extend((child,here) for child in node.children)
    return reports


def resolve(target):
    name=target['collection'];kind=target['kind']
    if kind=='SOURCE':
        state=botanical_trees.inspect({'collection':name});guard=state['tree_sha256']
    elif kind=='DEPTH':
        state=depth_assets.inspect({'collection':name})[-1];guard=state['asset_sha256']
    elif kind=='SUBSET':
        state=botanical_subsets.inspect({'subset_collection':name})[-1];guard=state['subset_sha256']
    else:raise ValueError('Unknown botanical display kind')
    return bpy.data.collections[name],state,guard


def inspect(p):
    from .bridge import check_cancelled
    if bpy.context.mode!='OBJECT':raise ValueError('Botanical display requires Object mode')
    targets=p['targets']
    if not 1<=len(targets)<=16 or len({t['collection'] for t in targets})!=len(targets):raise ValueError('Choose1..16 distinct display collections')
    resolved=[]
    for target in targets:
        check_cancelled();resolved.append(resolve(target))
    locations=contexts([v[0] for v in resolved]);rows=[];scene=bpy.context.scene
    for target,(col,state,guard) in zip(targets,resolved):
        occurrences=locations[col];issues=list(state['issues'])+list(state['ownership_blockers'])
        if not any(row['scene']==scene.name for row in occurrences):issues.append('Collection is not linked in the current scene')
        if any(row['scene']!=scene.name for row in occurrences):issues.append('Display collection is also linked in another scene')
        if col.library or col.override_library:issues.append('Display collection must be local and editable')
        rows.append({'kind':target['kind'],'collection':col.name,'identity':col.as_pointer(),'valid':state['valid'] and not issues,'issues':sorted(set(issues)),
                     'state_sha256':guard,'visibility':{k:getattr(col,k) for k in FIELDS},'animated_fields':animated(col),'contexts':occurrences})
    body={'scene':scene.name,'scene_identity':scene.as_pointer(),'view_layer':bpy.context.view_layer.name,'frame':scene.frame_current,'subframe':scene.frame_subframe,'targets':rows}
    return resolved,body|{'display_sha256':botany.digest(body),'valid':all(row['valid'] for row in rows),
                         'scope':'Collection-wide flags only. Individual object visibility, Cycles ray roles, layer exclusions and ancestors remain unchanged. Visibility flags affect current scene view layers; other-scene links refuse. No geometry, shader or optical validation beyond each target ownership inspection.'}


def configure(p):
    from .bridge import check_cancelled
    resolved,state=inspect(p)
    if state['display_sha256']!=p['expected_display']:raise ValueError('Botanical display guard is stale')
    if not state['valid']:raise ValueError('Display target ownership or scene context is invalid: '+str([r['issues'] for r in state['targets'] if not r['valid']]))
    changes=[]
    for target,(col,_,_),row in zip(p['targets'],resolved,state['targets']):
        patch={k:target[k] for k in FIELDS if target.get(k) is not None}
        if not patch:raise ValueError('Supply a display field for every target')
        if set(patch).intersection(row['animated_fields']):raise ValueError('Targeted collection visibility is keyed or driven')
        changes.append((col,patch,{k:getattr(col,k) for k in patch}))
    try:
        check_cancelled()
        for col,patch,_ in changes:
            for key,value in patch.items():setattr(col,key,value)
            check_cancelled()
        bpy.context.view_layer.update();check_cancelled()
        result=inspect(p)[-1]
        if not result['valid']:raise ValueError('Display target became invalid after switch')
        return result
    except BaseException:
        for col,_,old in reversed(changes):
            for key,value in old.items():setattr(col,key,value)
        bpy.context.view_layer.update();raise


def dispatch(command,p):return inspect(p)[-1] if command=='inspect_botanical_display' else configure(p)
