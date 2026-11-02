"""Component dependency graph for the explicitly supported constraint workflows."""
SUPPORTED={'COPY_LOCATION','COPY_ROTATION','COPY_TRANSFORMS','LIMIT_LOCATION','LIMIT_ROTATION','LIMIT_SCALE','DAMPED_TRACK','IK'}


def build_graph(records):
    graph={};blocked={}
    def ensure(node):return graph.setdefault(node,set())
    for obj in records:
        name=obj['name'];object_node=(name,None);ensure(object_node)
        if obj.get('parent'):ensure(object_node).add(tuple(obj['parent']))
        if obj.get('blocked'):blocked[object_node]=obj['blocked']
        for bone,parent in obj.get('bones',{}).items():
            ensure((name,bone)).add((name,parent))
        for item in obj.get('constraints',[]):
            owner=(name,item.get('bone'));affected=[owner]
            if item['type']=='IK' and owner[1] is not None:
                current=owner[1];count=item.get('chain_count',0);seen=set()
                affected=[]
                while current is not None and (not count or len(affected)<count):
                    if current in seen:raise ValueError('Bone parent cycle in dependency records')
                    seen.add(current);affected.append((name,current));current=obj['bones'].get(current)
            for node in affected:
                ensure(node).update(tuple(v) for v in item.get('targets',[]))
                if item.get('blocked') or item['type'] not in SUPPORTED:
                    blocked[node]=item.get('blocked') or 'Unsupported constraint dependency: '+item['type']
    return graph,blocked


def validate_graph(records,roots):
    graph,blocked=build_graph(records);finished=set();visiting=set()
    # Iteration avoids recursion limits for long native parent chains.
    for root in roots:
        todo=[(tuple(root),False)]
        while todo:
            node,leave=todo.pop()
            if leave:visiting.remove(node);finished.add(node);continue
            if node in finished:continue
            if node in visiting:raise ValueError('Constraint dependency cycle detected')
            if node not in graph:raise ValueError('Missing constraint dependency object/bone')
            if node in blocked:raise ValueError(blocked[node])
            visiting.add(node);todo.append((node,True))
            todo.extend((target,False) for target in graph[node])
