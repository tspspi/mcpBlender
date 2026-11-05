"""Read-only bounded render/texture PNG and scene-linear EXR comparisons."""
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
    max_abs_overlap_luminance_relative_bias: FiniteFloat|None = Field(default=None,ge=0,strict=True)

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
 'Read two bounded ordinary RGB/RGBA PNG8/16 files and compare alpha silhouette/soft overlap, missing/excess coverage and premultiplied/foreground RGB error at explicit box-filtered scales. Optional reference-alpha-normalized and shared-coverage straight-colour gates prevent transparent background from hiding shading losses. An optional absolute relative shared-luminance bias gate rejects both brightening and darkening even when absolute RGB errors are small; unavailable for black-reference or absent shared coverage. Default gates are configurable; empty reference coverage cannot pass. Uses library read policy, input hashes and cooperative cancellation; no native scene edits or automatic alignment. Explicit SRGB/LINEAR interpretation, not scene-radiance or receiving-renderer certification.')}


class EXRQuality(Quality):
    max_premultiplied_rgb_rmse: FiniteFloat|None = Field(default=.1,ge=0,strict=True)
    max_overlap_rgb_rmse: FiniteFloat|None = Field(default=None,ge=0,strict=True)

class CompareEXR(Compare):
    color_space: Literal['LINEAR_REC709'] = 'LINEAR_REC709'
    reference_pass: str = Field(description='Explicit channel prefix, such as ViewLayer.Combined or TreeCapture.Combined. Empty string selects bare R/G/B/A.')
    candidate_pass: str = Field(description='Explicit candidate channel prefix; no automatic pass or view-layer selection.')
    reference_alpha_mode: Literal['PREMULTIPLIED','STRAIGHT'] = 'PREMULTIPLIED'
    candidate_alpha_mode: Literal['PREMULTIPLIED','STRAIGHT'] = 'PREMULTIPLIED'
    max_pixels: int = Field(default=1024**2,strict=True,ge=1,le=4*1024**2)
    quality: EXRQuality = Field(default_factory=EXRQuality)

    @field_validator('reference_pass','candidate_pass')
    @classmethod
    def pass_prefix(cls,value):
        from .exr_comparison import prefix
        return prefix(value)

COMMANDS['compare_exr_images']=(CompareEXR,(),
 'Read two bounded float32 RGBA NONE/ZIPS/ZIP single/multipart scanline EXRs and apply the same alpha/RGB/multiscale quality criteria as compare_png_images directly to scene-linear data. Explicit reference_pass and candidate_pass channel prefixes (empty for bare RGBA), and PREMULTIPLIED or STRAIGHT alpha interpretation; no automatic selection or second premultiplication. Preserve finite HDR and negative RGB, require alpha [0,1] and equal zero-origin full frames. Declare LINEAR_REC709; no display, OCIO or primaries conversion/inference. HDR RGB-error bounds can exceed one. Relative luminance is unavailable for nonpositive shared reference luminance and fails when its gate is enabled. max_pixels applies before decoding each input (default1M, hard4M); existing EXR file/chunk/decoded-work limits also apply. Library-contained reads, source hashes, progress/free-space reporting and cancellation; no native datablocks, scene edits, alignment or general optical certification.')
