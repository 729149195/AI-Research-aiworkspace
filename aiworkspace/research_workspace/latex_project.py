"""Conservative LaTeX parsing, native section sync, compilation and non-destructive transfer.

This is a bounded source adapter, not a TeX interpreter. Dynamic imports are blocked;
research prose, equations, citations and graphics are preserved, never rewritten to fit.
"""
from __future__ import annotations
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from .model import WorkspaceError, digest, identifier, make_node, now, pretty, require
from .store import Store, atomic_write, file_hash, read_text, safe_path
from .workflow import add_issue, propose
from .publication_io import new_tree, sha, tree_bytes

MARKERS = re.compile(r'^% rw:section ([A-Z][A-Z0-9_-]+)\n(.*?)\n% /rw:section \1[ \t]*$', re.M|re.S)
DYNAMIC = re.compile(r'\\(?:includeonly|import|subimport|inputfrom|subinputfrom|catcode|directlua|write18|openout)\b')


def strip_comments(text: str) -> str:
    """Mask comments and literal verbatim/verb examples while preserving offsets."""
    out = list(text); i = 0
    while i < len(text):
        if text[i] == '%':
            k=i-1
            while k>=0 and text[k]=='\\': k-=1
            if (i-1-k)%2==0:
                end=text.find('\n',i);end=len(text) if end<0 else end
                out[i:end]=' '*(end-i);i=end;continue
        if text[i]=='\\':
            m=re.match(r'\\begin\{(verbatim\*?|Verbatim|lstlisting|minted|comment)\}',text[i:])
            if m:
                endmark='\\end{'+m.group(1)+'}';end=text.find(endmark,i+m.end())
                require(end>=0,'Unclosed literal environment.');end+=len(endmark)
                out[i:end]=['\n' if c=='\n' else ' ' for c in text[i:end]];i=end;continue
            m=re.match(r'\\verb\*?([^\w\s])',text[i:])
            if m:
                end=text.find(m.group(1),i+m.end());require(end>=0,'Unclosed verb expression.');end+=1
                out[i:end]=' '*(end-i);i=end;continue
        i+=1
    return ''.join(out)


def balanced(text: str, start: int, left='{', right='}') -> tuple[str,int]:
    require(start<len(text) and text[start]==left,'Expected a balanced LaTeX argument.')
    masked=strip_comments(text); depth=0
    for i in range(start,len(text)):
        if masked[i] in (left,right):
            k=i-1
            while k>=0 and masked[k]=='\\':k-=1
            if (i-1-k)%2:continue
            depth += 1 if masked[i]==left else -1
            if depth==0:return text[start+1:i],i+1
    raise WorkspaceError('Unclosed LaTeX argument; source not modified.')


def commands(text: str, names: str) -> list[dict]:
    masked=strip_comments(text);out=[]
    for m in re.finditer(r'\\('+names+r')(?![A-Za-z@])\*?',masked):
        previous=m.start()-1
        while previous>=0 and masked[previous]=='\\':previous-=1
        if (m.start()-1-previous)%2:continue
        i=m.end()
        while i<len(text) and masked[i].isspace():i+=1
        optional=[]
        while i<len(text) and masked[i]=='[':
            value,i=balanced(text,i,'[',']');optional.append(value)
            while i<len(text) and masked[i].isspace():i+=1
        if i<len(text) and masked[i]=='{':
            value,end=balanced(text,i)
            out.append({'name':m.group(1),'start':m.start(),'end':end,'value':value,'optional':optional,'raw':text[m.start():end]})
    return out


def document(text: str) -> tuple[str,str,str]:
    masked=strip_comments(text)
    starts=list(re.finditer(r'\\begin\s*\{document\}',masked));ends=list(re.finditer(r'\\end\s*\{document\}',masked))
    require(len(starts)==1 and len(ends)==1 and starts[0].end()<ends[0].start(),'Exactly one literal document environment is required.')
    return text[:starts[0].start()],text[starts[0].end():ends[0].start()],text[ends[0].end():]


