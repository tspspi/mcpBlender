"""Independent glTF skin/morph validation and sampled world replay.

Uses only the standard library, not bpy or native glTF importer/exporter code.
Matrices multiply column vectors; glTF serialized matrices are column-major.
"""
import bisect
from array import array
import math
import hashlib
import json
import struct

from .lod_files import read_glb

IDENTITY=((1.,0.,0.,0.),(0.,1.,0.,0.),(0.,0.,1.,0.),(0.,0.,0.,1.))


def multiply(a,b):return tuple(tuple(sum(a[r][i]*b[i][c] for i in range(4)) for c in range(4)) for r in range(4))
def point(a,p):return tuple(sum(a[r][c]*p[c] for c in range(3))+a[r][3] for r in range(3))
def matrix(values):return tuple(tuple(values[c*4+r] for c in range(4)) for r in range(4))


def trs(t,q,s):
    x,y,z,w=q
    if abs(x*x+y*y+z*z+w*w-1)>1e-4:raise ValueError('Nonunit glTF quaternion')
    r=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),(2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),(2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
    return tuple(tuple(r[i][j]*s[j] for j in range(3))+(t[i],) for i in range(3))+((0.,0.,0.,1.),)


def normalize(v):
    size=math.sqrt(sum(x*x for x in v))
    if size<1e-20:raise ValueError('Zero animated quaternion')
    return tuple(x/size for x in v)


def interpolate(a,b,t,rotation=False):
    if not rotation:return tuple(x+(y-x)*t for x,y in zip(a,b))
    dot=sum(x*y for x,y in zip(a,b))
    if dot<0:b=tuple(-x for x in b);dot=-dot
    dot=max(-1,min(1,dot))
    if dot>.9995:return normalize(tuple(x+(y-x)*t for x,y in zip(a,b)))
    angle=math.acos(dot);den=math.sin(angle)
    return tuple((math.sin((1-t)*angle)*x+math.sin(t*angle)*y)/den for x,y in zip(a,b))


class Accessor:
    def __init__(self,document,index):
        d,b=document.doc,document.binary
        if type(index)!=int or not 0<=index<len(d.get('accessors',[])):raise ValueError('Invalid glTF accessor index')
        a=d['accessors'][index]
        if a.get('normalized') or (a.get('sparse') and not document.allow_sparse):raise ValueError('Skin decoder requires dense nonnormalized accessors')
        types={5121:(1,'B'),5123:(2,'H'),5125:(4,'I'),5126:(4,'f')}
        if a.get('componentType') not in types or a.get('type') not in {'SCALAR','VEC2','VEC3','VEC4','MAT4'}:raise ValueError('Unsupported skin accessor type')
        self.kind=a['componentType'];size,fmt=types[self.kind];self.components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];self.type=a['type'];self.count=a['count']
        if type(self.count)!=int or not 0<self.count<=2000000:raise ValueError('Skin accessor count outside limits')
        self.unpack=struct.Struct('<'+fmt*self.components);self.binary=b;self.start=None;self.stride=size*self.components;self.sparse_indices=array('I');self.sparse_start=None
        if 'bufferView' in a:self.start,self.stride=self.region(document,a['bufferView'],a.get('byteOffset',0),self.count,self.unpack.size)
        elif not document.allow_sparse or a.get('byteOffset',0):raise ValueError('Missing dense buffer view')
        if 'sparse' in a:
            sparse=a['sparse'];count=sparse['count'];indices=sparse['indices'];values=sparse['values'];kind=indices['componentType']
            if type(count)!=int or not 1<=count<=self.count or kind not in {5121,5123,5125}:raise ValueError('Invalid sparse accessor count/index type')
            index_size,index_fmt=types[kind];start,stride=self.region(document,indices['bufferView'],indices.get('byteOffset',0),count,index_size,sparse=True)
            self.sparse_start,_=self.region(document,values['bufferView'],values.get('byteOffset',0),count,self.unpack.size,sparse=True)
            read=struct.Struct('<'+index_fmt);previous=-1
            for i in range(count):
                if i%128==0:document.check_cancelled()
                value=read.unpack_from(b,start+i*stride)[0]
                if not previous<value<self.count:raise ValueError('Sparse indices must be ordered, distinct and in range')
                self.sparse_indices.append(value);previous=value
    @staticmethod
    def region(document,index,offset,count,size,*,sparse=False):
        d,b=document.doc,document.binary
        if type(index)!=int or not 0<=index<len(d.get('bufferViews',[])):raise ValueError('Invalid skin buffer view')
        view=d['bufferViews'][index];base=view.get('byteOffset',0);stride=view.get('byteStride',size);length=view['byteLength']
        if any(type(v)!=int for v in (base,offset,stride,length)) or min(base,offset,length)<0 or stride<size or (sparse and 'byteStride' in view):raise ValueError('Invalid accessor byte layout')
        start=base+offset;end=start+(count-1)*stride+size
        if view.get('buffer',0)!=0 or end>min(len(b),d['buffers'][0]['byteLength'],base+length):raise ValueError('Skin accessor exceeds buffer view')
        return start,stride
    def row(self,index):
        if type(index)!=int or not 0<=index<self.count:raise ValueError('Accessor row out of range')
        location=bisect.bisect_left(self.sparse_indices,index)
        if location<len(self.sparse_indices) and self.sparse_indices[location]==index:value=self.unpack.unpack_from(self.binary,self.sparse_start+location*self.unpack.size)
        elif self.start is not None:value=self.unpack.unpack_from(self.binary,self.start+index*self.stride)
        else:value=(0,)*self.components
        if not all(math.isfinite(v) for v in value):raise ValueError('Nonfinite skin/animation data')
        return value


