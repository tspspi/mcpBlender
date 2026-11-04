"""Scene-local world lighting with guarded, reversible publication."""
from typing import Annotated,Literal
from pydantic import Field,FiniteFloat
from .config import Model
from .mesh_contracts import Digest
from .nla_contracts import SafeName

class Query(Model):
    pass
class Color(Model):
    mode: Literal['COLOR'] = 'COLOR'
    color: Annotated[list[Annotated[FiniteFloat,Field(ge=0,le=100000)]],Field(min_length=3,max_length=3)] = [.05,.05,.05]
    strength: FiniteFloat = Field(default=1,ge=0,le=10000)
class Sky(Model):
    mode: Literal['SKY'] = 'SKY'
    sky_model: Literal['AUTO','SINGLE_SCATTERING','MULTIPLE_SCATTERING','NISHITA'] = 'AUTO'
    strength: FiniteFloat = Field(default=1,ge=0,le=10000)
    sun_elevation_degrees: FiniteFloat = Field(default=35,ge=-90,le=90)
    sun_rotation_degrees: FiniteFloat = Field(default=0,ge=0,le=360)
    sun_disc: bool = True
    sun_size_degrees: FiniteFloat = Field(default=.545,ge=.001,le=90)
    sun_intensity: FiniteFloat = Field(default=1,ge=0,le=1000)
    altitude_m: FiniteFloat = Field(default=100,ge=0,le=100000)
    air_density: FiniteFloat = Field(default=1,ge=0,le=10)
    aerosol_density: FiniteFloat = Field(default=1,ge=0,le=10)
    ozone_density: FiniteFloat = Field(default=1,ge=0,le=10)
class HDRI(Model):
    mode: Literal['HDRI'] = 'HDRI'
    image_path: str = Field(min_length=1)
    strength: FiniteFloat = Field(default=1,ge=0,le=10000)
    rotation_degrees: FiniteFloat = Field(default=0,ge=-360,le=360)
    color_space: SafeName|None = None
    max_image_bytes: int = Field(default=128*1024**2,strict=True,ge=1,le=512*1024**2)
    max_image_pixels: int = Field(default=16*1024**2,strict=True,ge=1,le=32*1024**2)
class Configure(Model):
    expected_environment: Digest
    settings: Annotated[Color|Sky|HDRI,Field(discriminator='mode')]
    film_transparent: bool|None = None

COMMANDS={
 'environment_catalog':(Query,(),'Inspect installed sky model names and the static COLOR/SKY/HDRI world workflow. HDRI inputs are bounded ordinary PNG/JPEG/HDR/scanline EXR, packed privately for relocation.'),
 'inspect_environment':(Query,(),'Inspect current world graph/image dependencies, managed settings, ownership/users and a current environment guard. Includes film transparency, exposure and existing SUN lights. Animated, unsupported or dirty-image targets report refusal reasons.'),
 'configure_environment':(Configure,('allow_scene_edit',),'Stage a private scene-local COLOR, atmospheric SKY or rotated equirectangular HDRI world, then publish with a current environment guard. Preserve unmanaged/edited worlds and other scenes; retire only unchanged unused managed data. HDRI headers/bytes/pixels are bounded before decode and files are packed. Optional film_transparent is guarded; exposure and scene SUN lights remain independently controlled. Cooperative failures restore bindings/flags and remove staged IDs.'),
}