def expand(files: dict[str,bytes], main: str, stack=()) -> str:
    require(main in files and len(stack)<30 and main not in stack,'Missing/cyclic/excessive LaTeX input: '+main)
    try:text=files[main].decode('utf-8-sig')
    except UnicodeError as exc:raise WorkspaceError('Convert LaTeX source to UTF-8 explicitly.') from exc
    require(not DYNAMIC.search(strip_comments(text)),'Dynamic imports or executable TeX require a reviewed adapter before automatic migration.')
    replacements=[]
    for item in commands(text,'input|include'):
        value=item['value'].strip()
        require(re.fullmatch(r'[A-Za-z0-9 _./-]+',value) is not None,'Computed input path is unsupported.')
        if not Path(value).suffix:value+='.tex'
        # TeX inputs are resolved from the compilation working directory, not from
        # the containing input file. Do not silently guess a different base path.
        require('..' not in Path(value).parts and not Path(value).is_absolute(),'Input escapes manuscript.')
        replacement=expand(files,value,(*stack,main))
        if item['name']=='include':replacement='\n\\clearpage\n'+replacement+'\n\\clearpage\n'
        replacements.append((item['start'],item['end'],replacement))
    for a,b,value in reversed(replacements):text=text[:a]+value+text[b:]
    require(len(text.encode())<=2*1024*1024,'Expanded manuscript exceeds 2 MiB.')
    return text


def block(key: str,text: str)->str:
    return '% rw:section '+key+'\n'+text+'\n% /rw:section '+key


def parse(text: str)->tuple[dict[str,str],str]:
    sections={}
    for m in MARKERS.finditer(text):
        require(m.group(1) not in sections,'Duplicate LaTeX section marker.')
        sections[m.group(1)]=m.group(2)
    outside=MARKERS.sub('',text)
    require('% rw:section' not in outside and '% /rw:section' not in outside,'Malformed LaTeX section markers.')
    return sections,outside


def active_dir(store: Store)->Path|None:
    config=store.state['project'].get('latex')
    return safe_path(store.root,config['directory']) if config else None


def snapshot(store: Store)->dict:
    config=store.state['project'].get('latex');require(config,'No active native LaTeX manuscript. Run latex adopt.')
    folder=active_dir(store);files=tree_bytes(folder)
    require(config['main'] in files,'Active LaTeX main file is missing.')
    sections,locations,outside,texts={},{},{},{}
    for name,data in sorted(files.items()):
        if name.endswith('.tex'):
            try:text=data.decode('utf-8')
            except UnicodeError as exc:raise WorkspaceError('Expected UTF-8 LaTeX.') from exc
            found,remainder=parse(text);texts[name]=text
            for key,value in found.items():
                require(key not in sections,'Section marker duplicated across files: '+key)
                sections[key]=value;locations[key]=name
            outside[name]=sha(remainder.encode())
        else:outside[name]=sha(data)
    return {'sections':sections,'locations':locations,'outside':outside,'texts':texts,'files':{n:sha(b) for n,b in files.items()}}


def read_manuscript(store: Store)->str:
    if not active_dir(store):return read_text(safe_path(store.root,'manuscript/main.md'))
    config=store.state['project']['latex'];return expand(tree_bytes(active_dir(store)),config['main'])


def route_text(store: Store)->str:
    if not active_dir(store):return read_manuscript(store)
    snap=snapshot(store)
    from .sync import block as md_block
    return '\n'.join(md_block(k,v) for k,v in snap['sections'].items())+'\n'+digest(snap['outside'])


