"""Bounded, offline scientific diagrams with editable sources.

Only validated fields become DOT attributes. Requires Graphviz dot; CairoSVG is
optional for PDF/PNG. This file is copied into each provenance bundle and can
run independently: python reproduce.py spec.json --output NEW_DIRECTORY.
"""
from __future__ import annotations
import argparse
import copy
import html
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET

VERSION = '1.0'
KINDS = ('pipeline', 'architecture', 'experiment', 'mechanism', 'graphical-abstract', 'conceptual', 'response')
RELATIONS = ('flow', 'data', 'association', 'causal', 'inhibition', 'feedback')
PALETTES = {
    'paper': ('#193547', '#58717D', '#CEDBE0', '#F4F8FA', '#286487', '#EAF3F8', '#386E64', '#EDF5F1'),
    'editorial': ('#243E45', '#637980', '#D4E1DF', '#F5F9F8', '#207B80', '#E6F4F2', '#986638', '#F9F0E3'),
    'mono': ('#202020', '#626262', '#C8C8C8', '#F5F5F5', '#383838', '#EEEEEE', '#525252', '#E7E7E7'),
}
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)

class DiagramError(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise DiagramError(message)

def text(value, name, limit=160, required=False):
    need(isinstance(value, str) and len(value) <= limit, 'Invalid/long ' + name)
    need(not any(ord(c) < 32 and c not in '\n\t' for c in value), 'Control characters in ' + name)
    need(not required or bool(value.strip()), name + ' is required')
    return value

def numeric(value, name, low, high):
    need(isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high, 'Invalid ' + name)
    return float(value)

def identifier(value):
    need(isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}', value), 'Invalid node/group ID')
    return value

def ids(value, name):
    need(isinstance(value, list) and len(value) <= 100 and all(isinstance(x, str) and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,63}', x) for x in value), 'Invalid ' + name)
    need(len(value) == len(set(value)), 'Duplicate ' + name)
    return value

def validate(raw):
    need(isinstance(raw, dict), 'Diagram specification must be an object')
    s = copy.deepcopy(raw)
    allowed = {'id','kind','title','subtitle','purpose','caption','alt_text','status','style','direction','width_mm','height_mm','font_family','font_size','dpi','nodes','edges','groups','ranks','claims','evidence'}
    need(not set(s)-allowed, 'Unknown diagram fields: '+str(sorted(set(s)-allowed)))
    need(isinstance(s.get('id'), str) and re.fullmatch(r'FIG-[A-Z0-9][A-Z0-9_-]{0,40}', s['id']), 'Use FIG-... as diagram ID')
    need(s.get('kind') in KINDS, 'Unknown diagram kind')
    for name in ('title','purpose','caption','alt_text'):
        text(s.get(name), name, 100 if name=='title' else 4000, required=True)
    text(s.setdefault('subtitle',''), 'subtitle', 150)
    need(s.get('status') in ('planned','implemented','mixed','illustrative'), 'Explicit planned/implemented/mixed/illustrative status required')
    need(s.setdefault('style','editorial') in PALETTES, 'Unknown style (paper/editorial/mono)')
    need(s.setdefault('direction','LR') in ('LR','TB'), 'Direction must be LR or TB')
    numeric(s.setdefault('width_mm',180), 'width_mm', 70, 300)
    if 'height_mm' in s: numeric(s['height_mm'], 'height_mm', 40, 400)
    numeric(s.setdefault('font_size',12), 'font_size', 10, 18)
    numeric(s.setdefault('dpi',300), 'dpi', 96, 600)
    need(re.fullmatch(r'[A-Za-z0-9 _-]{1,60}', s.setdefault('font_family','DejaVu Sans')), 'Use an installed font family name')
    ids(s.setdefault('claims',[]), 'claims'); ids(s.setdefault('evidence',[]), 'evidence')
    nodes = s.get('nodes'); edges = s.get('edges')
    need(isinstance(nodes,list) and 2 <= len(nodes) <= 40, 'Use 2–40 nodes; split larger diagrams')
    need(isinstance(edges,list) and 1 <= len(edges) <= 80, 'Use 1–80 edges')
    groups = s.setdefault('groups',[])
    need(isinstance(groups,list) and len(groups)<=8, 'At most 8 groups')
    group_ids=[]
    for g in groups:
        need(isinstance(g,dict) and not set(g)-{'id','label'}, 'Invalid group')
        group_ids.append(identifier(g.get('id'))); text(g.get('label'),'group label',60,True)
    need(len(group_ids)==len(set(group_ids)), 'Duplicate group')
    names=[]
    for n in nodes:
        need(isinstance(n,dict) and not set(n)-{'id','label','detail','role','group'}, 'Invalid node fields')
        names.append(identifier(n.get('id'))); text(n.get('label'),'node label',90,True)
        text(n.setdefault('detail',''),'detail',150)
        need(n.setdefault('role','process') in ('input','process','decision','output','control','note'), 'Unknown node role')
        need(not n.get('group') or n['group'] in group_ids, 'Unknown node group')
    need(len(names)==len(set(names)) and not set(names)&set(group_ids), 'Duplicate node/group ID')
    for g in group_ids: need(any(n.get('group')==g for n in nodes), 'Empty group')
    for e in edges:
        need(isinstance(e,dict) and not set(e)-{'source','target','label','relation','certainty','evidence'}, 'Invalid edge fields')
        need(e.get('source') in names and e.get('target') in names, 'Edge refers to missing node')
        text(e.setdefault('label',''),'edge label',60)
        need(e.setdefault('relation','flow') in RELATIONS, 'Unknown edge relation')
        need(e.setdefault('certainty','schematic') in ('schematic','hypothesis','reported'), 'Explicit edge certainty required')
        ids(e.setdefault('evidence',[]), 'edge evidence')
        if e['relation'] in ('causal','inhibition'):
            need(e['certainty'] in ('hypothesis','reported'), 'Causal/inhibitory arrows must be hypothetical or source-bound reported relationships')
        if e['certainty']=='reported': need(e['evidence'], 'Reported relationships require evidence IDs')
        if e['source']==e['target']: need(e['relation']=='feedback', 'Self edges must be explicit feedback')
    ranks=s.setdefault('ranks',[])
    need(isinstance(ranks,list) and len(ranks)<=20, 'Invalid ranks')
    rank_names=[]
    for r in ranks:
        need(isinstance(r,list) and len(r)>=2 and all(x in names for x in r), 'Each same-rank group needs known nodes')
        rank_names.extend(r)
    need(len(rank_names)==len(set(rank_names)), 'A node belongs to multiple rank constraints')
    return s

def wrap(value, width=23):
    # Count wide CJK glyphs as two units; preserve all label text, never truncate.
    lines=[]
    for paragraph in value.split('\n'):
        line=''; count=0
        tokens=re.findall(r'\S+\s*',paragraph) if all(ord(c)<128 for c in paragraph) else list(paragraph)
        for token in tokens:
            size=sum(2 if unicodedata.east_asian_width(c) in ('W','F') else 1 for c in token)
            if line and count+size>width: lines.append(line.rstrip());line='';count=0
            line+=token;count+=size
        lines.append(line.rstrip())
    return lines

def q(value): return json.dumps(str(value),ensure_ascii=False)
def label_html(value,width=23): return '<BR ALIGN="LEFT"/>'.join(html.escape(x,quote=True) for x in wrap(value,width))+'<BR ALIGN="LEFT"/>'

def dot_source(s):
    ink,muted,border,panel,accent,fill,second,fill2=PALETTES[s['style']]
    fs=s['font_size']
    lines=['digraph research {', 'graph [rankdir='+s['direction']+', bgcolor="transparent", pad="0.18", nodesep="0.32", ranksep="0.52", splines=spline, outputorder=edgesfirst, compound=true, newrank=true, fontname='+q(s['font_family'])+'];',
           'node [shape=box, style="rounded,filled", color='+q(border)+', fillcolor="white", penwidth=1.1, margin="0.17,0.13", fontname='+q(s['font_family'])+'];',
           'edge [color='+q(muted)+', penwidth=1.3, arrowsize=0.7, fontname='+q(s['font_family'])+', fontsize='+str(fs-1)+', fontcolor='+q(muted)+'];']
    def node(n):
        color=second if n['role'] in ('control','output') else accent
        bg=fill2 if n['role'] in ('control','output') else fill
        if n['role']=='decision':
            return q(n['id'])+' [id='+q('node-'+n['id'])+', shape=diamond, fillcolor='+q(bg)+', color='+q(color)+', fontsize='+str(fs)+', label='+q('\n'.join(wrap(n['label'],17)))+'];'
        label='<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR><TD ALIGN="LEFT"><FONT POINT-SIZE="'+str(fs-2)+'" COLOR="'+color+'"><B>'+n['role'].upper()+'</B></FONT></TD></TR>'
        label+='<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="'+str(fs)+'" COLOR="'+ink+'"><B>'+label_html(n['label'])+'</B></FONT></TD></TR>'
        if n['detail']: label+='<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="'+str(fs-1)+'" COLOR="'+muted+'">'+label_html(n['detail'],27)+'</FONT></TD></TR>'
        label+='</TABLE>'
        return q(n['id'])+' [id='+q('node-'+n['id'])+', fillcolor='+q(bg)+', label=<'+label+'>];'
    for g in s['groups']:
        lines+=['subgraph '+q('cluster_'+g['id'])+' {', 'graph [label='+q(g['label'])+', labeljust=l, labelloc=t, fontsize='+str(fs)+', fontcolor='+q(ink)+', color='+q(border)+', style="rounded,filled", fillcolor='+q(panel)+', margin=18];']
        lines.extend(node(n) for n in s['nodes'] if n.get('group')==g['id']);lines.append('}')
    lines.extend(node(n) for n in s['nodes'] if not n.get('group'))
    for r in s['ranks']: lines.append('{rank=same; '+'; '.join(map(q,r))+';}')
    for i,e in enumerate(s['edges']):
        arrow='tee' if e['relation']=='inhibition' else 'none' if e['relation']=='association' else 'normal'
        label=e['label'] or (e['relation'] if e['relation'] not in ('flow','data') else '')
        if e['certainty']=='hypothesis': label=(label+'\n' if label else '')+'hypothesis'
        if e['certainty']=='reported': label=(label+'\n' if label else '')+'reported'
        attrs={'id':'edge-'+str(i),'arrowhead':arrow,'label':label,'style':'dashed' if e['certainty']=='hypothesis' else 'solid'}
        if e['relation']=='feedback':
            attrs['xlabel']=attrs.pop('label')
            same=any({e['source'],e['target']} <= set(r) for r in s['ranks'])
            port=('n' if same else 'w') if s['direction']=='TB' else ('w' if same else 's')
            attrs.update(constraint='false',tailport=port,headport=port)
        lines.append(q(e['source'])+' -> '+q(e['target'])+' ['+', '.join(k+'='+q(v) for k,v in attrs.items())+'];')
    lines.append('}');return '\n'.join(lines)+'\n'

def run_dot(source, fmt):
    program=shutil.which('dot');need(program,'Graphviz dot is required. Ask the host to install it with permission.')
    try: p=subprocess.run([program,'-T'+fmt],input=source.encode(),capture_output=True,timeout=30,check=False)
    except subprocess.TimeoutExpired as exc: raise DiagramError('Graph layout timed out; simplify or split the diagram') from exc
    need(p.returncode==0,'Graphviz layout failed: '+p.stderr.decode('utf-8','replace')[:600])
    need(len(p.stdout)<=8*1024*1024,'Oversized layout output')
    return p.stdout

def add_icons(s, root, layout):
    boxes=geometry(layout)
    accent=PALETTES[s['style']][4]
    for n in s['nodes']:
        if n['role']=='decision': continue
        group=next((g for g in root.iter() if g.get('id')=='node-'+n['id']),None)
        if group is None: continue
        x,y,w,h=boxes[n['id']]
        icon=ET.SubElement(group,'{'+NS+'}g',{'transform':f'translate({x+w-22:g},{-y+11:g})','stroke':accent,'stroke-width':'1.1','fill':'none','aria-hidden':'true'})
        def el(tag, **a):return ET.SubElement(icon,'{'+NS+'}'+tag,{k.replace('_','-'):str(v) for k,v in a.items()})
        if n['role']=='input':
            for yy in (2,6,10):el('path',d=f'M 1 {yy} L 7 {yy-2} L 13 {yy} L 7 {yy+2} Z')
        elif n['role']=='process':
            el('path',d='M 3 3 L 11 7 L 3 11')
            for xx,yy in ((3,3),(11,7),(3,11)):el('circle',cx=xx,cy=yy,r=2,fill='white')
        elif n['role']=='output':
            el('rect',x=1,y=1,width=12,height=13,rx=2);el('path',d='M 3 8 L 6 11 L 11 5')
        elif n['role']=='control':
            for yy,xx in ((3,5),(7,10),(11,4)):
                el('path',d=f'M 1 {yy} H 13');el('circle',cx=xx,cy=yy,r=1.5,fill='white')
        else:
            el('rect',x=1,y=1,width=12,height=13,rx=2);el('path',d='M 4 5 H 10 M 4 8 H 10 M 4 11 H 8')


def font_check(s):
    # Font files are consulted locally for glyph coverage, never copied/distributed.
    fc=shutil.which('fc-match')
    if not fc:return {'coverage':'not_checked','reason':'fontconfig absent; inspect all glyphs in the exported PDF'}
    try:
        p=subprocess.run([fc,'-f','%{file}\\n%{family}',s['font_family']],capture_output=True,text=True,timeout=5,check=False)
        parts=p.stdout.split('\n',1)
        if len(parts)!=2 or not Path(parts[0]).is_file():return {'coverage':'not_checked'}
        from fontTools.ttLib import TTFont
        f=TTFont(parts[0],fontNumber=0,lazy=True)
        cmap=f.getBestCmap();f.close()
        visible=s['title']+s['subtitle']+''.join(n['label']+n['detail'] for n in s['nodes'])+''.join(e['label'] for e in s['edges'])+''.join(g['label'] for g in s['groups'])
        missing=sorted(set(c for c in visible if not c.isspace() and ord(c) not in cmap))
        need(not missing,'Selected font lacks glyphs: '+''.join(missing[:20])+'. Select an installed font covering the text.')
        return {'coverage':'checked','resolved_family':parts[1].strip()}
    except ImportError:return {'coverage':'not_checked','reason':'optional fontTools not installed'}


def page(s, raw, layout):
    root=ET.fromstring(raw); add_icons(s,root,layout); box=list(map(float,root.attrib['viewBox'].split())); gw,gh=box[2:]
    # A reserved title and legend area leaves graph content intact and uncropped.
    width=max(gw+44,420)
    title_lines=wrap(s['title'],max(38,int((width-44)/9.5)))
    need(len(title_lines)<=2,'Shorten the title and put detail in the caption')
    top=(84 if s['subtitle'] else 65)+23*(len(title_lines)-1); height=gh+top+57
    physical_h=s.get('height_mm',s['width_mm']*height/width)
    scale=min(s['width_mm']*72/25.4/width,physical_h*72/25.4/height)
    effective=(s['font_size']-2)*scale
    need(effective>=6.5, 'Labels would be too small at final width (%.1f pt). Use TB layout, shorten labels, increase width, or split the figure.'%effective)
    out=ET.Element('{'+NS+'}svg',{'width':str(s['width_mm'])+'mm','height':str(round(physical_h,3))+'mm','viewBox':f'0 0 {width:g} {height:g}','role':'img','aria-labelledby':'diagram-title diagram-desc'})
    ET.SubElement(out,'{'+NS+'}title',{'id':'diagram-title'}).text=s['title']
    ET.SubElement(out,'{'+NS+'}desc',{'id':'diagram-desc'}).text=s['alt_text']
    ink,muted,border,panel,accent,*_=PALETTES[s['style']]
    ET.SubElement(out,'{'+NS+'}rect',{'width':str(width),'height':str(height),'fill':'white'})
    def t(x,y,value,size,color,weight='normal'):
        ET.SubElement(out,'{'+NS+'}text',{'x':str(x),'y':str(y),'font-family':s['font_family'],'font-size':str(size),'font-weight':weight,'fill':color}).text=value
    t(22,23,s['kind'].replace('-',' ').upper()+'  /  '+s['status'].upper(),9,accent,'bold')
    for j,line in enumerate(title_lines): t(22,46+23*j,line,17,ink,'bold')
    if s['subtitle']: t(22,65+23*(len(title_lines)-1),s['subtitle'],10,muted)
    root.attrib.update(x=str((width-gw)/2),y=str(top),width=str(gw),height=str(gh))
    out.append(root)
    footer=top+gh+19
    ET.SubElement(out,'{'+NS+'}line',{'x1':'22','y1':str(footer-11),'x2':str(width-22),'y2':str(footer-11),'stroke':border})
    # Legend stays truthful across all diagrams; certainty is also carried by edge labels.
    t(22,footer+4,'Schematic: not to scale. Dashed links: hypotheses.',9,muted)
    t(22,footer+19,'Arrows encode the stated relation; layout alone provides no evidence.',9,muted)
    for el in out.iter():
        need(el.tag.split('}')[-1] not in ('script','image','foreignObject','use'), 'Unsafe SVG element')
        need(not any(k.lower().endswith('href') or k.lower().startswith('on') for k in el.attrib), 'Unsafe SVG attribute')
    return ET.tostring(out,encoding='utf-8',xml_declaration=True),{'width_mm':s['width_mm'],'height_mm':round(physical_h,3),'minimum_label_pt':round(effective,2),'page_width':width,'page_height':height,'graph_x':(width-gw)/2,'graph_y':top,'graph_width':gw,'graph_height':gh}

def geometry(layout):
    result={}
    for n in layout.get('objects',[]):
        if 'pos' not in n or 'width' not in n: continue
        x,y=map(float,n['pos'].split(','));w=float(n['width'])*72;h=float(n['height'])*72
        result[n['name']]=(x-w/2,y+h/2,w,h)
    return result

def overlap_check(layout):
    boxes=geometry(layout);keys=list(boxes)
    for i,a in enumerate(keys):
        x,y,w,h=boxes[a]
        for b in keys[i+1:]:
            xx,yy,ww,hh=boxes[b]
            need(min(x+w,xx+ww)-max(x,xx)<0.5 or min(y,yy)-max(y-h,yy-hh)<0.5,'Overlapping nodes; simplify layout: '+a+', '+b)

def drawio(s, layout):
    """Editable, uncompressed mxGraph XML. It is not a pixel-identical SVG round trip."""
    ink,muted,border,panel,accent,fill,second,fill2=PALETTES[s['style']]
    _,_,gw,gh=map(float,layout['bb'].split(',')); boxes=geometry(layout)
    root=ET.Element('mxfile',{'host':'AI Research Workspace','version':'1.0'})
    diagram=ET.SubElement(root,'diagram',{'id':s['id'],'name':s['title']})
    graph=ET.SubElement(diagram,'mxGraphModel',{'grid':'1','gridSize':'10','page':'1','pageWidth':str(int(gw+80)),'pageHeight':str(int(gh+130))})
    cells=ET.SubElement(graph,'root'); ET.SubElement(cells,'mxCell',{'id':'0'});ET.SubElement(cells,'mxCell',{'id':'1','parent':'0'})
    def cell(key,value,x,y,w,h,style):
        c=ET.SubElement(cells,'mxCell',{'id':key,'value':value,'style':style,'vertex':'1','parent':'1'})
        ET.SubElement(c,'mxGeometry',{'x':str(round(x,2)),'y':str(round(y,2)),'width':str(round(w,2)),'height':str(round(h,2)),'as':'geometry'})
    font='fontFamily='+s['font_family']+';fontSize='+str(s['font_size'])+';fontColor='+ink+';html=0;'
    cell('title',s['title'],20,15,gw,40,font+'text;align=left;fontStyle=1;')
    for g in layout.get('objects',[]):
        if 'bb' not in g:continue
        x,y,xx,yy=map(float,g['bb'].split(','))
        cell('group-'+g['name'],g.get('label',''),20+x,70+gh-yy,xx-x,yy-y,font+'rounded=1;fillColor='+panel+';strokeColor='+border+';verticalAlign=top;spacingTop=7;')
    for n in s['nodes']:
        x,y,w,h=boxes[n['id']];shape='rhombus;' if n['role']=='decision' else 'rounded=1;arcSize=12;'
        color=fill2 if n['role'] in ('control','output') else fill
        cell('node-'+n['id'],n['label']+('\n'+n['detail'] if n['detail'] else ''),20+x,70+gh-y,w,h,font+shape+'whiteSpace=wrap;fillColor='+color+';strokeColor='+border+';')
    for i,e in enumerate(s['edges']):
        label=e['label']+(' ['+e['certainty']+']' if e['certainty']!='schematic' else '')
        arrow='none' if e['relation']=='association' else 'block'
        if e['relation']=='inhibition':arrow='ERone'
        c=ET.SubElement(cells,'mxCell',{'id':'edge-'+str(i),'value':label,'edge':'1','parent':'1','source':'node-'+e['source'],'target':'node-'+e['target'],
            'style':font+'edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow='+arrow+';dashed='+('1' if e['certainty']=='hypothesis' else '0')+';strokeColor='+muted+';',
            'rwRelation':e['relation'],'rwCertainty':e['certainty']})
        ET.SubElement(c,'mxGeometry',{'relative':'1','as':'geometry'})
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def render(raw, output, *, svg_only=False):
    s=validate(raw);output=Path(output)
    need(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),'Symlink output path refused')
    need(not output.exists(),'Use a new output directory; no diagram version is overwritten')
    fonts=font_check(s)
    source=dot_source(s);layout=json.loads(run_dot(source,'json'));overlap_check(layout)
    svg,dimensions=page(s,run_dot(source,'svg'),layout)
    products={'diagram.svg':svg,'diagram.dot':source.encode(),'diagram.drawio':drawio(s,layout),'layout.json':json.dumps(layout,ensure_ascii=False,indent=2).encode()}
    if not svg_only:
        try:import cairosvg
        except ImportError as exc:raise DiagramError('Install the optional diagrams extra in the project venv after authorization, or use --svg-only.') from exc
        products['diagram.pdf']=cairosvg.svg2pdf(bytestring=svg)
        products['diagram.png']=cairosvg.svg2png(bytestring=svg,output_width=round(s['width_mm']/25.4*s['dpi']),output_height=round(dimensions['height_mm']/25.4*s['dpi']))
    # Build everything before the first persistent write. Partial failures do not
    # touch any existing folder and never establish a scientific approval.
    output.mkdir(parents=True,exist_ok=False)
    for name,data in products.items():
        with (output/name).open('xb') as f:f.write(data)
    executable=shutil.which('dot')
    version=subprocess.run([executable,'-V'],capture_output=True,text=True,timeout=5).stderr.strip()
    return {'renderer':VERSION,'graphviz':version,'python':sys.version.split()[0], 'cairosvg':None if svg_only else cairosvg.__version__,
            'nodes':len(s['nodes']),'edges':len(s['edges']),'groups':len(s['groups']),'dimensions':dimensions,'style':s['style'],'font':fonts,
            'files':sorted(products),'warnings':['Visual review at the intended printed size is required.','SVG text requires installed fonts; no font files are distributed.','drawio contains editable shapes; its automatic edge rerouting can differ from the SVG.'],
            'scientific_status':'illustration_requires_review'}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec');p.add_argument('--output',required=True);p.add_argument('--svg-only',action='store_true');a=p.parse_args(argv)
    try:
        path=Path(a.spec);need(path.is_file() and path.stat().st_size<=256000,'Missing/oversized specification')
        report=render(json.loads(path.read_text(encoding='utf-8')),a.output,svg_only=a.svg_only)
        print(json.dumps(report,ensure_ascii=False,indent=2));return 0
    except (DiagramError,OSError,ValueError,ET.ParseError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
