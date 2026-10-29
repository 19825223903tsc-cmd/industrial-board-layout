#!/usr/bin/env python3
"""Render a board layout JSON to editable SVG and optional PNG previews."""
import argparse
import json
from pathlib import Path
from html import escape


def render(data, out, source_dir=None):
    if 'elements' in data:
        from typography_layout import render_elements
        return render_elements(data, out, source_dir)
    # Legacy image-block examples remain readable; new work uses elements.
    c, blocks = data['canvas'], data['blocks']
    W,H = c['width'],c['height']
    assert W>0 and H>0
    ids=set()
    for b in blocks:
        assert b['id'] not in ids, 'Duplicate block ID'
        ids.add(b['id'])
        assert b['w']>0 and b['h']>0 and b['x']>=0 and b['y']>=0
        assert b['x']+b['w']<=W and b['y']+b['h']<=H, 'Block outside canvas'
        assert b['cols']>0 and b['rows']>0 and 0<=b['count']<=b['cols']*b['rows']
    for i,a in enumerate(blocks):
        for b in blocks[i+1:]:
            assert not (max(a['x'],b['x'])<min(a['x']+a['w'],b['x']+b['w']) and max(a['y'],b['y'])<min(a['y']+a['h'],b['y']+b['h'])), 'Overlapping blocks'
    out.mkdir(parents=True,exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
        font_path='/System/Library/Fonts/Helvetica.ttc'
        def font(size):
            try: return ImageFont.truetype(font_path,size)
            except OSError: return ImageFont.load_default()
    except ImportError:
        Image=None
    for annotated in [False,True]:
        parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
        im=Image.new('RGB',(W,H),'white') if Image else None
        d=ImageDraw.Draw(im) if im else None
        def line(x1,y1,x2,y2,color='#d2d5d7',width=1):
            parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="{width}" fill="none"/>')
            if d:d.line((x1,y1,x2,y2),fill=color,width=width)
        def rect(x,y,w,h,color='#d2d5d7'):
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{color}"/>')
            if d:d.rectangle((x,y,x+w,y+h),outline=color,width=1)
        def text(x,y,s,size=12,color='#4b5055'):
            parts.append(f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" fill="{color}">{escape(s)}</text>')
            if d:d.text((x,y),s,font=font(size),fill=color,anchor='ls')
        def placeholder(x,y,w,h):
            rect(x,y,w,h)
            line(x,y,x+w,y+h,'#e2e4e6')
            line(x+w,y,x,y+h,'#e2e4e6')
        def copylines(x,y,w,n=4):
            for k in range(n):line(x,y+k*11,x+w*(.7 if k==n-1 else 1),y+k*11,'#c0c4c8')
        if annotated:
            text(64,32,'LAYOUT CHECK / module IDs and bounds / px',13,'#3c6c9c')
        for b in blocks:
            x,y,w,h=(b[k] for k in ['x','y','w','h'])
            if annotated:
                rect(x,y,w,h,'#7397b8')
                text(x,y-9,f"{b['id']}  [{x}, {y}, {w}, {h}]",11,'#3c6c9c')
            text(x,y+13,b['label'],12)
            if b['kind']=='sidebar':
                text(x,y+53,'PROJECT TITLE',20)
                text(x,y+77,'One-line design statement',12)
                copylines(x,y+108,w,5)
                for k in range(3):placeholder(x,y+192+k*108,w,92)
                text(x,y+550,'CMF',12)
                for k in range(5):rect(x+k*42,y+568,32,28)
                text(x,y+639,'DESIGN DESCRIPTION',12)
                copylines(x,y+665,w,7)
            elif b['kind']=='hero':
                placeholder(x,y+34,w,h-34)
                text(x+22,y+h/2,'MAIN PRODUCT IMAGE',23,'#969ca2')
            else:
                cols,rows=b['cols'],b['rows']
                gap=16
                top=28 if b['kind']=='sequence' else 34
                caption=0 if b['kind']=='sequence' else 19
                cw=(w-gap*(cols-1))/cols
                ch=(h-top-gap*(rows-1))/rows
                for k in range(b['count']):
                    xx=x+(k%cols)*(cw+gap); yy=y+top+(k//cols)*(ch+gap)
                    if b['kind']=='details':
                        placeholder(xx,yy,cw*.58,ch-4)
                        copylines(xx+cw*.64,yy+10,cw*.36,3)
                    else:
                        placeholder(xx,yy,cw,ch-caption)
                        if caption:line(xx,yy+ch-5,xx+cw*.62,yy+ch-5,'#aeb5ba')
        parts.append('</svg>')
        name='wireframe-annotated' if annotated else 'wireframe-image-input'
        (out/(name+'.svg')).write_text('\n'.join(parts),encoding='utf-8')
        if im:im.save(out/(name+'.png'))
    (out/'layout.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Rendered {len(blocks)} non-overlapping modules in {W}x{H}: {out}')
    if not Image:print('Pillow unavailable: SVG and JSON saved; PNG not generated')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('layout',type=Path)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    from language_policy import prepare_layout
    data = prepare_layout(json.loads(args.layout.read_text(encoding='utf-8')))
    render(data, args.out, args.layout.parent)