def adopt(store: Store,directory: str,main: str,actor: str,*,approve=False)->dict:
    require(directory.startswith('manuscript/') and not directory.endswith('/'),'Native manuscript must be below manuscript/.')
    folder=safe_path(store.root,directory);files=tree_bytes(folder);require(main in files,'Main file missing.')
    original=files[main].decode('utf-8');pre,body,tail=document(original)
    # Existing multi-file LaTeX is flattened once into a *new* generated body file;
    # original files remain in place, and the old main is archived outside the upload.
    expanded=expand(files,main);pre,body,tail=document(expanded)
    require('% rw:section' not in body,'Already marked source; use native sync instead of adopting twice.')
    chunks=[];heads=commands(body,'section')
    boundaries=[0]+[x['start'] for x in heads if x['start']>0]+[len(body)]
    for i,(a,b) in enumerate(zip(boundaries,boundaries[1:])):
        text=body[a:b].strip('\n');
        if not text.strip():continue
        heading=next((h['value'] for h in heads if a==h['start']), 'Front matter')
        key='SEC-LTX-'+digest([directory,heading,i])[:10].upper()
        chunks.append((key,heading,text))
    require(chunks,'Empty manuscript body.')
    generated='rw-content.tex';require(generated not in files,'rw-content.tex already exists; no overwrite.')
    rewritten=pre+'\\begin{document}\n\\input{rw-content}\n\\end{document}'+tail
    result={'directory':directory,'main':main,'section_ids':[c[0] for c in chunks],
            'retiring_sections':[k for k,n in store.state['nodes'].items() if n['kind']=='section' and n['status']!='retired'],
            'boundary':'Original Markdown and source files retained. Section text becomes raw LaTeX; scientific review remains required.'}
    if not approve:return result
    backup='workspace/history/latex/'+identifier('ADOPT')+'.json'
    old_sections=copy.deepcopy({k:n for k,n in store.state['nodes'].items() if n['kind']=='section'})
    for n in store.state['nodes'].values():
        if n['kind']=='section':n['status']='retired'
    for key,title,text in chunks:
        store.state['nodes'][key]=make_node(key,'section',title,{'text':text,'format':'latex','latex_owner':directory},['ARG-001'] if 'ARG-001' in store.state['nodes'] else [])
    store.state['project']['latex']={'directory':directory,'main':main,'adopted_at':now()}
    # Compute the future baseline without claiming semantic verification.
    future={**files,main:rewritten.encode(),generated:('\n\n'.join(block(k,t) for k,_,t in chunks)+'\n').encode()}
    outside={}
    for name,data in future.items():
        outside[name]=sha(parse(data.decode())[1].encode()) if name.endswith('.tex') else sha(data)
    store.state['sync']={'format':'latex','sections':{k:t for k,_,t in chunks},'outside_hash':digest(outside)}
    add_issue(store,'MANUSCRIPT','Native LaTeX adopted: reconcile imported sections with Claims, metadata, citations and venue rules; imported text is draft.','manuscript-sync','major',commit=False)
    store.event('latex.adopted',actor,result)
    writes={directory+'/'+main:rewritten,directory+'/'+generated:future[generated].decode(),backup:pretty({'original_main':original,'previous_sections':old_sections,'mapping':result})}
    store.commit(writes,{name:file_hash(safe_path(store.root,name)) for name in writes})
    return {**result,'adopted':True,'backup':backup}


def plan(store: Store)->dict:
    snap=snapshot(store);baseline=store.state['sync'];active={k:n for k,n in store.state['nodes'].items() if n['kind']=='section' and n['status']!='retired'}
    require(set(active)==set(snap['sections']),'Native section IDs differ from research nodes; reconcile structure explicitly.')
    changes,conflicts,semantic=[],[],[]
    for key,node in active.items():
        ws,ms,base=node['data']['text'],snap['sections'][key],baseline.get('sections',{}).get(key)
        if ws==ms:
            if base!=ws:changes.append({'section':key,'direction':'acknowledge','before':base,'after':ws});semantic.append(key)
        elif ws==base:changes.append({'section':key,'direction':'manuscript-to-workspace','before':ws,'after':ms});semantic.append(key)
        elif ms==base:changes.append({'section':key,'direction':'workspace-to-manuscript','before':ms,'after':ws})
        else:conflicts.append({'section':key,'base':base,'workspace':ws,'manuscript':ms})
    return {'changes':changes,'conflicts':conflicts,'semantic_review':semantic,'outside_changed':digest(snap['outside'])!=baseline.get('outside_hash'),
            'manuscript_text':read_manuscript(store),'outside':snap['outside'],'native_snapshot':snap}


