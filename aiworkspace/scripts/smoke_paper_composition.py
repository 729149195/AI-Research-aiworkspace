#!/usr/bin/env python3
"""Actual local SVG/Store/reproduction exercise with explicitly synthetic material."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from research_workspace import __version__, diagrams
from research_workspace.model import pretty, now
from research_workspace.store import Store, atomic_write, file_hash

PACKAGE=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',required=True);a=p.parse_args()
    base=Path(a.destination).resolve()
    if base.exists():raise ValueError('Use a new demonstration directory; existing work is never overwritten.')
    base.mkdir(parents=True)
    root=base/'synthetic-study';root.mkdir()
    # Minimal valid research state tests the actual Store integration. It does not
    # assert a full initialized paper, scientific review, or any human approval.
    state={'schema_version':1,'revision':0,'project':{'name':'Synthetic SVG composition exercise','mode':'demo'},
           'nodes':{},'proposals':{},'issues':{},'sync':{},'events':[],'approvals':[],'writers':[],'tasks':[]}
    atomic_write(root/'workspace/state.json',pretty(state));atomic_write(root/'manuscript/main.md','Original synthetic manuscript.\n')
    original=file_hash(root/'manuscript/main.md');results=[]
    for name in ('method-detail','interaction-storyboard'):
        source=PACKAGE/'examples/vis-hci';spec=json.loads((source/(name+'.json')).read_text())
        spec['artwork']='workspace/figures/'+name+'.svg';specpath='workspace/figures/'+name+'.json'
        atomic_write(root/spec['artwork'],(source/(name+'.svg')).read_text());atomic_write(root/specpath,pretty(spec))
        plan=diagrams.plan(Store(root),spec)
        out=diagrams.make(Store(root),spec,approve=True,spec_path=specpath)
        assert diagrams.check(Store(root),out['record'])['current']
        frozen=(root/out['editable']).parent;regen=base/(name+'-reproduced')
        subprocess.run([sys.executable,str(frozen/'reproduce.py'),str(frozen/'spec.json'),'--output',str(regen)],check=True,capture_output=True)
        assert file_hash(root/out['preview'])==file_hash(regen/'diagram.png')
        results.append({'name':name,**out,'same_environment_png_reproduced':True})
    assert file_hash(root/'manuscript/main.md')==original
    assert not Store(root).state['approvals'] and not Store(root).state['nodes']
    report={'passed':True,'at':now(),'engine':__version__,'python':platform.python_version(),
            'figures':results,'original_manuscript_unchanged':True,'no_scientific_approvals_created':True,
            'boundary':'Actual source-module/Store and standalone child-process rendering of synthetic fixtures. No whole-release installation, live agent or aesthetic quality certification.'}
    atomic_write(base/'walkthrough.json',pretty(report));print(pretty(report));return 0

if __name__=='__main__':raise SystemExit(main())
