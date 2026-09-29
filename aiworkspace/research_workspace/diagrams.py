"""Agent-operated diagram plans, local rendering, provenance and draft proposals.

User-facing entry remains menu 5 / natural language. Nothing is uploaded, no
scientific verification is minted, and existing diagram versions are preserved.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import tempfile
from . import diagram_render, paper_render
from .model import WorkspaceError, digest, identifier, make_node, node_payload, now, pretty, require
from .store import Store, file_hash, read_text, safe_path

RECORDS='workspace/history/diagrams/'
BOUNDARY='Diagram rendering and integrity checks do not establish scientific validity, visual approval or submission compliance.'


def validated(raw):
    return paper_render.validate(raw) if isinstance(raw,dict) and raw.get('kind')=='paper-composite' else diagram_render.validate(raw)


def artwork(store,spec):
    if spec['kind']!='paper-composite':return None,None
    name=spec['artwork']
    require(name.startswith('workspace/figures/') and name.endswith('.svg'),'Save authored SVG under workspace/figures/')
    path=safe_path(store.root,name)
    require(path.is_file() and path.stat().st_size<=paper_render.MAX_BYTES,'Missing or oversized artwork')
    data=path.read_bytes();paper_render.validate_svg(spec,data)
    return name,data


def linked(store, spec):
    keys=list(dict.fromkeys(spec['claims']+spec['evidence']+[k for e in spec['edges'] for k in e['evidence']]))
    for key in spec['claims']:
        n=store.node(key);require(n['kind']=='claim' and n['status']!='retired','Link an active Claim: '+key)
    for key in set(keys)-set(spec['claims']):
        n=store.node(key);require(n['kind'] in ('evidence','result') and n['status']!='retired','Link active evidence/result: '+key)
    # Reported scientific relationships must have existing, still-valid supporting
    # evidence, not just a string that resembles an evidence ID. No auto verification.
    from .workflow import evidence_problems
    for e in spec['edges']:
        if e['certainty']!='reported':continue
        for key in e['evidence']:
            n=store.node(key)
            require(n['kind']=='evidence' and not evidence_problems(store,n),'Reported arrow requires current verified evidence: '+key)
            require(n['data'].get('relation')=='supports' and n['data'].get('claim') in spec['claims'],'Reported arrow must support a linked Claim')
            if e['relation'] in ('causal','inhibition'):
                c=store.node(n['data']['claim'])
                require(c['data'].get('strength')=='causal','Association evidence cannot establish a causal/inhibitory arrow')
    # Panel declarations are not verification receipts. Any panel advertised as
    # source-bound requires actual current verified Evidence, not only an ID.
    if spec['kind']=='paper-composite' and any(p['source_status']=='source-bound' for p in spec['panels']):
        require(bool(spec['claims']) and bool(spec['evidence']),'Source-bound artwork needs Claims and evidence')
        for key in spec['evidence']:
            n=store.node(key)
            require(n['kind']=='evidence' and not evidence_problems(store,n),'Source-bound artwork needs current verified Evidence: '+key)
            require(n['data'].get('claim') in spec['claims'],'Panel evidence must address a linked Claim')
    return {key:node_payload(store.node(key)) for key in keys}


def plan(store, raw):
    spec=validated(raw);links=linked(store,spec);source,data=artwork(store,spec)
    return {'spec':spec,'linked_nodes':links,'base_fingerprint':store.fingerprint(),
            'unlinked':not bool(spec['claims'] and links.keys()-set(spec['claims'])),
            'source_artwork':source,'source_artwork_hash':digest(data) if data is not None else None,
            'requires_authorization':'local render and new artifacts only',
            'boundary':'Preview only; no execution, installation or file writes. '+BOUNDARY}


def make(store, raw, actor='ai:diagram', *, approve=False, svg_only=False, spec_path=None):
    require(approve,'Local rendering needs authorization; preview the plan first')
    report=plan(store,raw);spec=report['spec'];is_paper=spec['kind']=='paper-composite'
    original_hash=None
    if spec_path is not None:
        require(isinstance(spec_path,str) and spec_path.startswith('workspace/figures/') and spec_path.endswith('.json'),'Save the agent-authored spec under workspace/figures/')
        path=safe_path(store.root,spec_path);original_hash=file_hash(path)
        require(original_hash and validated(json.loads(read_text(path)))==spec,'Spec changed before drawing')
    run=identifier('DGR');leaf=spec['id']+'-'+run.split('-',1)[1]
    output='manuscript/figures/'+leaf;provenance='workspace/results/diagrams/'+leaf;record_path=RECORDS+run+'.json'
    for path in (output,provenance,record_path):require(not safe_path(store.root,path).exists(),'Diagram version exists')
    renderer=Path(paper_render.__file__ if is_paper else diagram_render.__file__).read_bytes()
    source,data=artwork(store,spec)
    require(data is None or digest(data)==report['source_artwork_hash'],'Artwork changed before rendering')
    with tempfile.TemporaryDirectory(prefix='rw-diagram-') as tmp:
        rendered=Path(tmp)/'rendered'
        summary=paper_render.render(spec,data,rendered,svg_only=svg_only) if is_paper else diagram_render.render(spec,rendered,svg_only=svg_only)
        products={p.name:p.read_bytes() for p in rendered.iterdir()}
        require(Store(store.root).fingerprint()==report['base_fingerprint'],'Study changed during layout; retry without discarding those changes')
        require(linked(store,spec)==report['linked_nodes'],'Linked evidence changed during layout')
        if spec_path:require(file_hash(safe_path(store.root,spec_path))==original_hash,'Source spec changed during layout')
        frozen={**spec,'artwork':'artwork.svg'} if is_paper else spec
        working={'spec.json':pretty(frozen).encode(),'reproduce.py':renderer,
            'caption.md':(spec['caption']+'\n\nDiagram status: '+spec['status']+'. '+('Unlinked illustration; no evidentiary claim. ' if report['unlinked'] else '')+BOUNDARY+'\n').encode(),
            'alt-text.txt':spec['alt_text'].encode(),
            'README.md':b'# Regenerate or edit\n\nThe agent can run reproduce.py spec.json --output NEW_DIRECTORY after authorization. Requires Graphviz and optional CairoSVG/fontTools for graph templates, or CairoSVG for paper compositions. No fonts or credentials are bundled. Paper compositions preserve artwork.svg as editable vector primitives; they have no drawio/DOT. Graph templates retain diagram.drawio. Edits invalidate this receipt; reconcile before publication. No external web upload is authorized by this bundle.\n'}
        image_files={n:b for n,b in products.items() if n.endswith(('.svg','.pdf','.png')) and n!='artwork.svg'}
        working.update({n:b for n,b in products.items() if n not in image_files})
        for directory in (output,provenance):safe_path(store.root,directory).mkdir(parents=True,exist_ok=False)
        files={}
        for directory,items in ((output,image_files),(provenance,working)):
            for name,raw_bytes in items.items():
                dest=safe_path(store.root,directory+'/'+name)
                with dest.open('xb') as f:f.write(raw_bytes)
                files[directory+'/'+name]=digest(raw_bytes)
    record={'format':1,'id':run,'figure_id':spec['id'],'at':now(),'actor':actor,'spec':spec,'source_spec':spec_path,'source_spec_hash':original_hash,
            'files':files,'output':output,'provenance':provenance,'linked_nodes':report['linked_nodes'],'summary':summary,
            'source_artwork':source,'source_artwork_hash':report['source_artwork_hash'],
            'status':'rendered_requires_review','unlinked':report['unlinked'],'boundary':BOUNDARY}
    store.event('diagram.rendered',actor,{'id':run,'record':record_path,'record_hash':digest(record)})
    expected={record_path:None,**files}
    if spec_path:expected[spec_path]=original_hash
    if source:expected[source]=report['source_artwork_hash']
    # New orphaned products may remain after an interrupted commit; they never
    # replace an older version or count as an approval. Recover via normal Store.
    store.commit({record_path:pretty(record)},expected)
    return {'record':record_path,'svg':output+'/diagram.svg','pdf':output+'/diagram.pdf' if not svg_only else None,
            'preview':output+'/diagram.png' if not svg_only else output+'/diagram.svg','editable':provenance+('/artwork.svg' if is_paper else '/diagram.drawio'),
            'unlinked':report['unlinked'],'needs_visual_review':True,'boundary':BOUNDARY}


def receipt(store,path):
    require(isinstance(path,str) and re.fullmatch(r'workspace/history/diagrams/DGR-[A-F0-9]{12}\.json',path),'Use a diagram receipt from this study')
    record=json.loads(read_text(safe_path(store.root,path)))
    require(record.get('format')==1 and isinstance(record.get('files'),dict),'Unknown receipt format')
    return record


def check(store,path):
    r=receipt(store,path);issues=[]
    if not any(e.get('action')=='diagram.rendered' and e.get('detail',{}).get('record')==path and e['detail'].get('record_hash')==digest(r) for e in store.state['events']):issues.append('Receipt does not match the rendering event')
    for name,h in r['files'].items():
        if file_hash(safe_path(store.root,name))!=h:issues.append('Artifact changed/missing: '+name)
    if r.get('source_spec') and file_hash(safe_path(store.root,r['source_spec']))!=r['source_spec_hash']:issues.append('Original diagram spec changed')
    if r.get('source_artwork') and file_hash(safe_path(store.root,r['source_artwork']))!=r['source_artwork_hash']:issues.append('Original paper artwork changed')
    for key,h in r.get('linked_nodes',{}).items():
        if key not in store.state['nodes'] or node_payload(store.node(key))!=h:issues.append('Linked research changed: '+key)
    try:
        linked(store,r['spec'])
        if r['spec']['kind']=='paper-composite':artwork(store,r['spec'])
    except (WorkspaceError,KeyError,TypeError,ValueError) as exc:issues.append(str(exc))
    return {'current':not issues,'issues':issues,'record':path,'visual_review':'required','scientific_review':'required'}


def propose(store,path,actor='ai:diagram'):
    require(check(store,path)['current'],'Diagram spec, source or outputs changed; regenerate/reconcile first')
    r=receipt(store,path);spec=r['spec'];require(not r['unlinked'],'Unlinked exploratory illustration cannot become an evidence-backed Figure')
    all_evidence=sorted(set(r['linked_nodes'])-set(spec['claims']))
    primary=r['output']+('/diagram.pdf' if r['output']+'/diagram.pdf' in r['files'] else '/diagram.svg')
    node=make_node(spec['id'],'figure',spec['title'],{'path':primary,'sha256':r['files'][primary],'claims':spec['claims'],
        'purpose':spec['purpose'],'caption':spec['caption'],'alt_text':spec['alt_text'],'diagram_record':path,
        'diagram_type':spec['kind'],'diagram_status':spec['status']},spec['claims']+all_evidence,status='draft')
    from .workflow import propose as create
    return create(store,[{'op':'upsert','node':node}],actor,'Review this source-linked diagram and its scientific/visual limitations')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',default='.');sub=p.add_subparsers(dest='action',required=True)
    t=sub.add_parser('template');t.add_argument('kind',choices=diagram_render.KINDS)
    t=sub.add_parser('render');t.add_argument('spec');t.add_argument('--approve',action='store_true');t.add_argument('--svg-only',action='store_true');t.add_argument('--actor',default='ai:diagram')
    t=sub.add_parser('check');t.add_argument('record')
    t=sub.add_parser('propose');t.add_argument('record');t.add_argument('--actor',default='ai:diagram')
    a=p.parse_args(argv)
    try:
        if a.action=='template':
            from .diagram_templates import template
            result=template(a.kind)
        else:
            store=Store(a.project)
            if a.action=='render':
                path=safe_path(store.root,a.spec);raw=json.loads(read_text(path))
                result=make(store,raw,a.actor,approve=True,svg_only=a.svg_only,spec_path=a.spec) if a.approve else plan(store,raw)
            elif a.action=='check':result=check(store,a.record)
            else:result=propose(store,a.record,a.actor)
        print(pretty(result));return 1 if a.action=='check' and not result['current'] else 0
    except (WorkspaceError,diagram_render.DiagramError,paper_render.PaperFigureError,OSError,ValueError,KeyError,TypeError) as exc:
        print(pretty({'error':str(exc)}),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
