#!/usr/bin/env python3
"""Seven rendered synthetic recipes, real Store receipts and standalone regeneration.

This is an isolated Schema 1 software fixture. No human approval or empirical result.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE))
from research_workspace import studio
from research_workspace.model import digest,pretty
from research_workspace.store import Store,atomic_write,file_hash


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',required=True);a=p.parse_args()
    root=Path(a.destination).expanduser().resolve()
    if root.exists():raise ValueError('Use a new output directory; no existing study will be overwritten.')
    for name in ('workspace/data','workspace/results','workspace/research','workspace/rules','workspace/reports','workspace/history','workspace/sync','manuscript/figures','.rw'):
        (root/name).mkdir(parents=True,exist_ok=True)
    atomic_write(root/'workspace/state.json',pretty({'schema_version':1,'revision':0,
        'project':{'name':'SYNTHETIC FIGURE GALLERY','author':'Software fixture','mode':'demo'},
        'nodes':{},'proposals':{},'issues':{},'events':[],'approvals':[],'writers':[],'tasks':[],
        'sync':{'sections':{},'outside_hash':digest('')}}))
    atomic_write(root/'manuscript/main.md','# Synthetic software fixture\n\nNo research conclusion or human review is claimed.\n')
    atomic_write(root/'workspace/data/observations.csv','id,time,baseline,candidate,group\n'+''.join(f'P{i+1},{i+1},{17+i},{14+i-i%4},{"A" if i<6 else "B"}\n' for i in range(12)))
    atomic_write(root/'workspace/data/intervals.csv','name,estimate,lower,upper\nMethod A,2.3,1.4,3.5\nMethod B,1.8,0.2,2.6\nMethod C,-0.4,-1.2,0.5\n')
    atomic_write(root/'workspace/data/matrix.csv','task,method,value\nSearch,A,0.82\nSearch,B,0.74\nCompare,A,0.71\nCompare,B,0.91\nExplain,A,0.62\n')
    before=file_hash(root/'manuscript/main.md');outputs={}
    for kind in ('scatter','line','distribution','paired','interval','heatmap','workflow'):
        spec={'id':'FIG-'+kind.upper(),'kind':kind,'input':'workspace/data/observations.csv',
              'title':{'scatter':'Paired performance observations','line':'Observed trajectory','distribution':'Full observation distributions','paired':'Within-pair comparison','interval':'Estimates and supplied intervals','heatmap':'Method performance by task','workflow':'Evidence-first research workflow'}[kind],
              'purpose':'Inspect this reproducible plotting recipe using artificial data.',
              'caption':'SYNTHETIC SOFTWARE FIXTURE ONLY. No real-world inference.',
              'alt_text':'Artificial data used to verify the '+kind+' plotting recipe.',
              'x':'baseline','y':'candidate','xlabel':'Baseline (arbitrary units)','ylabel':'Candidate (arbitrary units)',
              'unit':'arbitrary units','width_mm':100,'height_mm':82,'claims':[],'evidence':[]}
        if kind=='scatter':spec['group']='group'
        if kind=='line':spec.update(x='time',group='group',xlabel='Observation index')
        if kind=='distribution':spec.update(group='group',xlabel='Group')
        if kind=='paired':spec.update(pair_id='id',xlabel='Condition',ylabel='Value (arbitrary units)')
        if kind=='interval':spec.update(input='workspace/data/intervals.csv',x='estimate',label='name',lower='lower',upper='upper',xlabel='Effect (arbitrary units)',ylabel='',interval_definition='Synthetic supplied 95% confidence intervals; illustrative values, not estimated here.',width_mm=140)
        if kind=='heatmap':spec.update(input='workspace/data/matrix.csv',row='task',column='method',value='value',xlabel='Method',ylabel='Task',unit='Synthetic score',width_mm=160)
        if kind=='workflow':
            spec.pop('input');spec.update(steps=['Question','Original sources','Analysis','Bounded claims','Independent review'],workflow_status='planned',width_mm=180,height_mm=60)
        spec['title']='Synthetic / '+spec['title']
        result=studio.figure_make(Store(root),spec,approve=True)
        assert studio.figure_check(Store(root),result['record'])['current']
        record=json.loads((root/result['record']).read_text());folder=root/record['provenance']
        command=[sys.executable,str(folder/'reproduce.py'),str(folder/'spec.json'),'--output',str(folder/'regenerated')]
        if kind!='workflow':command+=['--data',str(folder/'input.csv')]
        proc=subprocess.run(command,text=True,capture_output=True)
        assert proc.returncode==0,proc.stderr+proc.stdout
        assert (folder/'regenerated/figure.png').read_bytes()==(root/result['preview']).read_bytes()
        outputs[kind]=result
    assert file_hash(root/'manuscript/main.md')==before
    assert not Store(root).state['approvals'] and not Store(root).state['nodes']
    report={'passed':True,'recipes':outputs,'standalone_regeneration_count':7,'original_manuscript_unchanged':True,
            'no_human_approvals_or_scientific_nodes_created':True,'python':sys.version.split()[0],
            'boundary':'Real drawing, file checks, provenance and standalone subprocesses; isolated synthetic Schema 1 fixture. No live model/agent, journal compliance, authenticated Overleaf or complete framework regression.'}
    atomic_write(root/'SMOKE.json',pretty(report))
    readme=['# Synthetic scientific figure gallery','','Every image is a software demonstration using artificial data.','']
    for kind,result in outputs.items():readme+=['## '+kind,'','![Synthetic '+kind+']('+result['preview']+')','','[PDF]('+result['pdf']+') · [SVG]('+result['svg']+')','']
    atomic_write(root/'README.md','\n'.join(readme))
    print(pretty(report));return 0


if __name__=='__main__':raise SystemExit(main())
