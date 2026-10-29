#!/usr/bin/env python3
"""Measure layout signals for visual review. Never assigns an aesthetic pass or score."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def union_area(rects):
    rects=[r for r in rects if r[2]>r[0] and r[3]>r[1]]
    xs=sorted({x for r in rects for x in (r[0],r[2])})
    total=0.0
    for x0,x1 in zip(xs,xs[1:]):
        spans=sorted((r[1],r[3]) for r in rects if r[0]<x1 and r[2]>x0)
        length=0.0;end=None
        for a,b in spans:
            if end is None or a>end:length+=b-a;end=b
            elif b>end:length+=b-end;end=b
        total+=(x1-x0)*length
    return total


def horizontal_neighbors(elements):
    images=[e for e in elements if e['type']=='image-box']
    ys=sorted({v for e in images for v in [e['y'],e['y']+e['h']]})
    pairs={}
    for y0,y1 in zip(ys,ys[1:]):
        mid=(y0+y1)/2
        row=sorted([e for e in images if e['y']<mid<e['y']+e['h']],key=lambda e:e['x'])
        for a,b in zip(row,row[1:]):
            gap=b['x']-a['x']-a['w']
            if gap>=0:
                key=(a['id'],b['id'])
                pairs.setdefault(key,{'left_id':a['id'],'right_id':b['id'],'gap_px':round(gap,3),'shared_y_bands':[]})['shared_y_bands'].append([y0,y1])
    return list(pairs.values())


def signals(layout, checks, root):
    c=layout['canvas'];W,H=float(c['width']),float(c['height'])
    if W<=0 or H<=0:raise ValueError('Positive canvas dimensions required')
    ink={t['id']:t['ink_bounds'] for t in checks['text_blocks']}
    boxes=[];images=[];sources=defaultdict(list)
    for e in layout['elements']:
        if e['type']=='image-box':
            r=[e['x'],e['y'],e['x']+e['w'],e['y']+e['h']];boxes.append(r)
            item={'id':e['id'],'frame_fraction':round(e['w']*e['h']/(W*H),5)}
            if e.get('source'):
                p=Path(e['source']);p=p if p.is_absolute() else root/p
                sources[str(p.resolve())].append(e['id'])
                from PIL import Image
                with Image.open(p) as im:sw,sh=im.size
                if e.get('source_region'):
                    _,_,rw,rh=e['source_region'];sw*=rw;sh*=rh
                factor=min(e['w']/sw,e['h']/sh)
                item['contain_rectangle_fill_fraction']=round(sw*factor*sh*factor/(e['w']*e['h']),5)
            images.append(item)
        elif e['type']=='text':
            if e['id'] not in ink:raise ValueError('Current measured ink missing: '+e['id'])
            boxes.append(ink[e['id']])
    # Full-width empty strips between ink bounding rectangles or image frames.
    spans=sorted((max(0,r[1]),min(H,r[3])) for r in boxes if r[3]>0 and r[1]<H)
    end=0.0;gaps=[]
    for a,b in spans:
        if a>end:gaps.append({'start_y':end,'end_y':a,'height_px':round(a-end,3)})
        end=max(end,b)
    if end<H:gaps.append({'start_y':end,'end_y':H,'height_px':round(H-end,3)})
    ph=c.get('physical_height_mm');pw=c.get('physical_width_mm')
    if ph:
        for g in gaps:g['height_mm']=round(g['height_px']*ph/H,3)
    quarters=[]
    for i in range(4):
        a,b=H*i/4,H*(i+1)/4
        clipped=[[max(0,r[0]),max(a,r[1]),min(W,r[2]),min(b,r[3])] for r in boxes]
        quarters.append({'quarter':i+1,'frame_and_ink_bbox_coverage':round(union_area(clipped)/(W*(b-a)),5)})
    result={'kind':'review-signals-only','aesthetic_verdict':None,
            'limitations':['Frame/ink-rectangle coverage is not perceived visual weight or aesthetic quality.',
                'Contain fill is a geometric warning signal; intentional background panels, transparency and source margins need actual-image inspection.',
                'Full-width gaps do not detect every isolated empty column. A declared alignment list cannot prove complete visual coverage.',
                'No universal occupancy threshold, hero size or pass score is applied.'],
            'image_frames':sorted(images,key=lambda e:-e['frame_fraction']),
            'quarter_coverage':quarters,'full_width_empty_strips':sorted(gaps,key=lambda g:-g['height_px']),
            'reused_sources':[{'source':s,'region_ids':ids} for s,ids in sources.items() if len(ids)>1]}
    result['horizontal_neighbor_gaps']=horizontal_neighbors(layout['elements'])
    expected=layout.get('spacing_tokens',{}).get('photo_gutter_px')
    if expected is not None:
        for item in result['horizontal_neighbor_gaps']:
            item['expected_px']=expected;item['matches_declared_token']=abs(item['gap_px']-expected)<=0.02
    if ph and pw:
        result['physical']={'width_mm':pw,'height_mm':ph,'aspect_ratio_consistent':abs(W/H-pw/ph)<1e-6,
            'font_sizes_pt':{k:round(v['font_size']*pw/W*72/25.4,2) for k,v in layout['typography'].items()}}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dir',type=Path,required=True);a=p.parse_args()
    result=signals(json.loads((a.dir/'layout.json').read_text()),json.loads((a.dir/'layout-checks.json').read_text()),a.dir)
    dest=a.dir/'composition-signals.json';dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(dest)
