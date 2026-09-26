"""Capture observed changes and route work; never promote observations to scientific truth."""
from __future__ import annotations
import difflib
import json
import re
from pathlib import Path
from .model import WorkspaceError, digest, impact, now, pretty, require
from .store import Store, file_hash, read_text, safe_path
from .sync import parse, plan as sync_plan
from .workflow import add_issue

SNAPSHOT = 'workspace/sync/auto-route.json'
HISTORY = 'workspace/history/auto-route/'
TEXT_LIMIT = 512_000
ROUTES = {
    'manuscript': ['manuscript-sync', 'logic-methodology', 'knowledge-evidence', 'writing-language', 'figure-visualization', 'reviewer'],
    'source': ['researcher', 'knowledge-evidence', 'logic-methodology', 'writing-language', 'reviewer'],
    'method': ['logic-methodology', 'knowledge-evidence', 'figure-visualization', 'writing-language', 'reviewer'],
    'rule': ['rules-compliance', 'writing-language', 'reviewer'],
    'idea': ['idea-evaluation', 'researcher', 'logic-methodology', 'reviewer'],
    'figure': ['figure-visualization', 'knowledge-evidence', 'writing-language', 'reviewer'],
    'memory': ['logic-methodology'],
}
NODE_GROUP = {'question': 'idea', 'hypothesis': 'idea', 'argument': 'idea', 'section': 'manuscript',
              'claim': 'manuscript', 'source': 'source', 'evidence': 'source', 'method': 'method',
              'result': 'method', 'rule': 'rule', 'figure': 'figure', 'decision': 'memory'}


def watched(path: str) -> bool:
    parts = Path(path).parts
    if any(p.startswith('.') or p in ('__pycache__', 'node_modules') or p.lower() in
           ('credentials', 'credentials.json', 'secrets', 'secrets.json') for p in parts):
        return False
    return path == 'workspace/memory.md' or path.startswith((
        'manuscript/', 'workspace/research/', 'workspace/sources/', 'workspace/evidence/',
        'workspace/methods/', 'workspace/data/', 'workspace/results/', 'workspace/rules/', 'workspace/figures/'))


def group_for(path: str) -> str:
    if path.startswith(('manuscript/figures/', 'workspace/figures/')): return 'figure'
    if path.startswith('manuscript/'): return 'manuscript'
    if path.startswith(('workspace/sources/', 'workspace/evidence/')): return 'source'
    if path.startswith(('workspace/methods/', 'workspace/data/', 'workspace/results/')): return 'method'
    if path.startswith('workspace/rules/'): return 'rule'
    if path.startswith('workspace/research/'): return 'idea'
    return 'memory'


def references(value, path: str) -> bool:
    if isinstance(value, str): return value == path
    if isinstance(value, list): return any(references(v, path) for v in value)
    if isinstance(value, dict): return path in value or any(references(v, path) for v in value.values())
    return False


def snapshot(store: Store) -> dict:
    files = {}
    for folder in ('workspace', 'manuscript'):
        for path in sorted((store.root / folder).rglob('*')):
            relative = path.relative_to(store.root).as_posix()
            if not watched(relative): continue
            require(not path.is_symlink(), 'Auto-route refuses a symlink: ' + relative)
            if path.is_file(): files[relative] = file_hash(safe_path(store.root, relative))
    require(len(files) <= 10000, 'Auto-route file limit exceeded; split the study or review the capture scope.')
    from .latex_project import route_text
    text = route_text(store)
    require(len(text.encode('utf-8')) <= TEXT_LIMIT, 'Manuscript exceeds auto-route 512 KB limit; no baseline advanced.')
    return {'format': 1, 'files': files, 'manuscript': text,
            'nodes': {key: {'hash': digest(node), 'kind': node['kind'], 'depends_on': node['depends_on'],
                            'meaning': {k: node['data'][k] for k in ('text', 'strength', 'scope', 'script', 'args', 'seed', 'causal_identification') if k in node['data']}}
                      for key, node in store.state['nodes'].items()}}


