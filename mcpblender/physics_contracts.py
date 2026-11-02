"""Typed rigid-body simulation and verified embedded-cache delivery."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .config import Model

Name = Annotated[str, Field(min_length=1, max_length=63)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Frame = Annotated[int, Field(strict=True, ge=1, le=10000)]
Vec3 = Annotated[list[FiniteFloat], Field(min_length=3, max_length=3)]


class PhysicsQuery(Model):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=32, ge=1, le=128)


class Guard(Model):
    expected_physics: Digest


class World(Guard):
    frame_start: Frame = 1
    frame_end: Frame = 120
    fps: int = Field(default=24, ge=1, le=240)
    gravity: Vec3 = [0, 0, -9.81]
    substeps_per_frame: int = Field(default=10, ge=1, le=1000)
    solver_iterations: int = Field(default=10, ge=1, le=1000)
    time_scale: FiniteFloat = Field(default=1, gt=0, le=10)
    reset_unbaked: bool = False

    @model_validator(mode="after")
    def ordered_frames(self):
        if self.frame_end < self.frame_start:
            raise ValueError("frame_end must not precede frame_start")
        return self


class Body(Guard):
    name: Name
    type: Literal["ACTIVE", "PASSIVE"] = "ACTIVE"
    collision_shape: Literal["BOX", "SPHERE", "CAPSULE", "CYLINDER", "CONE", "CONVEX_HULL", "MESH"] = "CONVEX_HULL"
    mass: FiniteFloat = Field(default=1, gt=0, le=1_000_000)
    friction: FiniteFloat = Field(default=.5, ge=0, le=100)
    restitution: FiniteFloat = Field(default=0, ge=0, le=1)
    linear_damping: FiniteFloat = Field(default=.04, ge=0, le=1)
    angular_damping: FiniteFloat = Field(default=.1, ge=0, le=1)
    use_margin: bool = True
    collision_margin: FiniteFloat = Field(default=.02, ge=0, le=1)
    reset_unbaked: bool = False

    @model_validator(mode="after")
    def static_concave(self):
        if self.type == "ACTIVE" and self.collision_shape == "MESH":
            raise ValueError("Use a passive MESH collider or an active convex collision shape")
        return self


class RemoveBody(Guard):
    name: Name
    reset_unbaked: bool = False


class Samples(Guard):
    objects: list[Name] = Field(min_length=1, max_length=64)
    sample_frames: list[Frame] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_targets(self):
        if len(set(self.objects)) != len(self.objects) or len(set(self.sample_frames)) != len(self.sample_frames):
            raise ValueError("Objects and sample frames must be unique")
        return self


class Bake(Guard):
    path: str


EDIT = ("allow_scene_edit",)
COMMANDS = {
    "inspect_physics": (PhysicsQuery, (), "Inspect rigid-body world, paginated bodies, native cache flags, source fingerprint and bake binding. Unsupported sources are reported explicitly."),
    "configure_rigid_world": (World, EDIT, "Configure gravity, FPS, solver and cache frame range, guarded by expected_physics. Existing evaluated unbaked caches require reset_unbaked=true; baked caches must be cleared explicitly."),
    "configure_rigid_body": (Body, EDIT, "Configure active/passive static local mesh colliders and physical parameters. Source meshes must be unparented, unconstrained, unanimated and have no modifiers/shape keys. Requires a configured world."),
    "remove_rigid_body": (RemoveBody, EDIT, "Remove a rigid-body binding with physics fingerprint/cache guards, preserving the object and its mesh."),
    "sample_rigid_bodies": (Samples, EDIT, "Step the world sequentially from its cache start and sample evaluated body poses at selected frames. Restores the original frame, retains unbaked memory cache, yields progress/storage and supports boundary cancellation."),
    "bake_rigid_bodies": (Bake, EDIT + ("allow_library_write",), "Step and bake the full rigid-body cache, bind it to the source fingerprint and save an embedded-cache .blend copy. Refuses existing output. Reports progress/storage; native finalization/save cannot be interrupted midway."),
    "validate_rigid_bake": (Guard, (), "Verify baked source binding and saved pose checkpoints against the live embedded cache. Restores the original frame; native outdated flags are reported separately."),
    "clear_rigid_bake": (Guard, EDIT, "Explicitly free the live rigid cache and remove its binding; saved snapshot files remain protected and unchanged."),
}