def propose_sync(store: Store,actor: str,resolutions=None,acknowledge_outside=False)->dict:
    report=plan(store);choices=resolutions or {};conflicts={x['section'] for x in report['conflicts']}
    require(set(choices)==conflicts and all(v in ('workspace','manuscript') for v in choices.values()),'Resolve every native LaTeX conflict explicitly.')
    require(not report['outside_changed'] or acknowledge_outside,'Unmapped LaTeX/preamble/bibliography/assets changed; inspect and acknowledge outside edits.')
    require(report['changes'] or conflicts or report['outside_changed'],'Already synchronized.')
    snap=report['native_snapshot'];texts=dict(snap['texts']);semantic=set(report['semantic_review']);operations=[];final=dict(snap['sections'])
    changes=report['changes']+[{'section':x['section'],'direction':'manuscript-to-workspace' if choices[x['section']]=='manuscript' else 'workspace-to-manuscript','after':x[choices[x['section']]]} for x in report['conflicts']]
    for c in changes:
        k=c['section'];final[k]=c['after']
        if c['direction']=='manuscript-to-workspace':
            node=copy.deepcopy(store.node(k));node['data']['text']=c['after'];operations.append({'op':'upsert','node':node})
        elif c['direction']=='workspace-to-manuscript':
            name=snap['locations'][k];texts[name]=texts[name].replace(block(k,snap['sections'][k]),block(k,c['after']),1)
    config=store.state['project']['latex'];changed=[n for n in texts if texts[n]!=snap['texts'][n]]
    if not changed:changed=[config['main']]
    for name in changed:
        relative=config['directory']+'/'+name
        operations.append({'op':'write','path':relative,'text':texts[name],'expected_sha256':file_hash(safe_path(store.root,relative))})
    semantic.update(conflicts)
    if report['outside_changed']:semantic.add('MANUSCRIPT')
    item=propose(store,operations,actor,'Synchronize native LaTeX sections with research state')
    item['sync_commit']={'baseline':{'format':'latex','sections':final,'outside_hash':digest(report['outside'])},'semantic_review':sorted(semantic)}
    store.state['proposals'][item['id']]=item;store.event('sync.proposed',actor,{'id':item['id'],'format':'latex'});store.commit();return item


def inventory(text: str)->dict:
    result={}
    for label,names in [('citations','cite|citep|citet|autocite|parencite|textcite'),('labels','label'),('references','ref|eqref|autoref|cref|Cref')]:
        result[label]=dict(Counter(value.strip() for item in commands(text,names) for value in item['value'].split(',') if value.strip()))
    result['graphics']=[x['value'] for x in commands(text,'includegraphics')]
    return result


def bibliography_keys(files: dict[str,bytes])->set[str]:
    return {m.group(1) for name,data in files.items() if name.endswith('.bib') for m in re.finditer(r'@\w+\s*\{\s*([^,\s]+)\s*,',data.decode('utf-8','replace'))}


