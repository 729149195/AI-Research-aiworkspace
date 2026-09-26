"""Publication command group. Network, compilation, remote writes and settings are opt-in."""
from __future__ import annotations
import json
from pathlib import Path
from .model import require
from .store import Store, read_text, safe_path


def add_commands(sub):
    def actor(q): q.add_argument('--actor', default='local-user')
    def approve(q): q.add_argument('--approve', action='store_true')
    def online(q): q.add_argument('--online', action='store_true')
    def sources(q): online(q); q.add_argument('--sources-dir')
    q=sub.add_parser('venue', help='Discover templates and current, source-bound venue rules')
    ss=q.add_subparsers(dest='action', required=True)
    q=ss.add_parser('discover');q.add_argument('--name',required=True);q.add_argument('--year',type=int,required=True);q.add_argument('--track',required=True);q.add_argument('--official-url',action='append',default=[]);q.add_argument('--allow-host',action='append',default=[]);online(q);actor(q)
    q=ss.add_parser('init');q.add_argument('--profile',required=True);q.add_argument('--archive');sources(q);actor(q);approve(q)
    q=ss.add_parser('refresh');q.add_argument('id');sources(q);actor(q);approve(q)
    ss.add_parser('list')
    q=ss.add_parser('transfer');q.add_argument('--source',required=True);q.add_argument('--source-main',default='main.tex');q.add_argument('--target',required=True);actor(q);approve(q)
    q=sub.add_parser('latex',help='Native LaTeX binding, compilation and manuscript-only ZIP')
    ss=q.add_subparsers(dest='action',required=True)
    q=ss.add_parser('adopt');q.add_argument('--directory',required=True);q.add_argument('--main',default='main.tex');actor(q);approve(q)
    q=ss.add_parser('build');q.add_argument('--directory');q.add_argument('--main');q.add_argument('--engine',choices=['pdflatex','xelatex','lualatex'],default='pdflatex');q.add_argument('--timeout',type=int,default=90);q.add_argument('--allow-exec',action='store_true')
    q=ss.add_parser('pack');q.add_argument('--directory');q.add_argument('--output',required=True)
    ss.add_parser('status')
    q=sub.add_parser('overleaf',help='Custom-host Workshop setup and native Git Bridge sync')
    ss=q.add_subparsers(dest='action',required=True)
    q=ss.add_parser('configure');q.add_argument('--server',default='https://nankaivisoverleaf.asia/');q.add_argument('--project-id',required=True);q.add_argument('--directory',required=True);q.add_argument('--mode',choices=['workshop','git'],default='workshop');q.add_argument('--git-url');actor(q);approve(q)
    q=ss.add_parser('install-plugin');q.add_argument('--editor',choices=['code','codium'],default='code');approve(q)
    ss.add_parser('status')
    q=ss.add_parser('sync');online(q);approve(q);actor(q);q.add_argument('--resolve',action='append',default=[]);q.add_argument('--allow-deletions',action='store_true');q.add_argument('--token-prompt',action='store_true')
    q=ss.add_parser('watch');online(q);approve(q);actor(q);q.add_argument('--interval',type=int,default=5);q.add_argument('--cycles',type=int,default=0);q.add_argument('--token-prompt',action='store_true')
    q=ss.add_parser('recover');online(q)
    q=ss.add_parser('bind-replica');q.add_argument('--directory',required=True);actor(q);approve(q)
    q=ss.add_parser('disconnect');approve(q)


def execute_publication(a):
    from . import venues,latex_project as latex,overleaf
    s=Store(a.project)
    if a.command=='venue':
        if a.action=='discover':return venues.discover(s,a.name,a.year,a.track,a.actor,urls=a.official_url,online=a.online,allowed_hosts=a.allow_host),0
        if a.action=='init':return venues.install(s,json.loads(read_text(Path(a.profile))),a.actor,approve=a.approve,online=a.online,archive=a.archive,sources_dir=a.sources_dir),0
        if a.action=='refresh':return venues.refresh(s,a.id,a.actor,online=a.online,sources_dir=a.sources_dir,approve=a.approve),0
        if a.action=='list':return venues.index(s),0
        if a.action=='transfer':return latex.transfer(s,a.source,a.source_main,a.target,a.actor,approve=a.approve),0
    if a.command=='latex':
        if a.action=='adopt':return latex.adopt(s,a.directory,a.main,a.actor,approve=a.approve),0
        if a.action=='build':
            result=latex.build(s,a.directory,a.main,allow_exec=a.allow_exec,engine=a.engine,timeout=a.timeout)
            return result,0 if result['compiled'] and not result['unresolved_references'] else 1
        if a.action=='pack':return latex.pack(s,a.output,a.directory),0
        if a.action=='status':return {'active':s.state['project'].get('latex'),'integrity_issues':latex.integrity_issues(s),'sync':latex.plan(s) if latex.active_dir(s) else None},0
    if a.command=='overleaf':
        if getattr(a, 'token_prompt', False):
            import getpass, os
            require(a.online, 'Token prompt requires explicit --online.')
            token = getpass.getpass('Overleaf Git token (not stored): ')
            require(bool(token.strip()), 'Empty token.')
            os.environ['RW_OVERLEAF_TOKEN'] = token
        if a.action=='configure':return overleaf.configure(s,a.actor,server=a.server,project_id=a.project_id,directory=a.directory,mode=a.mode,git_url=a.git_url,approve=a.approve),0
        if a.action=='install-plugin':return overleaf.install_plugin(approve=a.approve,code=a.editor),0
        if a.action=='status':
            c=overleaf.config(s);path=safe_path(s.root,overleaf.BASE,governed=False)
            return {'configuration':c,'baseline':json.loads(read_text(path)) if path.exists() else None,'pending':safe_path(s.root,overleaf.PENDING,governed=False).exists(),'note':'Local configuration only. No authenticated remote probe in status.'},0
        if a.action=='sync':
            choices={}
            for item in a.resolve:
                require('=' in item,'Use --resolve path=local|remote.');key,value=item.rsplit('=',1);require(key not in choices,'Duplicate resolution.');choices[key]=value
            result=overleaf.synchronize(s,a.actor,online=a.online,approve=a.approve,resolutions=choices,allow_deletions=a.allow_deletions)
            return result,1 if result.get('conflicts') else 0
        if a.action=='watch':
            result=overleaf.watch(s,a.actor,online=a.online,approve=a.approve,interval=a.interval,cycles=a.cycles)
            return result,1 if result.get('stopped')=='conflict' else 0
        if a.action=='recover':return overleaf.recover_sync(s,online=a.online),0
        if a.action=='bind-replica':return overleaf.bind_replica(s,a.directory,a.actor,approve=a.approve),0
        if a.action=='disconnect':return overleaf.disconnect(s,approve=a.approve),0
    require(False,'Unknown publication command.')
