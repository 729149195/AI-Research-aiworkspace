#!/usr/bin/env python3
"""Agent-only local request/packaging helper. No browser, HTTP, Git or login client.

The user speaks naturally. The agent runs this helper and invokes the returned
editor URI using its authorized local tools. Only Workshop owns the connection.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse
import uuid
import zipfile

EXTENSION = 'aiworkspace-local.overleaf-assistant'
FILES = ('package.json', 'extension.js', 'probe.js', 'LICENSE')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and relative and not relative.startswith('/') and
            '\\' not in relative and ':' not in relative and
            all(p not in ('', '.', '..') for p in relative.split('/')), 'Unsafe local relative path.')
    require(root.is_dir() and not root.is_symlink(), 'Open a real local project directory.')
    p = root
    for part in relative.split('/'):
        p = p / part
        require(not p.is_symlink(), 'Symlinks are not allowed for this check.')
    return p


def target(url: str) -> dict:
    require(isinstance(url, str) and len(url) < 4000 and not any(ord(c) <= 32 or ord(c) == 127 for c in url), 'Invalid project URL.')
    u = urllib.parse.urlsplit(url)
    require(u.scheme == 'https' and u.hostname and not u.username and not u.password and
            not u.query and not u.fragment, 'Use the normal HTTPS project URL without secrets or sharing tokens.')
    m = re.fullmatch(r'/project/([A-Za-z0-9_-]{1,128})/?', u.path)
    require(m is not None, 'Select an actual Overleaf project, not a homepage or share link.')
    _ = u.port  # Validate the port; retain self-hosted ports without guessing.
    return {'server': urllib.parse.urlunsplit(('https', u.netloc.lower(), '', '', '')),
            'project_id': m.group(1)}


def read_json(file: Path):
    require(file.is_file() and not file.is_symlink() and file.stat().st_size <= 1_000_000, 'Missing or invalid local record.')
    value = json.loads(file.read_text(encoding='utf-8'))
    require(isinstance(value, dict), 'Local record must be an object.')
    return value


def prepare(root: Path, url: str, *, main: str | None = None, directory: str | None = None, mode='read') -> dict:
    target(url)
    require(mode in ('read', 'roundtrip'), 'Unsupported check mode.')
    # Existing explicitly bound scope wins over a new default. No reinitialization.
    if directory is None:
        config = safe(root, '.rw/overleaf.json')
        if config.exists():
            c = read_json(config)
            require(c.get('mode') == 'workshop', 'An existing non-Workshop binding needs an explicit migration decision.')
            t = target(url)
            require(isinstance(c.get('server'), str) and c['server'].rstrip('/') == t['server'] and c.get('project_id') == t['project_id'], 'An existing binding points at another project.')
            directory = c.get('directory')
        else:
            directory = 'manuscript'
    require(isinstance(directory, str) and (directory == 'manuscript' or directory.startswith('manuscript/')), 'Limit the check to the manuscript.')
    require(all(not p.startswith('.') for p in directory.split('/')), 'Hidden manuscript scope is refused.')
    folder = safe(root, directory)
    if not safe(folder, '.overleaf/settings.json').exists():
        return {'status': 'awaiting_workshop_replica', 'verified': False, 'directory': directory,
                'next': 'Agent must create/reuse the real Workshop Replica through the editor, preserving any existing manuscript. Do not download through a browser or fabricate metadata.'}
    if main is None:
        candidates = []
        for f in sorted(folder.rglob('*.tex')):
            rel = f.relative_to(folder).as_posix()
            if any(p.startswith('.') for p in rel.split('/')): continue
            file = safe(folder, rel)
            if file.stat().st_size <= 2_000_000:
                text = file.read_bytes().decode('utf-8-sig', errors='replace')
                if re.search(r'(?m)^[ \t]*\\documentclass(?:\[|\{)', text): candidates.append(rel)
        if len(candidates) != 1:
            return {'status': 'needs_main_selection', 'candidates': candidates, 'verified': False,
                    'next': 'Agent selects the actual compiled main from project context, or asks one necessary question.'}
        main = candidates[0]
    require(isinstance(main, str) and all(not p.startswith('.') for p in main.split('/')) and main.endswith('.tex') and safe(folder, main).is_file(), 'Select the existing compiled main file.')
    request_id = uuid.uuid4().hex
    record = {'version': 1, 'id': request_id, 'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'project_url': url, 'directory': directory, 'main': main, 'mode': mode}
    file = safe(root, f'.rw/overleaf-agent/requests/{request_id}.json')
    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with file.open('x', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    try: file.chmod(0o600)
    except OSError: pass
    return {'status': 'request_prepared', 'verified': False, 'request_id': request_id,
            'launch_uri': f'vscode://{EXTENSION}/check?id={request_id}',
            'next': 'Agent invokes the URI in the selected local editor. The extension asks for scoped approval and writes a report. Preparing a request does not contact Overleaf.'}


def status(root: Path, request_id: str) -> dict:
    require(re.fullmatch(r'[a-f0-9]{32}', request_id) is not None, 'Invalid request ID.')
    req = read_json(safe(root, f'.rw/overleaf-agent/requests/{request_id}.json'))
    path = safe(root, f'.rw/overleaf-agent/reports/{request_id}.json')
    if not path.exists(): return {'status': 'awaiting_editor', 'verified': False, 'request_id': request_id}
    r = read_json(path)
    require(r.get('id') == request_id and r.get('version') == 1, 'Mismatched editor report.')
    if r.get('verified'):
        t = target(req['project_url'])
        require(req['mode'] == 'roundtrip' and r.get('status') == 'roundtrip_verified' and
                r.get('transport') == 'iamhyc.overleaf-workshop' and
                all(r.get(k) is True for k in ('local_to_remote', 'remote_to_local', 'cleanup', 'metadata_matched')) and
                all(r.get(k) == v for k, v in t.items()) and
                all(r.get(k) == req[k] for k in ('directory', 'main')) and
                r.get('before_hashes') == r.get('after_hashes') and r.get('before_hashes'),
                'Incomplete verification evidence; do not report success.')
        finished = dt.datetime.fromisoformat(r['finished_at'])
        age = (dt.datetime.now(dt.timezone.utc) - finished).total_seconds()
        require(age >= -60, 'Invalid report timestamp.')
        changed = []
        folder = safe(root, req['directory'])
        current = {}; total = 0
        for f in sorted(folder.rglob('*')):
            relative = f.relative_to(folder).as_posix()
            if any(p.startswith('.') for p in relative.split('/')): continue
            safe(folder, relative)
            if not f.is_file(): continue
            total += f.stat().st_size
            require(total <= 100663296 and f.stat().st_size <= 33554432 and len(current) < 2000, 'Current manuscript exceeds check limits.')
            current[relative] = hashlib.sha256(f.read_bytes()).hexdigest()
        changed = sorted(n for n in set(current) | set(r['after_hashes']) if current.get(n) != r['after_hashes'].get(n))
        meta = safe(folder, '.overleaf/settings.json')
        if not meta.is_file() or hashlib.sha256(meta.read_bytes()).hexdigest() != r.get('replica_binding_sha256'):
            changed.append('replica_binding')
        r['historical'] = age > 900 or bool(changed)
        r['changed_since_check'] = changed
        r['note'] = 'This is a local, time-scoped observation record, not a signed server attestation or a guarantee of future connectivity.'
    return r


def build_vsix(output: Path) -> dict:
    source = Path(__file__).resolve().parents[1] / 'integrations/overleaf-assistant'
    blobs = {name: safe(source, name).read_bytes() for name in FILES}
    metadata = json.loads(blobs['package.json'])
    require(metadata['name'] == 'overleaf-assistant' and metadata['publisher'] == 'aiworkspace-local', 'Unexpected extension identity.')
    require(not output.exists() and not output.is_symlink(), 'Use a new VSIX destination.')
    output.parent.mkdir(parents=True, exist_ok=True)
    types = '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/><Default Extension="js" ContentType="application/javascript"/><Default Extension="vsixmanifest" ContentType="text/xml"/><Override PartName="/extension/LICENSE" ContentType="text/plain"/></Types>'
    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
<Metadata><Identity Language="en-US" Id="overleaf-assistant" Version="{metadata['version']}" Publisher="aiworkspace-local"/><DisplayName>AI Workspace Overleaf Connection Check</DisplayName><Description xml:space="preserve">A locally built, agent-triggered Workshop verifier.</Description><Tags>overleaf,verification</Tags><Categories>Other</Categories><GalleryFlags>Public</GalleryFlags><Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.85.0"/><Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace"/></Properties></Metadata>
<Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/>
<Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>'''
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', types)
        z.writestr('extension.vsixmanifest', manifest)
        for name, data in blobs.items(): z.writestr('extension/' + name, data)
    return {'package': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'installed': False, 'marketplace_published': False,
            'next': 'Agent reviews and installs this local VSIX only after approval; real editor acceptance is separate from ZIP validation.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', default='.')
    s = p.add_subparsers(dest='action', required=True)
    q = s.add_parser('prepare'); q.add_argument('url'); q.add_argument('--main'); q.add_argument('--directory'); q.add_argument('--mode', choices=['read', 'roundtrip'], default='read')
    q = s.add_parser('status'); q.add_argument('request_id')
    q = s.add_parser('build'); q.add_argument('--output', required=True)
    a = p.parse_args(argv)
    try:
        root = Path(a.project).expanduser().absolute()
        result = prepare(root, a.url, main=a.main, directory=a.directory, mode=a.mode) if a.action == 'prepare' else status(root, a.request_id) if a.action == 'status' else build_vsix(Path(a.output).expanduser().absolute())
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({'error': str(e), 'verified': False}, ensure_ascii=False), file=sys.stderr); return 2

if __name__ == '__main__': raise SystemExit(main())
