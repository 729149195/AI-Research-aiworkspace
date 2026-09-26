"""Source-bound venue discovery, templates and versioned submission-rule dossiers."""
from __future__ import annotations
import copy
import difflib
import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from .model import WorkspaceError, digest, identifier, now, pretty, require
from .store import Store, file_hash, read_text, safe_path
from .workflow import add_issue
from .publication_io import download, new_tree, page_text, public_url, sha, unpack

TOPICS = {
    'scope_track': r'scope|track|topic|主题|范围',
    'format_length': r'format|template|page|word limit|页|模板',
    'anonymity': r'anonym|blind|匿名',
    'deadlines': r'deadline|due|submission date|截止',
    'submission_portal': r'submission system|submit.*(?:https|portal)|PCS|投稿系统',
    'supplementary': r'supplement|artifact|appendi|video|附录|补充',
    'ethics_consent': r'ethic|consent|human participant|IRB|伦理',
    'ai_policy': r'generative|artificial intelligence|AI-generated|AI policy|AI 使用',
    'originality_resubmission': r'original|resubmi|concurrent|plagiar|转投|重复投稿',
    'copyright_license': r'copyright|licen[cs]e|rights|版权',
    'fees_registration': r'fee|charge|registration|open access|注册费',
    'review_camera_ready': r'rebuttal|notification|camera.ready|review process|终稿',
    'references_accessibility': r'reference|citation|accessib|description|参考文献',
}
# Discovery seeds only. Every use fetches the live page; no stale deadline is baked in.
SEEDS = {
    ('ieee vis', 2026): ['https://ieeevis.org/year/2026/info/call-participation/paper-submission-guidelines/', 'https://tc.computer.org/vgtc/publications/journal/'],
    ('vis', 2026): ['https://ieeevis.org/year/2026/info/call-participation/paper-submission-guidelines/', 'https://tc.computer.org/vgtc/publications/journal/'],
    ('acm', 2026): ['https://www.acm.org/publications/proceedings-template'],
}
INDEX = 'workspace/venues/index.json'


