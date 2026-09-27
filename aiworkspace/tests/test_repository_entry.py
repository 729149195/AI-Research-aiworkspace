"""Offline root-entry/distribution checks; no live agent, network or real papers."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pack = load('entry_packager', 'package_delivery.py')
pub = load('entry_publisher', 'create_github_repo.py')


def put(root, path, text='Public synthetic fixture.\n'):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    return target


def distribution(root):
    for name in ('README.md', 'AGENTS.md', 'CLAUDE.md', 'update_aiworkspace.py', '.gitignore',
                 '.github/workflows/research-workspace.yml', '.claude/CLAUDE.md',
                 '.agents/skills/workspace-guide/SKILL.md', 'aiworkspace/pyproject.toml',
                 'aiworkspace/research_workspace/upgrade.py'):
        put(root, name)


class EntryContractCase(unittest.TestCase):
    def test_canonical_root_name(self):
        self.assertTrue((ROOT / 'AGENTS.md').is_file())
        self.assertFalse((ROOT / 'AGENTS.md').is_symlink())
        self.assertFalse((ROOT / 'agent.md').exists())

    def test_claude_imports_resolve_to_one_canonical_file(self):
        for name, relative in [('CLAUDE.md', 'AGENTS.md'), ('.claude/CLAUDE.md', '../AGENTS.md')]:
            path = ROOT / name
            imports = [line[1:] for line in path.read_text(encoding='utf-8').splitlines() if line.startswith('@')]
            self.assertEqual(imports, [relative])
            self.assertEqual((path.parent / imports[0]).resolve(), ROOT / 'AGENTS.md')

    def test_skill_bridge_points_to_root(self):
        path = ROOT / '.agents/skills/workspace-guide/SKILL.md'
        self.assertIn('(../../../AGENTS.md)', path.read_text(encoding='utf-8'))
        self.assertEqual((path.parent / '../../../AGENTS.md').resolve(), ROOT / 'AGENTS.md')

    def test_entry_separates_framework_and_paper_context(self):
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        for phrase in ('First interaction', 'aiworkspace/MENU.md', 'AGENT_PLAYBOOK.md',
                       'not an initialized paper', 'outside this checkout',
                       'Source text', 'Capture is not completion', 'no agent, service, hook'):
            self.assertIn(phrase, text)
        self.assertLess(len(text.encode('utf-8')), 10000)

    def test_readme_remains_a_nonterminal_entry(self):
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('(AGENTS.md)', text)
        self.assertIn('(CLAUDE.md)', text)
        self.assertIn('REPOSITORY_LAYOUT.md', text)
        for value in ('```bash', '```powershell', 'pip install ', 'git clone '):
            self.assertNotIn(value, text)


class IgnoreCase(unittest.TestCase):
    def test_real_git_excludes_personal_files_but_not_shared_entries(self):
        private = ['.claude/settings.local.json', 'nested/.claude/settings.local.json',
                   'CLAUDE.local.md', 'nested/CLAUDE.local.md', '.claude/.credentials.json',
                   '.claude/history.jsonl', '.claude/projects/a/transcript.jsonl',
                   '.claude/debug/session.log', '.agents/.credentials.json', '.env',
                   '.env.local', '.rw/overleaf.json', 'workspace/state.json', 'manuscript/main.tex']
        public = ['AGENTS.md', 'CLAUDE.md', '.claude/CLAUDE.md', '.claude/settings.json',
                  '.claude/skills/example/SKILL.md', '.agents/skills/workspace-guide/SKILL.md',
                  '.github/workflows/research-workspace.yml', 'aiworkspace/docs/REPOSITORY_LAYOUT.md']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            put(root, '.gitignore', (ROOT / '.gitignore').read_text(encoding='utf-8'))
            # Local Git only. Do not inherit repository routing or credential settings.
            env = {key: value for key, value in os.environ.items() if key in ('PATH', 'SYSTEMROOT', 'TMP', 'TEMP')}
            env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
            subprocess.run(['git', 'init', '--quiet', '--template=', str(root)], env=env, check=True)
            result = subprocess.run(['git', '-c', 'core.excludesFile=' + os.devnull, '-C', str(root),
                                     'check-ignore', '--no-index', '--stdin'],
                                    input='\n'.join(private + public) + '\n', text=True,
                                    capture_output=True, env=env, check=True)
            self.assertEqual(set(result.stdout.splitlines()), set(private))


class DistributionCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'source'
        distribution(self.root)

    def test_publisher_accepts_new_root_entries(self):
        with patch.object(pub, 'call', side_effect=AssertionError('No network allowed')):
            names = set(pub.payload(self.root))
        self.assertIn('AGENTS.md', names)
        self.assertIn('CLAUDE.md', names)

    def test_publisher_rejects_personal_host_settings(self):
        put(self.root, '.claude/settings.local.json', '{"fixture":true}')
        with self.assertRaises(pub.PublishError):
            pub.payload(self.root)

    def test_publisher_rejects_nested_private_settings(self):
        for name in ('CLAUDE.local.md', 'settings.local.json', '.credentials.json', 'credentials.json', 'secrets.json'):
            with self.subTest(name=name):
                target = put(self.root, 'aiworkspace/temporary/' + name)
                with self.assertRaises(pub.PublishError):
                    pub.payload(self.root)
                target.unlink()

    def test_source_zip_has_both_roots_and_only_explicit_host_files(self):
        put(self.root, '.claude/settings.local.json', 'PRIVATE_SYNTHETIC_SENTINEL')
        put(self.root, '.claude/projects/session/transcript.jsonl', 'PRIVATE_SYNTHETIC_SENTINEL')
        put(self.root, '.rw/overleaf.json', 'PRIVATE_SYNTHETIC_SENTINEL')
        put(self.root, 'aiworkspace/.rw/local-session.json', 'PRIVATE_SYNTHETIC_SENTINEL')
        dest = self.base / 'delivery'
        with patch.object(pack, 'ROOT', self.root), patch.object(pack, 'PACKAGE', self.root / 'aiworkspace'), \
             patch('sys.argv', ['packager', '--destination', str(dest)]), patch('builtins.print'):
            self.assertEqual(pack.main(), 0)
        with ZipFile(dest / 'aiworkspace-source.zip') as archive:
            names = set(archive.namelist())
            for name in ('AGENTS.md', 'CLAUDE.md', '.claude/CLAUDE.md', '.agents/skills/workspace-guide/SKILL.md'):
                self.assertIn(name, names)
                self.assertEqual(archive.read(name), (self.root / name).read_bytes())
            self.assertNotIn('.claude/settings.local.json', names)
            self.assertNotIn('.rw/overleaf.json', names)
            self.assertFalse(any(b'PRIVATE_SYNTHETIC_SENTINEL' in archive.read(n) for n in names))

    def test_zip_rejects_private_files_inside_package(self):
        for name in ('CLAUDE.local.md', 'settings.local.json', '.credentials.json', 'credentials.json', 'secrets.json'):
            with self.subTest(name=name):
                target = put(self.root, 'aiworkspace/temporary/' + name)
                with self.assertRaises(ValueError):
                    pack.archive(self.root / 'aiworkspace', self.base / 'rejected.zip', 'aiworkspace')
                target.unlink()

    def test_zip_requires_root_bootstrap_files(self):
        (self.root / 'AGENTS.md').unlink()
        with patch.object(pack, 'ROOT', self.root), patch.object(pack, 'PACKAGE', self.root / 'aiworkspace'), \
             patch('sys.argv', ['packager', '--destination', str(self.base / 'delivery')]):
            with self.assertRaises(ValueError):
                pack.main()


if __name__ == '__main__':
    unittest.main()
