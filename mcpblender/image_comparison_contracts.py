"""Read-only bounded render/texture PNG comparisons."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator,field_validator
from .config import Model

class Quality(Model):
    min_mask_iou: FiniteFloat|None = Field(default=.8,ge=0,le=1)
    min_soft_alpha_iou: FiniteFloat|None = Field(default=.8,ge=0,le=1)
    max_alpha_mae: FiniteFloat|None = Field(default=.05,ge=0,le=1)
    max_premultiplied_rgb_rmse: FiniteFloat|None = Field(default=.1,ge=0,le=1)
    max_reference_area_rgb_rmse: FiniteFloat|None = Field(default=None,ge=0)
    max_overlap_rgb_rmse: FiniteFloat|None = Field(default=None,ge=0,le=1)

class Compare(Model):
    reference: str = Field(min_length=1)
    candidate: str = Field(min_length=1)
    scales: list[Literal[1,2,4,8,16]] = Field(default=[1,2,4],min_length=1,max_length=5)
    alpha_threshold: FiniteFloat = Field(default=.5,gt=0,le=1)
    color_space: Literal['SRGB','LINEAR'] = 'SRGB'
    quality: Quality = Field(default_factory=Quality)
    @field_validator('scales',mode='before')
    @classmethod
    def integers(cls,value):
        if not isinstance(value,list) or any(type(s)!=int for s in value):raise ValueError('Scales must be integer powers of two')
        return value
    @model_validator(mode='after')
    def distinct(self):
        if any(isinstance(s,bool) for s in self.scales) or len(set(self.scales))!=len(self.scales) or 1 not in self.scales:raise ValueError('Scales must include 1 and be distinct powers of two')
        return self

COMMANDS={'compare_png_images':(Compare,(),
 'Read two bounded ordinary RGB/RGBA PNG8/16 files and compare alpha silhouette/soft overlap, missing/excess coverage and premultiplied/foreground RGB error at explicit box-filtered scales. Optional reference-alpha-normalized and shared-coverage straight-colour gates prevent transparent background from hiding shading losses. Default gates are configurable; empty reference coverage cannot pass. Uses library read policy, input hashes and cooperative cancellation; no native scene edits or automatic alignment. Explicit SRGB/LINEAR interpretation, not scene-radiance or receiving-renderer certification.')}
