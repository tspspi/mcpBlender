"""Structured compositing and real rendered pixels with Python tools disabled."""
import asyncio
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from mcpblender.blender.compositor_profile import NODE_TYPES


def link(a,x,b,y):return {'from_node':a,'from_socket':x,'to_node':b,'to_socket':y}
def spec(group='PostFX',exposure=0):
    return {'group':group,'nodes':[{'name':'Layers','type':'CompositorNodeRLayers'},
        {'name':'Exposure','type':'CompositorNodeExposure','inputs':[{'socket':'Exposure','value':exposure}]},
        {'name':'Output','type':'NodeGroupOutput'}],
        'links':[link('Layers','Image','Exposure','Image'),link('Exposure','Image','Output','Image')]}
async def inspect(client):return await tool(client,'inspect_render_pipeline')
async def render(client,path):
    op=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':path,'camera':'PostView_Camera','engine':'CYCLES','width':96,'height':96}})).data
    done=(await client.call_tool('wait_operation',{'operation_id':op['operation_id'],'timeout_seconds':60})).data
    assert done['state']=='succeeded',done
    assert (await client.call_tool('storage_status')).data['free_bytes']>0
    return done

def pixels(path):
    return subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout


def test_catalog_graph_render_passes_color_roundtrip_and_guards(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            catalog=await tool(client,'compositor_node_catalog');assert catalog['node_types']==list(NODE_TYPES)
            for node in NODE_TYPES:
                entry=await tool(client,'compositor_node_catalog',node_type=node);assert entry['type']==node
            glare=await tool(client,'compositor_node_catalog',node_type='CompositorNodeGlare')
            assert 'Fog Glow' in next(i['choices'] for i in glare['inputs'] if i['identifier']=='Type')
            await tool(client,'create_primitive',name='PostObject',kind='UV_SPHERE',location=[0,0,1])
            await tool(client,'apply_material_preset',material='PostPaint',base_color=[.08,.3,.55,1],roughness=.4)
            await tool(client,'assign_material',objects=['PostObject'],material='PostPaint')
            await tool(client,'setup_preview_stage',objects=['PostObject'],prefix='PostView')
            await tool(client,'configure_render',resolution_x=96,resolution_y=96,samples=8,engine='CYCLES')
            state=await inspect(client)
            assert 'Standard' in state['color_choices']['view_transform']
            state=await tool(client,'configure_color_management',expected_settings=state['settings_sha256'],view_transform='Standard',look='None',exposure=0,gamma=1)
            state=await tool(client,'configure_render_passes',expected_settings=state['settings_sha256'],passes={'z':True,'normal':True,'denoising_data':True})
            assert state['layers'][0]['passes']['z']
            catalog=await tool(client,'compositor_node_catalog',node_type='CompositorNodeRLayers')
            assert next(s['enabled'] for s in catalog['outputs'] if s['identifier']=='Depth')
            original=await tool(client,'configure_compositor_graph',**spec())
            state=await inspect(client)
            await tool(client,'configure_compositing',expected_settings=state['settings_sha256'],group='PostFX',expected_graph=original['graph_sha256'])
            await render(client,'post-before.png')
            original=await tool(client,'inspect_compositor_graph',group='PostFX')
            changed=await tool(client,'configure_compositor_graph',**(spec(exposure=1)|{'replace':True,'expected_graph':original['graph_sha256']}))
            assert changed['graph_sha256']!=original['graph_sha256']
            await render(client,'post-brighter.png')
            a=pixels(root/'library/post-before.png');b=pixels(root/'library/post-brighter.png')
            assert len(a)==len(b)==96*96*3
            assert sum(b)>sum(a)*1.12
            # A failed replacement never changes the bound graph.
            broken=spec(exposure=2)|{'replace':True,'expected_graph':changed['graph_sha256']}
            broken['links'][0]['from_socket']='Missing'
            with pytest.raises(ToolError):await tool(client,'configure_compositor_graph',**broken)
            assert (await tool(client,'inspect_compositor_graph',group='PostFX'))['graph_sha256']==changed['graph_sha256']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'configure_compositor_graph',**(spec()|{'replace':True,'expected_graph':original['graph_sha256']}))
            state=await inspect(client);before=copy.deepcopy(state)
            with pytest.raises(ToolError):await tool(client,'configure_color_management',expected_settings=state['settings_sha256'],exposure=2,view_transform='DefinitelyNotAnInstalledTransform')
            assert (await inspect(client))['settings_sha256']==before['settings_sha256']
            # Consume depth; disabling its pass must roll back.
            depth={'group':'DepthFX','nodes':[{'name':'Layers','type':'CompositorNodeRLayers'},{'name':'Normalize','type':'CompositorNodeNormalize'},{'name':'Output','type':'NodeGroupOutput'}],
                   'links':[link('Layers','Depth','Normalize','Value'),link('Normalize','Value','Output','Image')]}
            depth_graph=await tool(client,'configure_compositor_graph',**depth)
            state=await inspect(client)
            state=await tool(client,'configure_compositing',expected_settings=state['settings_sha256'],group='DepthFX',expected_graph=depth_graph['graph_sha256'])
            with pytest.raises(ToolError,match='disabled render pass'):
                await tool(client,'configure_render_passes',expected_settings=state['settings_sha256'],passes={'z':False})
            assert (await inspect(client))['settings_sha256']==state['settings_sha256']
            assert (await inspect(client))['layers'][0]['passes']['z']
            await render(client,'post-depth.png')
            # Denoise auxiliary passes, glare menu controls and a two-component blur.
            effects=spec('Effects')
            effects['nodes'][1]={'name':'Exposure','type':'CompositorNodeDenoise'}
            effects['nodes'].insert(2,{'name':'Glow','type':'CompositorNodeGlare','inputs':[{'socket':'Type','value':'Fog Glow'},{'socket':'Strength','value':.3}]})
            effects['nodes'].insert(3,{'name':'Blur','type':'CompositorNodeBlur','inputs':[{'socket':'Size','value':[1,1]}]})
            effects['links']=[link('Layers','Image','Exposure','Image'),link('Layers','Denoising Normal','Exposure','Normal'),link('Layers','Denoising Albedo','Exposure','Albedo'),link('Exposure','Image','Glow','Image'),link('Glow','Image','Blur','Image'),link('Blur','Image','Output','Image')]
            fx=await tool(client,'configure_compositor_graph',**effects)
            state=await inspect(client)
            await tool(client,'configure_compositing',expected_settings=state['settings_sha256'],group='Effects',expected_graph=fx['graph_sha256'])
            await render(client,'post-effects.png')
            await client.call_tool('save_blend',{'path':'composited.blend'})
            before=await inspect(client)
            await client.call_tool('open_blend',{'path':'composited.blend'})
            after=await inspect(client)
            assert after['group']=='Effects' and after['color']==before['color'] and after['layers']==before['layers']
            await render(client,'post-reopened.png')
            if destination:=os.environ.get('MCPBLENDER_COMPOSITOR_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                for name in ('composited.blend','post-before.png','post-brighter.png','post-depth.png','post-effects.png','post-reopened.png'):shutil.copy2(root/'library'/name,out/name)
                (out/'proof.json').write_text(json.dumps({'pipeline':after,'effects':fx,'pixel_sum_before':sum(a),'pixel_sum_brighter':sum(b)},indent=2))
    asyncio.run(run())
