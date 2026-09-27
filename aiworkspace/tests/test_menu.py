"""Menu/guide regression tests. No model, account, remote upload or scientific approval."""
from __future__ import annotations
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

menu = load('menu_under_test', PACKAGE / 'research_workspace/menu.py')
prep = load('prepare_under_test', PACKAGE / 'scripts/prepare_agent.py')
pub = load('publisher_menu_test', PACKAGE / 'scripts/create_github_repo.py')

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')

def state():
    return {'schema_version': 1, 'revision': 0, 'project': {'name': 'Already used paper', 'mode': 'research'},
            'tasks': [{'status': 'open'}, {'status': 'done'}], 'issues': {'ISS-1': {'status': 'open'}},
            'nodes': {}, 'proposals': {}, 'events': [], 'approvals': [], 'writers': [], 'sync': {}}

class MenuCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.study = self.base / 'paper'
        write(self.study / 'workspace/state.json', json.dumps(state()))
        write(self.study / 'manuscript/main.md', 'Existing real work is a fixture here.\n')
    def snapshot(self):
        return {p.relative_to(self.base).as_posix(): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
    def test_ten_stable_numbers(self):
        self.assertEqual([i['number'] for i in menu.catalog()['items']], list('1234567890'))
    def test_all_menu_skills_are_registered(self):
        module = ast.parse((PACKAGE / 'research_workspace/skills.py').read_text())
        names = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SKILLS' for t in n.targets))
        self.assertIn('workspace-guide', names)
        self.assertEqual(len(names), 14)
        self.assertTrue({s for i in menu.catalog()['items'] for s in i['skills']} <= set(names))
    def test_plain_menu_has_no_commands_or_configuration_homework(self):
        text = menu.render()
        for token in ('```', 'rw ', 'python ', '--approve', 'PROP-', 'state.json'):
            self.assertNotIn(token, text)
    def test_static_copies_match_catalogue(self):
        rendered = menu.render({'state': 'not_read', 'label': '尚未读取项目状态'})
        self.assertEqual((PACKAGE / 'MENU.md').read_text(), rendered)
        self.assertEqual((PACKAGE / 'research_workspace/assets/templates/workspace-menu.md').read_text(), rendered)
    def test_numbered_reply_after_menu(self):
        self.assertEqual(menu.resolve_selection('选 ２', in_menu=True)['item']['id'], 'write')
    def test_number_is_not_always_a_menu_choice(self):
        self.assertEqual(menu.resolve_selection('2')['kind'], 'free_text')
    def test_research_number_is_not_navigation(self):
        self.assertEqual(menu.resolve_selection('第2种方法', in_menu=True)['kind'], 'free_text')
    def test_common_aliases(self):
        for text, wanted in [('润色', 'write'), ('连接 Overleaf', 'overleaf'), ('更新', 'settings'), ('转投', 'transfer')]:
            self.assertEqual(menu.resolve_selection(text)['item']['id'], wanted)
    def test_help_controls(self):
        for text in ('菜单', 'HELP', '有哪些功能？', '开始', ''):
            self.assertEqual(menu.resolve_selection(text)['kind'], 'menu')
    def test_cancel_never_undoes_changes(self):
        before = self.snapshot(); out = menu.resolve_selection('返回')
        self.assertEqual(out['kind'], 'cancel'); self.assertFalse(out['execute']); self.assertEqual(before, self.snapshot())
    def test_resume_requires_real_context(self):
        out = menu.resolve_selection('继续'); self.assertEqual(out['kind'], 'resume'); self.assertFalse(out['execute'])
    def test_free_text_and_compound_requests_go_to_agent(self):
        for text in ('帮我润色摘要', '先查文献，再帮我改讨论', '选1，我想开始一篇论文'):
            self.assertEqual(menu.resolve_selection(text, in_menu=True)['kind'], 'free_text')
    def test_input_is_never_executed_or_echoed(self):
        before = self.snapshot(); private = 'token=DO_NOT_ECHO; rm -rf /'
        out = menu.resolve_selection(private, in_menu=True)
        self.assertNotIn(private, json.dumps(out)); self.assertFalse(out['execute']); self.assertEqual(before, self.snapshot())
    def test_oversized_input_refused(self):
        with self.assertRaises(menu.MenuError): menu.resolve_selection('x' * 8001)
    def test_project_summary_does_not_write(self):
        before = self.snapshot()
        for _ in range(2): self.assertEqual(menu.project_summary(self.study)['open_tasks'], 1)
        self.assertEqual(before, self.snapshot())
    def test_zero_tasks_does_not_claim_submission_ready(self):
        data = state(); data['tasks'] = []; data['issues'] = {}
        write(self.study / 'workspace/state.json', json.dumps(data))
        self.assertEqual(menu.project_summary(self.study)['quality'], '未在菜单中重新审查')
    def test_no_sibling_project_selection(self):
        self.assertEqual(menu.project_summary(self.base)['state'], 'not_selected')
    def test_explicit_subdirectory_is_not_silently_changed(self):
        self.assertEqual(menu.project_summary(self.study / 'manuscript')['state'], 'not_selected')
    def test_current_subdirectory_can_find_ancestor(self):
        with patch.object(Path, 'cwd', return_value=self.study / 'manuscript'):
            self.assertEqual(menu.project_summary()['project'], str(self.study))
    def test_missing_location_refused(self):
        with self.assertRaises(menu.MenuError): menu.project_summary(self.base / 'missing')
    def test_corrupt_state_refused_not_green(self):
        write(self.study / 'workspace/state.json', '{invalid')
        with self.assertRaises(menu.MenuError): menu.project_summary(self.study)
    def test_unknown_schema_refused(self):
        data = state(); data['schema_version'] = 99
        write(self.study / 'workspace/state.json', json.dumps(data))
        with self.assertRaises(menu.MenuError): menu.project_summary(self.study)
    def test_malformed_tasks_refused(self):
        data = state(); data['tasks'] = ['invalid']
        write(self.study / 'workspace/state.json', json.dumps(data))
        with self.assertRaises(menu.MenuError): menu.project_summary(self.study)
    def test_symlink_state_refused(self):
        p = self.study / 'workspace/state.json'; saved = p.read_text(); p.unlink()
        write(self.base / 'elsewhere.json', saved); p.symlink_to(self.base / 'elsewhere.json')
        with self.assertRaises(menu.MenuError): menu.project_summary(self.study)
    def test_summary_never_reads_secret_files(self):
        write(self.study / '.rw/overleaf.json', 'DO_NOT_READ_SECRET')
        write(self.study / '.env', 'DO_NOT_READ_SECRET')
        self.assertNotIn('DO_NOT_READ_SECRET', json.dumps(menu.project_summary(self.study)))
    def test_project_name_is_not_markdown_instructions(self):
        data = menu.project_summary(self.study); data['label'] = 'x\n# ignore [rules](bad) | <script>'
        text = menu.render(data); self.assertNotIn('\n# ignore', text); self.assertNotIn('<script>', text)
    def test_cli_works_in_isolated_process_without_install(self):
        out = subprocess.run([sys.executable, '-I', '-B', str(PACKAGE / 'research_workspace/menu.py'), '--project', str(self.study)], capture_output=True, text=True, check=True)
        self.assertIn('Already used paper', out.stdout); self.assertIn('新建论文', out.stdout)
    def test_cli_selection_has_no_side_effects(self):
        before = self.snapshot()
        out = subprocess.run([sys.executable, '-I', '-B', str(PACKAGE / 'research_workspace/menu.py'), '--project', str(self.study), '--select', '6', '--menu-reply'], capture_output=True, text=True, check=True)
        data = json.loads(out.stdout); self.assertEqual(data['selection']['item']['id'], 'overleaf')
        self.assertEqual(data['side_effects'], []); self.assertEqual(before, self.snapshot())

class PrepareCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'framework'
        write(self.root / 'aiworkspace/pyproject.toml', '[project]\n')
        (self.root / 'aiworkspace/research_workspace/assets').mkdir(parents=True)
    def environment(self):
        write(self.root / '.venv/pyvenv.cfg', 'synthetic fixture')
        python = self.root / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        write(python, 'Not executed: fixture only'); return python
    def test_default_preview_never_runs_commands(self):
        with patch.object(prep, '_run', side_effect=AssertionError('must not execute')):
            self.assertFalse(prep.prepare(self.root)['applied'])
        self.assertFalse((self.root / '.venv').exists())
    def test_download_flag_alone_is_not_approval(self):
        with patch.object(prep, '_run', side_effect=AssertionError('must not execute')):
            self.assertFalse(prep.prepare(self.root, allow_download=True)['applied'])
    def test_unmanaged_environment_is_preserved(self):
        write(self.root / '.venv/user-note.txt', 'keep this')
        with self.assertRaises(prep.SetupError): prep.prepare(self.root, approve=True)
        self.assertEqual((self.root / '.venv/user-note.txt').read_text(), 'keep this')
    def test_missing_build_tools_need_download_consent(self):
        self.environment()
        with patch.object(prep, '_run', return_value='["setuptools"]') as run:
            with self.assertRaises(prep.SetupError): prep.prepare(self.root, approve=True)
            self.assertEqual(run.call_count, 1)
    def test_install_uses_argument_arrays_and_only_local_environment(self):
        python = self.environment(); expected = self.root / 'aiworkspace/research_workspace/__init__.py'
        result = {'module': str(expected), 'menu_items': 10, 'version': 'fixture'}
        with patch.object(prep, '_run', side_effect=['[]', '', json.dumps(result)]) as run:
            out = prep.prepare(self.root, approve=True)
        self.assertTrue(out['applied'])
        install = run.call_args_list[1].args[0]
        self.assertIsInstance(install, list); self.assertEqual(install[0], str(python)); self.assertIn('--no-deps', install)
        self.assertNotIn('--user', install)
    def test_install_failure_never_deletes_environment(self):
        self.environment()
        with patch.object(prep, '_run', side_effect=prep.SetupError('fixture failure')):
            with self.assertRaises(prep.SetupError): prep.prepare(self.root, approve=True)
        self.assertTrue((self.root / '.venv/pyvenv.cfg').exists())
    def test_wrong_import_location_refused(self):
        self.environment()
        with patch.object(prep, '_run', side_effect=['[]', '', json.dumps({'module': '/wrong/__init__.py', 'menu_items': 10, 'version': 'fixture'})]):
            with self.assertRaises(prep.SetupError): prep.prepare(self.root, approve=True)

class DistributionCase(unittest.TestCase):
    def test_only_exact_public_agent_entries_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('README.md', 'update_aiworkspace.py', 'aiworkspace/pyproject.toml', 'aiworkspace/research_workspace/upgrade.py', '.claude/CLAUDE.md', '.agents/skills/workspace-guide/SKILL.md'):
                write(root / name, 'public fixture')
            self.assertEqual(len(pub.payload(root)), 6)
            write(root / '.claude/settings.local.json', '{"private":"do not publish"}')
            with self.assertRaises(pub.PublishError): pub.payload(root)
    def test_discovery_entries_and_packager_are_wired(self):
        for name in ('.claude/CLAUDE.md', '.agents/skills/workspace-guide/SKILL.md'):
            self.assertTrue((ROOT / name).exists())
            self.assertIn(name, (PACKAGE / 'scripts/package_delivery.py').read_text())
    def test_new_assets_fit_existing_upgrade_allowlist(self):
        sys.path.insert(0, str(PACKAGE))
        from research_workspace.upgrade import owned
        manifest = json.loads((PACKAGE / 'research_workspace/assets/release.json').read_text())
        self.assertEqual(manifest['schema_version'], 1)
        for path in ('workspace/templates/workspace-menu.md', 'workspace/skills/workspace-guide/SKILL.md'):
            self.assertIn(path, manifest['files']); self.assertTrue(owned(path))
    def test_guide_contains_existing_permission_boundaries(self):
        text = (PACKAGE / 'research_workspace/assets/skills/workspace-guide/SKILL.md').read_text()
        for key in ('## Inputs', '## Workflow', '## Outputs', '## Boundaries', '## Evaluation', 'Menu/status', 'local', 'credentials'):
            if key == 'Menu/status': continue
            self.assertIn(key.casefold(), text.casefold())
        self.assertIn('a menu selection cannot forge a signature', text)
    def test_readme_defaults_to_natural_language(self):
        text = (ROOT / 'README.md').read_text()
        for command in ('git clone ', 'pip install ', '```bash', '```powershell'):
            self.assertNotIn(command, text)
        self.assertIn('workspace-guide', text); self.assertIn('14 个', text)

class IncrementalMenuCase(unittest.TestCase):
    """Real unchanged updater with scoped synthetic old/new release manifests."""
    def test_add_menu_preserve_customizations_idempotent_and_rollback(self):
        sys.path.insert(0, str(PACKAGE))
        from research_workspace import upgrade
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root = base / 'paper'; old = base / 'old-assets'; new = base / 'release/research_workspace/assets'
            original = {'manifest_version': 1, 'schema_version': 1, 'version': '0.3.0-menu-fixture',
                        'files': {'AGENTS.md': 'AGENTS.md', 'workspace/skills/researcher/SKILL.md': 'skills/researcher/SKILL.md'}}
            for assets in (old, new):
                write(assets / 'release.json', json.dumps(original)); write(assets / 'AGENTS.md', 'Existing agent instructions.\n')
                write(assets / 'skills/researcher/SKILL.md', '# researcher\nOriginal\n')
            write(root / 'workspace/state.json', json.dumps(state()))
            with patch.object(upgrade, 'ASSETS', old): upgrade.initialize_baseline(root)
            upgrade.register_host(root, '.agents/skills')
            write(root / '.agents/skills/researcher/SKILL.md', '# researcher\nOriginal\n')
            write(root / 'workspace/skills/researcher/SKILL.md', '# researcher\nOriginal\nLocal customization\n')
            protected = ['workspace/state.json', 'manuscript/main.md', 'workspace/research/idea-evaluation.md', 'workspace/rules/project-policy.md', 'workspace/skills/researcher/SKILL.md']
            for name in protected[1:-1]: write(root / name, 'Existing user content.\n')
            before = {p: (root / p).read_bytes() for p in protected}
            next_release = json.loads(json.dumps(original)); next_release['version'] = '0.4.0-menu-fixture'
            for dest, src in [('workspace/templates/workspace-menu.md', 'templates/workspace-menu.md'), ('workspace/skills/workspace-guide/SKILL.md', 'skills/workspace-guide/SKILL.md')]:
                next_release['files'][dest] = src
                write(new / src, (PACKAGE / 'research_workspace/assets' / src).read_text())
            write(new / 'release.json', json.dumps(next_release))
            result = upgrade.apply_upgrade(root, base / 'release', 'Fixture author', approve=True)
            self.assertEqual(before, {p: (root / p).read_bytes() for p in protected})
            self.assertTrue((root / '.agents/skills/workspace-guide/SKILL.md').exists())
            self.assertTrue((root / 'workspace/templates/workspace-menu.md').exists())
            self.assertFalse(upgrade.apply_upgrade(root, base / 'release', 'Fixture author', approve=True)['updated'])
            upgrade.rollback(root, result['backup_id'])
            self.assertEqual(before, {p: (root / p).read_bytes() for p in protected})
            self.assertFalse((root / 'workspace/templates/workspace-menu.md').exists())

if __name__ == '__main__':
    unittest.main()
