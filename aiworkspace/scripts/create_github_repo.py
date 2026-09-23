#!/usr/bin/env python3
"""Publish a NEW standalone repository through the user's locally authenticated gh CLI.

Default mode is an offline, read-only preview. --publish plus --public/--private
is required to initialize Git and create/push the remote. This script never
uses, modifies, deletes, forks, renames or force-pushes an existing repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWNER = '729149195'
NAME = 'AI-Research-aiworkspace'
TARGET = OWNER + '/' + NAME
ALLOWED_ROOT = {'aiworkspace', 'README.md', 'update_aiworkspace.py', '.gitignore', '.github'}
SKIP = {'.venv', '__pycache__', '.pytest_cache', 'build', 'dist'}


class PublishError(RuntimeError):
    """Publication stopped without modifying any pre-existing repository."""


def require(ok: bool, text: str) -> None:
    if not ok:
        raise PublishError(text)


def payload(root: Path) -> list[str]:
    """Enumerate the explicit framework files; never 'git add' arbitrary user work."""
    require(root.is_dir() and not root.is_symlink(), 'Use an extracted source directory.')
    require(not (root / '.git').exists(), 'A .git already exists. Refusing to reuse repository history.')
    files = []
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if any(x in SKIP or x.endswith('.egg-info') for x in rel.parts):
            continue
        require(not p.is_symlink(), 'Symlinks must not be published: ' + rel.as_posix())
        require(rel.parts[0] in ALLOWED_ROOT, 'Unexpected root entry: ' + rel.as_posix())
        require(not any(x in ('.git', '.rw', 'workspace', 'manuscript') for x in rel.parts),
                'Research or nested Git data detected: ' + rel.as_posix())
        require(not any(x.startswith('.env') for x in rel.parts), 'Environment files must not be published.')
        if p.is_file():
            require(p.suffix.lower() not in ('.ppt', '.pptx', '.pyc', '.pem', '.key'),
                    'Private/binary material detected: ' + rel.as_posix())
            files.append(rel.as_posix())
    required = {'README.md', 'update_aiworkspace.py', 'aiworkspace/pyproject.toml',
                'aiworkspace/research_workspace/upgrade.py'}
    require(required <= set(files), 'Incomplete standalone framework.')
    require(len(files) <= 1000 and sum((root / f).stat().st_size for f in files) <= 64 * 1024 * 1024,
            'Distribution exceeds publisher limits.')
    return files


def file_hashes(root: Path, files: list[str]) -> dict[str, str]:
    return {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files}


def call(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(GH_HOST='github.com', GH_PROMPT_DISABLED='1', GIT_TERMINAL_PROMPT='0')
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=180, check=False)


def checked(args: list[str], root: Path) -> str:
    result = call(args, root)
    require(result.returncode == 0, 'Command failed: ' + ' '.join(args[:3]) + '\n' + result.stderr[-2000:])
    return result.stdout.strip()


def git(root: Path, *args: str) -> str:
    hooks = 'NUL' if sys.platform == 'win32' else '/dev/null'
    return checked(['git', '-c', 'core.hooksPath=' + hooks, '-C', str(root), *args], root)


def publish(root: Path, files: list[str], visibility: str) -> dict:
    require(visibility in ('public', 'private'), 'Choose --public or --private explicitly.')
    require(shutil.which('git') and shutil.which('gh'), 'Install Git and GitHub CLI (gh) first.')
    # Inherited Git environment could redirect writes into an unrelated repository.
    require(not any(os.environ.get(k) for k in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE',
                'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES')),
            'Clear inherited Git repository environment variables before publishing.')
    parent = call(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], root)
    require(parent.returncode != 0, 'This directory is inside an existing Git checkout. Extract outside it.')
    account = json.loads(checked(['gh', 'api', '--hostname', 'github.com', 'user'], root))
    require(account.get('login') == OWNER, 'Log in as ' + OWNER + ' locally; do not send tokens to a chat.')
    require(isinstance(account.get('id'), int), 'GitHub did not return a numeric account ID.')
    probe = call(['gh', 'api', '--hostname', 'github.com', '--include', 'repos/' + TARGET], root)
    require(probe.returncode != 0, 'Target repository already exists. It will not be overwritten.')
    require(re.search(r'HTTP/\S+\s+404\b', probe.stdout) is not None,
            'Could not confirm a 404 for the target. Fix authentication/network access before retrying.')
    before = file_hashes(root, files)
    require(payload(root) == files, 'Files changed during preflight; preview again.')
    git(root, 'init', '--initial-branch=main', '--template=')
    git(root, 'config', '--local', 'user.name', OWNER)
    git(root, 'config', '--local', 'user.email', str(account['id']) + '+' + OWNER + '@users.noreply.github.com')
    git(root, 'add', '--', *files)
    tracked = set(git(root, 'ls-files').splitlines())
    require(tracked == set(files), 'The staged files differ from the reviewed payload. Inspect local Git; nothing pushed.')
    require(file_hashes(root, files) == before, 'Files changed before commit. Nothing pushed.')
    git(root, '-c', 'commit.gpgsign=false', 'commit', '-m', 'Initial standalone AI Research Workspace')
    local_sha = git(root, 'rev-parse', 'HEAD')
    result = call(['gh', 'repo', 'create', TARGET, '--' + visibility, '--source', str(root),
                   '--remote', 'origin', '--push', '--description',
                   'Local-first AI research workspace with evidence, manuscript sync and safe incremental updates'], root)
    require(result.returncode == 0,
            'Creation/push did not complete. Local files are preserved; the new remote may already exist. '
            'Inspect gh repo view ' + TARGET + ' and local git status; do not run a force push.\n' + result.stderr[-2000:])
    info = json.loads(checked(['gh', 'api', '--hostname', 'github.com', 'repos/' + TARGET], root))
    require(info.get('full_name') == TARGET and info.get('private') == (visibility == 'private'),
            'Remote identity or visibility did not match; inspect the new repository.')
    ref = json.loads(checked(['gh', 'api', '--hostname', 'github.com', 'repos/' + TARGET + '/git/ref/heads/main'], root))
    require(ref.get('object', {}).get('sha') == local_sha, 'Push could not be verified against main.')
    return {'created_and_pushed': True, 'repository': TARGET, 'commit': local_sha,
            'visibility': visibility, 'url': info.get('html_url'), 'old_repositories_modified': False,
            'ci': 'Check Actions on this exact commit; publication does not establish a CI pass.'}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--publish', action='store_true', help='Create a NEW repository and push the source')
    v = p.add_mutually_exclusive_group()
    v.add_argument('--public', action='store_true', help='Explicitly publish the framework publicly')
    v.add_argument('--private', action='store_true', help='Create a private framework repository')
    a = p.parse_args(argv)
    try:
        files = payload(ROOT)
        if not a.publish:
            report = {'mode': 'offline_preview', 'repository_to_create': TARGET,
                      'files': files, 'sha256': file_hashes(ROOT, files),
                      'remote_created': False, 'old_repositories_modified': False,
                      'next': 'Review source, then use --publish --public or --publish --private with locally authenticated gh.'}
        else:
            require(a.public or a.private, 'Explicit --public or --private is required with --publish.')
            report = publish(ROOT, files, 'public' if a.public else 'private')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (PublishError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'error': str(exc), 'publication_confirmed': False,
                          'recovery': 'See aiworkspace/docs/NEW_REPOSITORY.md. No existing repository was deleted, reused or force-pushed.'},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
