"""Validate and export an agent-authored, evidence-described paper figure.

This compositor preserves local SVG primitives rather than reducing a VIS/HCI
method to a node-link graph. It has no network/file URLs, scripts or arbitrary
SVG embedding. Scientific/visual adequacy must still be inspected by the agent.
The file is standalone so a frozen copy can reproduce an archived composition.
"""
from __future__ import annotations
import argparse
import copy
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

MAX_BYTES = 2_000_000
SVG = 'http://www.w3.org/2000/svg'
ROLES = {'input', 'encoding', 'transformation', 'interaction', 'comparison', 'output', 'detail'}
TAGS = {'svg','g','title','desc','rect','circle','ellipse','line','polyline','polygon','path','text','tspan'}
ATTRS = {'id','viewBox','width','height','version','x','y','x1','x2','y1','y2','cx','cy','r','rx','ry',
         'points','d','fill','stroke','stroke-width','stroke-dasharray','stroke-linecap','stroke-linejoin',
         'opacity','fill-opacity','stroke-opacity','font-family','font-size','font-weight','font-style',
         'text-anchor','dominant-baseline','dx','dy','role','aria-label'}

class PaperFigureError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise PaperFigureError(message)


def validate(raw):
    require(isinstance(raw,dict), 'Composition specification must be an object.')
    s=copy.deepcopy(raw)
    allowed={'kind','id','title','purpose','caption','alt_text','status','artwork','panels','claims','evidence','edges','width_mm','min_font_pt','dpi'}
    require(not set(s)-allowed, 'Unknown composition fields; do not pass graph attributes.')
    require(s.get('kind')=='paper-composite', 'Expected paper-composite.')
    require(re.fullmatch(r'FIG-[A-Z0-9][A-Z0-9_-]{0,40}',str(s.get('id',''))), 'Stable FIG-ID required.')
    for k in ('title','purpose','caption','alt_text','artwork'):
        require(isinstance(s.get(k),str) and 0<len(s[k].strip())<=8000, 'Missing/oversized '+k)
    require(s['artwork'].endswith('.svg'), 'Use a local editable SVG.')
    require(s.get('status') in ('illustrative','planned','implemented','mixed'), 'State whether the figure is illustrative/planned/implemented/mixed.')
    for k in ('claims','evidence'):
        s.setdefault(k,[])
        require(isinstance(s[k],list) and all(isinstance(x,str) for x in s[k]), 'Invalid '+k)
    # Scientific arrows use the original engine's explicit relation/evidence model;
    # this authoring lane deliberately does not infer those semantics from pixels.
    s.setdefault('edges',[])
    require(s['edges']==[], 'Scientific relations in composed artwork require specialist review; do not use graph edge fields here.')
    s.setdefault('width_mm',180);s.setdefault('min_font_pt',7);s.setdefault('dpi',220)
    for k,lo,hi in [('width_mm',60,350),('min_font_pt',6,24),('dpi',72,600)]:
        v=s[k];require(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and lo<=v<=hi,'Invalid '+k)
    panels=s.get('panels')
    require(isinstance(panels,list) and 2<=len(panels)<=10,'Provide 2–10 source-described panels.')
    ids=[]
    for p in panels:
        require(isinstance(p,dict) and set(p)=={'id','role','object','shows','source_status','source_note'}, 'Each panel needs id, role, object, shows, source_status and source_note.')
        require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,60}',str(p['id'])), 'Invalid SVG panel ID.')
        require(p['role'] in ROLES, 'Unknown panel role.')
        require(p['source_status'] in ('illustrative','source-bound','hypothesis'), 'Label panel origin/status.')
        for k in ('object','shows','source_note'):
            require(isinstance(p[k],str) and 0<len(p[k].strip())<=4000,'Describe panel '+k)
        if p['source_status']=='source-bound':
            require(bool(s['evidence']), 'Source-bound panels need project Evidence IDs; explanatory notes alone are insufficient.')
        ids.append(p['id'])
    require(len(ids)==len(set(ids)), 'Duplicate panel IDs.')
    return s


