"""Independent static custom-field correspondence proof over decoded GLB buffers.

The versioned witness carries corner-local source rows. A private exported corner
ID avoids relying on exporter vertex order, material splits or UV seam duplication.
It consumes no UV channel. This is file correspondence, not runtime shader proof.
"""
from collections import Counter
import math
from types import SimpleNamespace
from .lod_files import read_glb,file_hash
from .skin_glb import Accessor,IDENTITY,multiply,matrix,trs,point
from .gltf_units import validate_document

FORMAT='mcpblender-numeric-fields-v1'
CORNER='_MCP_CORNER'


def cyclic(v):
    v=tuple(v);return min(v,v[1:]+v[:1],v[2:]+v[:2])


def close(actual,expected,tolerance):
    return len(actual)==len(expected) and all(math.isfinite(v) and math.isfinite(e) and abs(v-e)<=tolerance*max(1.,abs(e)) for v,e in zip(actual,expected))


def verify(path,witness,*,cancelled=None):
    cancel=cancelled or (lambda:None)
    if witness.get('format')!=FORMAT:raise ValueError('Unsupported numeric field witness version')
    positions=witness['positions'];count=len(positions);fields=witness['fields'];uvs=witness['uvs']
    if not 0<count<=4000000 or len(uvs)>8 or not 1<=len(fields)<=64:raise ValueError('Numeric field witness exceeds profile limits')
    if any(len(f['values'])!=count or f['semantic']==CORNER for f in fields) or len({f['semantic'] for f in fields})!=len(fields):raise ValueError('Invalid field witness inventory')
    if any(len(uv)!=count for uv in uvs):raise ValueError('Invalid UV witness inventory')
    for collection,width in [(positions,3),*[(uv,2) for uv in uvs],*[(f['values'],f['components']) for f in fields]]:
        if type(width)!=int or not 1<=width<=4 or any(not isinstance(row,(list,tuple)) or len(row)!=width or any(type(v) not in (int,float) or not math.isfinite(v) for v in row) for row in collection):raise ValueError('Nonfinite or malformed source witness rows')
    triangles=witness['triangles']
    if len(triangles)>2000000 or any(len(t)!=3 or any(type(i)!=int or not 0<=i<count for i in t) for t in triangles):raise ValueError('Invalid triangle witness')
    doc,binary=read_glb(path)
    if doc.get('animations') or doc.get('skins') or doc.get('extensionsRequired') or len(doc.get('meshes',[]))!=1:raise ValueError('Numeric field proof requires one uncompressed static mesh')
    unit=validate_document(doc,witness.get('scene_unit_scale',1.))
    nodes=doc.get('nodes',[])
    if not 1<=len(nodes)<=64:raise ValueError('Numeric field node budget exceeded')
    mesh_nodes=[i for i,n in enumerate(nodes) if 'mesh' in n]
    if len(mesh_nodes)!=1 or nodes[mesh_nodes[0]]['mesh']!=0 or any(n.get('extensions') for n in nodes):raise ValueError('Numeric field mesh placement is ambiguous or instanced')
    parents={}
    for i,n in enumerate(nodes):
        for child in n.get('children',[]):
            if type(child)!=int or not 0<=child<len(nodes) or child in parents:raise ValueError('Invalid numeric field hierarchy')
            parents[child]=i
    chain=[];current=mesh_nodes[0]
    while True:
        if current in chain:raise ValueError('Numeric field node cycle')
        chain.append(current)
        if current not in parents:break
        current=parents[current]
    scene=doc.get('scene',0)
    if type(scene)!=int or not 0<=scene<len(doc.get('scenes',[])) or current not in doc['scenes'][scene].get('nodes',[]):raise ValueError('Numeric field mesh is outside the active scene')
    world=IDENTITY
    for index in reversed(chain):
        n=nodes[index];local=matrix(n['matrix']) if 'matrix' in n else trs(n.get('translation',[0,0,0]),n.get('rotation',[0,0,0,1]),n.get('scale',[1,1,1]))
        world=multiply(world,local)
    native=witness.get('matrix_world',IDENTITY)
    for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1)):
        converted=(p[0],p[2],-p[1]);expected=point(native,p);expected=(expected[0]*unit,expected[2]*unit,-expected[1]*unit)
        if not close(point(world,converted),expected,2e-6):raise ValueError('Decoded world placement differs from source metre placement')
    document=SimpleNamespace(doc=doc,binary=binary,allow_sparse=False,check_cancelled=cancel)
    expected=Counter(cyclic(t) for t in triangles);actual=Counter();seen=set();rows=0;primitives=0
    for primitive in doc['meshes'][0]['primitives']:
        cancel();primitives+=1
        if primitive.get('mode',4)!=4 or primitive.get('targets') or primitive.get('extensions'):raise ValueError('Unsupported numeric field primitive')
        attrs=primitive['attributes']
        if CORNER not in attrs or any(f['semantic'] not in attrs for f in fields) or any('TEXCOORD_'+str(i) not in attrs for i in range(len(uvs))):raise ValueError('Export dropped a field, correspondence ID or UV map')
        ids=Accessor(document,attrs[CORNER]);pos=Accessor(document,attrs['POSITION'])
        decoded=[Accessor(document,attrs[f['semantic']]) for f in fields];tex=[Accessor(document,attrs['TEXCOORD_'+str(i)]) for i in range(len(uvs))]
        if ids.kind!=5126 or pos.kind!=5126 or ids.components!=1 or pos.components!=3 or any(a.count!=ids.count for a in [pos,*decoded,*tex]):raise ValueError('Field accessor cardinality mismatch')
        mapping=[]
        for i in range(ids.count):
            if i%256==0:cancel()
            value=ids.row(i)[0];index=int(value)
            if value!=index or not 0<=index<count:raise ValueError('Invalid decoded corner correspondence')
            mapping.append(index);seen.add(index);rows+=1
            # Native exporter uses glTF +Y up; custom vectors remain raw payloads.
            p=positions[index];converted=(p[0],p[2],-p[1])
            if not close(pos.row(i),converted,2e-6):raise ValueError('Decoded position differs from source corner')
            for field,a in zip(fields,decoded):
                if a.kind!=5126 or a.components!=field['components'] or not close(a.row(i),field['values'][index],1e-7):raise ValueError('Decoded custom field differs from source: '+field['semantic'])
            for uv,a in zip(uvs,tex):
                value=uv[index]
                if not close(a.row(i),(value[0],1-value[1]),2e-6):raise ValueError('Decoded UV differs from source; lightmap channel preservation failed')
        indices=Accessor(document,primitive['indices']) if 'indices' in primitive else None
        length=indices.count if indices else ids.count
        if length%3 or indices and indices.components!=1:raise ValueError('Invalid triangle indices')
        for start in range(0,length,3):
            if start%768==0:cancel()
            trip=[]
            for j in range(start,start+3):
                value=indices.row(j)[0] if indices else j;index=int(value)
                if value!=index or not 0<=index<len(mapping):raise ValueError('Triangle index outside field rows')
                trip.append(mapping[index])
            actual[cyclic(trip)]+=1
    if actual!=expected or seen!={i for t in triangles for i in t}:raise ValueError('Decoded triangle/corner coverage differs from source')
    return {'format':FORMAT,'glb_sha256':file_hash(path),'primitives':primitives,'decoded_rows':rows,
            'triangles':sum(actual.values()),'source_corners':len(seen),'fields':[f['semantic'] for f in fields],
            'uv_channels':len(uvs),'scene_unit_scale':unit,'world_placement_verified':True,'scope':'Decoded local-position, metre placement, oriented triangle, corner-field and UV correspondence. No engine import or runtime shader qualification.'}
