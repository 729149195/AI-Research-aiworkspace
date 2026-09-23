"""Offline publisher safety checks. No real gh command, credentials or remote writes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/create_github_repo.py'
spec = importlib.util.spec_from_file_location('workspace_publisher', SCRIPT)
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


class PublisherCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'distribution'
        for name in ('README.md', 'update_aiworkspace.py', 'aiworkspace/pyproject.toml',
                     'aiworkspace/research_workspace/upgrade.py'):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('fixture\n', encoding='utf-8')

    def test_payload_contains_only_framework(self):
        self.assertEqual(len(pub.payload(self.root)), 4)

    def test_existing_git_refused(self):
        (self.root / '.git').mkdir()
        with self.assertRaises(pub.PublishError):
            pub.payload(self.root)

    def test_unrelated_root_refused(self):
        (self.root / 'package.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(pub.PublishError):
            pub.payload(self.root)

    def test_private_research_refused(self):
        p = self.root / 'aiworkspace/workspace'
        p.mkdir()
        (p / 'state.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(pub.PublishError):
            pub.payload(self.root)

    def test_env_file_refused(self):
        (self.root / 'aiworkspace/.env').write_text('fixture only', encoding='utf-8')
        with self.assertRaises(pub.PublishError):
            pub.payload(self.root)

    def test_ppt_refused(self):
        (self.root / 'aiworkspace/source.ppt').write_bytes(b'fixture')
        with self.assertRaises(pub.PublishError):
            pub.payload(self.root)

    def test_preview_never_calls_remote(self):
        with patch.object(pub, 'ROOT', self.root), patch.object(pub, 'call', side_effect=AssertionError('Network not allowed')), patch('builtins.print'):
            self.assertEqual(pub.main([]), 0)
        self.assertFalse((self.root / '.git').exists())

    def test_visibility_must_be_explicit(self):
        with patch.object(pub, 'ROOT', self.root), patch.object(pub, 'publish', side_effect=AssertionError('Must not publish')), patch('builtins.print'):
            self.assertEqual(pub.main(['--publish']), 2)

    def test_account_mismatch_refused(self):
        files = pub.payload(self.root)
        with patch.object(pub.shutil, 'which', return_value='/mock'), patch.dict(os.environ, {}, clear=True), \
             patch.object(pub, 'call', return_value=subprocess.CompletedProcess([], 128, '', '')), \
             patch.object(pub, 'checked', return_value=json.dumps({'login':'another-user','id':1})), \
             patch.object(pub, 'git', side_effect=AssertionError('Must not initialize Git')):
            with self.assertRaises(pub.PublishError):
                pub.publish(self.root, files, 'public')

    def test_inherited_git_location_refused(self):
        with patch.object(pub.shutil, 'which', return_value='/mock'), patch.dict(os.environ, {'GIT_DIR':'/another/repo'}, clear=True):
            with self.assertRaises(pub.PublishError):
                pub.publish(self.root, pub.payload(self.root), 'public')

    def test_parent_git_checkout_refused(self):
        with patch.object(pub.shutil, 'which', return_value='/mock'), patch.dict(os.environ, {}, clear=True), \
             patch.object(pub, 'call', return_value=subprocess.CompletedProcess([], 0, '/parent', '')), \
             patch.object(pub, 'checked', side_effect=AssertionError('Must not call gh')):
            with self.assertRaises(pub.PublishError):
                pub.publish(self.root, pub.payload(self.root), 'public')

    def test_existing_remote_refused(self):
        calls = [subprocess.CompletedProcess([], 128, '', ''), subprocess.CompletedProcess([], 0, 'HTTP/2 200\n{}', '')]
        with patch.object(pub.shutil, 'which', return_value='/mock'), patch.dict(os.environ, {}, clear=True), \
             patch.object(pub, 'call', side_effect=calls), \
             patch.object(pub, 'checked', return_value=json.dumps({'login':pub.OWNER,'id':75566931})), \
             patch.object(pub, 'git', side_effect=AssertionError('Must not initialize Git')):
            with self.assertRaises(pub.PublishError):
                pub.publish(self.root, pub.payload(self.root), 'public')


if __name__ == '__main__':
    unittest.main()
