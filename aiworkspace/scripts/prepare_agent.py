#!/usr/bin/env python3
"""Agent-only environment preparation. Preview by default; no global installation.

Users give natural-language approval to their agent, which invokes this helper.
No paper, credential store, host permission file, or remote project is modified.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

class SetupError(ValueError):
    pass

def layout(root: Path) -> tuple[Path, Path, Path]:
    root = root.resolve()
    package = root / 'aiworkspace'
    if any(p.is_symlink() for p in (package, package / 'pyproject.toml', package / 'research_workspace', package / 'research_workspace/assets')):
        raise SetupError('框架入口包含符号链接；请检查真实源码位置。')
    if not (package / 'pyproject.toml').is_file() or not (package / 'research_workspace/assets').is_dir():
        raise SetupError('未找到框架目录；请由 agent 在已下载的框架中检查。')
    venv = root / '.venv'
    cfg = venv / 'pyvenv.cfg'
    if venv.is_symlink() or (venv.exists() and not venv.is_dir()) or cfg.is_symlink():
        raise SetupError('已有 .venv 路径不安全；保留原文件并检查。')
    if venv.exists() and any(venv.iterdir()) and not cfg.is_file():
        raise SetupError('.venv 已有其他内容，停止以免覆盖；请由 agent 另行处理。')
    bindir = venv / ('Scripts' if sys.platform == 'win32' else 'bin')
    if bindir.is_symlink():
        raise SetupError('虚拟环境目录指向符号链接；请检查。')
    return package, venv, bindir / ('python.exe' if sys.platform == 'win32' else 'python')

def _run(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=180, check=False)
    except subprocess.TimeoutExpired as exc:
        raise SetupError('环境准备超时，已保留现有目录；未修改论文。') from exc
    if result.returncode:
        raise SetupError('环境准备中的本地命令未成功（退出码 ' + str(result.returncode) + '）；保留环境并检查，未修改论文。')
    return result.stdout

def prepare(root: Path = ROOT, *, approve: bool = False, allow_download: bool = False) -> dict:
    if sys.version_info < (3, 11):
        raise SetupError('需要 Python 3.11 或更新版本；请由 agent 协助检查本机安装。')
    root = root.resolve()
    package, venv, python = layout(root)
    report = {'applied': False, 'environment': str(venv), 'package': str(package),
              'download_authorized': allow_download,
              'plan': ['在框架目录准备独立 Python 环境', '仅安装本地框架及必要构建工具', '检查菜单模块入口'],
              'boundary': 'No study creation, manuscript edits, host permissions, model calls, credentials or uploads.'}
    if not approve:
        return report
    if not (venv / 'pyvenv.cfg').exists():
        _run([sys.executable, '-m', 'venv', str(venv)], root)
    if not python.is_file():
        raise SetupError('虚拟环境缺少可用解释器；保留环境，请由 agent 修复。')
    probe = """import importlib.metadata as m, json
missing=[]
for name in ('setuptools','wheel'):
    try:
        version=m.version(name)
        if name=='setuptools' and int(version.split('.')[0])<68: missing.append(name)
    except (m.PackageNotFoundError, ValueError): missing.append(name)
print(json.dumps(missing))"""
    missing = json.loads(_run([str(python), '-I', '-B', '-c', probe], root))
    if missing:
        if not allow_download:
            raise SetupError('独立环境缺少构建工具；需要确认下载后才能继续。已保留环境，未修改论文。')
        _run([str(python), '-I', '-m', 'pip', '--isolated', 'install', 'setuptools>=68', 'wheel'], root)
    _run([str(python), '-I', '-m', 'pip', '--isolated', 'install', '--no-deps',
          '--no-build-isolation', '-e', str(package)], root)
    check = "import json,research_workspace; from research_workspace.menu import catalog; print(json.dumps({'version':research_workspace.__version__,'module':research_workspace.__file__,'menu_items':len(catalog()['items'])}))"
    installed = json.loads(_run([str(python), '-I', '-B', '-c', check], root))
    expected = package / 'research_workspace/__init__.py'
    if Path(installed['module']).resolve() != expected.resolve() or installed['menu_items'] != 10:
        raise SetupError('安装结果与当前框架不一致；请由 agent 检查，未修改论文。')
    return {**report, 'applied': True, 'python': str(python), 'version': installed['version'],
            'next': 'Agent can continue the selected workflow using this interpreter; no shell activation needed.'}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approve', action='store_true')
    parser.add_argument('--allow-download', action='store_true', help='Explicit permission for required build-tool downloads only')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(approve=args.approve, allow_download=args.allow_download), ensure_ascii=False, indent=2))
        return 0
    except (SetupError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({'error': str(exc), 'study_untouched': True}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
