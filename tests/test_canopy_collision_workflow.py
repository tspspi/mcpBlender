"""Three retained dense canopies: typed collision creation, persistence and GLB proof."""
import asyncio
import collections
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from mcpblender.lod_files import read_glb,glb_report
from mcpblender.skin_glb import Accessor,IDENTITY,trs,matrix,multiply,point


def decoded_collisions(path,state):
    doc,binary=read_glb(path);data=SimpleNamespace(doc=doc,binary=binary,allow_sparse=False,check_cancelled=lambda:None)
    planned={r['object']:r for r in state['colliders']};proof={}
    def visit(index,parent):
        node=doc['nodes'][index];local=matrix(node['matrix']) if 'matrix' in node else trs(node.get('translation',[0,0,0]),node.get('rotation',[0,0,0,1]),node.get('scale',[1,1,1]));world=multiply(parent,local)
        if 'mesh' in node:
            name=node['name'];assert name in planned and name not in proof;triangles=[]
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                assert primitive.get('mode',4)==4
                positions=Accessor(data,primitive['attributes']['POSITION']);vertices=[point(world,positions.row(i)) for i in range(positions.count)]
                indices=Accessor(data,primitive['indices']) if 'indices' in primitive else None
                order=[indices.row(i)[0] for i in range(indices.count)] if indices else list(range(len(vertices)))
                triangles.extend(tuple(vertices[order[i+j]] for j in range(3)) for i in range(0,len(order),3))
            assert len(triangles)==planned[name]['triangles']
            edges=collections.Counter(tuple(sorted((t[i],t[(i+1)%3]))) for t in triangles for i in range(3))
            assert set(edges.values())=={2},name
            origin=triangles[0][0]
            subtract=lambda a:tuple(a[i]-origin[i] for i in range(3))
            def determinant(t):
                a,b,c=map(subtract,t)
                return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
            volume=sum(determinant(t) for t in triangles)/6
            expected=planned[name]['world_volume_m3'];assert volume>0 and math.isclose(volume,expected,rel_tol=2e-5,abs_tol=1e-8),(name,volume,expected)
            coords=[(p[0],-p[2],p[1]) for t in triangles for p in t]
            proof[name]={'triangles':len(triangles),'volume_m3':volume,'branch_index':planned[name]['branch_index'],
                         'world_bounds_m':{k:[f(p[a] for p in coords) for a in range(3)] for k,f in (('min',min),('max',max))}}
            expected_bounds=state['native_bounds'][name]
            assert all(abs(proof[name]['world_bounds_m'][k][a]-expected_bounds[k][a])<=1e-5+abs(expected_bounds[k][a])*1e-7 for k in ('min','max') for a in range(3)),name
        for child in node.get('children',[]):visit(child,world)
    for index in doc['scenes'][doc.get('scene',0)]['nodes']:visit(index,IDENTITY)
    assert set(proof)==set(planned)
    return proof


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_COLLISION_CANOPY_SOURCE'),reason='Requires retained Canopy1/2/3.blend')
def test_dense_three_seed_collision_workflow(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    source=Path(os.environ['MCPBLENDER_COLLISION_CANOPY_SOURCE']);evidence=Path(os.environ['MCPBLENDER_COLLISION_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_COLLISION_EVIDENCE_DIR') else None
    for seed in (1,2,3):shutil.copy2(source.parent/f'Canopy{seed}.blend',library/f'Canopy{seed}.blend')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                op=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+600
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':op['operation_id'],'timeout_seconds':15})).data
                    if evidence:
                        evidence.mkdir(parents=True,exist_ok=True)
                        with (evidence/'operations.jsonl').open('a') as f:f.write(json.dumps({'command':command,'operation':state})+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':
                        if command=='create_botanical_collisions':
                            storage=state['progress']['storage']
                            assert storage['free_bytes']>0 and storage['estimated_output_bytes']>=4*1024**2 and storage['enough_space']
                        return state['result']
                    assert time.monotonic()<deadline
            proofs={}
            for seed in (1,2,3):
                tree=f'Canopy{seed}';name=f'Collision{seed}'
                await client.call_tool('open_blend',{'path':tree+'.blend'})
                original=await operation('inspect_botanical_tree',collection=tree);assert original['valid'] and original['foliage']['metrics']['leaves']>80000
                with pytest.raises(ToolError,match='count budget'):
                    await tool(client,'inspect_botanical_collision_source',collection=tree,max_colliders=1)
                plan=await operation('inspect_botanical_collision_source',collection=tree)
                created=await operation('create_botanical_collisions',collection=tree,collision_collection=name,expected_plan=plan['plan_sha256'],display_offset_m=[20,0,0],hide_render=False)
                assert created['valid'] and created['source_unchanged'] and created['total']<=32
                assert (await operation('inspect_botanical_tree',collection=tree))['tree_sha256']==original['tree_sha256']
                scene=(await client.call_tool('get_scene_info')).data
                for obj in scene['objects']:
                    if obj['type']=='LIGHT':
                        light=obj['name'];kind='SUN' if light.endswith('_Sun') else 'POINT' if light=='Light' else 'AREA'
                        await tool(client,'configure_light',name=light,type=kind,energy=0)
                env=await tool(client,'inspect_environment')
                await tool(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'SKY','strength':.3,'sun_rotation_degrees':180})
                pipeline=await tool(client,'inspect_render_pipeline')
                await tool(client,'configure_color_management',expected_settings=pipeline['settings_sha256'],exposure=-2)
                await tool(client,'configure_render',samples=8,resolution_x=320,resolution_y=320)
                await tool(client,'configure_camera',name='CollisionView',location=[20,-25,7.5],target=[20,0,7.5],projection='ORTHO',ortho_scale=18)
                await operation('render_still',path=name+'.png',camera='CollisionView',width=320,height=320,engine='CYCLES')
                await tool(client,'export_objects_glb',objects=[created['root'],*created['objects']],path=name+'.glb',animations=False)
                created['native_bounds']={obj:(await tool(client,'inspect_mesh',name=obj))['world_bounds'] for obj in created['objects']}
                decoded=decoded_collisions(library/(name+'.glb'),created)
                report=glb_report(library/(name+'.glb'));assert report['triangles']==plan['triangles'] and report['meshes']==plan['collider_count']
                assert (await operation('inspect_botanical_tree',collection=tree))['tree_sha256']==original['tree_sha256']
                await client.call_tool('save_blend',{'path':name+'.blend'})
                await client.call_tool('open_blend',{'path':name+'.blend'})
                restored=await operation('inspect_botanical_collisions',collision_collection=name);assert restored['valid'] and restored['source_unchanged']
                source_after_reload=await operation('inspect_botanical_tree',collection=tree)
                await operation('remove_botanical_collisions',collision_collection=name,expected_collision=restored['collision_sha256'])
                assert (await operation('inspect_botanical_tree',collection=tree))['tree_sha256']==source_after_reload['tree_sha256']
                decoded_collisions(library/(name+'.glb'),created)
                proofs[str(seed)]={'plan':plan,'created':created,'restored':restored,'decoded':decoded,'glb':report}
                (library/'collision-proof.json').write_text(json.dumps(proofs,indent=2))
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence and (root/'blender.log').exists():shutil.copy2(root/'blender.log',evidence/'blender.log')


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_COLLISION_SAVED'),reason='Requires retained Collision3.blend')
def test_saved_trunk_piece_native_rigid_contact(assets_live):
    from test_physics import physics
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(Path(os.environ['MCPBLENDER_COLLISION_SAVED'])/'Collision3.blend',library/'collision.blend')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'collision.blend'})
            source=await tool(client,'inspect_botanical_tree',collection='Canopy3')
            plan=await tool(client,'inspect_botanical_collision_source',collection='Canopy3')
            collision=await tool(client,'create_botanical_collisions',collection='Canopy3',collision_collection='PhysicsPieces',expected_plan=plan['plan_sha256'],display_offset_m=[20,0,0],parent_to_root=False)
            assert collision['valid'] and collision['parent_to_root'] is False
            name=next(p['object'] for p in collision['colliders'] if p['branch_index']==0)
            mesh=await tool(client,'inspect_mesh',name=name);bounds=mesh['world_bounds'];top=bounds['max'][2]
            center=[(a+b)/2 for a,b in zip(bounds['min'],bounds['max'])];center[2]=top+1.2
            await physics(client,'configure_rigid_world',frame_end=60)
            await physics(client,'configure_rigid_body',name=name,type='PASSIVE',collision_shape='CONVEX_HULL',collision_margin=.001,reset_unbaked=True)
            await tool(client,'create_primitive',name='ContactProbe',location=center,scale=[.05,.05,.05])
            await physics(client,'configure_rigid_body',name='ContactProbe',collision_shape='BOX',mass=.1,collision_margin=.001,reset_unbaked=True)
            sampled=await physics(client,'sample_rigid_bodies',objects=['ContactProbe'],sample_frames=[1,12,36,60])
            heights=[s['poses']['ContactProbe'][2][3] for s in sampled['samples']]
            assert heights[0]==pytest.approx(center[2]) and heights[1]<heights[0]
            assert heights[-1]==pytest.approx(top+.05,abs=.08),heights
            blocked=await tool(client,'inspect_botanical_collisions',collision_collection='PhysicsPieces')
            assert blocked['ownership_blockers']
            with pytest.raises(ToolError,match='physics|reference'):
                await tool(client,'remove_botanical_collisions',collision_collection='PhysicsPieces',expected_collision=blocked['collision_sha256'],discard_derived_edits=True)
            await physics(client,'remove_rigid_body',name='ContactProbe',reset_unbaked=True)
            await physics(client,'remove_rigid_body',name=name,reset_unbaked=True)
            current=await tool(client,'inspect_botanical_collisions',collision_collection='PhysicsPieces');assert not current['ownership_blockers']
            assert (await tool(client,'inspect_mesh',name=name))['geometry_sha256']==mesh['geometry_sha256']
            await tool(client,'remove_botanical_collisions',collision_collection='PhysicsPieces',expected_collision=current['collision_sha256'],discard_derived_edits=True)
            assert (await tool(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==source['tree_sha256']
            (library/'contact-proof.json').write_text(json.dumps({'collider':name,'bounds':bounds,'heights':heights,'samples':sampled,'blocked':blocked['ownership_blockers'],'cleanup_had_derived_edits':current['issues']},indent=2))
    try:asyncio.run(run())
    finally:
        if destination:=os.environ.get('MCPBLENDER_COLLISION_EVIDENCE_DIR'):
            shutil.copytree(library,Path(destination)/'contact',dirs_exist_ok=True)


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_COLLISION_SAVED'),reason='Requires retained collision projects and GLBs')
def test_saved_collision_glb_native_placement(tmp_path):
    library=Path(os.environ['MCPBLENDER_COLLISION_SAVED']);script=tmp_path/'bounds.py';output=tmp_path/'native-bounds.json'
    script.write_text('LIBRARY='+repr(str(library))+'\nOUTPUT='+repr(str(output))+'\n'+r'''
import bpy,json
from pathlib import Path
root=Path(LIBRARY);result={}
for seed in (1,2,3):
 bpy.ops.wm.open_mainfile(filepath=str(root/f'Collision{seed}.blend'),load_ui=False,use_scripts=False)
 bpy.context.view_layer.update();meta=json.loads(bpy.data.collections[f'Collision{seed}']['mcpblender_botanical_collisions']);rows={}
 for entry in meta['colliders']:
  obj=bpy.data.objects[entry['object']];coords=[obj.matrix_world@v.co for v in obj.data.vertices]
  rows[obj.name]={k:[fn(p[a]*bpy.context.scene.unit_settings.scale_length for p in coords) for a in range(3)] for k,fn in (('min',min),('max',max))}
 result[str(seed)]=rows
Path(OUTPUT).write_text(json.dumps(result,indent=2))
''')
    native=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert native.returncode==0,native.stdout+'\n'+native.stderr
    bounds=json.loads(output.read_text());original=json.loads((library/'collision-proof.json').read_text());proof={}
    for seed in (1,2,3):
        state=original[str(seed)]['created']|{'native_bounds':bounds[str(seed)]}
        proof[str(seed)]=decoded_collisions(library/f'Collision{seed}.glb',state)
    if destination:=os.environ.get('MCPBLENDER_COLLISION_EVIDENCE_DIR'):
        path=Path(destination);(path/'native-bounds.json').write_text(json.dumps(bounds,indent=2));(path/'placement-proof.json').write_text(json.dumps(proof,indent=2))