class WeightRows:
    def __init__(self,scalar,count):
        self.scalar=scalar;self.width=count;self.count=scalar.count//count;self.kind=scalar.kind
    def row(self,index):return tuple(self.scalar.row(index*self.width+i)[0] for i in range(self.width))


class Document:
    def __init__(self,path,*,morphs=False,check_cancelled=None):
        self.allow_sparse=morphs;self.check_cancelled=check_cancelled or (lambda:None)
        self.doc,self.binary=read_glb(path);self.arrays={};self.nodes=self.doc.get('nodes',[])
        if not 1<=len(self.nodes)<=2048 or len(self.doc.get('meshes',[]))!=1 or len(self.doc.get('skins',[])) not in ({0,1} if morphs else {1}):raise ValueError('Expected one bounded mesh and at most one skin')
        if any('EXT_meshopt_compression' in v.get('extensions',{}) for v in self.doc.get('bufferViews',[])) or any('EXT_mesh_gpu_instancing' in n.get('extensions',{}) for n in self.nodes) or any('KHR_draco_mesh_compression' in p.get('extensions',{}) for m in self.doc.get('meshes',[]) for p in m.get('primitives',[])):raise ValueError('Compressed or instanced GLB geometry is outside the replay profile')
        self.parents={}
        for i,node in enumerate(self.nodes):
            for child in node.get('children',[]):
                if type(child)!=int or not 0<=child<len(self.nodes) or child in self.parents:raise ValueError('Invalid/multiply parented glTF node')
                self.parents[child]=i
        for i in range(len(self.nodes)):
            seen=set();current=i
            while current in self.parents:
                if current in seen:raise ValueError('glTF node hierarchy cycle')
                seen.add(current);current=self.parents[current]
                if len(seen)>512:raise ValueError('Node hierarchy exceeds 512 levels')
        self.joints=[];self.names=[];self.inverse=[]
        if self.doc.get('skins'):
            skin=self.doc['skins'][0];self.joints=skin['joints']
            if not 1<=len(self.joints)<=256 or len(set(self.joints))!=len(self.joints) or any(type(i)!=int or not 0<=i<len(self.nodes) for i in self.joints):raise ValueError('Invalid skin joints')
            self.names=[self.nodes[i].get('name','') for i in self.joints]
            if not all(self.names) or len(set(self.names))!=len(self.names):raise ValueError('Distinct named skin joints required')
            inverse=self.array(skin['inverseBindMatrices'])
            if inverse.kind!=5126 or inverse.type!='MAT4' or inverse.count!=len(self.joints):raise ValueError('Invalid inverse-bind matrices')
            self.inverse=[matrix(inverse.row(i)) for i in range(inverse.count)]
            if any(abs(row[3][c]-(1 if c==3 else 0))>1e-5 for row in self.inverse for c in range(4)):raise ValueError('Inverse binds must be affine')
            for m in self.inverse:
                determinant=m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0])
                scale=max(abs(v) for row in m[:3] for v in row[:3])
                if not scale or abs(determinant)/(scale**3)<1e-12:raise ValueError('Inverse binds must be nondegenerate')
        mesh_nodes=[(i,n) for i,n in enumerate(self.nodes) if 'mesh' in n]
        if len(mesh_nodes)!=1 or mesh_nodes[0][1]['mesh']!=0 or (mesh_nodes[0][1].get('skin')!=0 if self.joints else 'skin' in mesh_nodes[0][1]):raise ValueError('Mesh must reference the validated skin when present')
        self.mesh_node=mesh_nodes[0][0];mesh=self.doc['meshes'][0]
        counts={len(p.get('targets',[])) for p in mesh['primitives']}
        if len(counts)!=1:raise ValueError('Morph target counts differ between primitives')
        self.morph_count=next(iter(counts)) if counts else 0
        if self.morph_count and not morphs:raise ValueError('Morph targets require morph-enabled replay')
        if self.morph_count>63:raise ValueError('Morph replay supports at most 63 non-Basis targets')
        self.target_names=mesh.get('extras',{}).get('targetNames',[f'Target_{i}' for i in range(self.morph_count)])
        if len(self.target_names)!=self.morph_count or not all(isinstance(n,str) and n for n in self.target_names) or len(set(self.target_names))!=self.morph_count:raise ValueError('Distinct morph target names required')
        self.default_weights=self.weight_vector(self.nodes[self.mesh_node].get('weights',mesh.get('weights',[0.]*self.morph_count)))
        for node in self.nodes:
            if 'weights' in node:
                if node is not self.nodes[self.mesh_node]:raise ValueError('Weights on a nonmesh node')
                self.weight_vector(node['weights'])
        if 'weights' in mesh:self.weight_vector(mesh['weights'])
        self.morph_targets=[]
        self.primitives=[];total=0
        for primitive in self.doc['meshes'][0]['primitives']:
            attrs=primitive['attributes']
            if any(k.startswith(('JOINTS_','WEIGHTS_')) and k not in {'JOINTS_0','WEIGHTS_0'} for k in attrs):raise ValueError('Skin bundle supports four influences')
            p=self.array(attrs['POSITION']);j=w=None
            if p.type!='VEC3' or p.kind!=5126:raise ValueError('Position attribute layout mismatch')
            if self.joints:
                j,w=(self.array(attrs[k]) for k in ('JOINTS_0','WEIGHTS_0'))
                if j.type!='VEC4' or j.kind not in {5121,5123} or w.type!='VEC4' or w.kind!=5126 or not p.count==j.count==w.count:raise ValueError('Skin attribute layout mismatch')
                for i in range(p.count):
                    if i%128==0:self.check_cancelled()
                    weights=w.row(i);joints=j.row(i)
                    if any(not 0<=v<=1 for v in weights) or abs(sum(weights)-1)>1e-4 or any(v>=len(self.joints) for v in joints):raise ValueError('Invalid normalized skin influences')
            elif any(k.startswith(('JOINTS_','WEIGHTS_')) for k in attrs):raise ValueError('Joint attributes without a skin')
            targets=[]
            for target in primitive.get('targets',[]):
                if set(target)-{'POSITION','NORMAL','TANGENT'}:raise ValueError('Unsupported morph target attribute')
                for name,index in target.items():
                    values=self.array(index)
                    if values.kind!=5126 or values.type!='VEC3' or values.count!=p.count:raise ValueError('Morph target attribute layout mismatch')
                    for i in range(values.count):
                        if i%128==0:self.check_cancelled()
                        values.row(i)
                targets.append(self.array(target['POSITION']) if 'POSITION' in target else None)
            self.morph_targets.append(targets)
            self.primitives.append((p,j,w));total+=p.count
        if self.morph_count*total>4000000:raise ValueError('Morph replay supports four million target-vertex entries')
        if not 0<total<=2000000:raise ValueError('Skin vertex count outside limits')
        self.vertex_count=total;self._representatives={};self.clips={};keys=0
        for animation in self.doc.get('animations',[]):
            name=animation.get('name')
            if not name or name in self.clips or len(self.clips)>=32:raise ValueError('Expected at most 32 distinct named clips')
            channels=[];targets=set()
            for channel in animation['channels']:
                target=channel['target'];node=target['node'];path=target['path'];sampler=animation['samplers'][channel['sampler']]
                if type(node)!=int or not 0<=node<len(self.nodes) or path not in ({'translation','rotation','scale','weights'} if morphs else {'translation','rotation','scale'}) or (node,path) in targets or (path!='weights' and 'matrix' in self.nodes[node]):raise ValueError('Unsupported/duplicate animated node channel')
                targets.add((node,path));times=self.array(sampler['input']);values=self.array(sampler['output']);mode=sampler.get('interpolation','LINEAR')
                if path=='weights':
                    if node!=self.mesh_node or not self.morph_count or values.type!='SCALAR' or values.count%self.morph_count:raise ValueError('Invalid morph weight sampler layout')
                    values=WeightRows(values,self.morph_count)
                if times.kind!=5126 or times.type!='SCALAR' or mode not in {'LINEAR','STEP','CUBICSPLINE'} or values.kind!=5126 or (path!='weights' and values.type!=('VEC4' if path=='rotation' else 'VEC3')) or values.count!=times.count*(3 if mode=='CUBICSPLINE' else 1):raise ValueError('Invalid animation sampler')
                t=tuple(times.row(i)[0] for i in range(times.count));keys+=values.count*(self.morph_count if path=='weights' else 1)
                if keys>2000000 or t[0]<0 or any(a>=b for a,b in zip(t,t[1:])):raise ValueError('Animation time/key limits exceeded')
                for i in range(values.count):
                    if i%128==0:self.check_cancelled()
                    value=values.row(i)
                    if path=='rotation' and (mode!='CUBICSPLINE' or i%3==1) and abs(sum(v*v for v in value)-1)>1e-4:raise ValueError('Nonunit animation quaternion')
                channels.append((node,path,t,values,mode))
            if not channels:raise ValueError('Empty animation clip')
            self.clips[name]=channels
        # Validate all default transforms, including nodes unused by animation.
        self.world(None,0)
    def weight_vector(self,values):
        if not isinstance(values,(list,tuple)) or len(values)!=self.morph_count or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Invalid default morph weights')
        return tuple(values)
    def array(self,index):
        if type(index)!=int:raise ValueError('Invalid glTF accessor index')
        if index not in self.arrays:self.arrays[index]=Accessor(self,index)
        return self.arrays[index]
    def channel_value(self,channel,time):
        node,path,t,values,mode=channel;idx=max(0,min(len(t)-1,bisect.bisect_right(t,time)-1))
        if time==t[idx]:return values.row(idx*3+1 if mode=='CUBICSPLINE' else idx)
        if mode=='CUBICSPLINE':
            if idx==len(t)-1 or time<=t[0]:value=values.row(idx*3+1)
            else:
                dt=t[idx+1]-t[idx];u=(time-t[idx])/dt;a=values.row(idx*3+1);b=values.row((idx+1)*3+1);out=values.row(idx*3+2);incoming=values.row((idx+1)*3)
                value=tuple((2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*dt*o+(-2*u**3+3*u*u)*y+(u**3-u*u)*dt*n for x,o,y,n in zip(a,out,b,incoming))
            return normalize(value) if path=='rotation' else value
        if mode=='STEP' or idx==len(t)-1 or time<=t[0]:return values.row(idx)
        return interpolate(values.row(idx),values.row(idx+1),(time-t[idx])/(t[idx+1]-t[idx]),path=='rotation')
    def world(self,clip,time):
        channels=self.clips[clip] if clip is not None else [];overrides={(c[0],c[1]):self.channel_value(c,time) for c in channels};result={}
        def visit(index):
            if index in result:return result[index]
            node=self.nodes[index]
            if 'matrix' in node:
                if len(node['matrix'])!=16:raise ValueError('Invalid node matrix')
                local=matrix(node['matrix'])
            else:local=trs(overrides.get((index,'translation'),node.get('translation',(0,0,0))),overrides.get((index,'rotation'),node.get('rotation',(0,0,0,1))),overrides.get((index,'scale'),node.get('scale',(1,1,1))))
            if any(not math.isfinite(v) for row in local for v in row):raise ValueError('Nonfinite node transform')
            if any(abs(local[3][c]-(1 if c==3 else 0))>1e-6 for c in range(4)):raise ValueError('Node transforms must be affine')
            result[index]=multiply(visit(self.parents[index]),local) if index in self.parents else local
            if any(not math.isfinite(v) for row in result[index] for v in row):raise ValueError('Nonfinite world transform')
            return result[index]
        for i in range(len(self.nodes)):visit(i)
        return result
    def times(self,clip,count):
        times=sorted({t for channel in self.clips[clip] for t in channel[2]})
        return sorted({times[0]+(times[-1]-times[0])*i/(count-1) for i in range(count)})
    def vertices(self):
        for primitive,(p,j,w) in enumerate(self.primitives):
            for i in range(p.count):yield primitive,i,p.row(i),j.row(i) if j else (),w.row(i) if w else ()
    def representatives(self,limit=256):
        if limit in self._representatives:return self._representatives[limit]
        selected=set();by_joint={};by_target={};offset=0;count=min(limit,self.vertex_count)
        offsets={round(i*(self.vertex_count-1)/max(1,count-1)) for i in range(count)}
        for primitive,i,p,j,w in self.vertices():
            if i%128==0:self.check_cancelled()
            if offset in offsets:selected.add((primitive,i))
            for joint,weight in zip(j,w):
                if weight<=0:continue
                for axis in range(3):
                    for direction in (-1,1):
                        key=(joint,axis,direction);candidate=(direction*p[axis],primitive,i)
                        if key not in by_joint or candidate[0]>by_joint[key][0]:by_joint[key]=candidate
            for target,values in enumerate(self.morph_targets[primitive]):
                delta=values.row(i) if values else (0.,0.,0.)
                for axis in range(3):
                    for direction in (-1,1):
                        key=(target,axis,direction);candidate=(direction*delta[axis],primitive,i)
                        if key not in by_target or candidate[0]>by_target[key][0]:by_target[key]=candidate
            offset+=1
        selected.update((v[1],v[2]) for v in by_target.values())
        selected.update((v[1],v[2]) for v in by_joint.values())
        self._representatives[limit]=sorted(selected)
        return self._representatives[limit]
    def replay(self,clip,time,indices,*,morph_weights=None):
        if not math.isfinite(time):raise ValueError('Replay time must be finite')
        world=self.world(clip,time);matrices=[multiply(world[node],inverse) for node,inverse in zip(self.joints,self.inverse)];points=[]
        weights=self.default_weights
        if clip is not None:
            for channel in self.clips[clip]:
                if channel[1]=='weights':weights=self.channel_value(channel,time)
        if morph_weights is not None:weights=self.weight_vector(morph_weights)
        for sample,(primitive,index) in enumerate(indices):
            if sample%128==0:self.check_cancelled()
            p,j,w=self.primitives[primitive];position=p.row(index)
            for value,target in zip(weights,self.morph_targets[primitive]):
                if target and value:position=tuple(a+value*b for a,b in zip(position,target.row(index)))
            if self.joints:
                positions=[point(matrices[k],position) for k in j.row(index)]
                points.append(tuple(sum(weight*v[axis] for weight,v in zip(w.row(index),positions)) for axis in range(3)))
            else:points.append(point(world[self.mesh_node],position))
        if any(not math.isfinite(v) for p in points for v in p):raise ValueError('Nonfinite decoded deformation')
        return {'joints':{name:world[node] for name,node in zip(self.names,self.joints)},'points':points}
    def report(self):
        result={'joints':self.names,'vertices':self.vertex_count,'clips':[{'name':name,'start':min(c[2][0] for c in channels),'end':max(c[2][-1] for c in channels),'channels':len(channels)} for name,channels in sorted(self.clips.items())]}
        if self.morph_count:result.update(morph_targets=self.target_names,default_weights=list(self.default_weights))
        return result


def replay_digest(replay):
    def canonical(value):
        if isinstance(value,dict):return {k:canonical(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [canonical(v) for v in value]
        rounded=float(format(value,'.9g'))
        return rounded if rounded else 0.
    return hashlib.sha256(json.dumps(canonical(replay),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def check_recorded_samples(document,samples):
    for sample in samples:
        replay=document.replay(sample['clip'],sample['time'],document.representatives(sample['point_limit']),morph_weights=sample.get('morph_weights'))
        if replay_digest(replay)!=sample['replay_sha256']:raise ValueError('Decoded skin replay differs from manifest')


def inspect_file(p,*,check_cancelled=None,progress=None):
    """Read one native-profile GLB and report bounded sampled world playback."""
    from pathlib import Path
    from .lod_files import file_hash,glb_report
    path=Path(p['path']);check=check_cancelled or (lambda:None);notify=progress or (lambda _:None)
    if not path.is_file() or path.stat().st_size>512*1024**2:raise ValueError('Expected a GLB file no larger than 512 MiB')
    check();notify({'phase':'reading GLB deformation'})
    before=file_hash(path);geometry=glb_report(path,skinned=True,morphs=True);document=Document(path,morphs=True,check_cancelled=check)
    report=document.report();available=[c['name'] for c in report['clips']]
    if p.get('clip') is not None:
        if p['clip'] not in document.clips:raise ValueError('GLB clip not found')
        selected=[p['clip']]
    else:selected=available[p.get('offset',0):p.get('offset',0)+p.get('limit',4)]
    indices=document.representatives(128);samples=[]
    requests=[(None,0.)]+[(name,time) for name in selected for time in document.times(name,p.get('animation_samples',3))]
    for index,(name,time) in enumerate(requests):
        check();replay=document.replay(name,time,indices);points=replay['points']
        samples.append({'clip':name,'time':time,'vertices_sampled':len(points),
                        'sampled_world_bounds':{'min':[min(v[a] for v in points) for a in range(3)],'max':[max(v[a] for v in points) for a in range(3)]},
                        'vertex_samples':[{'primitive':ref[0],'vertex':ref[1],'world_position':list(value)} for ref,value in list(zip(indices,points))[:p.get('sample_limit',8)]],
                        'replay_sha256':replay_digest(replay)})
        notify({'phase':'sampled GLB deformation','clip':name,'time':time,'sample':index+1,'samples':len(requests)})
    check()
    if file_hash(path)!=before:raise ValueError('GLB changed during inspection; retry with a stable file')
    return {'path':str(path),'sha256':before,'geometry':geometry,'deformation':report,'samples':samples,
            'next_offset':p.get('offset',0)+len(selected) if p.get('clip') is None and p.get('offset',0)+len(selected)<len(available) else None,
            'scope':'Independent native-profile GLB decoding in glTF world coordinates (+Y up). Bounds/vertices are sampled, not exhaustive shape, shading, native correspondence or engine playback proof.'}
