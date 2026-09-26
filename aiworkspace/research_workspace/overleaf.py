"""Overleaf Git Bridge transport and editor-plugin setup for custom servers.

Only an explicitly selected manuscript subtree is synchronized. No force push, no
workspace/history/credentials uploads, no automatic conflict resolution or blind delete.
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from .model import WorkspaceError, identifier, now, pretty, require
from .store import Store, atomic_write, file_hash, project_lock, read_text, safe_path
from .publication_io import SOURCE_EXTENSIONS, archive_path, sha, tree_bytes
from .upgrade import merge_text

CONFIG='.rw/overleaf.json'
BASE='.rw/overleaf/baseline.json'
PENDING='.rw/overleaf/pending.json'
DEFAULT_SERVER='https://nankaivisoverleaf.asia'
EXTENSION='iamhyc.overleaf-workshop'
EXTENSION_VERSION='0.15.10'


def server_url(value: str)->str:
    u=urllib.parse.urlsplit(value.rstrip('/'))
    require(u.scheme=='https' and u.hostname and not u.username and not u.password and not u.query and not u.fragment and u.path in ('','/'),'Use an HTTPS server homepage URL without credentials or project path.')
    require(not any(c in value for c in '\r\n\x00'),'Invalid server URL.')
    return urllib.parse.urlunsplit((u.scheme,u.netloc,'','',''))


def checked_git_url(server: str,project_id: str,url: str|None=None)->str:
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,128}',project_id)),'Enter the project ID from its URL.')
    host=urllib.parse.urlsplit(server).hostname
    default=('https://git.overleaf.com/'+project_id if host=='www.overleaf.com' else server+'/git/'+project_id)
    value=url or default;u=urllib.parse.urlsplit(value)
    allowed={host}|({'git.overleaf.com'} if host=='www.overleaf.com' else set())
    require(u.scheme=='https' and u.hostname in allowed and u.username in (None,'git') and not u.password and not u.query and not u.fragment,'Git URL must belong to the selected server; never embed a token/password.')
    require(u.port==urllib.parse.urlsplit(server).port or (host=='www.overleaf.com' and u.port is None),'Git endpoint port differs from selected server.')
    return urllib.parse.urlunsplit((u.scheme,u.netloc.split('@')[-1],u.path,'',''))


def config(store: Store)->dict:
    c=json.loads(read_text(safe_path(store.root,CONFIG,governed=False)))
    server_url(c['server']);checked_git_url(c['server'],c['project_id'],c.get('git_url'))
    require(c.get('mode') in ('git','workshop') and c.get('directory','').startswith('manuscript/'),'Invalid Overleaf configuration.')
    return c


def configure(store: Store,actor: str,*,server=DEFAULT_SERVER,project_id: str,directory: str,mode='workshop',git_url=None,approve=False)->dict:
    server=server_url(server);require(mode in ('workshop','git'),'Choose workshop or git.')
    require(directory.startswith('manuscript/') and safe_path(store.root,directory).is_dir(),'Select one existing manuscript subtree, not the whole research workspace.')
    value={'version':1,'server':server,'project_id':project_id,'git_url':checked_git_url(server,project_id,git_url),
           'directory':directory,'mode':mode,'configured_by':actor,'at':now(),'credential':'Git credential helper or RW_OVERLEAF_TOKEN; Workshop login belongs to the extension',
           'live_connection_verified':False}
    old_path=safe_path(store.root,CONFIG,governed=False)
    if old_path.exists():
        old=json.loads(read_text(old_path))
        baseline=safe_path(store.root,BASE,governed=False)
        require(not baseline.exists() or all(old.get(k)==value.get(k) for k in ('server','project_id','directory','mode','git_url')),'Existing sync baseline is bound to another project/directory. Use a new study or disconnect --approve after preserving backups.')
    if not approve:return {'configuration':value,'applied':False,'note':'No credentials stored, plugin installed or network operation performed.'}
    atomic_write(old_path,pretty(value))
    try:old_path.chmod(0o600)
    except OSError:pass
    guide=workshop_guide(value)
    atomic_write(safe_path(store.root,'workspace/reports/overleaf-setup.md'),guide)
    return {'configuration':value,'applied':True,'guide':'workspace/reports/overleaf-setup.md'}


def workshop_guide(c: dict)->str:
    return f'''# Overleaf setup — {c['server']}

Mode: {c['mode']}. Project: {c['project_id']}. Local paper: `{c['directory']}`.

## VS Code / Overleaf Workshop (Community Edition or Server Pro)

1. Install `iamhyc.overleaf-workshop` (reviewed upstream version {EXTENSION_VERSION}).
2. Run **Overleaf Workshop: Add New Server** (`overleaf-workshop.projectManager.addServer`). Enter `{c['server']}` exactly.
3. Log in through the extension using email/password. For SSO or CAPTCHA use **Login with Cookies** from your own already-authenticated browser. Cookies are session credentials: never paste them into chat, a repository or this Workspace.
4. Upload a manuscript-only ZIP as a **new project**, or select your existing project `{c['project_id']}`.
5. Choose **Open Project Locally...**, using a new empty parent under `manuscript/replicas/`. The extension appends the remote project name. It can overwrite an existing path: do not select your only local paper copy.
6. Open the resulting local replica in VS Code. Keep that window running for synchronization. Configure Source Control there; do not use Invisible Mode for live collaboration.
7. Set the Workspace's native LaTeX directory to the actual replica via `rw latex adopt --directory manuscript/replicas/PROJECT_NAME --main main.tex --approve --actor YOUR_NAME` only after checking its content. For an already marked manuscript, use `rw overleaf bind-replica` instead.

This integration uses the extension's real server/login and Local Replica interfaces. It does not fabricate an `overleaf.server` settings key or read/write its private login database. Its upstream documentation warns that Local Replica is not yet robust under unstable networks. Keep independent versioned backups and check conflicts.

## Native Git Bridge (requires server feature)

Use mode `git` only when this server's project menu exposes Git. Endpoint: `{c['git_url']}`. Account Settings → Git authentication tokens; Git username is `git`, password is the Git token. Ordinary account passwords and browser cookies are not Git tokens.

Use an OS-backed Git credential helper or a process-local `RW_OVERLEAF_TOKEN`. No token goes into a URL, command argument or config file. Run `rw overleaf sync --online` to preview; then `rw overleaf sync --online --approve --actor YOUR_NAME` to reconcile. Foreground near-real-time polling: `rw overleaf watch --online --approve --actor YOUR_NAME --interval 5`. Conflicts and deletes pause; no force-push occurs. Do not run Workshop and Git synchronization against the same local directory simultaneously.

Only `{c['directory']}` may be uploaded. `workspace/`, history, raw research directories and `.rw/` are outside the upload boundary. These configuration steps do not prove that login or network synchronization has succeeded.
'''


def install_plugin(*,approve=False,code='code')->dict:
    require(code in ('code','codium'),'Use a known VS Code/VSCodium executable.')
    command=[code,'--install-extension',EXTENSION+'@'+EXTENSION_VERSION]
    if not approve:return {'command':command,'installed':False,'third_party':True}
    executable=shutil.which(code);require(executable,'VS Code CLI is missing; install the extension from its Marketplace page.')
    p=subprocess.run([executable,*command[1:]],capture_output=True,timeout=120,check=False)
    require(p.returncode==0,'Editor extension install failed. Inspect it locally; no login credentials were requested.')
    return {'installed':True,'extension':EXTENSION,'version':EXTENSION_VERSION,'connected':False}


def managed(path: str)->bool:
    parts=Path(path).parts
    if any(x.startswith('.') or x.lower() in {'credentials.json','secrets.json','token.json','passwords.txt','node_modules','__pycache__','build'} for x in parts):return False
    return Path(path).suffix.lower() in SOURCE_EXTENSIONS or Path(path).name in ('LICENSE','README')


def local_files(store: Store,c: dict)->dict[str,bytes]:
    values=tree_bytes(safe_path(store.root,c['directory']))
    bad=[p for p in values if not managed(p)]
    require(not bad,'Potential credential/control files inside the upload tree; remove them before sync: '+', '.join(bad))
    return values


class GitTransport:
    """Fetch objects, never execute a fetched worktree or remote hooks."""
    def __init__(self,store: Store,c: dict):
        self.store,self.c=store,c
        self.root=safe_path(store.root,'.rw/overleaf/repository.git',governed=False)
        self.root.parent.mkdir(parents=True,exist_ok=True)
        self.env=os.environ.copy()
        self.env.update(GIT_TERMINAL_PROMPT='0',GIT_AUTHOR_NAME='AI Workspace sync',GIT_AUTHOR_EMAIL='sync@localhost.invalid',GIT_COMMITTER_NAME='AI Workspace sync',GIT_COMMITTER_EMAIL='sync@localhost.invalid')
        # No token contents are written. The isolated helper reads only the intended
        # process variable, and Git's ordinary credential helper remains available.
        helper=self.root.parent/'askpass.py'
        atomic_write(helper,'import os,sys\nprint("git" if "username" in " ".join(sys.argv[1:]).lower() else os.environ.get("RW_OVERLEAF_TOKEN", ""))\n')
        if os.environ.get('RW_OVERLEAF_TOKEN'):
            launcher=self.root.parent/('askpass.cmd' if os.name=='nt' else 'askpass.sh')
            if os.name=='nt': text='@"'+sys.executable+'" -I "'+str(helper)+'" %*\r\n'
            else:
                import shlex
                text='#!/bin/sh\nexec '+shlex.quote(sys.executable)+' -I '+shlex.quote(str(helper))+' "$@"\n'
            atomic_write(launcher,text);launcher.chmod(0o700);self.env['GIT_ASKPASS']=str(launcher)
        if not self.root.exists():
            p=subprocess.run(['git','init','--bare',str(self.root)],capture_output=True,env=self.env,timeout=30)
            require(p.returncode==0,'Cannot initialize local Git object cache.')
        self.remote=self.c['git_url'];self.other=[];self.branch=None

    def call(self,*args: str,input:bytes|None=None,env=None)->bytes:
        command=['git','-c','core.hooksPath='+('NUL' if os.name=='nt' else '/dev/null'),'-c','http.followRedirects=false','--git-dir='+str(self.root),*args]
        p=subprocess.run(command,input=input,capture_output=True,env=env or self.env,timeout=90,check=False)
        require(p.returncode==0,'Git operation failed ('+args[0]+'). Check endpoint, Git Bridge availability, permissions, token and network. Sensitive command output is omitted.')
        return p.stdout

    def read(self)->tuple[dict[str,bytes],str]:
        info=self.call('ls-remote','--symref',self.remote,'HEAD').decode()
        m=re.search(r'^ref: refs/heads/([A-Za-z0-9/._-]+)\s+HEAD$',info,re.M)
        require(m,'Remote must contain an initialized project branch.')
        self.branch=m.group(1);require('..' not in self.branch and not self.branch.startswith('-'),'Invalid remote branch.')
        self.call('fetch','--no-tags','--no-recurse-submodules',self.remote,'refs/heads/'+self.branch)
        commit=self.call('rev-parse','FETCH_HEAD').decode().strip()
        values={};self.other=[];total=0
        for item in self.call('ls-tree','-rz','--full-tree',commit).split(b'\0'):
            if not item:continue
            head,name=item.split(b'\t',1);mode,kind,oid=head.decode().split();path=name.decode('utf-8')
            archive_path(path);require(mode in ('100644','100755') and kind=='blob','Remote symlinks/submodules/devices are not supported.')
            if not managed(path):self.other.append((mode,oid,path));continue
            size=int(self.call('cat-file','-s',oid).decode().strip())
            require(size<=32*1024*1024 and total+size<=96*1024*1024,'Remote source exceeds size limit.')
            data=self.call('cat-file','blob',oid);total+=len(data)
            require(total<=96*1024*1024 and len(data)<=32*1024*1024 and len(values)<2000,'Remote source exceeds size limit.')
            values[path]=data
        return values,commit

    def push(self,files:dict[str,bytes],parent:str)->str:
        require(self.branch,'Read the remote before pushing.')
        with tempfile.TemporaryDirectory(dir=self.root.parent,prefix='index-') as temp:
            env={**self.env,'GIT_INDEX_FILE':str(Path(temp)/'index')}
            self.call('read-tree','--empty',env=env)
            entries=list(self.other)
            for name,data in sorted(files.items()):
                require(managed(name),'Unmanaged upload path.')
                oid=self.call('hash-object','-w','--stdin',input=data).decode().strip();entries.append(('100644',oid,name))
            raw=b''.join((mode+' '+oid+'\t'+name).encode()+b'\0' for mode,oid,name in entries)
            self.call('update-index','-z','--index-info',input=raw,env=env)
            tree=self.call('write-tree',env=env).decode().strip()
            commit=self.call('commit-tree',tree,'-p',parent,'-m','Synchronize reviewed local manuscript changes').decode().strip()
            self.call('push','--porcelain',self.remote,commit+':refs/heads/'+self.branch)
            return commit


def object_bytes(store:Store,h:str)->bytes:
    require(re.fullmatch(r'[a-f0-9]{64}',h),'Invalid sync object hash.')
    path=safe_path(store.root,'.rw/overleaf/objects/'+h,governed=False)
    require(path.is_file() and path.stat().st_size<=32*1024*1024,'Sync baseline object missing or too large.')
    data=path.read_bytes();require(sha(data)==h,'Sync object is corrupt.');return data


def put_object(store:Store,data:bytes)->str:
    h=sha(data);p=safe_path(store.root,'.rw/overleaf/objects/'+h,governed=False);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():require(p.read_bytes()==data,'Corrupt sync object.')
    else:p.write_bytes(data)
    return h


def merge_files(base:dict[str,bytes],local:dict[str,bytes],remote:dict[str,bytes],*,resolutions=None,allow_deletions=False)->dict:
    choices=resolutions or {};require(set(choices)<=set(base)|set(local)|set(remote),'Unknown conflict resolution path.')
    merged,conflicts,changes={},{},[]
    for name in sorted(set(base)|set(local)|set(remote)):
        b,l,r=base.get(name),local.get(name),remote.get(name)
        if l==r:action,value='unchanged',l
        elif r==b:action,value='local-to-remote',l
        elif l==b:action,value='remote-to-local',r
        else:
            try:
                require(all(x is not None and len(x)<=1024*1024 for x in (b,l,r)),'Binary/add-delete conflict.')
                action,text=merge_text(b.decode('utf-8'),l.decode('utf-8'),r.decode('utf-8'))
                value=text.encode('utf-8') if text is not None else None
            except (WorkspaceError,UnicodeError):action,value='conflict',None
        if name in choices:
            require(choices[name] in ('local','remote'),'Resolution must be local or remote.')
            action,value='explicit-'+choices[name],l if choices[name]=='local' else r
        if value is None and (l is not None or r is not None) and action!='conflict' and not allow_deletions:
            action='conflict'
        if action=='conflict':conflicts[name]={'base':sha(b) if b is not None else None,'local':sha(l) if l is not None else None,'remote':sha(r) if r is not None else None};continue
        if value is not None:merged[name]=value
        if value!=l or value!=r:changes.append({'path':name,'action':action,'deletion':value is None})
    return {'files':merged,'conflicts':conflicts,'changes':changes}


def finish_pending(store:Store,*,expected_remote:str|None=None)->dict:
    path=safe_path(store.root,PENDING,governed=False);record=json.loads(read_text(path));c=config(store)
    require(record['directory']==c['directory'],'Pending sync belongs to another directory.')
    if expected_remote is not None:require(record.get('remote_commit')==expected_remote,'Remote advanced; review pending operation before recovery.')
    require(record.get('remote_commit'),'Remote push outcome is unresolved; inspect remote history before recovery.')
    folder=safe_path(store.root,c['directory']);current=local_files(store,c)
    for name in set(record['before'])|set(record['after']):
        actual=sha(current[name]) if name in current else None
        require(actual in (record['before'].get(name),record['after'].get(name)),'New local edits preserved; resolve pending sync for '+name)
    for name in set(record['before'])|set(record['after']):
        target=safe_path(folder,name,governed=False)
        if name not in record['after']:target.unlink(missing_ok=True)
        else:
            data=object_bytes(store,record['after'][name]);target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_name(target.name+'.rw-tmp');require(not temporary.is_symlink(),'Unsafe temp path.');temporary.write_bytes(data);os.replace(temporary,target)
    atomic_write(safe_path(store.root,BASE,governed=False),pretty({'version':1,'files':record['after'],'remote_commit':record['remote_commit'],'at':now()}))
    record.update(status='completed',completed_at=now());atomic_write(safe_path(store.root,'.rw/overleaf/receipts/'+record['id']+'.json',governed=False),pretty(record));path.unlink()
    return {'synchronized':True,'receipt':record['id'],'remote_commit':record['remote_commit'],'changed_files':record['changes']}


def synchronize(store:Store,actor='local-user',*,online=False,approve=False,resolutions=None,allow_deletions=False,transport=None)->dict:
    require(online,'Overleaf requests require --online.');c=config(store);require(c['mode']=='git','Workshop owns synchronization in workshop mode; do not run a second sync engine.')
    require(not safe_path(store.root,PENDING,governed=False).exists(),'Interrupted synchronization: run overleaf recover first.')
    active=store.state['project'].get('latex')
    require(not active or active['directory']==c['directory'],'Active template changed. Reconfigure the remote target explicitly before uploading.')
    channel=transport or GitTransport(store,c);remote,remote_commit=channel.read();local=local_files(store,c)
    path=safe_path(store.root,BASE,governed=False)
    previous=json.loads(read_text(path)) if path.exists() else {'files':{}}
    base={n:object_bytes(store,h) for n,h in previous['files'].items()}
    merged=merge_files(base,local,remote,resolutions=resolutions,allow_deletions=allow_deletions)
    report={k:v for k,v in merged.items() if k!='files'};report.update(synchronized=False,remote_commit=remote_commit,first_sync=not path.exists(),scope=c['directory'])
    if not approve or merged['conflicts']:return report
    if not merged['changes'] and path.exists():return {**report,'synchronized':True,'unchanged':True}
    with project_lock(store.root):
        require(local_files(store,c)==local,'Local source changed after preview; rerun synchronization.')
        after=merged['files'];sync_id=identifier('SYNC')
        record={'id':sync_id,'actor':actor,'at':now(),'directory':c['directory'],'before':{n:put_object(store,b) for n,b in local.items()},
                'after':{n:put_object(store,b) for n,b in after.items()},'previous_remote_commit':remote_commit,'remote_commit':None,'changes':merged['changes'],'status':'prepared'}
        atomic_write(safe_path(store.root,PENDING,governed=False),pretty(record))
        try:commit=channel.push(after,remote_commit) if remote!=after else remote_commit
        except Exception:
            # Do not assume a failed network return means no push happened.
            record['status']='remote-outcome-unknown';atomic_write(safe_path(store.root,PENDING,governed=False),pretty(record));raise
        record.update(remote_commit=commit,status='remote-committed');atomic_write(safe_path(store.root,PENDING,governed=False),pretty(record))
        result=finish_pending(store,expected_remote=commit)
    try:
        from .routing import capture
        result['research_capture']=capture(Store(store.root),'overleaf-sync')
    except ImportError:result['research_capture']='Run rw route after updating the engine.'
    return result


def recover_sync(store:Store,*,online=False,transport=None)->dict:
    require(online,'Recovery validates the current remote; use --online.');c=config(store);channel=transport or GitTransport(store,c)
    remote,commit=channel.read();path=safe_path(store.root,PENDING,governed=False);record=json.loads(read_text(path))
    # Recover an uncertain push only when remote bytes exactly equal the intended result.
    require({n:sha(b) for n,b in remote.items()}==record['after'],'Remote content differs from pending sync; preserve both copies and resolve explicitly.')
    record['remote_commit']=commit;atomic_write(path,pretty(record))
    with project_lock(store.root):return finish_pending(store,expected_remote=commit)


def watch(store:Store,actor: str,*,online=False,approve=False,interval=5,cycles=0)->dict:
    require(online and approve and 2<=interval<=3600 and cycles>=0,'Watch requires --online --approve and an interval of at least 2 seconds.')
    completed=0
    try:
        while not cycles or completed<cycles:
            result=synchronize(Store(store.root),actor,online=True,approve=True)
            if result.get('conflicts'):return {'stopped':'conflict','details':result}
            completed+=1
            if result.get('changed_files'):print(pretty(result),flush=True)
            if not cycles or completed<cycles:time.sleep(interval)
    except KeyboardInterrupt:return {'stopped':'user','cycles':completed}
    return {'stopped':'cycle-limit','cycles':completed}


def bind_replica(store:Store,replica: str,actor: str,*,approve=False)->dict:
    c=config(store);require(c['mode']=='workshop','Replica binding is for Workshop mode.')
    require(replica.startswith('manuscript/'),'Replica must be below manuscript/.')
    folder=safe_path(store.root,replica)
    metadata=json.loads(read_text(safe_path(folder,'.overleaf/settings.json',governed=False)))
    require(metadata.get('serverName')==urllib.parse.urlsplit(c['server']).hostname,'Replica server differs from configured server.')
    uri=urllib.parse.urlsplit(metadata.get('uri',''));query=urllib.parse.parse_qs(urllib.parse.unquote(uri.query))
    require(query.get('project')==[c['project_id']],'Replica project id differs from configured project.')
    active=store.state['project'].get('latex');require(active,'Adopt the manuscript first.')
    old=safe_path(store.root,active['directory']);require(tree_bytes(old)==tree_bytes(folder),'Replica bytes differ from current manuscript. Reconcile before binding; nothing overwritten.')
    if not approve:return {'bind':replica,'applied':False}
    store.state['project']['latex']['directory']=replica;c['directory']=replica
    for node in store.state['nodes'].values():
        if node['kind']=='section' and node['status']!='retired':node['data']['latex_owner']=replica
    store.event('overleaf.replica-bound',actor,{'directory':replica,'project_id':c['project_id']});store.commit()
    atomic_write(safe_path(store.root,CONFIG,governed=False),pretty(c))
    return {'bound':replica,'applied':True,'boundary':'Local metadata and bytes checked; extension owns authenticated live connection.'}


def disconnect(store:Store,*,approve=False)->dict:
    require(approve,'Disconnect requires --approve; no remote files will be deleted.')
    require(not safe_path(store.root,PENDING,governed=False).exists(),'Resolve pending sync before disconnecting.')
    folder=safe_path(store.root,'.rw/overleaf',governed=False)
    backup='.rw/overleaf-archive-'+identifier('BACKUP')
    if folder.exists():folder.rename(safe_path(store.root,backup,governed=False))
    safe_path(store.root,CONFIG,governed=False).unlink(missing_ok=True)
    return {'disconnected':True,'preserved_local_sync_history':backup,'remote_unchanged':True}
