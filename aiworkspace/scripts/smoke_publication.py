#!/usr/bin/env python3
"""Actual installed-engine publication workflow on synthetic local source material.

No credentials, network downloads or real venue compliance claims. Optional TeX must
be installed; each unavailable class is reported skipped rather than fabricated.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def main():
    from research_workspace import venues, latex_project as latex, overleaf, routing
    from research_workspace.model import pretty, now
    from research_workspace.scaffold import initialize
    from research_workspace.store import Store
    from research_workspace.publication_io import tree_bytes, sha
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True);a=parser.parse_args()
    base=Path(a.destination).resolve()
    if base.exists():raise ValueError('Choose a new smoke-test directory.')
    base.mkdir(parents=True);study=base/'study';initialize(study,'Synthetic publication workflow','Fixture')
    sources=base/'sources';sources.mkdir();(sources/'venue.txt').write_text('Synthetic 2026 test venue. Anonymous review. No real submission rules are asserted.\n',encoding='utf-8')
    source=r'''\documentclass{article}
\title{Synthetic migration check}
\author{Synthetic source author}
\begin{document}
\maketitle
\begin{abstract}A software fixture, with no scientific claim.\end{abstract}
\section{Introduction}\label{sec:intro}
Preserve this sentence and its citation \cite{fixture}. See Section~\ref{sec:intro}.
\section{Method}The equation $x+y=y+x$ is preserved.
\bibliographystyle{plain}\bibliography{refs}
\end{document}
'''
    bib=b'@article{fixture,title={Synthetic reference},author={Doe, Jane},journal={Test fixture},year={2026}}\n'
    def install(name,family,options=''):
        archive=base/(name+'.zip')
        with zipfile.ZipFile(archive,'w') as z:z.writestr('main.tex',source.replace('{article}','{'+family+'}'));z.writestr('refs.bib',bib)
        p={'profile_version':1,'id':name,'name':'Synthetic '+family,'year':2026,'track':'fixture','stage':'review','anonymous':True,
           'sources':[{'id':'venue','role':'venue','url':'https://example.org/fixture'}],
           'template':{'url':'https://example.org/fixture.zip','main':'main.tex','license_note':'Synthetic local fixture only','class_options':options,'bibliography_style':'plain'}}
        return venues.install(Store(study),p,'fixture',approve=True,archive=archive,sources_dir=sources)
    first=install('source','article');original=tree_bytes(study/first['working_directory']);outcomes=[]
    for family,options in [('article',''),('acmart','manuscript,review,anonymous'),('IEEEtran','conference'),('llncs',''),('elsarticle','review')]:
        target=install('target-'+family.lower(),family,options)
        moved=latex.transfer(Store(study),first['working_directory'],'main.tex',target['venue_id'],'fixture',approve=True)
        assert tree_bytes(study/first['working_directory'])==original
        if not shutil.which('pdflatex'):
            build={'compiled':False,'skipped':'pdflatex unavailable'}
        elif shutil.which('kpsewhich') and not subprocess.run(['kpsewhich',family+'.cls'],capture_output=True).stdout.strip():
            build={'compiled':False,'skipped':family+' class unavailable'}
        else:
            build=latex.build(Store(study),moved['destination'],'main.tex',allow_exec=True)
        outcomes.append({'family':family,'directory':moved['destination'],'inventories_preserved':True,'source_bytes_unchanged':True,'build':build})
    active=outcomes[0]['directory'];latex.adopt(Store(study),active,'main.tex','fixture',approve=True)
    routing.capture(Store(study),'fixture');body=study/active/'rw-content.tex';body.write_text(body.read_text().replace('Preserve this sentence','Preserve this edited sentence'),encoding='utf-8')
    captured=routing.capture(Store(study),'fixture');assert 'manuscript-sync' in captured['routes']
    configuration=overleaf.configure(Store(study),'fixture',project_id='synthetic-project',directory=active,approve=True)
    packaged=latex.pack(Store(study),str(base/'manuscript-only.zip'))
    assert not any(p.startswith(('.','workspace/')) for p in packaged['files'])
    result={'at':now(),'cases':outcomes,'native_latex_auto_route':True,'custom_host_configuration':configuration['configuration']['server'],
            'manuscript_only_packaging':True,'authenticated_self_hosted_sync':'not_tested_no_credentials','plugin_host_session':'not_tested',
            'template_network_download':'transport-contract-tests_only; smoke uses synthetic local ZIPs','boundary':'Actual source migration and TeX compilation when available; no real submission or human-review claim.'}
    (base/'results.json').write_text(pretty(result),encoding='utf-8');print(pretty(result),end='')
    return 1 if any(not x['build'].get('compiled') and not x['build'].get('skipped') for x in outcomes) else 0

if __name__=='__main__':raise SystemExit(main())
