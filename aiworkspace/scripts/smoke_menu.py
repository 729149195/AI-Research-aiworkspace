#!/usr/bin/env python3
"""Actual isolated setup/menu exercise using a minimal, clearly named test distribution.

No network or real paper is used. This validates the new helper, not all research
features or a live agent's interpretation. Existing build tools seed the test venv.
"""
from __future__ import annotations
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def main() -> int:
    spec = importlib.util.spec_from_file_location('prepare_smoke', PACKAGE / 'scripts/prepare_agent.py')
    prep = importlib.util.module_from_spec(spec); spec.loader.exec_module(prep)
    with tempfile.TemporaryDirectory(prefix='rw-menu-smoke-') as tmp:
        base = Path(tmp); root = base / 'framework'; module = root / 'aiworkspace/research_workspace'
        (module / 'assets').mkdir(parents=True)
        shutil.copy2(PACKAGE / 'research_workspace/menu.py', module / 'menu.py')
        shutil.copy2(PACKAGE / 'research_workspace/assets/menu.json', module / 'assets/menu.json')
        (module / '__init__.py').write_text('__version__ = "0.4.0+menu-fixture"\n')
        (root / 'aiworkspace/pyproject.toml').write_text('''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "ai-workspace-menu-smoke-fixture"
version = "0.4.0+menu-fixture"
[tool.setuptools.packages.find]
include = ["research_workspace*"]
[tool.setuptools.package-data]
research_workspace = ["assets/*.json"]
''')
        before = sorted(str(p) for p in root.rglob('*'))
        assert not prep.prepare(root)['applied']
        assert before == sorted(str(p) for p in root.rglob('*'))
        subprocess.run([sys.executable, '-m', 'venv', str(root / '.venv')], check=True, capture_output=True)
        python = root / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        purelib = Path(subprocess.check_output([str(python), '-c', "import sysconfig;print(sysconfig.get_path('purelib'))"], text=True).strip())
        for name in ('setuptools', 'wheel'):
            try:
                distribution = importlib.metadata.distribution(name)
            except importlib.metadata.PackageNotFoundError:
                vendor = Path(importlib.metadata.distribution('setuptools').locate_file('setuptools/_vendor'))
                distribution = next((d for d in importlib.metadata.distributions(path=[str(vendor)]) if d.metadata['Name'].lower() == name), None)
                if distribution is None:
                    raise RuntimeError('Local build-tool distribution missing: ' + name)
            for entry in distribution.files or []:
                if '..' in Path(str(entry)).parts: continue
                source = Path(distribution.locate_file(entry))
                if source.is_file():
                    target = purelib / str(entry); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        result = prep.prepare(root, approve=True)
        assert result['applied'] and not result['download_authorized']
        study = base / 'used-paper'; (study / 'workspace').mkdir(parents=True); (study / 'manuscript').mkdir()
        state = {'schema_version': 1, 'project': {'name': 'Synthetic menu walkthrough'}, 'tasks': [], 'issues': {}}
        (study / 'workspace/state.json').write_text(json.dumps(state))
        (study / 'manuscript/main.md').write_text('Synthetic existing manuscript; do not overwrite.\n')
        original = {p.relative_to(study).as_posix(): p.read_bytes() for p in study.rglob('*') if p.is_file()}
        command = [str(python), '-I', '-B', '-m', 'research_workspace.menu', '--project', str(study)]
        display = subprocess.check_output(command, cwd=base, text=True)
        assert '新建论文' in display and 'Synthetic menu walkthrough' in display
        selected = json.loads(subprocess.check_output(command + ['--select', '7', '--menu-reply'], cwd=base, text=True))
        assert selected['selection']['item']['id'] == 'transfer' and selected['side_effects'] == []
        assert original == {p.relative_to(study).as_posix(): p.read_bytes() for p in study.rglob('*') if p.is_file()}
    print(json.dumps({'passed': True, 'actual_venv_install': True, 'isolated_menu_process': True,
                      'read_only_preview': True, 'numbered_selection': True, 'study_bytes_preserved': True,
                      'network_used': False, 'fixture': 'Minimal menu module test package, not a complete 0.4.0 distribution',
                      'live_agent_session': 'not_run'}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
