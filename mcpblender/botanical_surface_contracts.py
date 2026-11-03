"""Bounded procedural botanical detail on shared native materials."""
from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .foliage_contracts import Material
from .mesh_contracts import Digest,Name
from .nla_contracts import SafeName
Color=Annotated[list[Annotated[FiniteFloat,Field(ge=0,le=1)]],Field(min_length=4,max_length=4)]
class Opaque(Model):
    @model_validator(mode='after')
    def opaque_colors(self):
        if any(v[3]!=1 for k,v in self.model_dump().items() if k.endswith('_color')):raise ValueError('Botanical color alpha must be one')
        return self
class Bark(Opaque):
    profile: Literal['OAK_BARK'] = 'OAK_BARK'
    uv_map: Name = 'BarkUV'
    cross_scale: FiniteFloat = Field(default=24,ge=1,le=200)
    length_scale: FiniteFloat = Field(default=2,ge=.1,le=40)
    dark_color: Color = [.035,.023,.014,1]
    light_color: Color = [.23,.16,.095,1]
    bump_distance: FiniteFloat = Field(default=.012,ge=0,le=.05)
    bump_strength: FiniteFloat = Field(default=.5,ge=0,le=1)
class Leaf(Opaque):
    profile: Literal['OAK_LEAF'] = 'OAK_LEAF'
    uv_map: Name = 'LeafUV'
    vein_pairs: int = Field(default=6,strict=True,ge=3,le=12)
    vein_slope: FiniteFloat = Field(default=1.5,ge=.1,le=5)
    vein_width: FiniteFloat = Field(default=.1,ge=.02,le=.4)
    midrib_width: FiniteFloat = Field(default=.025,ge=.005,le=.1)
    vein_color: Color = [.18,.29,.045,1]
    color_strength: FiniteFloat = Field(default=.35,ge=0,le=1)
    bump_distance: FiniteFloat = Field(default=.0004,ge=0,le=.005)
    bump_strength: FiniteFloat = Field(default=.35,ge=0,le=1)
Settings=Annotated[Bark|Leaf,Field(discriminator='profile')]
class Create(Model):
    material: SafeName
    settings: Settings
    @model_validator(mode='after')
    def bounded_name(self):
        if len(self.material.encode())>63:raise ValueError('New botanical surface names support at most 63 UTF-8 bytes')
        return self
class Configure(Create):
    expected_material: Digest
class Guard(Material):
    expected_material: Digest
COMMANDS={
 'create_botanical_surface':(Create,('allow_scene_edit',),'Create a reusable native OAK_BARK PBR or OAK_LEAF thin-surface material with editable UV-driven fissures/veins and bump. These are artistic procedural textures, not displacement, scanned biology or an atlas.'),
 'inspect_botanical_surface':(Material,(),'Inspect shared material guard and managed procedural botanical detail ownership/recipe. Report whether the owned detail graph is unchanged; no edits.'),
 'configure_botanical_surface':(Configure,('allow_scene_edit',),'Guardedly add/rebuild procedural bark or leaf detail on a shared local material, retaining material identity, original input sources and thin-leaf optics. Refuse manual edits to owned detail; rollback before final old-node deletion.'),
 'remove_botanical_surface':(Guard,('allow_scene_edit',),'Restore original material color/normal input sources and remove only unchanged owned botanical detail nodes. Retain the shared material and other shader content.'),
}
