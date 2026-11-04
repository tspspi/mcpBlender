"""Explicit generated-chart allocation in the declared texture's pixel space."""
from pydantic import Field,FiniteFloat
from .config import Model


class ChartLayout(Model):
    min_area_pixels: FiniteFloat = Field(default=64,ge=1,le=1048576)
    min_span_pixels: FiniteFloat = Field(default=2,gt=0,le=256)
    gutter_pixels: int = Field(default=4,strict=True,ge=0,le=256)
    allow_stretch: bool = False
    max_charts: int = Field(default=4096,strict=True,ge=1,le=16384)
