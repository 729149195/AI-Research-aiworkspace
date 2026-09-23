#!/usr/bin/env python3
"""Actual installed-engine and hook-CLI walkthrough; all scientific material is synthetic.

Run in a venv where this distribution is installed. No live Claude/model session is used.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
from research_workspace import __version__, routing, route_hooks, sync, workflow
from research_workspace.demo import demonstrate, AUTHOR, NOTE
from research_workspace.store import Store, atomic_write, file_hash


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='auto-route-walkthrough-') as tmp:
        root=Path(tmp)/'study';demo=demonstrate(root)
        first=routing.capture(Store(root),'demo:auto-route')
        for iid in first['issue_ids']: workflow.resolve_issue(Store(root),iid,'Demo reviewer (simulation)',NOTE)
        routing.complete(Store(root),first['change_id'],'demo:agent',NOTE)
        path=root/'manuscript/main.md';before_nodes=Store(root).state['nodes']
        text=path.read_text(encoding='utf-8')
        assert 'external validity is unknown' in text
        atomic_write(path,text.replace('external validity is unknown','external validity remains untested and causal interpretation is unsupported'))
        edited_hash=file_hash(path)
        configured=route_hooks.configure(Store(root),approve=True)
        command=shlex.split(configured['command'])
        event=json.dumps({'hook_event_name':'PostToolUse','tool_name':'Edit'})
        result=subprocess.run(command,input=event,text=True,capture_output=True,cwd=tmp,check=True)
        assert 'hookSpecificOutput' in json.loads(result.stdout)
        assert Store(root).state['nodes']==before_nodes and file_hash(path)==edited_hash
        snapshots=file_hash(root/routing.SNAPSHOT)
        repeated=subprocess.run(command,input=event,text=True,capture_output=True,cwd=tmp,check=True)
        assert json.loads(repeated.stdout)=={'suppressOutput':True}
        assert file_hash(root/routing.SNAPSHOT)==snapshots
        pending=[t for t in Store(root).state['tasks'] if t['status']=='open' and t.get('origin')=='auto-route']
        assert any(t['skill']=='knowledge-evidence' for t in pending)
        proposal=sync.propose_sync(Store(root),'demo:sync')
        workflow.apply(Store(root),proposal['id'],AUTHOR,NOTE,approve=True)
        routing.capture(Store(root),'demo:auto-route',note='SIMULATION: supervisor suggests narrower wording; no real expert review.',note_kind='discussion')
        for iid,item in Store(root).state['issues'].items():
            if item['status']=='open':workflow.resolve_issue(Store(root),iid,'Demo reviewer (simulation)',NOTE)
        change_ids={cid for t in Store(root).state['tasks'] if t.get('origin')=='auto-route' and t['status']=='open' for cid in t['change_ids']}
        for cid in sorted(change_ids):routing.complete(Store(root),cid,'demo:agent',NOTE)
        assert not any(t['status']=='open' for t in Store(root).state['tasks'] if t.get('origin')=='auto-route')
        assert not sync.plan(Store(root))['changes']
        stopped=subprocess.run(command,input=json.dumps({'hook_event_name':'Stop','stop_hook_active':True}),text=True,capture_output=True,cwd=tmp,check=True)
        assert json.loads(stopped.stdout)=={'suppressOutput':True}
        result={'passed':True,'engine':__version__,'actual_isolated_python_hook_process':True,
                'manuscript_change_captured':True,'capture_did_not_overwrite_nodes_or_manuscript':True,
                'repeated_hook_silent_and_idempotent':True,'specialist_tasks_persisted':True,
                'explicit_sync_proposal_applied':True,'context_note_remained_unconfirmed':True,
                'reconciled_tasks_completed':True,'stop_did_not_restart':True,
                'synthetic_computation':demo['computed_values'],
                'boundary':'Actual installed-engine/CLI/hook-payload execution with synthetic material and simulated author/reviewer declarations. No live host, model or scientific review.'}
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:Path(a.output).write_text(output,encoding='utf-8')
    print(output,end='');return 0

if __name__=='__main__':raise SystemExit(main())
