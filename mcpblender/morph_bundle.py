"""Recorded timeline/morph proof consistency checks without Blender."""
import math


def validate_proofs(manifest,level,document):
    fps=manifest.get('fps');count=manifest.get('animation_samples');tolerance=manifest.get('skin_tolerance');clips=manifest.get('clips',[])
    if type(fps) not in (int,float) or not math.isfinite(fps) or fps<=0 or type(count)!=int or not 3<=count<=9 or type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 1e-7<=tolerance<=1:raise ValueError('Invalid morph timeline sampling metadata')
    if not isinstance(clips,list) or len(clips)>32 or len({c['name'] for c in clips})!=len(clips):raise ValueError('Invalid morph clip inventory')
    reference=manifest.get('reference_frame')
    if type(reference) not in (int,float) or not math.isfinite(reference) or abs(reference)>1048574 or (clips and reference!=clips[0]['frame_start']):raise ValueError('Invalid morph bind reference frame')
    for field,limit in (('max_morph_offset_error',tolerance),('max_weight_error',4e-4)):
        value=level[field]
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=limit:raise ValueError('Recorded morph correspondence exceeds tolerance')
    inventory={c['name']:c for c in document.report()['clips']}
    if set(inventory)!={c['name'] for c in clips}:raise ValueError('Morph bundle clip names differ from recorded timeline')
    expected=[]
    for spec in clips:
        start,end=spec['frame_start'],spec['frame_end']
        if any(type(f)!=int or abs(f)>1048574 for f in (start,end)) or not 1<=end-start<=10000:raise ValueError('Invalid morph native frame range')
        duration=(end-start)/fps;stored=inventory[spec['name']]
        if abs(stored['start'])>1e-6 or abs(stored['end']-duration)>1e-5+duration*1e-7:raise ValueError('Morph clip duration differs from timeline metadata')
        expected.extend((spec['name'],frame,(frame-start)/fps) for frame in sorted({round(start+i*(end-start)/(count-1)) for i in range(count)}))
    samples=level['playback'];default=[];units=[];animated=[];size=len(document.representatives(128))
    for sample in samples:
        if sample.get('point_limit')!=128 or sample.get('points')!=size:raise ValueError('Morph proof representative inventory differs')
        if sample['clip'] is None:
            if sample['time']!=0:raise ValueError('Default/unit morph proofs must use time zero')
            if 'morph_weights' in sample:units.append(tuple(document.weight_vector(sample['morph_weights'])))
            else:default.append(sample)
        else:animated.append(sample)
    required=[tuple(float(i==j) for i in range(document.morph_count)) for j in range(document.morph_count)]
    if len(default)!=1 or sorted(units)!=sorted(required) or len(animated)!=len(expected):raise ValueError('Missing or duplicate default, target or animation proofs')
    seen=set()
    for sample in animated:
        if type(sample.get('native_frame'))!=int:raise ValueError('Morph proof native frame must be an integer')
        key=(sample['clip'],sample.get('native_frame'));match=[t for name,frame,t in expected if (name,frame)==key]
        if key in seen or len(match)!=1 or abs(sample['time']-match[0])>1e-6+abs(match[0])*1e-7:raise ValueError('Morph proof time differs from native frame mapping')
        seen.add(key)
        for field in ('max_vertex_error','max_joint_matrix_error'):
            value=sample[field]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=tolerance:raise ValueError('Recorded morph native comparison exceeds tolerance')
    bake=level.get('timeline_bake',[])
    if len(bake)!=len(clips) or {v['clip'] for v in bake}!={c['name'] for c in clips}:raise ValueError('Missing timeline bake proofs')
    for item in bake:
        spec=next(c for c in clips if c['name']==item['clip'])
        if item['frames']!=spec['frame_end']-spec['frame_start']+1:raise ValueError('Timeline bake frame count differs')
        for field in ('native_vertex_error','native_joint_matrix_error'):
            value=item[field]
            if not math.isfinite(value) or not 0<=value<=tolerance:raise ValueError('Recorded native bake exceeds tolerance')