def diff_text(before: str, after: str) -> dict:
    value = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile='previous-observation', tofile='current-observation'))
    return {'diff': value[:16000], 'diff_truncated': len(value) > 16000,
            'before_sha256': digest(before.encode()), 'after_sha256': digest(after.encode())}


def inspect(store: Store, note: str = '', note_kind: str = 'discussion') -> dict:
    require(note_kind in ('discussion', 'preference', 'decision-candidate'), 'Unsupported note kind.')
    require(isinstance(note, str) and len(note.encode('utf-8')) <= 8000, 'Use a short, authorized handover note (at most 8 KB).')
    path = safe_path(store.root, SNAPSHOT)
    old = json.loads(read_text(path)) if path.exists() else None
    require(old is None or old.get('format') == 1, 'Unknown auto-route snapshot format.')
    current = snapshot(store)
    # Existing studies have no pre-install file history. Their explicit sync baseline is usable.
    baseline = old or {**current, 'manuscript': None}
    changes, groups, roots = [], set(), set()
    nodes = store.state['nodes']
    graph = {key: {'kind': n['kind'], 'depends_on': list(n['depends_on'])} for key, n in nodes.items()}
    for key, n in baseline['nodes'].items():
        if key in graph:
            graph[key]['depends_on'] = sorted(set(graph[key]['depends_on']) | set(n['depends_on']))
        else:
            graph[key] = {'kind': n['kind'], 'depends_on': n['depends_on']}
    if old:
        for name in sorted(set(old['files']) | set(current['files'])):
            if old['files'].get(name) == current['files'].get(name): continue
            group = group_for(name); groups.add(group)
            changes.append({'type': 'file', 'path': name, 'group': group,
                            'before': old['files'].get(name), 'after': current['files'].get(name)})
            roots.update(k for k, n in nodes.items() if references(n['data'], name))
        for key in sorted(set(old['nodes']) | set(current['nodes'])):
            if old['nodes'].get(key) == current['nodes'].get(key): continue
            n = current['nodes'].get(key) or old['nodes'][key]
            groups.add(NODE_GROUP[n['kind']]); roots.add(key)
            changes.append({'type': 'node', 'id': key, 'group': NODE_GROUP[n['kind']],
                            'before': old['nodes'].get(key), 'after': current['nodes'].get(key)})
    structural_error, section_changes = None, []
    try:
        sections, outside = parse(current['manuscript'])
        previous, previous_outside = parse(old['manuscript']) if old else (store.state['sync']['sections'], None)
        for key in sorted(set(previous) | set(sections)):
            if previous.get(key) == sections.get(key): continue
            section_changes.append(key)
            if key in graph: roots.add(key)
            groups.add('manuscript')
            changes.append({'type': 'section', 'id': key, 'group': 'manuscript',
                            **diff_text(previous.get(key, ''), sections.get(key, ''))})
        changed_outside = outside != previous_outside if old else digest(outside) != store.state['sync'].get('outside_hash')
        if changed_outside:
            groups.add('manuscript')
            changes.append({'type': 'unmapped-text', 'group': 'manuscript', 'manual_review': True})
        syncing = sync_plan(store)
        if not old:
            for item in syncing['changes'] + syncing['conflicts']:
                key = item['section']
                if key in graph: roots.add(key)
                groups.add('manuscript')
                if key not in section_changes:
                    changes.append({'type': 'preexisting-unsynced', 'id': key, 'group': 'manuscript'})
    except WorkspaceError as exc:
        structural_error = str(exc)
        syncing = {'conflicts': [], 'changes': [], 'outside_changed': True}
        if not old or current['manuscript'] != old['manuscript'] or current['nodes'] != old['nodes']:
            groups.add('manuscript')
            changes.append({'type': 'structure', 'group': 'manuscript', 'error': structural_error})
    if 'manuscript' in groups:
        if not section_changes: roots.update(k for k, n in graph.items() if n['kind'] == 'section')
        # A section change can affect other sections sharing its Claims, even when the
        # dependency graph only points from Claims to sections. Do not propagate all
        # the way to the research question merely because one sentence was edited.
        queue, seen = list(roots), set(roots)
        while queue:
            key = queue.pop()
            for dep in graph.get(key, {}).get('depends_on', []):
                if dep in graph and dep not in seen:
                    seen.add(dep); queue.append(dep)
                    if graph[dep]['kind'] in ('claim', 'evidence', 'method', 'result', 'figure'): roots.add(dep)
    if 'rule' in groups: roots.update(graph)
    note_key = digest({'note': note, 'kind': note_kind}) if note else None
    fresh_note = bool(note) and (not old or note_key != old.get('last_note'))
    if fresh_note: groups.add('rule' if note_kind == 'preference' else 'idea' if note_kind == 'decision-candidate' else 'memory')
    details = impact(graph, sorted(roots)) if roots else {'changed': [], 'affected': [], 'sections': [], 'figures': [], 'reasons': {}}
    routes = list(dict.fromkeys(skill for group in sorted(groups) for skill in ROUTES[group]))
    required = bool(changes and groups - {'memory'})
    return {'initialized': old is not None, 'changed': bool(changes) or fresh_note,
            'changes': changes, 'routes': routes, 'impact': details, 'requires_review': required,
            'conflicts': syncing['conflicts'], 'structure_error': structural_error,
            'note': {'kind': note_kind, 'text': note, 'status': 'unconfirmed-context'} if fresh_note else None,
            'current': {**current, 'last_note': note_key if fresh_note else (old or {}).get('last_note')},
            'expected_snapshot': file_hash(path),
            'boundary': 'Observed edits and provisional routing only; no Claim approval, evidence verification or automatic manuscript overwrite.'}


