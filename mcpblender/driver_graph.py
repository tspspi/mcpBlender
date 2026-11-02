"""Driver property nodes layered over object/bone evaluated-transform graphs."""
from .animation_graph import build_graph


def validate_drivers(records,drivers,root):
    base,blocked_base=build_graph(records)
    graph={('EVAL',*k):{('EVAL',*v) for v in values} for k,values in base.items()}
    blocked={('EVAL',*k):v for k,v in blocked_base.items()}
    for row in drivers:
        node=tuple(row['node']); graph.setdefault(node,set()).update(tuple(v) for v in row['inputs'])
        if row.get('blocked'):blocked[node]=row['blocked']
        for affected in row.get('affects',[]):graph.setdefault(('EVAL',*affected),set()).add(node)
    # Undriven numeric properties are leaves, supplied by the trusted inventory.
    for row in drivers:
        for node in row['inputs']:
            if node[0]=='RAW':graph.setdefault(tuple(node),set())
    visited=set();active=set();todo=[(tuple(root),False)]
    while todo:
        node,leave=todo.pop()
        if leave:active.remove(node);visited.add(node);continue
        if node in visited:continue
        if node in active:raise ValueError('Animation driver dependency cycle detected')
        if node not in graph:raise ValueError('Missing driver dependency')
        if node in blocked:raise ValueError(blocked[node])
        active.add(node);todo.append((node,True));todo.extend((v,False) for v in graph[node])
