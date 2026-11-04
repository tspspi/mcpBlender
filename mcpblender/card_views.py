"""Stable directional names/frames shared by fitting, selection and delivery."""
import math
from typing import Literal

View=Literal['TOP','FRONT','SIDE','BACK','LEFT','BOTTOM','FRONT_RIGHT','BACK_RIGHT','BACK_LEFT','FRONT_LEFT']
LEGACY=('TOP','FRONT','SIDE')
S=math.sqrt(.5)
# Preserve original view indices and tie order; append the wider catalog.
DIRECTIONS={'TOP':(0.,0.,1.),'FRONT':(0.,-1.,0.),'SIDE':(1.,0.,0.),
            'BACK':(0.,1.,0.),'LEFT':(-1.,0.,0.),'BOTTOM':(0.,0.,-1.),
            'FRONT_RIGHT':(S,-S,0.),'BACK_RIGHT':(S,S,0.),'BACK_LEFT':(-S,S,0.),'FRONT_LEFT':(-S,-S,0.)}
# U cross V = N; vertical horizon planes keep V = +Z.
FRAMES={'TOP':((1.,0.,0.),(0.,1.,0.)), 'FRONT':((1.,0.,0.),(0.,0.,1.)),
        'SIDE':((0.,1.,0.),(0.,0.,1.)), 'BACK':((-1.,0.,0.),(0.,0.,1.)),
        'LEFT':((0.,-1.,0.),(0.,0.,1.)), 'BOTTOM':((-1.,0.,0.),(0.,1.,0.)),
        'FRONT_RIGHT':((S,S,0.),(0.,0.,1.)), 'BACK_RIGHT':((-S,S,0.),(0.,0.,1.)),
        'BACK_LEFT':((-S,-S,0.),(0.,0.,1.)), 'FRONT_LEFT':((S,-S,0.),(0.,0.,1.))}
CAMERA_VIEWS={'TOP':'TOP','FRONT':'FRONT','SIDE':'RIGHT','BACK':'BACK','LEFT':'LEFT','BOTTOM':'BOTTOM'}