def public(report: dict) -> dict:
    return {k: v for k, v in report.items() if k not in ('current', 'expected_snapshot')}


def capture(store: Store, actor: str = 'auto-route', note: str = '', note_kind: str = 'discussion') -> dict:
    report = inspect(store, note, note_kind)
    pending = [t['id'] for t in store.state['tasks'] if t.get('origin') == 'auto-route' and t['status'] == 'open']
    if report['initialized'] and not report['changed']:
        return {'captured': False, 'pending_tasks': pending, 'boundary': report['boundary']}
    require(bool(actor.strip()), 'Actor required.')
    change_id = 'CHANGE-' + digest({'revision': store.state['revision'], 'previous': report['expected_snapshot'], 'current': report['current'],
                                    'note': report['note']})[:12].upper()
    record_path = HISTORY + change_id + '.json'
    require(not safe_path(store.root, record_path).exists(), 'Capture record already exists; investigate snapshot recovery.')
    issue_ids, task_ids = [], []
    if report['requires_review']:
        issue = add_issue(store, 'MANUSCRIPT' if 'manuscript-sync' in report['routes'] else 'PROJECT',
                          'Captured edit ' + change_id + ': inspect ' + record_path +
                          '; reconcile Claim scope, evidence, methods and affected sections. Capture is not verification.',
                          'auto-route', 'major', commit=False)
        issue_ids.append(issue['id'])
    fingerprint = store.fingerprint()
    for skill in report['routes']:
        existing = next((t for t in store.state['tasks'] if t.get('origin') == 'auto-route' and t['status'] == 'open' and t['skill'] == skill), None)
        if existing:
            existing.setdefault('change_ids', [existing['change_id']]).append(change_id)
            existing.setdefault('records', [existing['record']]).append(record_path)
            existing['fingerprint'] = fingerprint
            task_ids.append(existing['id'])
            continue
        task_id = 'TASK-' + digest([change_id, skill])[:12].upper()
        store.state['tasks'].append({'id': task_id, 'origin': 'auto-route', 'status': 'open', 'skill': skill,
                                    'code': 'AUTO_ROUTE_CHANGE', 'node': 'MANUSCRIPT', 'fingerprint': fingerprint,
                                    'change_id': change_id, 'change_ids': [change_id], 'record': record_path, 'records': [record_path], 'created_at': now(),
                                    'instruction': 'Read the change record and use ' + skill + ' within its permissions; do not self-certify.'})
        task_ids.append(task_id)
    record = {**public(report), 'id': change_id, 'at': now(), 'actor': actor, 'status': 'captured',
              'task_ids': task_ids, 'issue_ids': issue_ids,
              'initial_history_limit': None if report['initialized'] else 'Only existing sync baseline and current files observed; earlier edits are unknown.'}
    changes = {SNAPSHOT: pretty(report['current']), record_path: pretty(record)}
    require(all(len(text.encode()) <= 4 * 1024 * 1024 for text in changes.values()), 'Capture exceeds 4 MiB; no baseline advanced.')
    store.event('auto-route.captured', actor, {'id': change_id, 'record': record_path, 'record_hash': digest(record),
                                            'tasks': task_ids, 'issues': issue_ids})
    expected = {SNAPSHOT: report['expected_snapshot'], record_path: None}
    # Catch edits made after the initial scan as well as concurrent metadata writers.
    expected.update(report['current']['files'])
    for item in report['changes']:
        if item['type'] == 'file' and item['after'] is None: expected[item['path']] = None
    store.commit(changes, expected)
    return {'captured': report['changed'], 'baseline_initialized': not report['initialized'],
            'change_id': change_id, 'record': record_path, 'routes': report['routes'], 'tasks': task_ids,
            'pending_tasks': sorted(set(pending + task_ids)), 'issue_ids': issue_ids, 'impact': report['impact'],
            'needs_confirmation': bool(report['requires_review'] or report['conflicts'] or report['structure_error']),
            'boundary': report['boundary']}


