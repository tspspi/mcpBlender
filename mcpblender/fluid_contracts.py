"""Typed static-source fluid authoring and isolated cache-bundle jobs."""
from pydantic import Field, FiniteFloat, model_validator
from typing import Literal
from .config import Model
from .physics_contracts import Name, Digest, Vec3, Frame


class Query(Model):
    pass


class Guard(Model):
    expected_fluid: Digest


class Target(Guard):
    name: Name
    modifier: Name = "Fluid"


class Domain(Target):
    type: Literal["LIQUID", "GAS"] = "LIQUID"
    resolution: int = Field(default=32, strict=True, ge=16, le=128)
    frame_start: Frame = 1
    frame_end: Frame = 48
    time_scale: FiniteFloat = Field(default=1, gt=0, le=4)
    gravity_weight: FiniteFloat = Field(default=1, ge=0, le=1)
    mesh_scale: int = Field(default=1, strict=True, ge=1, le=2)
    use_collision_border_bottom: bool = True
    use_collision_border_top: bool = True
    use_collision_border_front: bool = True
    use_collision_border_back: bool = True
    use_collision_border_left: bool = True
    use_collision_border_right: bool = True

    @model_validator(mode="after")
    def bounded(self):
        if self.frame_end < self.frame_start or self.frame_end-self.frame_start>499:
            raise ValueError("Fluid range must contain 1..500 ordered frames")
        return self


class Flow(Target):
    type: Literal["LIQUID", "SMOKE", "FIRE", "BOTH"] = "LIQUID"
    behavior: Literal["GEOMETRY", "INFLOW", "OUTFLOW"] = "GEOMETRY"
    density: FiniteFloat = Field(default=1, ge=0, le=10)
    temperature: FiniteFloat = Field(default=1, ge=-10, le=10)
    fuel_amount: FiniteFloat = Field(default=1, ge=0, le=10)
    surface_distance: FiniteFloat = Field(default=1.5, ge=0, le=5)
    velocity: Vec3 = [0, 0, 0]
    subframes: int = Field(default=0, strict=True, ge=0, le=16)


class Effector(Target):
    surface_distance: FiniteFloat = Field(default=0, ge=0, le=5)
    use_effector: bool = True
    subframes: int = Field(default=0, strict=True, ge=0, le=16)


class Bake(Target):
    directory: str
    threads: int = Field(default=2, strict=True, ge=1, le=16)
    max_bytes: int = Field(default=2*1024**3, strict=True, ge=1024**2, le=64*1024**3)
    timeout_seconds: int = Field(default=1800, strict=True, ge=10, le=86400)


class Cache(Model):
    directory: str


class Cleanup(Cache):
    dry_run: bool = True
    include_interrupted: bool = False


EDIT=("allow_scene_edit",)
WRITE=("allow_library_write",)
COMMANDS={
    "inspect_fluids":(Query,(),"Inspect installed fluid support, static source fingerprint, domain/flow/effector configuration and unsupported dependencies."),
    "configure_fluid_domain":(Domain,EDIT,"Create/update an owned static LIQUID/GAS domain with bounded resolution/range. Existing native caches are refused; baking uses a separate snapshot worker."),
    "configure_fluid_flow":(Flow,EDIT,"Create/update an owned static mesh liquid/smoke/fire source with geometry/inflow/outflow behavior and initial velocity."),
    "configure_fluid_effector":(Effector,EDIT,"Create/update an owned static mesh fluid collision effector."),
    "remove_fluid_controller":(Target,EDIT,"Remove an owned unbaked fluid modifier, preserving mesh data and files. Cached imported projects are protected."),
    "bake_fluid":(Bake,EDIT+WRITE,"Bake a new project/cache bundle in an isolated owned Blender worker. Reports storage/progress, supports worker cancellation/timeouts, leaves live scene unchanged and preserves partial files on failure."),
    "validate_fluid_bake":(Cache,(),"Verify a fluid bundle's manifest hashes and the currently opened baked project's source binding and sampled native geometry/grid checkpoints. Open its asset.blend first."),
    "inspect_fluid_job":(Cache,(),"Inspect a fluid bundle/job, process liveness and bounded disk usage without executing or replaying native work."),
    "recover_fluid_job":(Cache,WRITE,"Reconcile an owned abandoned fluid job only after its recorded parent and worker are gone. Adopt a complete bound manifest or mark an incomplete job interrupted, without replay."),
    "cleanup_fluid_job":(Cleanup,WRITE,"Preview or remove only an owned failed/cancelled partial fluid job. Refuses successful deliverables, symlinks, unknown entries and files referenced by the current project. Dry run defaults true."),
}