def transfer(store: Store,source: str,source_main: str,target_id: str,actor: str,*,approve=False)->dict:
    from .venues import get
    require(source.startswith('manuscript/'),'Migration source must be in manuscript/.')
    source_dir=safe_path(store.root,source);source_files=tree_bytes(source_dir)
    require(source_main in source_files,'Migration source main missing.')
    entry=get(store,target_id);template=tree_bytes(safe_path(store.root,entry['template_dir']))
    template.pop('template-provenance.json',None)
    target_main=entry['main'];require(target_main in template,'Target template main missing.')
    src=expand(source_files,source_main);old_pre,body,tail=document(src)
    target_source=template[target_main].decode('utf-8');new_pre,_,_=document(target_source)
    classes=commands(new_pre,'documentclass');require(len(classes)==1,'Target needs exactly one documentclass.')
    family=classes[0]['value'];supported={'article','acmart','IEEEtran','vgtc','llncs','elsarticle'}
    require(family in supported,'No tested adapter for target class '+family+'; provide a reviewed wrapper rather than guessing.')
    # Preserve title and abstract, without carrying old publisher author/rights metadata.
    titles=commands(src,'title');title=titles[0]['value'] if titles else 'TITLE REQUIRES REVIEW'
    masked=strip_comments(body);abstract='';m=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',masked,re.S)
    if m:abstract=body[m.start(1):m.end(1)];body=body[:m.start()]+body[m.end():]
    else:
        abs_commands=commands(old_pre,'abstract')
        if abs_commands:abstract=abs_commands[0]['value']
    # Remove only structural front/bibliography commands, retaining their source in
    # a research-history record outside the upload. Never delete prose to meet length.
    removals=commands(body,'title|author|affiliation|email|institute|address|ead|date|bibliographystyle|bibliography|addbibresource')
    bibs=[x['value'] for x in removals if x['name']=='bibliography']
    if not bibs:bibs=[Path(n).with_suffix('').as_posix() for n in source_files if n.endswith('.bib')]
    for item in reversed(removals):body=body[:item['start']]+body[item['end']:]
    for item in reversed(list(re.finditer(r'\\(?:maketitle|printbibliography)\b',strip_comments(body)))):
        body=body[:item.start()]+body[item.end():]
    for item in reversed(list(re.finditer(r'\\(?:begin|end)\{frontmatter\}',strip_comments(body)))):
        body=body[:item.start()]+body[item.end():]
    # Remove only our section marker comments when moving to a fresh binding.
    body=re.sub(r'^% /?rw:section .*\n?','',body,flags=re.M)
    before=inventory(src);after=inventory(body+'\n'+abstract)
    # Citations and labels in author/front matter are unusual: stop rather than drop.
    for key in ('citations','labels','references','graphics'):
        require(before[key]==after[key],'Migration would alter '+key+' inventory; a reviewed custom mapping is required.')
    inline_keys={x['value'] for x in commands(src,'bibitem')}
    missing=sorted(set(after['citations'])-(bibliography_keys(source_files)|inline_keys))
    require(not missing,'Unresolved bibliography keys in source: '+', '.join(missing))
    blockers=[]
    if re.search(r'\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{[^}]*(?:geometry|fullpage|titlesec|fancyhdr|authblk|caption|biblatex)',strip_comments(old_pre)):
        blockers.append('Source has layout/author/bibliography packages requiring target-specific adaptation.')
    if re.search(r'\\(?:def|newenvironment|renewenvironment|let|Declare)',strip_comments(old_pre)):
        blockers.append('Inspect custom environment/primitive definitions from the archived source preamble.')
    # Carry macro declarations only when they can be isolated with balanced arguments.
    macros=[]
    for item in commands(old_pre,'newcommand|renewcommand|providecommand'):
        i=item['end'];masked_pre=strip_comments(old_pre)
        while i<len(old_pre) and masked_pre[i].isspace():i+=1
        for _ in range(2):
            if i<len(old_pre) and masked_pre[i]=='[':
                _,i=balanced(old_pre,i,'[',']')
                while i<len(old_pre) and masked_pre[i].isspace():i+=1
        if i<len(old_pre) and masked_pre[i]=='{':
            _,end=balanced(old_pre,i);macros.append(old_pre[item['start']:end])
        else:blockers.append('A nonstandard macro definition needs manual porting.')
    options=entry['profile']['template'].get('class_options')
    require(isinstance(options,str),'Target template.class_options must be explicitly selected for the venue/track/stage; empty string is permitted.')
    require(not any(c in options for c in '{}\\\n\r'),'Invalid class options.')
    classline='\\documentclass'+('['+options+']' if options else '')+'{'+family+'}\n'
    # Only portable packages. Specialized source packages are preserved for review.
    packages=['graphicx','amsmath','booktabs'] + ([] if family=='acmart' else ['amssymb'])
    for c in commands(old_pre,'usepackage'):
        for name in c['value'].split(','):
            if name.strip() not in packages and name.strip() not in {'inputenc','fontenc','hyperref','cite','natbib'}:
                blockers.append('Review package: '+name.strip())
    pre=classline+''.join('\\usepackage{'+p+'}\n' for p in packages)+'\n'.join(macros)+'\n'
    if family=='acmart':
        # ACM class defaults contain example DOI/ISBN and publication metadata.
        # A transfer draft must not present those examples as the user's publication.
        pre += '\\settopmatter{printacmref=false}\n\\setcopyright{none}\n\\acmDOI{}\n\\acmISBN{}\n'
        blockers.append('ACM draft suppresses default publication metadata. Set real rights, DOI, ISBN and reference-format fields only from the target venue before camera-ready.')
    anonym=entry['profile'].get('anonymous',True)
    author='Anonymous authors' if anonym else 'AUTHOR AND AFFILIATION REQUIRE REVIEW'
    bstyle=entry['profile']['template'].get('bibliography_style')
    require(isinstance(bstyle,str) and re.fullmatch(r'[A-Za-z0-9_./-]+',bstyle),'Explicit safe target bibliography_style required.')
    bib='\\bibliographystyle{'+bstyle+'}\n\\bibliography{'+','.join(bibs)+'}\n' if bibs else ''
    metadata='\\title{'+title+'}\n\\author{'+author+'}\n'
    if family=='llncs': metadata+='\\institute{'+('Anonymous institution' if anonym else 'AFFILIATION REQUIRES REVIEW')+'}\n'
    ab='\\begin{abstract}\n'+abstract+'\n\\end{abstract}\n' if abstract.strip() else ''
    if family=='vgtc':
        wrapper=pre+metadata+'\\abstract{'+abstract+'}\n\\begin{document}\n\\maketitle\n\\input{rw-transfer-body}\n'+bib+'\\end{document}\n'
    elif family=='elsarticle':
        wrapper=pre+'\\begin{document}\n\\begin{frontmatter}\n'+metadata+ab+'\\end{frontmatter}\n\\input{rw-transfer-body}\n'+bib+'\\end{document}\n'
    else:
        front=metadata+ab+'\\maketitle\n' if family=='acmart' else metadata+'\\maketitle\n'+ab
        wrapper=pre+'\\begin{document}\n'+front+'\\input{rw-transfer-body}\n'+bib+'\\end{document}\n'
    dest='manuscript/latex/'+target_id+'-transfer-'+identifier('V').split('-')[1].lower()
    # Keep target class/style assets, source bibliography/figures/data byte-for-byte.
    output={n:b for n,b in template.items() if not n.endswith(('.tex','.bib')) and n!='template-provenance.json'}
    for name,data in source_files.items():
        if name.endswith(('.tex','.cls','.sty','.bst','.bbx','.cbx','.cfg','.def','.dtx','.ins')):continue
        if name in output and output[name]!=data:raise WorkspaceError('Target/source asset collision: '+name)
        output[name]=data
    output['main.tex']=wrapper.encode();output['rw-transfer-body.tex']=body.encode()
    record={'source':source,'source_main':source_main,'target':target_id,'destination':dest,'class':family,'source_files':{n:sha(b) for n,b in source_files.items()},
            'output_files':{n:sha(b) for n,b in output.items()},'inventories':after,'blockers':sorted(set(blockers)),
            'required_checks':['target rules/track/stage','author metadata and anonymization including acknowledgments, images and supplements','page/word limit','package/macro compatibility','actual compile and rendered PDF','cross references and citations','independent scientific review'],
            'status':'migration-draft-not-submission-ready','source_untouched':True}
    if not approve:return record
    require(tree_bytes(source_dir)==source_files,'Source changed during migration; retry.')
    new_tree(store.root,dest,output)
    history='workspace/history/transfers/'+identifier('TRANSFER')+'.json'
    issue=add_issue(store,'MANUSCRIPT','Transfer created '+dest+'. Resolve migration report '+history+'; compile, check current target rules and review all metadata/limits before activation.','venue-transfer','major',commit=False)
    store.event('venue.transferred',actor,{'record':history,'destination':dest,'issue':issue['id']})
    store.commit({history:pretty({**record,'source_preamble':old_pre,'source_main_original':source_files[source_main].decode('utf-8')})},{history:None})
    return {**record,'created':True,'record':history,'issue':issue['id']}


