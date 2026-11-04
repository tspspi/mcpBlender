"""Bounded, observational tangent-normal statistics; never modifies normal maps."""
import hashlib
import math
from .image_comparison import decode_png


def inspect(normal,coverage,*,cancelled=lambda:None,progress=lambda v:None):
    width,height,pixels=decode_png(normal,color_space='LINEAR',premultiply=False,cancelled=cancelled,progress=progress)
    cw,ch,mask=decode_png(coverage,color_space='LINEAR',premultiply=False,cancelled=cancelled,progress=progress)
    if (width,height)!=(cw,ch):raise ValueError('Normal and coverage PNG dimensions differ')
    covered=valid=backward=grazing=invalid=0;sum_z=sum_abs_z=sum_length_error=0.
    # Two PNG8 code steps absorb quantisation around tangent Z=0. Apply the
    # same conservative dead band to PNG16 for a stable diagnostic definition.
    dead_band=2/255
    for i in range(width*height):
        if i%16384==0:
            cancelled();progress({'phase':'measuring covered tangent normals','completed':i,'total':width*height})
        j=4*i
        # Coverage is the scalar RED signal. Its file alpha may be entirely one.
        if mask[j]<=.5:continue
        covered+=1
        vector=[2*pixels[j+c]-1 for c in range(3)];length=math.sqrt(sum(v*v for v in vector))
        if length<=dead_band:invalid+=1;continue
        valid+=1;z=vector[2]/length;sum_z+=z;sum_abs_z+=abs(z);sum_length_error+=abs(length-1)
        backward+=z < -dead_band;grazing+=abs(z)<.25
    cancelled()
    return {'method':'COVERED_TANGENT_NORMAL_DIRECTIONS_V1','width':width,'height':height,
            'normal_sha256':hashlib.sha256(normal).hexdigest(),'coverage_sha256':hashlib.sha256(coverage).hexdigest(),
            'coverage_threshold':.5,'coverage_comparison':'RED_GREATER_THAN','backward_z_threshold':-dead_band,
            'grazing_abs_z_threshold':.25,'covered_pixels':covered,'valid_direction_pixels':valid,
            'invalid_direction_pixels':invalid,'backward_pixels':backward,'grazing_pixels':grazing,
            'backward_fraction':backward/valid if valid else None,'grazing_fraction':grazing/valid if valid else None,
            'mean_tangent_z':sum_z/valid if valid else None,'mean_abs_tangent_z':sum_abs_z/valid if valid else None,
            'mean_unit_length_error':sum_length_error/valid if valid else None,
            'scope':'Raw unpremultiplied linear RGB decoded to [-1,1], normalized for direction; coverage red > 0.5. Backward and grazing sets may overlap. No automatic normal correction or optical pass/fail. Flat geometry can shade differently from the represented geometry even with facing-corrected normals.'}
