"""Whole-hierarchy rest plans with deterministic connected-head following."""
import math
import struct


def plan_rest(original,patches,additions):
    planned={name:dict(row) for name,row in original.items()};explicit_heads=set()
    for patch in patches:
        name=patch['name']
        if name not in planned:raise ValueError('Existing rest bone not found: '+name)
        if patch.get('head') is not None:explicit_heads.add(name)
        planned[name].update({k:v for k,v in patch.items() if k!='name' and v is not None})
        if patch.get('roll_degrees') is not None:planned[name]['roll_degrees']=math.remainder(patch['roll_degrees'],360)
    for row in additions:
        if row['name'] in planned:raise ValueError('New bone name already exists')
        planned[row['name']]=dict(row);planned[row['name']]['roll_degrees']=math.remainder(row['roll_degrees'],360);explicit_heads.add(row['name'])
    if len(planned)>512:raise ValueError('Rest refinement supports at most 512 bones')
    for row in planned.values():
        for key in ('head','tail'):
            try:row[key]=list(struct.unpack('!3f',struct.pack('!3f',*row[key])))
            except (OverflowError,struct.error):raise ValueError('Rest coordinates exceed native float precision') from None
        row['parent']=row.get('parent') or None
        if row['parent'] and row['parent'] not in planned:raise ValueError('Rest bone parent not found')
    ordered=[];visited=set()
    for name in planned:
        chain=[];seen=set();current=name
        while current and current not in visited:
            if current in seen:raise ValueError('Bone parent hierarchy contains a cycle')
            chain.append(current);seen.add(current);current=planned[current]['parent']
        for bone in reversed(chain):visited.add(bone);ordered.append(bone)
    for name in ordered:
        row=planned[name]
        if row['connected']:
            if not row['parent']:raise ValueError('Connected bone requires a parent')
            head=planned[row['parent']]['tail']
            if name in explicit_heads and max(abs(a-b) for a,b in zip(head,row['head']))>1e-5:raise ValueError('Explicit connected head must match parent tail')
            row['head']=list(head)
        if any(not math.isfinite(v) for k in ('head','tail') for v in row[k]):raise ValueError('Rest coordinates must be finite')
        if sum((a-b)**2 for a,b in zip(row['head'],row['tail']))<1e-12:raise ValueError('Rest bones require nonzero length')
    return planned,ordered
