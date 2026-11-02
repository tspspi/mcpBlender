"""Static asset LOD generation, managed selection and independent GLB bundles."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Digest
from .nla_contracts import SafeName


class Source(Model):
    name: SafeName


class Level(Model):
    triangle_budget: int = Field(ge=4,le=500000)
    method: Literal['COLLAPSE','PLANAR','UNSUBDIVIDE'] = 'COLLAPSE'
    angle_degrees: FiniteFloat = Field(default=5,ge=0,le=180)
    iterations: int = Field(default=1,ge=1,le=6)


class Generate(Source):
    chain: SafeName
    expected_source: Digest
    levels: list[Level] = Field(min_length=1,max_length=7)
    transfer_normals: bool = True
    max_relative_error: FiniteFloat = Field(default=.1,ge=0,le=1)
    error_samples: int = Field(default=512,ge=16,le=4096)
    @model_validator(mode='after')
    def recipe(self):
        if len(self.chain.encode('utf-8'))>40:raise ValueError('Chain name supports at most 40 UTF-8 bytes')
        budgets=[l.triangle_budget for l in self.levels]
        if any(a<=b for a,b in zip(budgets,budgets[1:])):raise ValueError('LOD budgets must strictly decrease')
        return self


class Chain(Model):
    chain: SafeName


class Guard(Chain):
    expected_chain: Digest


class Activate(Guard):
    level: int = Field(strict=True,ge=0,le=7)


class Export(Guard):
    directory: str = Field(min_length=1)


class Validate(Model):
    directory: str = Field(min_length=1)


COMMANDS={
 'inspect_lod_source':(Source,(),'Inspect a finite static evaluated mesh snapshot, UV/material/attribute inventory and a source fingerprint. Rig/morph/object-animation sources require a separate workflow.'),
 'generate_lod_chain':(Generate,('allow_scene_edit',),'Create independent LOD0 and reduced static snapshots in a managed named collection/root. COLLAPSE/PLANAR/UNSUBDIVIDE, decreasing budgets, UV/material/normal checks and sampled bidirectional surface error; preserves source and cleans up cancellation/failures.'),
 'inspect_lod_chain':(Chain,(),'Inspect managed LOD meshes, recipes/budgets, sampled quality, source staleness and current-content fingerprint. Invalid or modified chains are not silently exportable.'),
 'activate_lod_level':(Activate,('allow_scene_edit',),'Select one managed LOD representation by viewport/render visibility, preserving source objects and geometry. Requires a current chain fingerprint.'),
 'export_lod_chain':(Export,('allow_library_write',),'Export each static LOD into a separate GLB plus a checked manifest, independently decode counts/positions/normals/UVs, restore visibility/selection and publish a new bundle directory only after success.'),
 'validate_lod_export':(Validate,(),'Independently re-read a generated LOD bundle, verify file hashes, GLB triangle/attribute inventory and embedded buffer/image dependencies. No engine or silhouette certification.'),
}
