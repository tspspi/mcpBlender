"""Read-only frozen vegetation material parameter contracts."""
from pydantic import Field,model_validator
from .config import Model
from .mesh_contracts import Name
from .nla_contracts import SafeName

class Inspect(Model):
    materials: list[Name]|None = Field(default=None,min_length=1,max_length=32)
    collection: SafeName|None = None
    lod_collection: SafeName|None = None
    @model_validator(mode='after')
    def source(self):
        if sum(v is not None for v in (self.materials,self.collection,self.lod_collection))!=1:raise ValueError('Choose materials, a botanical collection or a LOD collection')
        if self.materials and len(set(self.materials))!=len(self.materials):raise ValueError('Choose distinct materials')
        return self

COMMANDS={'inspect_vegetation_materials':(Inspect,(),'Inspect frozen Principled/managed thin-leaf source parameters, independent alpha/double-sided/backlighting semantics, procedural detail and bake requirements. Choose a tree, native LOD profile or explicit materials. Returns materials_sha256 for guarded parameter delivery; generates no images or optical equivalence claim.')}
