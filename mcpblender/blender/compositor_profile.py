"""Dependency-free structured Blender 5 compositor profile."""
NODE_TYPES=('CompositorNodeRLayers','NodeGroupOutput','CompositorNodeRGB',
 'CompositorNodeExposure','CompositorNodeGlare','CompositorNodeBlur','CompositorNodeDenoise',
 'CompositorNodeColorBalance','CompositorNodeSetAlpha','CompositorNodeAlphaOver',
 'CompositorNodeInvert','CompositorNodeTransform','CompositorNodeScale','CompositorNodeEllipseMask',
 'CompositorNodeRGBToBW','CompositorNodeBrightContrast','CompositorNodeHueSat',
 'CompositorNodeFilter','CompositorNodeNormalize','CompositorNodeZcombine',
 'CompositorNodeCombineColor','CompositorNodeSeparateColor','CompositorNodeLensdist',
 'ShaderNodeMath','ShaderNodeMapRange','ShaderNodeValToRGB','ShaderNodeValue',
 'ShaderNodeCombineXYZ','ShaderNodeVectorMath','ShaderNodeMix')
PROPERTIES={'ShaderNodeMath':('operation','use_clamp'),
 'ShaderNodeVectorMath':('operation',),'ShaderNodeMapRange':('data_type','interpolation_type','clamp'),
 'ShaderNodeMix':('data_type','factor_mode','blend_type','clamp_factor','clamp_result')}
PASSES={key:'use_pass_'+key for key in ('combined','z','normal','position','vector','uv','mist',
 'object_index','material_index','emit','environment','diffuse_direct','diffuse_indirect','diffuse_color',
 'glossy_direct','glossy_indirect','glossy_color','transmission_direct','transmission_indirect','transmission_color')}
PASSES['denoising_data']='cycles.denoising_store_passes'
COLOR_KEYS=('display_device','view_transform','look','exposure','gamma','use_white_balance',
            'white_balance_temperature','white_balance_tint')
