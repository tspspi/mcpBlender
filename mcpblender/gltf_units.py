"""Uniform scene-unit conversion at glTF roots without rewriting mesh/skin buffers."""
import json
import math
from pathlib import Path
import struct

KEY='mcpblender_units'


def factor(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite scene unit scale required')
    return float(value)


def validate_document(doc,expected=None):
    expected=factor(expected) if expected is not None else None
    extra=doc.get('asset',{}).get('extras',{});meta=extra.get(KEY) if isinstance(extra,dict) else None
    if meta is None:
        if expected not in (None,1.):raise ValueError('Missing GLB scene-unit normalization')
        return 1.
    if not isinstance(meta,dict) or meta.get('version')!=1:raise ValueError('Unsupported GLB unit metadata')
    scale=factor(meta.get('scene_unit_scale'))
    if expected is not None and scale!=expected:raise ValueError('GLB scene unit scale differs from source declaration')
    nodes=doc.get('nodes',[]);scenes=doc.get('scenes',[]);roots=meta.get('roots')
    if not isinstance(roots,list) or len(roots)>len(nodes):raise ValueError('Malformed GLB unit roots')
    parents={i:[] for i in range(len(nodes))}
    for i,node in enumerate(nodes):
        for child in node.get('children',[]):
            if type(child)!=int or child not in parents:raise ValueError('Invalid GLB child index')
            parents[child].append(i)
    owners=set();sources=set()
    for item in roots:
        if not isinstance(item,dict) or set(item)!={'node','source_root'}:raise ValueError('Invalid GLB unit root entry')
        index=item['node'];source=item['source_root']
        if any(type(i)!=int or not 0<=i<len(nodes) for i in (index,source)) or index in owners or source in sources or index==source:raise ValueError('Duplicate/invalid GLB unit root')
        node=nodes[index]
        if set(node)!={'name','scale','children','extras'} or node['scale']!=[scale]*3 or node['children']!=[source] or node['extras']!={'mcpblender_unit_root':1}:raise ValueError('GLB unit root transform differs from declared scale')
        if parents[index] or parents[source]!=[index]:raise ValueError('GLB unit root has unexpected parent links')
        owners.add(index);sources.add(source)
    referenced=set()
    for scene in scenes:
        indices=scene.get('nodes',[])
        if len(set(indices))!=len(indices) or any(type(i)!=int or i not in owners for i in indices):raise ValueError('GLB scene bypasses unit normalization')
        referenced.update(indices)
    if referenced!=owners or owners&sources:raise ValueError('Unused or nested GLB unit roots')
    return scale


def normalize_document(doc,scale):
    scale=factor(scale)
    if scale==1:return False
    asset=doc.setdefault('asset',{});extra=asset.setdefault('extras',{})
    if not isinstance(extra,dict) or KEY in extra:raise ValueError('GLB export already declares unit normalization')
    nodes=doc.setdefault('nodes',[]);scenes=doc.get('scenes',[])
    indices={i for scene in scenes for i in scene.get('nodes',[])}
    if any(type(i)!=int or not 0<=i<len(nodes) for i in indices):raise ValueError('Invalid GLB scene roots')
    if any(i in indices for node in nodes for i in node.get('children',[])):raise ValueError('GLB scene root is also a child')
    mapping={};roots=[]
    for index in sorted(indices):
        new=len(nodes);mapping[index]=new;roots.append({'node':new,'source_root':index})
        nodes.append({'name':'MCP Scene Units '+str(index),'scale':[scale]*3,'children':[index],'extras':{'mcpblender_unit_root':1}})
    for scene in scenes:scene['nodes']=[mapping[i] for i in scene.get('nodes',[])]
    extra[KEY]={'version':1,'scene_unit_scale':scale,'roots':roots}
    validate_document(doc,scale)
    return True


def normalize_file(path,scale):
    scale=factor(scale)
    if scale==1:return False
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>512*1024**2:raise ValueError('GLB normalization requires an ordinary file up to 512 MiB')
    data=path.read_bytes()
    if len(data)<20 or struct.unpack_from('<4sII',data)!=(b'glTF',2,len(data)):raise ValueError('Invalid GLB header')
    size,kind=struct.unpack_from('<II',data,12)
    if kind!=0x4e4f534a or size>16*1024**2 or size%4 or 20+size>len(data):raise ValueError('Invalid GLB JSON chunk')
    cursor=20+size
    while cursor<len(data):
        if cursor+8>len(data):raise ValueError('Truncated GLB chunk')
        count,tag=struct.unpack_from('<II',data,cursor);cursor+=8
        if tag==0x4e4f534a or count%4 or cursor+count>len(data):raise ValueError('Invalid trailing GLB chunk')
        cursor+=count
    doc=json.loads(data[20:20+size]);normalize_document(doc,scale)
    encoded=json.dumps(doc,separators=(',',':'),allow_nan=False).encode();encoded+=b' '*((-len(encoded))%4)
    if len(encoded)>16*1024**2:raise ValueError('Normalized GLB JSON exceeds 16 MiB')
    # Like the native exporter, write only this owned output path. Do not create
    # unjournaled sibling artifacts that could obstruct interrupted-job recovery.
    with path.open('wb') as out:
        out.write(struct.pack('<4sII',b'glTF',2,len(data)-size+len(encoded)))
        out.write(struct.pack('<I4s',len(encoded),b'JSON'));out.write(encoded);out.write(memoryview(data)[20+size:])
    return True


def native_comparison(doc,expected):
    scale=validate_document(doc,expected)
    if scale!=1:
        for item in doc['asset']['extras'][KEY]['roots']:doc['nodes'][item['node']]['scale']=[1.,1.,1.]
    return scale