def validate_svg(spec, data):
    """Strict inert vector subset. No CSS, external resources or transformed text.

    Each text sets its own size; physical-size checking is exact for this subset.
    Arbitrary SVG imports need a separate reviewed conversion, never unsafe=True.
    """
    s=validate(spec)
    require(isinstance(data,bytes) and len(data)<=MAX_BYTES, 'SVG missing or larger than 2 MB.')
    text=data.decode('utf-8-sig')
    require('<!DOCTYPE' not in text.upper() and '<!ENTITY' not in text.upper() and '<?' not in text, 'DTD, entities and processing instructions are not accepted.')
    try: root=ET.fromstring(text)
    except ET.ParseError as exc: raise PaperFigureError('Malformed SVG.') from exc
    require(root.tag=='{'+SVG+'}svg', 'Use an SVG namespace root.')
    try: box=[float(v) for v in re.split(r'[ ,]+',root.attrib.get('viewBox','').strip())]
    except ValueError as exc: raise PaperFigureError('Invalid viewBox.') from exc
    require(len(box)==4 and all(math.isfinite(v) for v in box) and box[:2]==[0,0] and 10<=box[2]<=20000 and 10<=box[3]<=20000,'Bounded origin-zero viewBox required.')
    require(.15<=box[2]/box[3]<=8, 'Excessive aspect ratio; split the figure.')
    nodes=list(root.iter());require(len(nodes)<=12000,'SVG element limit exceeded.')
    ids={};sizes=[]
    for e in nodes:
        require(e.tag.startswith('{'+SVG+'}'), 'Foreign namespace rejected.')
        tag=e.tag.split('}',1)[1]
        require(tag in TAGS, 'Unsupported SVG element: '+tag)
        require(e is root or tag!='svg', 'Nested SVG viewports are not accepted.')
        require(all(k in ATTRS for k in e.attrib), 'Unsupported SVG attributes (including style, transform, href and events).')
        for k,v in e.attrib.items():
            require(not re.search(r'url\s*\(|javascript\s*:|https?\s*:|file\s*:|data\s*:',v,re.I), 'External or active SVG content rejected.')
            require(len(v)<=200000,'SVG attribute too long.')
            if k in {'fill','stroke'}: require(v in {'none','black','white','currentColor'} or re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?',v), 'Use solid colours only.')
        for k in ('x','y','x1','x2','y1','y2','cx','cy','r','rx','ry','stroke-width','dx','dy','opacity','fill-opacity','stroke-opacity'):
            if k not in e.attrib: continue
            try: value=float(e.attrib[k])
            except ValueError as exc: raise PaperFigureError('Use numeric SVG geometry: '+k) from exc
            require(math.isfinite(value) and abs(value)<=100000, 'Invalid or excessive SVG geometry: '+k)
            if k in ('r','rx','ry','stroke-width'): require(value>=0, 'Negative SVG extent: '+k)
            if 'opacity' in k: require(0<=value<=1, 'Opacity outside 0–1.')
        if e.get('id'):
            require(e.get('id') not in ids,'Duplicate SVG element ID.');ids[e.get('id')]=e
        if tag in ('text','tspan'):
            require(e.get('font-size') is not None,'Each text/tspan must set an explicit numeric font-size.')
            try: size=float(e.get('font-size'))
            except ValueError as exc: raise PaperFigureError('Font sizes are numeric viewBox units.') from exc
            points=size*s['width_mm']/box[2]*72/25.4
            require(math.isfinite(points) and points>=s['min_font_pt'], 'Text too small at final width; redesign or enlarge, never silently shrink.')
            sizes.append(points)
    require(sizes,'Figure needs readable labels.')
    for p in s['panels']:
        group=ids.get(p['id']);require(group is not None and group.tag=='{'+SVG+'}g','Missing panel group: '+p['id'])
        require(any(e.tag.split('}',1)[1] in {'path','rect','circle','ellipse','line','polyline','polygon'} for e in group.iter()),'Panel has no graphical content: '+p['id'])
    return {'panel_ids':[p['id'] for p in s['panels']], 'width_mm':s['width_mm'],
            'height_mm':s['width_mm']*box[3]/box[2], 'min_text_pt':min(sizes),
            'visual_review':'required; semantic detail, occlusion, bounds, glyphs and colour meaning are not certified',
            'scientific_review':'required; source notes and role labels are not scientific evidence'}


def render(spec,data,output,*,svg_only=False):
    s=validate(spec); report=validate_svg(s,data); dest=Path(output)
    require(not dest.exists(),'Use a new output directory.')
    root=ET.fromstring(data);root.set('width',str(report['width_mm'])+'mm');root.set('height',str(report['height_mm'])+'mm')
    ET.register_namespace('',SVG);svg=ET.tostring(root,encoding='utf-8')
    products={'diagram.svg':svg,'artwork.svg':data}
    if not svg_only:
        try: import cairosvg
        except ImportError as exc: raise PaperFigureError('PDF/PNG require the optional diagrams dependencies; ask for scoped installation.') from exc
        # A bytestring and a strict allowlist ensure Cairo sees no external resources.
        products['diagram.pdf']=cairosvg.svg2pdf(bytestring=svg)
        products['diagram.png']=cairosvg.svg2png(bytestring=svg,output_width=round(s['width_mm']/25.4*s['dpi']))
        report['cairosvg']=cairosvg.__version__
    dest.mkdir(parents=True,exist_ok=False)
    for name,b in products.items():(dest/name).write_bytes(b)
    report['warnings']=['Author-authored vector composition; inspect the exported image and every represented research detail.']
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec');p.add_argument('--output',required=True);p.add_argument('--svg-only',action='store_true');a=p.parse_args(argv)
    try:
        path=Path(a.spec).resolve();s=validate(json.loads(path.read_text(encoding='utf-8')))
        name=s['artwork'];require(name=='artwork.svg','Standalone reproduction only reads adjacent frozen artwork.svg.')
        art=path.parent/name;require(art.is_file() and not art.is_symlink(),'Missing/unsafe frozen SVG.')
        print(json.dumps(render(s,art.read_bytes(),a.output,svg_only=a.svg_only),ensure_ascii=False,indent=2));return 0
    except (PaperFigureError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
