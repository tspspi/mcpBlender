"""Independent saved-buffer readback: only masked occupancy alpha may change."""
import json,sys,resource
from array import array
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mcpblender import exr_scanline
bpy.ops.wm.open_mainfile(filepath=args[1],use_scripts=False)
names=['RawDepth','WeightedDepth']+(['WeightedBatch-FRONT'] if 'WeightedBatch-FRONT' in bpy.data.collections else [])
metas=[json.loads(bpy.data.collections[name]['mcpblender_depth_asset']) for name in names]
def buffer(meta,key):
    image=bpy.data.images[meta['images'][key]];values=array('f',[0.])*len(image.pixels);image.pixels.foreach_get(values);return values
for key in metas[0]['images']:
    a=buffer(metas[0],key);b=buffer(metas[1],key)
    if len(metas)>2:assert b==buffer(metas[2],key)
    if key!='base_coverage':assert a==b,key
alpha=exr_scanline.decode(Path(args[2])/'outputs/c00_f0000.exr',['ProjectedCoverage.Combined.A'])['channels']['ProjectedCoverage.Combined.A'];size=metas[0]['plan']['width'];changed=0;zeros=0
a=buffer(metas[0],'base_coverage');b=buffer(metas[1],'base_coverage')
for y in range(size):
    for x in range(size):
        i=4*((size-1-y)*size+x);expected=a[i+3]*alpha[y*size+x]
        assert a[i:i+3]==b[i:i+3]
        assert b[i+3]==expected,(x,y,expected,b[i+3])
        changed+=a[i+3]!=expected;zeros+=expected==0
assert changed>0
objects=[bpy.data.objects[m['object']] for m in metas]
vertices=[[(tuple(v.co)) for v in obj.data.vertices] for obj in objects];assert all(v==vertices[0] for v in vertices[1:])
faces=[[tuple(p.vertices) for p in obj.data.polygons] for obj in objects];assert all(v==faces[0] for v in faces[1:])
uvs=[]
for obj in objects:
    values=array('f',[0.])*(len(obj.data.uv_layers.active.data)*2);obj.data.uv_layers.active.data.foreach_get('uv',values);uvs.append(values)
assert all(v==uvs[0] for v in uvs[1:])
print('PROJECTED_DEPTH_READBACK_COMPLETE',{'changed_alpha_pixels':changed,'zero_alpha_pixels':zeros},flush=True)
