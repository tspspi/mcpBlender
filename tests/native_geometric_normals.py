"""Native flat/smooth/rotated face-normal controls and unchanged beauty."""
import sys,json,math
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0]);out=Path(args[1])
import bpy
from mathutils import Matrix,Euler,Vector
from mcpblender import exr_scanline,geometric_normals,normal_moments,tree_capture
from mcpblender.blender import capture_material_fields as fields

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.device='CPU'
s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=48;s.render.resolution_y=48;s.render.resolution_percentage=100;s.render.film_transparent=True
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
vl=s.view_layers[0];vl.name='TreeCapture'
for flag in tree_capture.PASSES:setattr(vl,'use_pass_'+flag,True)
# Include an ordinary extra native pass to exercise the exact 32-part boundary.
vl.use_pass_emit=True
mesh=bpy.data.meshes.new('Bent');mesh.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,1)],[],[(0,1,2),(0,2,3)])
obj=bpy.data.objects.new('Bent',mesh);s.collection.objects.link(obj)
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);s.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=3
report={}


def render(label,extra=()):
    bpy.context.view_layer.update();bpy.ops.render.render(write_still=False)
    s.render.image_settings.media_type='MULTI_LAYER_IMAGE';s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='32';s.render.image_settings.exr_codec='ZIP'
    path=out/(label+'.exr');bpy.data.images['Render Result'].save_render(str(path),scene=s)
    names=['TreeCapture.Combined.'+a for a in 'RGBA']+['TreeCapture.'+p+'.'+a for p in ('Normal','Position') for a in 'XYZ']+list(extra)
    return path,exr_scanline.decode(path,names)['channels']


for mode in ('flat','smooth','rotated','bump'):
    for aov in list(vl.aovs):vl.aovs.remove(aov)
    for polygon in mesh.polygons:polygon.use_smooth=mode!='flat'
    rotation=Euler((.2,-.3,.4)).to_matrix().to_4x4() if mode=='rotated' else Matrix.Identity(4);obj.matrix_world=rotation
    mat=bpy.data.materials.new(mode);mat.use_nodes=True;nt=mat.node_tree;p=nt.nodes['Principled BSDF'];mesh.materials.clear();mesh.materials.append(mat)
    if mode=='bump':
        noise=nt.nodes.new('ShaderNodeTexNoise');bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.15
        nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    count=len(nt.nodes);legacy=fields.describe([mat]);assert 'geometric_normals' not in legacy and len(nt.nodes)==count
    reserved=nt.nodes.new('ShaderNodeOutputAOV');reserved.aov_name='MCP_GeometricNormal'
    try:fields.describe([mat],geometric_normals=True)
    except ValueError as exc:assert 'reserved' in str(exc)
    else:raise AssertionError('Reserved geometric-normal AOV accepted')
    nt.nodes.remove(reserved)
    contract=fields.describe([mat],normal_moments=True,geometric_normals=True)
    # Stale bindings must refuse before any worker node/AOV allocation.
    p.inputs['Roughness'].default_value=.4;count=len(nt.nodes)
    try:fields.install(s,contract)
    except ValueError as exc:assert 'changed' in str(exc)
    else:raise AssertionError('Stale capture bindings admitted')
    assert len(nt.nodes)==count and len(vl.aovs)==0;p.inputs['Roughness'].default_value=.5
    baseline={}
    for side in ('front','back'):
        camera.matrix_world=rotation@(Matrix.Translation((0,0,5)) if side=='front' else Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,-5),(0,0,0,1))))
        baseline[side]=render(mode+'-'+side+'-before')[1]
    original=nt.nodes['Material Output'].inputs['Surface'].links[0].from_socket;fields.install(s,contract)
    assert nt.nodes['Material Output'].inputs['Surface'].links[0].from_socket==original
    for side in ('front','back'):
        camera.matrix_world=rotation@(Matrix.Translation((0,0,5)) if side=='front' else Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,-5),(0,0,0,1))))
        names=['TreeCapture.MCP_SurfaceWeight.X',*geometric_normals.channels()]
        path,data=render(mode+'-'+side+'-after',names)
        assert all(data['TreeCapture.Combined.'+a]==baseline[side]['TreeCapture.Combined.'+a] for a in 'RGBA'),'Beauty changed'
        assert all(data['TreeCapture.Normal.'+a]==baseline[side]['TreeCapture.Normal.'+a] for a in 'XYZ'),'Shading normals changed'
        with path.open('rb') as stream:multi,parts=exr_scanline.headers(stream)
        assert multi and len(parts)==32,len(parts)
        checked=negative=0;maximum=0.
        for i,a in enumerate(data['TreeCapture.Combined.A']):
            if a<1-1e-6 or data[names[0]][i]<1-1e-6:continue
            pos=Vector([data['TreeCapture.Position.'+axis][i] for axis in 'XYZ']);local=rotation.inverted()@pos
            if abs(local.x-local.y)<.15 or max(abs(local.x),abs(local.y))>.85:continue
            index=0 if local.y<local.x else 1
            expected=rotation.to_3x3()@mesh.polygons[index].normal
            if expected.dot(camera.location-pos)<0:expected=-expected
            actual=[data[n][i]/data[names[0]][i] for n in names[1:]]
            error=max(abs(v-w) for v,w in zip(actual,expected));maximum=max(maximum,error)
            assert error<1e-5,(mode,side,index,actual,list(expected),error)
            negative+=min(actual)<-.1;checked+=1
        assert checked>50
        measured=geometric_normals.measure({'channels':data},data[names[0]],[data[n] for n in names[1:]],.01)
        assert measured['conditional_length_over_one']==0 and measured['nonfinite_pixels']==0
        if mode=='flat':assert measured['statistics']['shading_angle_degrees']['max']<.01
        else:assert measured['different_direction_pixels']>50
        if side=='back':assert negative>50
        report[mode+'-'+side]={'measure':measured,'checked_face_pixels':checked,'maximum_face_component_error':maximum,'negative_face_pixels':negative,'parts':len(parts),'beauty_exact':True,'normal_pass_exact':True}
        (out/'proof.json').write_text(json.dumps(report,indent=2));print('GEOMETRIC_NORMAL_CONTROL',mode,side,checked,maximum,flush=True)
print('GEOMETRIC_NORMALS_NATIVE_OK',flush=True)
