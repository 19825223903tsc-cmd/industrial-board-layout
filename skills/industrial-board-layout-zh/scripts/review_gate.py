#!/usr/bin/env python3
"""Bind five actual review rounds to one composition-guide version before handoff."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

FILES = ['layout.json', 'wireframe-image-input.svg', 'wireframe-image-input.png',
         'wireframe-annotated.png', 'layout-checks.json', 'generation-prompt.txt']
ROUNDS = [
    (1, 'content-composition', ['product_fit', 'hierarchy', 'source_mapping', 'product_evidence'], {'visual'}),
    (2, 'whole-board-alignment', ['coverage', 'cross_region', 'spacing_bounds'], {'visual', 'measurement'}),
    (3, 'image-placement', ['actual_bounds', 'crop_identity', 'visual_scale'], {'visual'}),
    (4, 'language-typesetting', ['language_type', 'wrapping', 'caption_association'], {'visual'}),
    (5, 'density-handoff', ['density_balance', 'prompt_mapping', 'handoff_clarity'], {'visual', 'prompt'}),
]


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root):
    paths = {name:root/name for name in FILES}
    for name,path in paths.items():
        if not path.is_file():
            raise ValueError(f'Missing required guide artifact: {name}')
    data=json.loads((root/'layout.json').read_text(encoding='utf-8'))
    from source_regions import inspect_sources
    sources=inspect_sources(data,root,strict=True)
    if sources['regions']:
        for name in ['source-map.svg','source-regions.json']:
            if not (root/name).is_file():raise ValueError(f'Missing source-region review artifact: {name}')
            paths[name]=root/name
        recorded=json.loads((root/'source-regions.json').read_text(encoding='utf-8'))
        if recorded.get('regions')!=sources['regions']:
            raise ValueError('Source-region map metadata is stale; regenerate it before review')
        if (root/'source-map.png').is_file():paths['source-map.png']=root/'source-map.png'
    for name in ['placement-preview.svg','placement-preview.png']:
        if (root/name).is_file():paths[name]=root/name
    manifest=root/'generation-inputs.json'
    if manifest.is_file():
        paths['generation-inputs.json']=manifest
        spec=json.loads(manifest.read_text())
        references=spec['references'];limit=spec['reference_limit']
        if not isinstance(limit,int) or limit<1 or len(references)>limit:
            raise ValueError('Generation reference limit exceeded or invalid')
        for ref in references:
            if not str(ref.get('role','')).strip():raise ValueError('Generation reference role missing')
            rp=Path(ref['path']);rp=rp if rp.is_absolute() else root/rp
            if not rp.is_file() or digest(rp)!=ref['sha256']:
                raise ValueError('Generation reference missing or changed; review current references')
            paths['generation-reference:'+ref['path']]=rp
    for e in data.get('elements',[]):
        if e.get('type')=='image-box' and e.get('source'):
            p=Path(e['source'])
            if not p.is_absolute(): p=root/p
            if p.is_file(): paths['source:'+e['id']+':'+str(p.resolve())]=p
    return {name:digest(path) for name,path in sorted(paths.items())}


def initialize(root):
    root=Path(root).resolve()
    (root/'handoff-ready.json').unlink(missing_ok=True)
    files=snapshot(root)
    audit=root/'qa-review.json'
    if audit.exists():
        history=root/'qa-history';history.mkdir(exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        shutil.copy2(audit,history/f'qa-review-{stamp}.json')
    report={'schema_version':1,'state':'pending','reviewed_files':files,
            'rounds':[{'number':n,'focus':focus,'status':'pending',
                       'checks':{key:{'status':'pending','note':''} for key in keys},
                       'evidence':[],'issues':[]}
                      for n,focus,keys,kinds in ROUNDS]}
    write(audit,report)
    return report


def check(root):
    root=Path(root).resolve()
    marker=root/'handoff-ready.json'
    marker.unlink(missing_ok=True)
    audit=root/'qa-review.json'
    report=json.loads(audit.read_text(encoding='utf-8'))
    report['state']='pending'
    write(audit,report)
    current=snapshot(root)
    if report.get('reviewed_files')!=current:
        raise ValueError('Guide version changed; reinitialize and review the current version in five rounds')
    rounds=report.get('rounds',[])
    if len(rounds)!=len(ROUNDS) or [r.get('number') for r in rounds]!=[r[0] for r in ROUNDS]:
        raise ValueError('Exactly five ordered review rounds are required')
    from source_regions import inspect_sources
    data=json.loads((root/'layout.json').read_text(encoding='utf-8'))
    has_regions=bool(inspect_sources(data,root,strict=True)['regions'])
    for r,(n,focus,keys,kinds) in zip(rounds,ROUNDS):
        kinds=set(kinds)
        if n==1 and has_regions:kinds.add('source-map')
        if n==3 and any(e.get('source') and e.get('evidence_status')!='unsupported-placeholder' for e in data.get('elements',[]) if e.get('type')=='image-box'):kinds.add('placement')
        if r.get('focus')!=focus or r.get('status')!='pass':
            raise ValueError(f'Round {n} is incomplete')
        for key in keys:
            item=r.get('checks',{}).get(key,{})
            if item.get('status')!='pass' or not str(item.get('note','')).strip():
                raise ValueError(f'Round {n}: unchecked item {key}')
        seen=set()
        for evidence in r.get('evidence',[]):
            kind=evidence.get('kind')
            p=Path(evidence.get('path',''))
            if not p.is_absolute():p=root/p
            if not p.is_file() or not str(evidence.get('note','')).strip():
                raise ValueError(f'Round {n}: missing evidence file or observation')
            # Evidence must point to a file bound by this review, not unrelated assets.
            if digest(p) not in current.values():
                raise ValueError(f'Round {n}: evidence is not part of the reviewed version')
            if kind=='visual' and p.suffix.lower() not in ['.png','.jpg','.jpeg','.webp']:
                raise ValueError(f'Round {n}: visual evidence must be an actual rendered image')
            if kind=='visual' and p.resolve() not in [(root/'wireframe-image-input.png').resolve(),(root/'wireframe-annotated.png').resolve()]:
                raise ValueError(f'Round {n}: visual evidence must be the current rendered guide')
            if kind=='placement' and p.resolve()!=(root/'placement-preview.png').resolve():
                raise ValueError(f'Round {n}: placement evidence must reference placement-preview.png')
            if kind=='measurement' and p.resolve()!=(root/'layout-checks.json').resolve():
                raise ValueError(f'Round {n}: measurement evidence must reference layout-checks.json')
            if kind=='prompt' and p.resolve()!=(root/'generation-prompt.txt').resolve():
                raise ValueError(f'Round {n}: prompt evidence must reference generation-prompt.txt')
            if kind=='source-map' and p.resolve() not in [(root/'source-map.svg').resolve(),(root/'source-map.png').resolve()]:
                raise ValueError(f'Round {n}: source-map evidence must reference the region marker diagram')
            seen.add(kind)
        if not kinds.issubset(seen):
            raise ValueError(f'Round {n}: required evidence missing: {sorted(kinds-seen)}')
        for issue in r.get('issues',[]):
            if issue.get('resolved') is not True or not str(issue.get('resolution','')).strip():
                raise ValueError(f'Round {n}: unresolved issue')
    # A clean report must accompany the final guide. Warnings need actual resolution.
    geometry=json.loads((root/'layout-checks.json').read_text(encoding='utf-8'))
    if geometry.get('warnings'):
        resolutions=report.get('warning_resolutions',{})
        if any(not str(resolutions.get(w,'')).strip() for w in geometry['warnings']):
            raise ValueError('Unresolved renderer warnings; fix or document reviewed design rationale')
    report['state']='ready_for_handoff'
    write(audit,report)
    write(marker,{'state':'ready_for_handoff','review_sha256':digest(audit),
                  'reviewed_files':current,'note':'Structural review gate passed; actual visual inspection must be performed by the reviewing agent.'})
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['init','check'])
    p.add_argument('--dir',type=Path,required=True)
    args=p.parse_args()
    try:
        report=initialize(args.dir) if args.action=='init' else check(args.dir)
        print(report['state'])
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as e:
        p.exit(1,str(e)+'\n')
