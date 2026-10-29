"""Content-aware wireframe renderer. Requires Pillow for font measurement and PNG."""
import json
import re
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont


def render_elements(data, out, source_dir=None):
    c = data['canvas']
    W, H = int(c['width']), int(c['height'])
    if W <= 0 or H <= 0:
        raise ValueError('Canvas dimensions must be positive')
    fontpath = c.get('font_path')
    if not fontpath:
        for candidate in ['/System/Library/Fonts/Hiragino Sans GB.ttc',
                          '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
            if Path(candidate).is_file():
                fontpath = candidate
                break
    if not fontpath or not Path(fontpath).is_file():
        raise ValueError('Set canvas.font_path to an available font supporting the text')
    styles = data.get('typography', {})
    items = []
    ids = set()
    from source_regions import inspect_sources, write_source_map
    source_report = inspect_sources(data, source_dir or out, strict=False)
    warnings = list(source_report['warnings'])
    for raw in data['elements']:
        e = dict(raw)
        ident = e['id']
        if ident in ids:
            raise ValueError(f'Duplicate ID: {ident}')
        ids.add(ident)
        kind = e['type']
        if kind not in ['text', 'image-box', 'rule']:
            raise ValueError(f'Unsupported element: {kind}')
        for key in ['x', 'y', 'w', 'h']:
            e[key] = float(e[key])
        x,y,w,h = [e[k] for k in ['x','y','w','h']]
        if min(x,y) < 0 or w <= 0 or h < 0 or (kind != 'rule' and h == 0) or x+w > W or y+h > H:
            raise ValueError(f'Outside canvas or invalid bounds: {ident}')
        if kind == 'text':
            st = dict(styles.get(e.get('style'), {}))
            st.update({k:e[k] for k in ['font_size','line_height','color','font_path'] if k in e})
            size = float(st.get('font_size', 20))
            lh = float(st.get('line_height', size*1.5))
            if size <= 0 or lh < size*1.15:
                raise ValueError(f'Invalid font size or cramped line height: {ident}')
            language = e.get('language', c.get('language', 'auto'))
            profile = data.get('language_profiles', {}).get(language, {})
            efp = st.get('font_path', profile.get('font_path', fontpath))
            if not Path(efp).is_file():
                raise ValueError(f'Font unavailable: {ident}: {efp}')
            f = ImageFont.truetype(efp, round(size))
            family = f.getname()[0]
            lines = []
            for para in e.get('text', '').split('\n'):
                # Keep Latin words intact; CJK is wrapped at characters for later visual QA.
                tokens = re.findall(r'[A-Za-z0-9]+(?:[\x27’/-][A-Za-z0-9]+)*|\s+|.', para)
                current = ''
                for token in tokens:
                    if f.getlength(token.strip()) > w:
                        raise ValueError(f'Unbreakable word wider than text box: {ident}')
                    if f.getlength(current+token) > w and current:
                        head = current.rstrip()
                        carry = ''
                        # Basic CJK boundary handling; never split a Latin word to fix punctuation.
                        closing = '，。！？；：、）》】」』〕〉”’'
                        opening = '（《【「『〔〈“‘'
                        if token and token[0] in closing:
                            if not head or not re.search(r'[\u3400-\u9fff]$', head):
                                raise ValueError(f'Adjust punctuation break manually: {ident}')
                            carry, head = head[-1], head[:-1]
                        while head and head[-1] in opening:
                            carry, head = head[-1]+carry, head[:-1]
                        if not head or f.getlength(carry+token.lstrip()) > w:
                            raise ValueError(f'Cannot fit punctuation boundary: {ident}')
                        lines.append(head)
                        current = carry+token.lstrip()
                    else:
                        current += token
                lines.append(current.rstrip())
            closing = '，。！？；：、）》】」』〕〉”’'
            opening = '（《【「『〔〈“‘'
            if any(t and (t[0] in closing or t[-1] in opening) for t in lines):
                raise ValueError(f'Invalid CJK punctuation at line boundary: {ident}')
            if len(lines)>1 and lines[-1] and not re.search(r'[\u3400-\u9fff]',lines[-1]) and len(lines[-1].split())==1:
                warnings.append(f'{ident}: last line has one word; review widow and column width')
            used = len(lines)*lh
            if used > h+0.01 or len(lines) > e.get('max_lines', len(lines)):
                raise ValueError(f'Text overflow: {ident}; needs {used:g}px height, has {h:g}px')
            e.update(lines=lines, font_size=size, line_height=lh,
                     color=st.get('color','#25282b'), baseline=y+size,
                     used_height=used, font_path=str(efp), font_family=family, language=language,
                     last_baseline=y+size+(len(lines)-1)*lh)
            boxes=[(x+f.getbbox(t,anchor='ls')[0], y+size+i*lh+f.getbbox(t,anchor='ls')[1],
                    x+f.getbbox(t,anchor='ls')[2], y+size+i*lh+f.getbbox(t,anchor='ls')[3])
                   for i,t in enumerate(lines) if t]
            e['ink_bounds'] = ([min(b[0] for b in boxes),min(b[1] for b in boxes),
                                max(b[2] for b in boxes),max(b[3] for b in boxes)] if boxes else [x,y,x,y])
            if boxes and (e['ink_bounds'][0]<x-.01 or e['ink_bounds'][1]<y-.01 or
                          e['ink_bounds'][2]>x+w+.01 or e['ink_bounds'][3]>y+h+.01):
                raise ValueError(f'Glyph extends outside text box: {ident}; allow padding or adjust placement')
        items.append(e)
    byid = {e['id']:e for e in items}
    # Intersections are errors unless a specific pair is explicitly declared intentional.
    allowed = {frozenset(pair) for pair in data.get('allowed_overlaps', [])}
    for i,a in enumerate(items):
        if a['type']=='rule': continue
        for b in items[i+1:]:
            if b['type']=='rule': continue
            if (max(a['x'],b['x']) < min(a['x']+a['w'],b['x']+b['w']) and
                max(a['y'],b['y']) < min(a['y']+a['h'],b['y']+b['h']) and
                frozenset([a['id'],b['id']]) not in allowed):
                raise ValueError(f'Unintended overlap: {a["id"]}, {b["id"]}')
    def anchor(e, axis):
        if axis=='left': return e['x']
        if axis=='right': return e['x']+e['w']
        if axis=='top': return e['y']
        if axis=='bottom': return e['y']+e['h']
        if e['type']=='text':
            if axis in ['baseline','first-baseline']: return e['baseline']
            if axis=='last-baseline': return e['last_baseline']
            if axis in ['ink-left','ink-top','ink-right','ink-bottom']:
                return e['ink_bounds'][['ink-left','ink-top','ink-right','ink-bottom'].index(axis)]
        raise ValueError(f'Unsupported alignment anchor {axis} for {e["id"]}')
    checks=[]
    if sum(e['type']=='image-box' for e in items)>1 and not data.get('alignment_bands'):
        warnings.append('Cross-region alignment bands not declared; local alignment checks do not establish whole-board alignment')
    rules=list(data.get('alignments',[]))
    for band in data.get('alignment_bands',[]):
        for field,axes in [('heading_ids',['first-baseline']),
                           ('image_ids',[band.get('image_edge','bottom')]),
                           ('caption_ids',['first-baseline','last-baseline'])]:
            members=band.get(field,[])
            if len(members)>=2:
                for axis in axes:
                    rules.append({'axis':axis,'ids':members,'tolerance':band.get('tolerance',0.5),'band':band['id']})
    for rule in rules:
        vals=[anchor(byid[i],rule['axis']) for i in rule['ids']]
        if len(vals)<2: raise ValueError('Alignment requires at least two IDs')
        delta=max(vals)-min(vals)
        if delta > float(rule.get('tolerance',0.5)):
            raise ValueError(f'Alignment mismatch: {rule["axis"]} {rule["ids"]}; delta={delta:g}')
        checks.append(dict(rule, measured_delta=delta))
    gap_checks=[]
    for rule in data.get('gap_rules',[]):
        vals=[]
        for before,after in rule['pairs']:
            a,b=byid[before],byid[after]
            value=(b['y']-(a['y']+a['h']) if rule.get('axis','vertical')=='vertical'
                   else b['x']-(a['x']+a['w']))
            vals.append(value)
        if not vals: raise ValueError('Gap rule requires pairs')
        tolerance=float(rule.get('tolerance',0.5))
        if max(vals)-min(vals)>tolerance or any(abs(v-rule.get('expected',vals[0]))>tolerance for v in vals):
            raise ValueError(f'Gap mismatch: {rule.get("id","unnamed")}: {vals}')
        gap_checks.append(dict(rule,measured_gaps=vals))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for annotated in [False,True]:
        im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
        def line(x,y,xx,yy,color='#c4c8cc'):
            svg.append(f'<path d="M{x},{y} L{xx},{yy}" fill="none" stroke="{color}"/>')
            d.line((x,y,xx,yy),fill=color,width=1)
        def rect(x,y,w,h,color='#c4c8cc'):
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{color}"/>')
            d.rectangle((x,y,x+w,y+h),outline=color)
        for e in items:
            x,y,w,h=[e[k] for k in ['x','y','w','h']]
            kind=e['type']
            if kind=='text':
                size=e['font_size'];f=ImageFont.truetype(e['font_path'],round(size));family=e['font_family']
                for i,t in enumerate(e['lines']):
                    yy=e['baseline']+i*e['line_height']
                    svg.append(f'<text x="{x}" y="{yy}" font-family="{escape(family, quote=True)},sans-serif" font-size="{size}" fill="{e["color"]}">{escape(t)}</text>')
                    d.text((x,yy),t,font=f,fill=e['color'],anchor='ls')
            elif kind=='image-box':
                rect(x,y,w,h);line(x,y,x+w,y+h,'#e0e3e5');line(x+w,y,x,y+h,'#e0e3e5')
                if e.get('source_region') is not None:
                    label=e['id'];f=ImageFont.truetype(fontpath,14)
                    svg.append(f'<text x="{x+8}" y="{y+22}" font-size="14" fill="#426c89">{escape(label)}</text>')
                    d.text((x+8,y+22),label,font=f,fill='#426c89',anchor='ls')
            else: line(x,y,x+w,y+h,e.get('color','#c4c8cc'))
            if annotated and kind!='rule':
                rect(x,y,w,h,'#779bb5')
                f=ImageFont.truetype(fontpath,12)
                label=e['id']
                svg.append(f'<text x="{x}" y="{max(12,y-4)}" font-size="12" fill="#426c89">{escape(label)}</text>')
                d.text((x,max(12,y-4)),label,font=f,fill='#426c89',anchor='ls')
        svg.append('</svg>')
        name='wireframe-annotated' if annotated else 'wireframe-image-input'
        (out/(name+'.svg')).write_text('\n'.join(svg),encoding='utf-8')
        im.save(out/(name+'.png'))
    write_source_map(source_report, out)
    (out/'layout.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'font_path':str(fontpath),'text_blocks':[{k:e[k] for k in ['id','lines','font_size','line_height','used_height','font_path','font_family','language','baseline','last_baseline','ink_bounds']} for e in items if e['type']=='text'],
            'alignment_checks':checks,'gap_checks':gap_checks,'product_evidence':source_report['product_evidence'],'source_regions':source_report['regions'],'warnings':warnings,'geometry':'bounds and unintended overlaps checked',
            'limitations':'Font glyph coverage, CJK punctuation, optical alignment and cross-software font substitution require visual verification.'}
    (out/'layout-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Rendered {len(items)} elements; measured {len(report["text_blocks"])} text blocks and {len(checks)} alignment groups: {out}')
