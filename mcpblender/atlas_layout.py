"""Deterministic nonrotating texture tiles and explicit RGBA memory budgets."""


def pack(entries,width=1024,height=1024,gutter=8,max_texture_bytes=256*1024**2):
    if any(type(v)!=int for v in (width,height,gutter,max_texture_bytes)) or not 32<=width<=4096 or not 32<=height<=4096 or width*height>4*1024**2 or not 0<=gutter<=64:raise ValueError('Invalid atlas dimensions/gutter/budget')
    if not 1<=len(entries)<=16 or len({e['id'] for e in entries})!=len(entries):raise ValueError('Atlas needs distinct bounded entries')
    maps=entries[0]['maps']
    if not maps or len(set(maps))!=len(maps) or any(e['maps']!=maps for e in entries):raise ValueError('Atlas entries require matching ordered map sets')
    tiles=[];x=y=row_height=0
    for e in sorted(entries,key=lambda e:(-e['height'],-e['width'],e['id'])):
        w=e['width'];h=e['height']
        if any(type(v)!=int or not 32<=v<=4096 for v in (w,h)):raise ValueError('Invalid atlas source dimensions')
        ow=w+2*gutter;oh=h+2*gutter
        if x+ow>width:x=0;y+=row_height;row_height=0
        if ow>width or y+oh>height:raise ValueError('Atlas tiles do not fit; increase dimensions or reduce input resolution/gutter')
        tiles.append({'id':e['id'],'pixel_rect':[x+gutter,y+gutter,w,h],
                      'outer_rect':[x,y,ow,oh],'uv_rect':[(x+gutter)/width,(y+gutter)/height,w/width,h/height]})
        x+=ow;row_height=max(row_height,oh)
    pixels=0;w=width;h=height;levels=0
    while True:
        pixels+=w*h;levels+=1
        if w==h==1:break
        w=max(1,w//2);h=max(1,h//2)
    memory=pixels*4*len(maps)
    if memory>max_texture_bytes:raise ValueError('Atlas RGBA8 full-mip texture memory exceeds max_texture_bytes')
    inner=sum(e['width']*e['height'] for e in entries);outer=sum(t['outer_rect'][2]*t['outer_rect'][3] for t in tiles)
    return {'method':'NONROTATING_SHELF_V1','width':width,'height':height,'gutter':gutter,'maps':maps,'tiles':sorted(tiles,key=lambda t:t['id']),
            'base_rgba8_bytes':width*height*4*len(maps),'full_mip_rgba8_bytes':memory,'mip_levels':levels,
            'source_pixel_fraction':inner/(width*height),'allocated_pixel_fraction':outer/(width*height),
            'scope':'No resizing/rotation. Edge-duplicated gutters at base resolution; no mip images or compression emitted. Full-mip RGBA8 is an estimate, not measured GPU memory or a bleed-free mip/anisotropy guarantee.'}