def validate_profile(p: dict) -> None:
    require(isinstance(p, dict) and p.get('profile_version') == 1, 'Expected a version-1 venue profile JSON.')
    require(isinstance(p.get('id'), str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', p['id']), 'Use a portable unique venue id, e.g. vis-2026-full-review.')
    require(isinstance(p.get('name'), str) and p['name'].strip(), 'Venue name required.')
    require(type(p.get('year')) is int and 2000 <= p['year'] <= 2200, 'Explicit venue edition year required.')
    require(isinstance(p.get('track'), str) and p['track'].strip(), 'Explicit track/article type required.')
    require(p.get('stage') in ('review','camera-ready','preprint'), 'Specify review, camera-ready, or preprint stage.')
    sources = p.get('sources')
    require(isinstance(sources, list) and 1 <= len(sources) <= 12, 'Provide 1-12 primary policy sources.')
    ids = set()
    for s in sources:
        require(isinstance(s, dict) and re.fullmatch(r'[a-z][a-z0-9-]{0,40}', s.get('id','')), 'Invalid source ID.')
        require(s['id'] not in ids, 'Duplicate source id.'); ids.add(s['id'])
        require(s.get('role') in ('venue','publisher','template'), 'Source role must be venue, publisher or template.')
        require(isinstance(s.get('url'), str) and urllib.parse.urlsplit(s['url']).hostname, 'Original source URL required.')
    require(any(s['role'] == 'venue' for s in sources), 'Include the specific venue/track policy page, beyond the generic publisher template.')
    t = p.get('template')
    require(isinstance(t, dict) and isinstance(t.get('url'), str), 'Provide the actual template ZIP URL discovered from official sources.')
    require(isinstance(t.get('license_note'), str) and t['license_note'].strip(), 'Record the template license or unresolved rights; do not assign the framework MIT license.')
    require(isinstance(p.get('allowed_hosts', []), list), 'allowed_hosts must be a list.')
    if p.get('submission_year') is not None:
        require(type(p['submission_year']) is int and 2000 <= p['submission_year'] <= 2200, 'Invalid submission year.')
    for r in p.get('requirements', []):
        require(r.get('topic') in TOPICS and r.get('source') in ids and r.get('quote'), 'Requirements need topic, source ID and exact quote.')
    for d in p.get('deadlines', []):
        require(d.get('source') in ids and d.get('quote') and d.get('label'), 'Deadlines need a source, exact quote and label.')
        if d.get('at'):
            value = datetime.fromisoformat(d['at'].replace('Z','+00:00'))
            require(value.utcoffset() is not None, 'Exact deadlines need an explicit UTC offset; do not infer midnight or a timezone.')


def hosts_for(p: dict) -> set[str]:
    urls = [s['url'] for s in p['sources']] + [p['template']['url']]
    if p['template'].get('overleaf_url'): urls.append(p['template']['overleaf_url'])
    return {urllib.parse.urlsplit(u).hostname for u in urls} | set(p.get('allowed_hosts', []))


def source_dossier(p: dict, *, online=False, sources_dir: str | Path | None = None, transport=None, strict_quotes=True) -> dict:
    records = []
    for source in p['sources']:
        if sources_dir:
            folder = Path(sources_dir).expanduser().resolve()
            raw_path = safe_path(folder, source['id'] + '.txt', governed=False)
            data = read_text(raw_path).encode('utf-8')
            meta = {'url': source['url'], 'sha256': sha(data), 'retrieval': 'user-supplied-offline-extract', 'live_fetched': False}
            text = data.decode()
        else:
            data, meta = download(source['url'], hosts_for(p), online=online, transport=transport, limit=4*1024*1024)
            text, _ = page_text(data, meta.get('content_type',''))
            meta['live_fetched'] = True
        require(text.strip(), 'Empty policy source: ' + source['id'])
        records.append({**source, **meta, 'text': text, 'text_sha256': sha(text.encode()), 'retrieved_at': now(),
                        'edition_mentioned': str(p['year']) in text, 'status': 'retrieved-unreviewed'})
    by_id = {s['id']: s for s in records}
    invalid_quotes = []
    for r in p.get('requirements', []) + p.get('deadlines', []):
        if r['quote'] not in by_id[r['source']]['text']:
            invalid_quotes.append(copy.deepcopy(r))
            require(not strict_quotes, 'Requirement/deadline quote absent from source: ' + r['source'])
    coverage = {}
    for topic, pattern in TOPICS.items():
        passages = []
        for s in records:
            for number, line in enumerate(s['text'].splitlines(), 1):
                if re.search(pattern, line, re.I):
                    passages.append({'source': s['id'], 'line': number, 'text': line[:1600], 'truncated': len(line)>1600})
        coverage[topic] = {'status': 'candidate-passages' if passages else 'unknown', 'passages': passages[:20],
                           'more_passages': len(passages)>20}
    return {'version': 1, 'venue': {k: p.get(k) for k in ('id','name','year','submission_year','track','stage')},
            'retrieved_at': now(), 'sources': records, 'coverage': coverage,
            'requirements': [copy.deepcopy(r) for r in p.get('requirements', []) if r not in invalid_quotes], 'deadlines': [copy.deepcopy(d) for d in p.get('deadlines', []) if d not in invalid_quotes],
            'invalidated_structured_entries': invalid_quotes,
            'status': 'requires-review', 'boundary': 'Captured sources and candidate passages; year mentions and exact quote matching do not establish applicability or completeness.'}


def deadline_status(d: dict, at: datetime | None = None) -> str:
    if not d.get('at'): return 'time-or-timezone-unresolved'
    value = datetime.fromisoformat(d['at'].replace('Z','+00:00'))
    require(value.utcoffset() is not None, 'Timezone missing.')
    return 'past' if value < (at or datetime.now(timezone.utc)) else 'upcoming'


def calendar(dossier: dict) -> str:
    def esc(t): return str(t).replace('\\','\\\\').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
    lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//AI Research Workspace//Venue deadlines//EN']
    for d in dossier['deadlines']:
        if not d.get('at'): continue
        dt = datetime.fromisoformat(d['at'].replace('Z','+00:00')).astimezone(timezone.utc)
        lines += ['BEGIN:VEVENT', 'UID:'+digest([dossier['venue']['id'],d])+'@aiworkspace.local',
                  'DTSTAMP:'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'), 'DTSTART:'+dt.strftime('%Y%m%dT%H%M%SZ'),
                  'SUMMARY:'+esc(dossier['venue']['name']+' — '+d['label']), 'STATUS:TENTATIVE',
                  'DESCRIPTION:'+esc('Source-bound candidate; verify current official deadline. '+d['quote']), 'END:VEVENT']
    return '\r\n'.join(lines+['END:VCALENDAR',''])


def render_dossier(d: dict) -> str:
    v = d['venue']
    text = f"# {v['name']} {v['year']} — {v['track']} / {v['stage']}\n\n检索时间：{d['retrieved_at']}\n\n"
    text += '**状态：待核对适用性和完整性。模板年份、会议届次、实际投稿年份分别记录。**\n\n'
    for deadline in d['deadlines']:
        text += f"- {deadline['label']}: `{deadline.get('at') or '时间/时区待核查'}` ({deadline_status(deadline)}), 来源 {deadline['source']}\n"
    for topic, item in d['coverage'].items():
        text += '\n## '+topic+' — '+item['status']+'\n\n'
        for p in item['passages']:
            text += f"{p['source']}:{p['line']} — {p['text']}\n\n"
    text += '\n## 原始来源\n\n' + '\n'.join(f"- {s['id']}: {s['url']}；SHA256 `{s['sha256']}`；{s['retrieved_at']}" for s in d['sources'])
    return text+'\n'


def index(store: Store) -> dict:
    path = safe_path(store.root, INDEX)
    return json.loads(read_text(path)) if path.exists() else {'version':1,'venues':{}}


def get(store: Store, venue_id: str) -> dict:
    entries = index(store)['venues']; require(venue_id in entries, 'Unknown venue; run venue init first.')
    return entries[venue_id]


def detect_main(files: dict[str, bytes], selected: str | None = None) -> str:
    from .latex_project import strip_comments
    candidates = [n for n,b in files.items() if n.endswith('.tex') and re.search(r'\\documentclass(?:\s*\[[^\]]*\])?\s*\{', strip_comments(b.decode('utf-8','replace')))]
    if selected:
        require(selected in candidates, 'Selected main is missing or does not declare a document class.'); return selected
    require(len(candidates)==1, 'Template has multiple/no main files; set template.main explicitly. Candidates: '+', '.join(candidates))
    return candidates[0]


def install(store: Store, p: dict, actor: str, *, approve=False, online=False, archive: str | Path | None = None, sources_dir=None, transport=None) -> dict:
    validate_profile(p)
    require(approve, 'Review venue/profile/download scope, then supply --approve.')
    old = index(store); require(p['id'] not in old['venues'], 'Venue version already installed; refresh rules or use a new venue id.')
    dossier = source_dossier(p, online=online, sources_dir=sources_dir, transport=transport)
    if archive:
        path = Path(archive).expanduser().resolve(); require(path.is_file() and path.stat().st_size<=32*1024*1024, 'Invalid local template archive.')
        raw = path.read_bytes(); meta = {'url':p['template']['url'], 'sha256':sha(raw), 'retrieval':'user-supplied-archive'}
    else:
        raw, meta = download(p['template']['url'], hosts_for(p), online=online, transport=transport)
    if p['template'].get('sha256'): require(sha(raw)==p['template']['sha256'], 'Template hash changed; review the upstream version explicitly.')
    files, skipped = unpack(raw)
    main = detect_main(files, p['template'].get('main'))
    template_dir = 'workspace/venues/'+p['id']+'/template'
    working_dir = 'manuscript/latex/'+p['id']
    rules_dir = 'workspace/rules/venues/'+p['id']+'/revision-001'
    for path in (template_dir, working_dir, rules_dir): require(not safe_path(store.root, path).exists(), 'Existing publication directory: '+path)
    manifest = {**meta,'main':main,'files':{n:sha(b) for n,b in files.items()},'skipped_execution_or_unrecognized_files':skipped,
                'overleaf_url':p['template'].get('overleaf_url'), 'license_note':p['template']['license_note']}
    # All network/ZIP/source checks precede writes. New version directories never replace prior work.
    new_tree(store.root, template_dir, {**files,'template-original.zip':raw,'template-provenance.json':pretty(manifest).encode()})
    new_tree(store.root, working_dir, files)
    rule_files = {'dossier.json':pretty(dossier).encode(),'SUBMISSION_RULES.md':render_dossier(dossier).encode(),'deadlines.ics':calendar(dossier).encode()}
    rule_files.update({'sources/'+s['id']+'.txt':s['text'].encode() for s in dossier['sources']})
    new_tree(store.root, rules_dir, rule_files)
    entry = {'profile':p, 'template_dir':template_dir,'directory':working_dir,'main':main,'rules_dir':rules_dir,
             'template_sha256':sha(raw),'created_at':now(), 'rules_revision':1}
    old['venues'][p['id']] = entry
    issue = add_issue(store,'PROJECT','Venue '+p['id']+': check current edition/track, template example text, dates/timezone and all submission-rule topics before release.','venue-setup','major',commit=False)
    store.event('venue.initialized',actor,{'id':p['id'],'template':manifest,'rules':rules_dir,'issue':issue['id']})
    store.commit({INDEX:pretty(old)}, {INDEX:file_hash(safe_path(store.root,INDEX))})
    return {'venue_id':p['id'],'template_original':template_dir,'working_directory':working_dir,'main':main,'rules':rules_dir,
            'issue':issue['id'],'deadlines':[{**d,'temporal_status':deadline_status(d)} for d in dossier['deadlines']],
            'next':'Edit the downloaded main file; use latex adopt to bind sections to the research graph. Example author/results are not research.'}


def refresh(store: Store, venue_id: str, actor: str, *, online=False, sources_dir=None, transport=None, approve=False) -> dict:
    entry = get(store,venue_id); old = json.loads(read_text(safe_path(store.root,entry['rules_dir']+'/dossier.json')))
    fresh = source_dossier(entry['profile'],online=online,sources_dir=sources_dir,transport=transport,strict_quotes=False)
    old_by = {s['id']:s for s in old['sources']}
    diffs = [{'source':s['id'],'diff':''.join(difflib.unified_diff(old_by[s['id']]['text'].splitlines(True),s['text'].splitlines(True),fromfile='previous',tofile='current'))} for s in fresh['sources'] if s['text_sha256']!=old_by[s['id']]['text_sha256']]
    report = {'changed':bool(diffs),'checked_at':now(),'diffs':diffs,'applied':False}
    if not approve or not diffs: return report
    number = entry['rules_revision']+1
    folder = 'workspace/rules/venues/'+venue_id+'/revision-'+f'{number:03d}'
    outputs = {'dossier.json':pretty(fresh).encode(),'SUBMISSION_RULES.md':render_dossier(fresh).encode(),'deadlines.ics':calendar(fresh).encode()}
    outputs.update({'sources/'+s['id']+'.txt':s['text'].encode() for s in fresh['sources']})
    new_tree(store.root,folder,outputs)
    idx=index(store);idx['venues'][venue_id].update(rules_dir=folder,rules_revision=number)
    issue=add_issue(store,'PROJECT','Venue policy source changed: '+venue_id+'. Review '+folder+' and propagate to all manuscript/figure/method/AI-use rules.','rules-compliance','major',commit=False)
    store.event('venue.rules-refreshed',actor,{'id':venue_id,'previous':entry['rules_dir'],'current':folder,'issue':issue['id']})
    store.commit({INDEX:pretty(idx)}, {INDEX:file_hash(safe_path(store.root,INDEX))})
    return {**report,'applied':True,'rules_dir':folder,'issue':issue['id']}


def discover(store: Store, name: str, year: int, track: str, actor: str, *, urls=None, online=False, allowed_hosts=None, transport=None) -> dict:
    urls = urls or SEEDS.get((name.lower().strip(),year),[])
    require(urls, 'No verified discovery seed for this venue/year. Ask venue-setup to web-search official pages and pass --official-url; do not reuse a previous year.')
    require(1<=len(urls)<=8 and 2000<=year<=2200 and track.strip(), 'Specify bounded official URLs, edition year and track.')
    hosts={urllib.parse.urlsplit(u).hostname for u in urls}|set(allowed_hosts or [])
    records, links = [], []
    for u in urls:
        raw, meta=download(u,hosts,online=online,transport=transport,limit=4*1024*1024)
        text, found=page_text(raw,meta.get('content_type',''))
        records.append({'url':meta['url'],'sha256':meta['sha256'],'retrieved_at':now(),'text':text,'edition_mentioned':str(year) in text})
        for link in found:
            target=urllib.parse.urljoin(meta['url'],link)
            if urllib.parse.urlsplit(target).scheme!='https':continue
            if re.search(r'\.zip(?:\?|$)|overleaf\.com/latex/templates|github\.com/.*/(?:archive|releases)|template|deadline|author|submission|call-for',target,re.I):
                links.append(target)
    result={'name':name,'year':year,'track':track,'checked_at':now(),'sources':records,'candidate_links':list(dict.fromkeys(links)),
            'status':'discovered-unreviewed','next':'venue-setup reads the official pages and template candidates, selects exact track/stage/main file and builds a source-bound profile; venue init downloads the complete ZIP.'}
    path='workspace/venues/discovery/'+identifier('DISCOVERY')+'.json'
    store.event('venue.discovered',actor,{'record':path,'urls':urls})
    store.commit({path:pretty(result)},{path:None})
    return {'record':path,'candidate_links':result['candidate_links'],'status':result['status'],'next':result['next']}


def context(store: Store) -> dict:
    """Small rule summaries; originals remain addressable without dumping whole web pages."""
    result={}
    for key,entry in index(store)['venues'].items():
        dossier=json.loads(read_text(safe_path(store.root,entry['rules_dir']+'/dossier.json')))
        result[key]={'venue':dossier['venue'],'status':dossier['status'],'retrieved_at':dossier['retrieved_at'],
                     'rules_directory':entry['rules_dir'],'template_directory':entry['template_dir'],
                     'coverage':{topic:rec['status'] for topic,rec in dossier['coverage'].items()},
                     'requirements':dossier['requirements'],'deadlines':dossier['deadlines'],
                     'invalidated_entries':dossier.get('invalidated_structured_entries',[]),
                     'sources':[{'id':src['id'],'url':src['url'],'snapshot':entry['rules_dir']+'/sources/'+src['id']+'.txt',
                                 'text_sha256':src['text_sha256'],'status':src['status']} for src in dossier['sources']]}
    return result
