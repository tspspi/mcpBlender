"""Structured deform/particle controllers and shared native point-cache workflows."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .config import Model
from .physics_contracts import Name, Digest, Vec3, Frame


class Query(Model):
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=32,ge=1,le=128)


class Guard(Model):
    expected_simulation: Digest


class Editing(Guard):
    reset_unbaked: bool = False


class Cloth(Model):
    type: Literal["CLOTH"]
    quality: int = Field(default=5,strict=True,ge=1,le=20)
    mass: FiniteFloat = Field(default=.3,ge=.001,le=100)
    air_damping: FiniteFloat = Field(default=1,ge=0,le=10)
    tension_stiffness: FiniteFloat = Field(default=15,ge=0,le=10000)
    compression_stiffness: FiniteFloat = Field(default=15,ge=0,le=10000)
    shear_stiffness: FiniteFloat = Field(default=5,ge=0,le=10000)
    bending_stiffness: FiniteFloat = Field(default=.5,ge=0,le=10000)
    pins: list[Annotated[int,Field(strict=True,ge=0)]] = Field(default_factory=list,max_length=50000)
    pin_stiffness: FiniteFloat = Field(default=1,ge=0,le=50)
    use_collision: bool = True
    distance_min: FiniteFloat = Field(default=.015,ge=.001,le=1)
    collision_quality: int = Field(default=2,strict=True,ge=1,le=20)
    use_self_collision: bool = False
    self_distance_min: FiniteFloat = Field(default=.015,ge=.001,le=1)


class Soft(Model):
    type: Literal["SOFT_BODY"]
    mass: FiniteFloat = Field(default=1,ge=.001,le=100)
    pull: FiniteFloat = Field(default=.5,ge=0,le=.999)
    push: FiniteFloat = Field(default=.5,ge=0,le=.999)
    damping: FiniteFloat = Field(default=.5,ge=0,le=50)
    bend: FiniteFloat = Field(default=.1,ge=0,le=10)
    step_min: int = Field(default=5,strict=True,ge=1,le=100)
    step_max: int = Field(default=30,strict=True,ge=1,le=300)
    error_threshold: FiniteFloat = Field(default=.1,ge=.001,le=10)

    @model_validator(mode="after")
    def step_order(self):
        if self.step_min>self.step_max:raise ValueError("step_min exceeds step_max")
        return self


class ConfigureDeform(Editing):
    name: Name
    modifier: Name = "Simulation"
    settings: Annotated[Cloth|Soft,Field(discriminator="type")]
    frame_start: Frame = 1
    frame_end: Frame = 120
    expected_topology: Digest | None = None
    make_single_user: bool = False

    @model_validator(mode="after")
    def ordered(self):
        if self.frame_end<self.frame_start:raise ValueError("Invalid cache frame range")
        if isinstance(self.settings,Cloth) and self.settings.pins:
            if not self.expected_topology:raise ValueError("Pin indices require expected_topology")
            if len(set(self.settings.pins))!=len(self.settings.pins):raise ValueError("Pin indices must be unique")
        return self


class ConfigureCollision(Editing):
    name: Name
    modifier: Name = "Collision"
    thickness_outer: FiniteFloat = Field(default=.02,ge=.001,le=1)
    damping_factor: FiniteFloat = Field(default=0,ge=0,le=1)
    friction_factor: FiniteFloat = Field(default=0,ge=0,le=1)
    permeability: FiniteFloat = Field(default=0,ge=0,le=1)
    use_particle_kill: bool = False


class ConfigureParticles(Editing):
    name: Name
    modifier: Name = "Particles"
    type: Literal["EMITTER","HAIR"] = "EMITTER"
    count: int = Field(default=100,strict=True,ge=1,le=10000)
    seed: int = Field(default=0,strict=True,ge=0,le=1000000)
    frame_start: Frame = 1
    frame_end: Frame = 20
    cache_end: Frame = 120
    lifetime: FiniteFloat = Field(default=50,ge=1,le=10000)
    normal_factor: FiniteFloat = Field(default=1,ge=-100,le=100)
    factor_random: FiniteFloat = Field(default=0,ge=0,le=100)
    particle_size: FiniteFloat = Field(default=.1,ge=.001,le=100)
    size_random: FiniteFloat = Field(default=0,ge=0,le=1)
    instance_object: Name | None = None
    hair_length: FiniteFloat = Field(default=1,ge=.001,le=100)
    hair_step: int = Field(default=2,strict=True,ge=2,le=64)
    make_single_user: bool = False

    @model_validator(mode="after")
    def ordered(self):
        if not self.frame_start<=self.frame_end<=self.cache_end:raise ValueError("Emission/cache ranges must be ordered")
        if self.type=="HAIR" and self.instance_object:raise ValueError("Hair uses PATH rendering, not an instance object")
        return self


class Force(Editing):
    name: Name
    type: Literal["WIND","FORCE","VORTEX","TURBULENCE","DRAG","MAGNET","HARMONIC","CHARGE"] = "WIND"
    shape: Literal["POINT","LINE","PLANE"] | None = None
    location: Vec3 = [0,0,0]
    rotation_euler: Vec3 = [0,0,0]
    strength: FiniteFloat = Field(default=1,ge=-10000,le=10000)
    flow: FiniteFloat = Field(default=0,ge=0,le=10)
    noise: FiniteFloat = Field(default=0,ge=0,le=10)
    seed: int = Field(default=1,strict=True,ge=1,le=128)
    falloff_power: FiniteFloat = Field(default=0,ge=0,le=10)
    distance_max: FiniteFloat | None = Field(default=None,ge=.001,le=10000)


class Target(Model):
    name: Name
    modifier: Name = "Simulation"


class Controlled(Guard,Target):
    pass


class RemoveController(Editing,Target):
    make_single_user: bool = False


class RemoveField(Editing):
    name: Name


class Samples(Controlled):
    sample_frames: list[Frame] = Field(min_length=1,max_length=64)
    sample_limit: int = Field(default=16,ge=1,le=64)
    max_cache_bytes: int = Field(default=2*1024**3,ge=1,le=64*1024**3)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.sample_frames))!=len(self.sample_frames):raise ValueError("Sample frames must be unique")
        return self


class Bake(Controlled):
    path: str
    max_cache_bytes: int = Field(default=2*1024**3,ge=1,le=64*1024**3)


EDIT=("allow_scene_edit",)
COMMANDS={
    "inspect_simulations":(Query,(),"Inspect cloth/soft-body/particle controllers, colliders, force fields, source fingerprint, cache flags and source-binding status."),
    "configure_deform_simulation":(ConfigureDeform,EDIT,"Create/update a managed CLOTH or SOFT_BODY controller. Pins require topology guard; static/local shared meshes require make_single_user. Configuration affects shared caches; evaluated caches need reset_unbaked and baked caches must be cleared."),
    "configure_collision":(ConfigureCollision,EDIT,"Configure a managed static collision mesh for cloth/soft bodies and Newtonian particles."),
    "configure_particles":(ConfigureParticles,EDIT,"Create/update managed Newtonian EMITTER particles or static HAIR. Supports count/seed/emission/size and optional static object instances. Shared settings require make_single_user."),
    "configure_force_field":(Force,EDIT,"Create/update a managed Empty force-field helper with typed strength/falloff/location/Euler-radian rotation. Edits require shared cache guards."),
    "remove_simulation_controller":(RemoveController,EDIT,"Remove an owned simulation or collision modifier, preserving the mesh and unrelated vertex groups. Removing pins on shared meshes requires make_single_user."),
    "remove_force_field":(RemoveField,EDIT,"Remove an owned standalone force-field Empty after cache checks; refuses children/shared-scene helpers."),
    "sample_simulation":(Samples,EDIT,"Sequentially evaluate a named cloth/soft/particle controller and sample bounded geometry/particle data. Restores frame; yields progress/storage and supports boundary cancellation."),
    "bake_simulation":(Bake,EDIT+("allow_library_write",),"Bake a named cloth/soft/EMITTER native memory cache, bind sampled checkpoints and save an embedded full-scene .blend copy. Existing paths refused; native finalization/save are noninterruptible."),
    "validate_simulation_bake":(Controlled,(),"Check source binding and saved bounded geometry/particle checkpoints against a baked native cache; restore frame afterward."),
    "clear_simulation_cache":(Controlled,EDIT,"Free only the selected controller's live cache/binding; preserve saved snapshot files."),
}