def build(store: Store,directory: str|None=None,main: str|None=None,*,allow_exec=False,engine='pdflatex',timeout=90)->dict:
    require(allow_exec,'Compilation executes TeX. Review sources first and pass --allow-exec. This is not a security sandbox.')
    require(engine in ('pdflatex','xelatex','lualatex') and 1<=timeout<=300,'Unsupported engine/timeout.')
    config=store.state['project'].get('latex',{})
    directory=directory or config.get('directory');main=main or config.get('main')
    require(directory and main and directory.startswith('manuscript/'),'Specify the manuscript directory and main file.')
    folder=safe_path(store.root,directory);files=tree_bytes(folder);require(main in files,'Main file missing.')
    require(main.endswith('.tex'), 'Build main must be an explicit .tex source path relative to the manuscript root.')
    executable=shutil.which(engine);require(executable,'Install a TeX distribution providing '+engine)
    # No .latexmkrc, shell escape, private workspace data or credentials enter build dir.
    build_id=identifier('BUILD');work=safe_path(store.root,'.rw/builds/'+build_id,governed=False);work.mkdir(parents=True)
    for name,data in files.items():
        p=safe_path(work,name,governed=False);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    env={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','LANG')}
    env.update(HOME=str(work),openin_any='p',openout_any='p',shell_escape='f')
    logs=[];ok=True
    sequence=[[executable,'-no-shell-escape','-halt-on-error','-interaction=nonstopmode','./'+main]]
    for iteration in range(3):
        try:run=subprocess.run(sequence[0],cwd=work,env=env,capture_output=True,timeout=timeout,check=False)
        except subprocess.TimeoutExpired:ok=False;logs.append('TeX timeout.');break
        logs.append(run.stdout.decode('utf-8','replace')[-32000:]);ok=run.returncode==0
        if not ok:break
        if iteration==0:
            aux=work/(Path(main).stem+'.aux')
            if aux.exists() and '\\bibdata{' in aux.read_text(errors='replace'):
                bibtex=shutil.which('bibtex') or shutil.which('bibtex.original')
                if not bibtex:ok=False;logs.append('bibtex missing.');break
                try:run=subprocess.run([bibtex,Path(main).stem],cwd=work,env=env,capture_output=True,timeout=timeout,check=False)
                except subprocess.TimeoutExpired:ok=False;logs.append('BibTeX timeout.');break
                logs.append(run.stdout.decode('utf-8','replace')[-16000:]);ok=run.returncode==0
                if not ok:break
    pdf=work/(Path(main).stem+'.pdf');last=logs[-1] if logs else ''
    unresolved=bool(re.search(r'undefined references|undefined citations|Citation .+ undefined|Reference .+ undefined',last,re.I))
    result={'build_id':build_id,'directory':directory,'main':main,'engine':engine,'at':now(),'compiled':bool(ok and pdf.exists()),'unresolved_references':unresolved,
            'sources':{n:sha(b) for n,b in files.items()},'pdf':str(pdf.relative_to(store.root)) if pdf.exists() else None,'pdf_sha256':file_hash(pdf) if pdf.exists() else None,
            'boundary':'Actual local TeX compile; inspect PDF, scientific meaning and venue rules separately.'}
    atomic_write(work/'build-log.txt','\n\n'.join(logs));atomic_write(work/'receipt.json',pretty(result))
    atomic_write(safe_path(store.root,'.rw/latex-last-build.json',governed=False),pretty(result))
    require(tree_bytes(folder)==files,'Manuscript changed while compiling; result is stale.')
    return result


def integrity_issues(store: Store)->list[dict]:
    if not active_dir(store):return []
    issues=[]
    def add(code,msg):issues.append({'code':code,'node':'MANUSCRIPT','message':msg,'severity':'major','domain':'rules_compliance'})
    path=safe_path(store.root,'.rw/latex-last-build.json',governed=False)
    if not path.exists():add('LATEX_BUILD_MISSING','Compile the active native LaTeX source and inspect its PDF.');return issues
    receipt=json.loads(read_text(path));config=store.state['project']['latex']
    if receipt.get('directory')!=config['directory'] or receipt.get('main')!=config['main'] or receipt.get('sources')!={n:sha(b) for n,b in tree_bytes(active_dir(store)).items()}:
        add('LATEX_BUILD_STALE','LaTeX source changed since the last build.')
    pdf = receipt.get('pdf')
    if not pdf or file_hash(safe_path(store.root,pdf,governed=False)) != receipt.get('pdf_sha256'):add('LATEX_PDF_CHANGED','Compiled PDF is missing or changed; rebuild and inspect it.')
    if not receipt.get('compiled') or receipt.get('unresolved_references'):add('LATEX_BUILD_FAILED','Resolve compilation/citation/reference errors.')
    return issues


def pack(store: Store, output: str, directory: str|None=None)->dict:
    """New manuscript-only ZIP for Overleaf upload, never include .rw or research history."""
    import zipfile
    from .overleaf import managed
    config=store.state['project'].get('latex',{})
    directory=directory or config.get('directory')
    require(directory and directory.startswith('manuscript/'),'Select an explicit manuscript directory.')
    folder=safe_path(store.root,directory);files=tree_bytes(folder)
    require(files and all(managed(n) for n in files),'Unsafe or empty manuscript upload scope.')
    destination=Path(output).expanduser().resolve()
    require(not destination.exists() and not destination.is_relative_to(folder),'ZIP must be new and outside its own source directory.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
    return {'zip':str(destination),'sha256':file_hash(destination),'files':{n:sha(b) for n,b in files.items()},'boundary':'Manuscript source only; metadata/anonymity and upload permission still require review.'}
