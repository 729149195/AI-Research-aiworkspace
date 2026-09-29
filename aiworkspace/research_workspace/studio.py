"""Agent-operated writing and figure workbench. User interaction remains natural language.

Run with python -m research_workspace.studio. No network and no implicit approvals.
The 0.4 CLI remains compatible; these additive helpers use the same Schema 1 Store.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from .model import WorkspaceError, digest, identifier, make_node, node_payload, now, pretty, require
from .store import Store, atomic_write, file_hash, read_text, safe_path
from . import figure_render

RECORDS = 'workspace/history/figures/'
BRIEF = 'workspace/research/writing-brief.md'
BOUNDARY = 'Software checks and located evidence, not scientific certification or independent human review.'


def _input(store, spec):
    if spec.get('kind') == 'workflow': return None, None
    name = spec.get('input')
    require(isinstance(name, str) and name.startswith(('workspace/data/','workspace/results/')) and name.endswith('.csv'),
            'Use a CSV analysis table in workspace/data or workspace/results; never read credentials or arbitrary files.')
    path = safe_path(store.root, name)
    require(path.is_file() and path.stat().st_size <= figure_render.MAX_BYTES, 'Missing or oversized CSV input.')
    return name, path.read_bytes()


def inspect_data(store, path):
    _, data = _input(store, {'kind':'scatter','input':path})
    names, rows = figure_render.table(data)
    columns = []
    for name in names:
        present = [r[name] for r in rows if r[name].strip().lower() not in figure_render.MISSING]
        numeric = []
        for value in present:
            try: numeric.append(figure_render.number(value, name))
            except figure_render.FigureError: break
        is_numeric = bool(present) and len(numeric) == len(present)
        columns.append({'name':name,'type':'numeric' if is_numeric else 'text_or_mixed',
                        'missing':len(rows)-len(present),'distinct':len(set(present)),
                        'range':[min(numeric),max(numeric)] if is_numeric else None})
    return {'input':path,'sha256':digest(data),'rows':len(rows),'columns':columns,
            'next':'Agent chooses encodings from the scientific task; confirm units and independent/paired structure. No data or figures changed.'}


def _linked(store, spec):
    claims, evidence = spec.get('claims', []), spec.get('evidence', [])
    require(isinstance(claims, list) and isinstance(evidence, list), 'Claim/evidence IDs must be lists.')
    require(all(isinstance(k, str) for k in claims+evidence), 'Invalid provenance ID.')
    require(len(claims+evidence) == len(set(claims+evidence)), 'Duplicate provenance ID.')
    for key in claims:
        require(store.node(key)['kind'] == 'claim' and store.node(key)['status'] != 'retired', 'Link an active Claim.')
    for key in evidence:
        require(store.node(key)['kind'] in ('evidence','result') and store.node(key)['status'] != 'retired', 'Link active evidence or an executed result.')
    return {key:node_payload(store.node(key)) for key in claims+evidence}


def figure_plan(store, spec):
    require(isinstance(spec, dict) and re.fullmatch(r'FIG-[A-Z0-9][A-Z0-9_-]{0,40}',str(spec.get('id',''))), 'Use a stable figure ID such as FIG-001.')
    source, data = _input(store,spec)
    _, summary = figure_render.prepare(spec,data)
    links = _linked(store,spec)
    return {'spec':copy.deepcopy(spec),'input':source,'input_sha256':digest(data) if data is not None else None,
            'linked_nodes':links,'summary':summary,'exploratory':not (spec.get('claims') and spec.get('evidence')),
            'needs_visual_review':True,'base_fingerprint':store.fingerprint(),
            'boundary':'Preview only. No files or research nodes changed. '+BOUNDARY}


def figure_make(store, spec, actor='ai:figure', *, approve=False):
    require(approve,'The agent needs authorization to create this local figure; preview first.')
    plan = figure_plan(store,spec)
    source,data = _input(store,spec)
    require(data is None or digest(data) == plan['input_sha256'], 'CSV changed after preview.')
    run = identifier('FGR'); leaf=spec['id']+'-'+run.split('-',1)[1]
    output='manuscript/figures/'+leaf
    provenance='workspace/results/figures/'+leaf
    record_path=RECORDS+run+'.json'
    for name in (output,provenance,record_path):
        require(not safe_path(store.root,name).exists(), 'Figure version already exists.')
    renderer_file=Path(figure_render.__file__)
    renderer_code=renderer_file.read_bytes()
    # Render entirely off-project. A bad font, invalid table or dense layout cannot
    # overwrite previous work or leave a successful research receipt.
    with tempfile.TemporaryDirectory(prefix='rw-figure-') as temp:
        folder=Path(temp)/'output'
        summary=figure_render.render(spec,data,folder)
        products={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
        require(Store(store.root).fingerprint() == plan['base_fingerprint'], 'Research changed during drawing; regenerate against current input.')
        require(_linked(store,spec)==plan['linked_nodes'], 'Provenance changed during drawing.')
        for name in (output,provenance): safe_path(store.root,name).mkdir(parents=True,exist_ok=False)
        for name,raw in products.items():
            target=safe_path(store.root,output+'/'+name)
            with target.open('xb') as handle: handle.write(raw)
        frozen={**spec,'input':'input.csv'} if data is not None else copy.deepcopy(spec)
        local = {'spec.json':pretty(frozen).encode(), 'reproduce.py':renderer_code}
        if data is not None: local['input.csv']=data
        missing = len(summary['omitted_csv_rows'])+len(summary['missing_line_gaps'])
        caption = spec['caption']+'\n\n'+('EXPLORATORY / UNLINKED: verify and link evidence before manuscript claims.\n\n' if plan['exploratory'] else '')
        caption += ('Observed rows: '+str(summary['raw_rows'])+'; used observations: '+str(summary['used_rows'])+'; missing: '+str(missing)+'.\n' if data is not None else '')
        if spec.get('interval_definition'): caption += 'Interval: '+spec['interval_definition']+'.\n'
        if spec['kind']=='distribution':caption += summary['transformation']+'\n'
        if missing:caption += 'Missing-data decision: '+spec['omission_reason']+'\n'
        local['caption.md']=caption.encode();local['alt-text.txt']=spec['alt_text'].encode()
        local['README.md']=('# Local regeneration bundle\n\nThe original input and code are retained here, outside the Overleaf manuscript subtree.\n'
            'The agent can run the reviewed local reproduce.py with spec.json, '+('--data input.csv, ' if data is not None else '')+
            'and --output NEW_DIRECTORY. Requires the recorded Python/Matplotlib environment and font family.\n'
            'Use a new output directory. Byte identity across software/font versions is not promised.\n'
            'Figures need visual and scientific review; no human approval is recorded by rendering.\n').encode()
        for name,raw in local.items():
            with safe_path(store.root,provenance+'/'+name).open('xb') as handle: handle.write(raw)
    files={output+'/'+n:digest(b) for n,b in products.items()}
    files.update({provenance+'/'+n:digest(b) for n,b in local.items()})
    record={'format':1,'id':run,'figure_id':spec['id'],'at':now(),'actor':actor,'input':source,
            'input_sha256':plan['input_sha256'],'spec':spec,'linked_nodes':plan['linked_nodes'],
            'files':files,'output':output,'provenance':provenance,'summary':summary,
            'python':sys.version.split()[0],'renderer_sha256':digest(renderer_code),
            'status':'rendered_requires_review','exploratory':plan['exploratory'],'boundary':BOUNDARY}
    store.event('figure.rendered',actor,{'id':run,'record':record_path,'record_hash':digest(record)})
    expected={record_path:None,**files}
    if source:expected[source]=plan['input_sha256']
    # If registration fails, newly generated versions remain inspectable but are not
    # approved. Existing files are never removed to hide a failure.
    store.commit({record_path:pretty(record)},expected)
    return {'record':record_path,'preview':output+'/figure.png','pdf':output+'/figure.pdf','svg':output+'/figure.svg',
            'caption':provenance+'/caption.md','alt_text':provenance+'/alt-text.txt','exploratory':plan['exploratory'],
            'next':'Inspect actual output, then propose a linked Figure node. Rendering does not apply a research Claim.',
            'warnings':summary['warnings']}


def figure_check(store, record_path):
    require(isinstance(record_path,str) and re.fullmatch(r'workspace/history/figures/FGR-[A-F0-9]{12}\.json',record_path), 'Use a figure receipt path from this study.')
    record=json.loads(read_text(safe_path(store.root,record_path)))
    require(record.get('format')==1 and isinstance(record.get('files'),dict),'Unknown figure receipt.')
    errors=[]
    if not any(e.get('action')=='figure.rendered' and e.get('detail',{}).get('record')==record_path and e['detail'].get('record_hash')==digest(record) for e in store.state['events']):
        errors.append('Figure receipt does not match its execution event.')
    for path,expected in record['files'].items():
        if file_hash(safe_path(store.root,path)) != expected: errors.append('Artifact changed/missing: '+path)
    if record.get('input') and file_hash(safe_path(store.root,record['input'])) != record['input_sha256']:
        errors.append('Original data changed; regenerate this figure.')
    for key,sha in record.get('linked_nodes',{}).items():
        if key not in store.state['nodes'] or node_payload(store.node(key))!=sha:errors.append('Linked research changed: '+key)
    return {'current':not errors,'record':record_path,'issues':errors,'visual_review':'required','scientific_review':'required'}


def figure_propose(store, record_path, actor='ai:figure'):
    require(figure_check(store,record_path)['current'],'Figure input/output/provenance is stale; regenerate or inspect.')
    record=json.loads(read_text(safe_path(store.root,record_path)));spec=record['spec']
    require(spec.get('claims') and spec.get('evidence'),'Link actual Claims and evidence/results before registering a scientific figure.')
    primary=record['output']+'/figure.pdf'
    node=make_node(spec['id'],'figure',spec['title'],{
        'path':primary,'sha256':record['files'][primary],'claims':spec['claims'],
        'caption':read_text(safe_path(store.root,record['provenance']+'/caption.md')),
        'purpose':spec['purpose'],'alt_text':spec['alt_text'],'studio_record':record_path,
        'provenance':record['provenance'],'visual_review':'pending','exploratory':record['exploratory']},
        spec['claims']+spec['evidence'],'draft')
    from .workflow import propose
    return propose(store,[{'op':'upsert','node':node}],actor,'Register generated figure for review; preserve data and Claim provenance.')


def _manuscript(store):
    if store.state['project'].get('latex'):
        from .latex_project import read_manuscript
        return read_manuscript(store)
    return read_text(safe_path(store.root,'manuscript/main.md'))


def audit_text(value, *, latex=False):
    """Located editing leads. Lexical checks are not scientific entailment judgments."""
    require(isinstance(value,str) and len(value.encode('utf-8')) <= 2*1024*1024,'Audit at most 2 MiB of manuscript text; split the task explicitly.')
    lines=value.splitlines(); masked=[]; fenced=False;literal=None
    for line in lines:
        if re.match(r'^\s*(```|~~~)',line):fenced=not fenced;masked.append('');continue
        if fenced:masked.append('');continue
        if re.search(r'\\begin\{(?:verbatim|lstlisting|minted|comment)\}',line):literal=True
        if literal:
            if re.search(r'\\end\{(?:verbatim|lstlisting|minted|comment)\}',line):literal=None
            masked.append('');continue
        line=re.sub(r'<!--.*?-->','',line)
        masked.append(re.sub(r'(?<!\\)%.*','',line) if latex else line)
    findings=[]; numbers=[]
    for line_no,line in enumerate(masked,1):
        checks=(('placeholder',r'\b(?:TODO|TBD|TBC|PLACEHOLDER)\b|待填写|尚未填写','Fill from actual evidence or leave the item explicitly unresolved.'),
                ('strength_review',r'\b(?:proves?|causes?|definitively|unprecedented|state[- ]of[- ]the[- ]art)\b|证明了|导致|首次提出','Inspect inference, scope and comparator; wording alone does not establish support.'),
                ('vague_language',r'\b(?:it is worth noting that|in the realm of|very significant|remarkably superior)\b','Replace stock language with a specific supported statement; preserve technical meaning.'))
        for code,pattern,fix in checks:
            for m in re.finditer(pattern,line,re.I):findings.append({'code':code,'line':line_no,'excerpt':line[max(0,m.start()-45):m.end()+70],'required_check':fix,'status':'editing_lead'})
        for m in re.finditer(r'(?<![\w.])(?:n\s*=\s*)?[-+]?\d+(?:\.\d+)?(?:\s*%|\s*(?:ms|s|kg|mm|cm))?(?!\w|\.\d)',line):
            numbers.append({'line':line_no,'literal':m.group(),'context':line[max(0,m.start()-35):m.end()+45]})
    paragraphs=[]; start=None; content=[]
    for no,line in enumerate(masked+[''],1):
        if line.strip():
            if start is None:start=no
            content.append(line)
        elif start is not None:
            raw=' '.join(content)
            if len(raw)>70 and not raw.startswith(('#','\\section')):
                paragraphs.append({'start_line':start,'end_line':no-1,'opening':raw[:180],
                                   'citation_present':bool(re.search(r'@\w|\\cite\w*\s*(?:\[[^\]]*\]\s*)*\{',raw)),
                                   'agent_checks':['paragraph purpose','bounded assertion','original evidence or derivation','relation to whole argument']})
            start=None;content=[]
    return {'findings':findings,'numeric_ledger':numbers,'paragraph_map':paragraphs,
            'boundary':'Rule-based leads only. Different cohorts may legitimately have different numbers; do not auto-normalize them. Missing citations are not automatically errors.'}


def audit(store):
    from .workflow import evidence_problems
    result=audit_text(_manuscript(store),latex=bool(store.state['project'].get('latex')));claims=[]
    for key,node in store.state['nodes'].items():
        if node['kind']!='claim' or node['status']=='retired':continue
        items=[]
        for dep in node['depends_on']:
            e=store.state['nodes'].get(dep)
            if e and e['kind']=='evidence':
                try: problems=evidence_problems(store,e)
                except (WorkspaceError,OSError,ValueError) as exc:problems=[str(exc)]
                if e['data'].get('claim')!=key:problems.append('Evidence targets another Claim.')
                items.append({'id':dep,'relation':e['data'].get('relation'),'issues':problems,
                              'response':node['data'].get('responses',{}).get(dep)})
        claims.append({'id':key,'text':node['data']['text'],'strength':node['data']['strength'],'scope':node['data'].get('scope'),
                       'valid_support':any(e['relation']=='supports' and not e['issues'] for e in items),'evidence':items})
    figures=[]
    folder=safe_path(store.root,RECORDS)
    for path in sorted(folder.glob('FGR-*.json')):
        figures.append(figure_check(store,path.relative_to(store.root).as_posix()))
    result.update(project=store.state['project']['name'],fingerprint=store.fingerprint(),claims=claims,figures=figures,
                  brief=read_text(safe_path(store.root,BRIEF)) if safe_path(store.root,BRIEF).exists() else None,
                  next='Resolve unsupported/changed evidence first; then whole argument, paragraphs and language. No numerical quality score is assigned.')
    return result


def resume(store):
    """Read actual work without rewriting state or generating a second task queue."""
    order={'critical':0,'major':1,'minor':2}
    issues=sorted((copy.deepcopy(i) for i in store.state['issues'].values() if i['status']=='open'),key=lambda i:(order.get(i['severity'],9),i['id']))
    tasks=[copy.deepcopy(t) for t in store.state['tasks'] if t['status']=='open']
    return {'project':store.state['project']['name'],'active_manuscript':store.state['project'].get('latex') or 'manuscript/main.md',
            'next_issues':issues[:3],'other_open_issue_count':max(0,len(issues)-3),'open_tasks':tasks,
            'brief_present':safe_path(store.root,BRIEF).exists(),'boundary':'Read-only handover. No task has been executed or marked complete.'}


def responses(store, data):
    require(isinstance(data,dict) and isinstance(data.get('comments'),list) and 0<len(data['comments'])<=200,'Provide 1–200 original reviewer comments.')
    require(len(pretty(data).encode())<=1024*1024,'Response plan exceeds 1 MiB; split it explicitly.')
    ids=set();rows=[]
    for entry in data['comments']:
        require(isinstance(entry,dict),'Comment must be an object.')
        key=entry.get('id');require(isinstance(key,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,40}',key) and key not in ids,'Unique bounded comment IDs required.')
        ids.add(key);comment=entry.get('comment');require(isinstance(comment,str) and bool(comment.strip()),'Retain the actual reviewer wording.')
        locations=entry.get('locations',[]);require(isinstance(locations,list) and len(locations)<=30,'Use a bounded locations list.')
        verified=[];problems=[]
        for loc in locations:
            require(isinstance(loc,dict) and isinstance(loc.get('path'),str) and isinstance(loc.get('quote'),str) and loc['quote'].strip(),'Location needs exact path and quote.')
            path=loc['path'];require(path.startswith(('manuscript/','workspace/results/','workspace/methods/')),'Locations must refer to actual research outputs.')
            target=safe_path(store.root,path)
            if not target.is_file():problems.append('Missing file: '+path);continue
            current=file_hash(target)
            if loc.get('sha256')!=current:problems.append('Missing/stale expected hash: '+path);continue
            content=read_text(target)
            if loc['quote'] not in content:problems.append('Claimed changed text absent: '+path);continue
            verified.append({'path':path,'sha256':current,'line':content[:content.index(loc['quote'])].count('\n')+1,'quote':loc['quote']})
        response=entry.get('response','');action=entry.get('action','')
        require(isinstance(response,str) and isinstance(action,str),'Response/action must be text.')
        state='located_for_review' if verified and response and action and not problems else 'response_draft' if response else 'needs_work'
        rows.append({'id':key,'reviewer':entry.get('reviewer','unspecified'),'comment':comment,'action':action,'response':response,
                     'locations':verified,'issues':problems,'status':state})
    return {'fingerprint':store.fingerprint(),'input_packet_sha256':digest(data),'comments':rows,'unresolved':sum(r['status']!='located_for_review' for r in rows),
            'boundary':'Exact cited text located in the current files. No claim of reviewer satisfaction, actual scientific adequacy, or completed human review.'}


def save_report(store, name, result):
    require(name in ('writing-audit','reviewer-responses'), 'Unsupported studio report.')
    base='workspace/reports/studio/'+name+'-'+identifier('RPT')
    atomic_write(safe_path(store.root,base+'.json'),pretty(result))
    lines=['# '+name,'',result.get('boundary',BOUNDARY),'','Fingerprint: '+result['fingerprint'],'']
    if name=='reviewer-responses':
        for row in result['comments']:
            lines+=['## '+row['id']+' / '+row['status'],'','### Original comment',row['comment'],'','### Action',row['action'],'','### Draft response',row['response'],'']
            lines+=['Location: '+v['path']+':'+str(v['line']) for v in row['locations']]
            lines+=['Pending: '+p for p in row['issues']]
    else:
        lines+=['## Claim–evidence checks','']
        for c in result['claims']:
            lines += [c['id']+' | '+c['strength']+' | current support: '+str(c['valid_support']),c['text'],'']
        lines+=['## Located editing leads','']
        for f in result['findings']:lines += ['Line '+str(f['line'])+' / '+f['code']+': '+f['excerpt'],f['required_check'],'']
        lines+=['## Numbers to reconcile by metric, population and unit','']
        for n in result['numeric_ledger']:lines += ['Line '+str(n['line'])+': '+n['literal']+' — '+n['context']]
    atomic_write(safe_path(store.root,base+'.md'),'\n'.join(lines)+'\n')
    return {'json':base+'.json','markdown':base+'.md', 'boundary':BOUNDARY}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',default='.')
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('recipes');sub.add_parser('resume')
    p=sub.add_parser('inspect-data');p.add_argument('path')
    p=sub.add_parser('figure');p.add_argument('spec');p.add_argument('--approve',action='store_true');p.add_argument('--actor',default='ai:figure')
    for name in ('figure-check','figure-propose'):
        p=sub.add_parser(name);p.add_argument('record');p.add_argument('--actor',default='ai:figure')
    p=sub.add_parser('audit');p.add_argument('--save',action='store_true')
    p=sub.add_parser('responses');p.add_argument('input');p.add_argument('--save',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.action=='recipes':
            print(pretty({'recipes':list(figure_render.KINDS),'spec_reference':'Read the figure-visualization Skill and docs/RESEARCH_STUDIO.md. The agent fills a recipe; users do not edit JSON.'}));return 0
        store=Store(args.project)
        if args.action=='resume':out=resume(store)
        elif args.action=='inspect-data':out=inspect_data(store,args.path)
        elif args.action=='figure':
            spec=json.loads(read_text(Path(args.spec)))
            out=figure_make(store,spec,args.actor,approve=True) if args.approve else figure_plan(store,spec)
        elif args.action=='figure-check':
            out=figure_check(store,args.record);print(pretty(out));return 0 if out['current'] else 1
        elif args.action=='figure-propose':out=figure_propose(store,args.record,args.actor)
        elif args.action=='audit':
            out=audit(store)
            if args.save:out['saved']=save_report(store,'writing-audit',out)
        else:
            out=responses(store,json.loads(read_text(Path(args.input))))
            if args.save:out['saved']=save_report(store,'reviewer-responses',out)
        print(pretty(out));return 0
    except (WorkspaceError,figure_render.FigureError,OSError,ValueError,TypeError,KeyError) as exc:
        print(pretty({'error':str(exc),'next':'Preserve original work; have the agent inspect the named input or missing dependency.'}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
