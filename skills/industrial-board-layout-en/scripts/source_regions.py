#!/usr/bin/env python3
"""Validate product evidence and write an SVG source-region map without modifying photos."""
import argparse
import base64
import hashlib
import json
import math
from html import escape
from pathlib import Path
from PIL import Image

STATUSES={'provided-view','visible-crop','unsupported-placeholder'}


def inspect_sources(data, root, strict=False):
    root=Path(root);regions=[];warnings=[];evidence=[]
    for e in data.get('elements',[]):
        if e.get('type')!='image-box':continue
        ident=e['id'];status=e.get('evidence_status')
        def reject(message):
            if strict:raise ValueError(message)
            warnings.append(message)
        if status not in STATUSES:
            reject(f'{ident}: product evidence status missing or invalid')
        if not str(e.get('evidence_note','')).strip():
            reject(f'{ident}: product evidence note missing')
        source=Path(e.get('source',''))
        if not source.is_absolute():source=root/source
        if status=='unsupported-placeholder':
            if e.get('source_region') is not None:
                raise ValueError(f'{ident}: unsupported placeholder cannot claim a verified crop')
            evidence.append({'id':ident,'status':status,'note':e.get('evidence_note','')})
            continue
        if not source.is_file():
            reject(f'{ident}: provided product source unavailable')
            continue
        if e.get('fit')=='crop' and status!='visible-crop':
            reject(f'{ident}: cropped product slot must use visible-crop evidence status')
        row={'id':ident,'status':status,'source':str(source.resolve()),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'note':e.get('evidence_note','')}
        evidence.append(row)
        roi=e.get('source_region')
        if status=='visible-crop' or e.get('fit')=='crop':
            if roi is None:
                reject(f'{ident}: visible detail needs a source_region')
                continue
        if roi is None:continue
        if not isinstance(roi,list) or len(roi)!=4 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in roi):
            raise ValueError(f'{ident}: source_region must be four finite numbers')
        x,y,w,h=roi
        if x<0 or y<0 or w<=0 or h<=0 or x+w>1 or y+h>1:
            raise ValueError(f'{ident}: source_region outside source image')
        if not str(e.get('target_feature','')).strip() or not isinstance(e.get('exclude_features'),list) or not e['exclude_features']:
            raise ValueError(f'{ident}: detail requires target_feature and exclude_features')
        with Image.open(source) as im:sw,sh=im.size
        bbox=[math.floor(round(x*sw,8)),math.floor(round(y*sh,8)),math.ceil(round((x+w)*sw,8)),math.ceil(round((y+h)*sh,8))]
        if bbox[2]<=bbox[0] or bbox[3]<=bbox[1]:raise ValueError(f'{ident}: empty pixel region')
        regions.append(dict(row,source_region=roi,source_size=[sw,sh],pixel_bounds=bbox,
                            target_feature=e['target_feature'],exclude_features=e['exclude_features']))
    return {'regions':regions,'product_evidence':evidence,'warnings':warnings,
            'limitation':'Coordinates and evidence records validated; a reviewer must inspect each actual source marker to confirm the intended visible feature.'}


def write_source_map(report, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'source-regions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    groups={}
    for region in report['regions']:groups.setdefault(region['source'],[]).append(region)
    if not groups:
        (out/'source-map.svg').unlink(missing_ok=True)
        return
    height=60+sum(100+min(600,680*rows[0]['source_size'][1]/rows[0]['source_size'][0]) for rows in groups.values())
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}"><rect width="100%" height="100%" fill="white"/>',
         '<text x="30" y="30" font-family="sans-serif" font-size="18">SOURCE REGIONS / guide annotations only</text>']
    y=60
    for source,rows in groups.items():
        sw,sh=rows[0]['source_size'];scale=min(680/sw,600/sh);dw,dh=sw*scale,sh*scale
        svg.append(f'<text x="30" y="{y+18}" font-family="sans-serif" font-size="14">{escape(Path(source).name)}</text>')
        yy=y+36
        raw=base64.b64encode(Path(source).read_bytes()).decode()
        with Image.open(source) as source_image:
            mime=Image.MIME.get(source_image.format,'image/png')
        svg.append(f'<image x="30" y="{yy}" width="{dw}" height="{dh}" href="data:{mime};base64,{raw}"/>')
        for i,r in enumerate(rows):
            x0,y0,x1,y1=r['pixel_bounds'];color=['#c62a57','#126cbd','#14805d'][i%3]
            xx=30+x0*scale;ry=yy+y0*scale
            svg.append(f'<rect x="{xx}" y="{ry}" width="{(x1-x0)*scale}" height="{(y1-y0)*scale}" fill="none" stroke="{color}" stroke-width="3"/>')
            svg.append(f'<text x="{xx+4}" y="{ry+19}" fill="{color}" font-family="sans-serif" font-size="16">{escape(r["id"])}</text>')
            svg.append(f'<text x="740" y="{yy+24+i*80}" font-family="sans-serif" font-size="16">{escape(r["id"])}</text>')
            # Long feature descriptions remain in JSON to avoid clipped legend text.
        y+=100+min(600,680*sh/sw)
    svg.append('</svg>')
    (out/'source-map.svg').write_text('\n'.join(svg),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('layout',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    try:
        r=inspect_sources(json.loads(args.layout.read_text(encoding='utf-8')),args.layout.parent,strict=True)
        write_source_map(r,args.out);print(f'{len(r["regions"])} source regions validated; visual review still required')
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
