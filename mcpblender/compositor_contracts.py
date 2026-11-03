"""Structured compositing, pass selection and display transform controls."""
from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest
from .shader_contracts import ShaderLink,RampStop
from .blender.compositor_profile import NODE_TYPES,PASSES

Value=FiniteFloat|bool|Annotated[str,Field(max_length=255)]|Annotated[list[FiniteFloat],Field(min_length=2,max_length=4)]
class Input(Model):
    socket: int|SafeName
    value: Value
class Node(Model):
    name: SafeName
    type: Literal[NODE_TYPES]
    label: str = Field(default='',max_length=255)
    inputs: list[Input] = Field(default_factory=list,max_length=64)
    properties: dict[SafeName,FiniteFloat|bool|SafeName] = Field(default_factory=dict,max_length=8)
    view_layer: SafeName|None = None
    output_value: Value|None = None
    ramp: list[RampStop]|None = Field(default=None,min_length=2,max_length=32)
    @model_validator(mode='after')
    def options(self):
        if self.view_layer and self.type!='CompositorNodeRLayers':raise ValueError('view_layer requires a Render Layers node')
        if self.output_value is not None and self.type not in {'CompositorNodeRGB','ShaderNodeValue'}:raise ValueError('output_value requires a color/value constant')
        if self.ramp and self.type!='ShaderNodeValToRGB':raise ValueError('ramp requires a color ramp')
        if len({i.socket for i in self.inputs})!=len(self.inputs):raise ValueError('Duplicate input defaults')
        return self
class Catalog(Model):
    node_type: Literal[NODE_TYPES]|None = None
class GraphName(Model):
    group: SafeName
class Graph(GraphName):
    nodes: list[Node] = Field(min_length=1,max_length=128)
    links: list[ShaderLink] = Field(default_factory=list,max_length=256)
    replace: bool = False
    expected_graph: Digest|None = None
    allow_shared: bool = False
    @model_validator(mode='after')
    def graph(self):
        if len({n.name for n in self.nodes})!=len(self.nodes):raise ValueError('Node names must be unique')
        if sum(n.type=='NodeGroupOutput' for n in self.nodes)!=1:raise ValueError('Exactly one Image group output is required')
        if self.replace and self.expected_graph is None:raise ValueError('Replacement requires expected_graph')
        return self
class SceneQuery(Model):
    pass
class SettingsGuard(Model):
    expected_settings: Digest
class Passes(SettingsGuard):
    view_layer: SafeName|None = None
    passes: dict[Literal[tuple(PASSES)],bool] = Field(min_length=1,max_length=len(PASSES))
class Color(SettingsGuard):
    display_device: SafeName|None = None
    view_transform: SafeName|None = None
    look: SafeName|None = None
    exposure: FiniteFloat|None = Field(default=None,ge=-32,le=32)
    gamma: FiniteFloat|None = Field(default=None,ge=.01,le=5)
    use_white_balance: bool|None = None
    white_balance_temperature: FiniteFloat|None = Field(default=None,ge=1800,le=100000)
    white_balance_tint: FiniteFloat|None = Field(default=None,ge=-500,le=500)
    @model_validator(mode='after')
    def patch(self):
        if not any(getattr(self,key) is not None for key in self.model_fields_set-{'expected_settings'}):raise ValueError('Supply color management settings')
        return self
class Attach(SettingsGuard):
    group: SafeName|None = None
    expected_graph: Digest|None = None
    enabled: bool = True
    @model_validator(mode='after')
    def target(self):
        if self.group and self.expected_graph is None:raise ValueError('Attaching a group requires expected_graph')
        return self
COMMANDS={
 'compositor_node_catalog':(Catalog,(),'Discover installed allowlisted compositor nodes, socket identifiers/defaults, menu choices and properties. Blender 5 Image group output profile; no executable/file-output nodes.'),
 'inspect_compositor_graph':(GraphName,(),'Inspect a compositor graph, full-content guard for supported bounded graphs, native users, Render Layers bindings and unavailable pass links. Imported/animated graphs remain read-only.'),
 'configure_compositor_graph':(Graph,('allow_scene_edit',),'Stage and validate a complete Blender 5 compositor graph before publication. Replace managed local graphs with a current guard; multiple scene users require allow_shared. Originals and bindings restore on cooperative failure before final deletion.'),
 'inspect_render_pipeline':(SceneQuery,(),'Inspect current scene compositing binding, render-pass flags and color management with a settings fingerprint. Includes installed display/view/look choices; does not fingerprint scene geometry.'),
 'configure_render_passes':(Passes,('allow_scene_edit',),'Guardedly patch allowlisted view-layer render passes and denoising data, update Render Layers sockets and restore on validation/cancellation failure. Reject disabling passes consumed by attached graphs.'),
 'configure_color_management':(Color,('allow_scene_edit',),'Guardedly configure installed display/view/look, exposure/gamma and white balance with staged native validation. Refuse targeted keyed/driven settings; restore on cooperative failure.'),
 'configure_compositing':(Attach,('allow_scene_edit',),'Guardedly bind a validated managed compositor group to the current scene and enable/disable compositing. Group=None retains the current binding. No file-output nodes or arbitrary RNA paths.'),
}