def complete(store: Store, change_id: str, actor: str, note: str) -> dict:
    require(re.fullmatch(r'CHANGE-[A-F0-9]{12}', change_id) is not None, 'Invalid change ID.')
    require(len(note.strip()) >= 20, 'Describe the actual completed work and rechecks (20+ characters).')
    path = HISTORY + change_id + '.json'
    record = json.loads(read_text(safe_path(store.root, path)))
    require(any(e.get('action') == 'auto-route.captured' and e.get('detail', {}).get('id') == change_id and
                e['detail'].get('record_hash') == digest(record) for e in store.state['events']), 'Change record hash does not match its capture event.')
    require(all(store.state['issues'].get(i, {}).get('status') == 'resolved' for i in record['issue_ids']), 'Resolve and recheck associated issues first.')
    require(not inspect(store)['changed'], 'Capture newer edits before completing earlier routing work.')
    if 'manuscript-sync' in record['routes']:
        syncing = sync_plan(store)
        require(not syncing['changes'] and not syncing['conflicts'] and not syncing['outside_changed'], 'Reconcile manuscript sync first.')
    tasks = [t for t in store.state['tasks'] if change_id in t.get('change_ids', []) and t['status'] == 'open' and change_id not in t.get('completed_changes', {})]
    if not tasks: return {'completed': [], 'already_complete': True}
    for task in tasks:
        task.setdefault('completed_changes', {})[change_id] = {'actor': actor, 'at': now(), 'note': note}
        if set(task['change_ids']) <= set(task['completed_changes']):
            task.update(status='done', completed_by=actor, completed_at=now(), completion_note=note)
    store.event('auto-route.completed', actor, {'id': change_id, 'note': note, 'tasks': [t['id'] for t in tasks]})
    store.commit()
    return {'completed': [t['id'] for t in tasks], 'boundary': 'Task bookkeeping only; independent human review and final gate still apply.'}
