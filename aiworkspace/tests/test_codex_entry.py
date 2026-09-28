"""Codex entry/distribution contracts; no live Codex process or model is exercised."""
from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
META = '.agents/skills/workspace-guide/agents/openai.yaml'
EXTRAS = ['README.md', 'AGENTS.md', 'CLAUDE.md', 'update_aiworkspace.py', '.gitignore',
          '.github/workflows/research-workspace.yml', '.agents/skills/workspace-guide/SKILL.md',
          META, '.claude/CLAUDE.md']


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pub = load('codex_test_publisher', 'aiworkspace/scripts/create_github_repo.py')
pkg = load('codex_test_packager', 'aiworkspace/scripts/package_delivery.py')


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def fixture(root):
    for name in EXTRAS:
        write(root, name, (ROOT / META).read_text(encoding='utf-8') if name == META else 'public fixture\n')
    for name in ('aiworkspace/pyproject.toml', 'aiworkspace/research_workspace/upgrade.py'):
        write(root, name, '# Minimal publication fixture; not an installed research engine.\n')


class CodexEntryCase(unittest.TestCase):
    def test_root_has_explicit_codex_entry_without_new_authority(self):
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        for value in ('## Codex entry', '.agents/skills/workspace-guide/SKILL.md',
                      'aiworkspace/docs/CODEX.md', 'grants no execution permission',
                      'Claude hooks only'):
            self.assertIn(value, text)

    def test_readme_names_codex_and_keeps_natural_language_start(self):
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('| **Codex** |', text)
        self.assertIn('Codex 专门指引', text)
        self.assertIn('显示菜单', text)
        for value in ('```bash', 'pip install ', 'git clone '):
            self.assertNotIn(value, text)

    def test_metadata_has_only_expected_passive_fields(self):
        # Restricted contract for this deliberately small checked-in YAML mapping.
        lines = (ROOT / META).read_text(encoding='utf-8').splitlines()
        self.assertEqual([line for line in lines if not line.startswith(' ')], ['interface:', 'policy:'])
        strings = {}
        for line in lines:
            match = re.fullmatch(r'  (display_name|short_description|default_prompt): (".*")', line)
            if match:
                strings[match.group(1)] = json.loads(match.group(2))
        self.assertEqual(set(strings), {'display_name', 'short_description', 'default_prompt'})
        self.assertIn('AI Workspace', strings['display_name'])
        self.assertIn('$workspace-guide', strings['default_prompt'])
        self.assertEqual(lines[-1], '  allow_implicit_invocation: true')
        self.assertEqual(len(lines), 6)

    def test_one_shared_guide_and_portable_root_link(self):
        skill = ROOT / '.agents/skills/workspace-guide/SKILL.md'
        text = skill.read_text(encoding='utf-8')
        self.assertIn('name: workspace-guide', text)
        self.assertEqual((skill.parent / '../../../AGENTS.md').resolve(), ROOT / 'AGENTS.md')
        self.assertIn('menu browsing is read-only', text)

    def test_codex_doc_separates_hooks_and_metadata_from_permissions(self):
        text = (ROOT / 'aiworkspace/docs/CODEX.md').read_text(encoding='utf-8')
        for value in ('.codex/config.toml', 'Claude 专用安装器', '未运行真实 Codex',
                      '现有论文安装器仍分发 SKILL.md', '不关闭沙箱'):
            self.assertIn(value, text)
        for page in ('guides/agents-md', 'skills', 'config-basic', 'hooks'):
            self.assertIn('https://developers.openai.com/codex/' + page, text)

    def test_publisher_accepts_metadata_without_changing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fixture(root)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            files = pub.payload(root)
            self.assertIn(META, files)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_publisher_rejects_unlisted_skill_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fixture(root)
            write(root, '.agents/skills/workspace-guide/agents/private.json', '{"private":"fixture"}')
            with self.assertRaises(pub.PublishError):
                pub.payload(root)

    def test_publisher_rejects_codex_account_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fixture(root)
            write(root, '.codex/auth.json', '{"private":"fixture-not-a-real-credential"}')
            with self.assertRaises(pub.PublishError):
                pub.payload(root)

    def test_real_zip_contains_metadata_but_no_root_personal_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root = base / 'source'; root.mkdir(); fixture(root)
            write(root, '.codex/auth.json', 'PRIVATE_FIXTURE')
            write(root, '.claude/settings.local.json', 'PRIVATE_FIXTURE')
            destination = base / 'delivery'
            with patch.object(pkg, 'ROOT', root), patch.object(pkg, 'PACKAGE', root / 'aiworkspace'), \
                 patch('sys.argv', ['package_delivery', '--destination', str(destination)]), redirect_stdout(io.StringIO()):
                self.assertEqual(pkg.main(), 0)
            with zipfile.ZipFile(destination / 'aiworkspace-source.zip') as archive:
                self.assertEqual(archive.read(META), (ROOT / META).read_bytes())
                self.assertTrue(set(EXTRAS) <= set(archive.namelist()))
                self.assertNotIn('.codex/auth.json', archive.namelist())
                self.assertNotIn('.claude/settings.local.json', archive.namelist())
                self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))

    def test_packager_refuses_symlinked_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fixture(root)
            path = root / META; path.unlink(); path.symlink_to(root / 'README.md')
            with patch.object(pkg, 'ROOT', root), self.assertRaises(ValueError):
                pkg.archive(root / 'aiworkspace', root / 'fixture.zip', 'aiworkspace', extra=[path])


if __name__ == '__main__':
    unittest.main()
