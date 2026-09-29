#!/usr/bin/env python3
"""Render editable illustrative examples and independently reproduce them. No model or network."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from research_workspace.diagram_render import KINDS, render
from research_workspace.diagram_templates import template
from research_workspace import diagram_render


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',required=True);a=p.parse_args()
    root=Path(a.destination);root.mkdir(parents=True,exist_ok=False);reports={}
    for kind in KINDS:
        s=template(kind);folder=root/kind;report=render(s,folder)
        (folder/'spec.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (folder/'reproduce.py').write_bytes(Path(diagram_render.__file__).read_bytes())
        again=folder/'reproduced'
        process=subprocess.run([sys.executable,str(folder/'reproduce.py'),str(folder/'spec.json'),'--output',str(again)],capture_output=True,text=True,check=True)
        assert (folder/'diagram.png').read_bytes()==(again/'diagram.png').read_bytes()
        reports[kind]={'actual_render':True,'independent_reproduction':True,'same_environment_png_identical':True,'summary':report}
    for style in ('paper','mono'):
        s=template('graphical-abstract');s['style']=style;render(s,root/style)
    # Explicit CJK example when the developer environment provides the font.
    cjk=template('response');cjk.update(title='科研修改与审稿回复流程',subtitle='示意模板：不代表已完成真实研究',font_family='Noto Sans CJK SC')
    cjk['nodes'][0].update(label='审稿人的原始意见',detail='保留原文，理解问题')
    cjk['nodes'][1].update(label='执行有依据的修改',detail='保留证据与作者意图')
    cjk['nodes'][2].update(label='核对全文与图表',detail='检查论点、数据和引用')
    cjk['nodes'][3].update(label='回复并定位修改',detail='说明真实改动和未完成事项')
    cjk['edges'][-1]['label']='仍待解决'
    reports['cjk']=render(cjk,root/'cjk')
    (root/'README.md').write_text('# Illustrative diagrams only\n\nThese original templates contain no real study results. Each template includes SVG/PDF/PNG, editable .drawio and DOT, plus a frozen specification and standalone renderer. Use the actual study evidence before publication. All generated versions are inspectable; reproducing across other Graphviz/Cairo/font versions can change layout. No font binaries are distributed.\n',encoding='utf-8')
    report={'passed':True,'templates':reports,'boundary':'Actual local rendering and subprocess reproduction. No live agent, remote editor, diagrams.net GUI or scientific validation.'}
    (root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
