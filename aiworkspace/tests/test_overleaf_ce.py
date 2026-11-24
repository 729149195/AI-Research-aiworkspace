"""Offline unit tests for the built-in Overleaf CE transport (no network/live login)."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workspace import cli, overleaf, overleaf_ce as ce
from research_workspace.model import WorkspaceError, pretty
from research_workspace.publication_io import sha, tree_bytes
from research_workspace.scaffold import initialize
from research_workspace.store import Store


class OverleafCEProtocolCase(unittest.TestCase):
    def test_ot_roundtrip_ascii_cjk_and_surrogate_emoji(self):
        cases = [
            ('', 'Hello world\n'),
            ('Hello world\n', ''),
            ('A\nB\nC\n', 'A\nX\nY\nC\n'),
            ('中文第一行\n第二行测试\n', '中文第一行\n修改后的第二行\n新增第三行\n'),
            ('Intro 😀 emoji\nBody text\n', 'Intro 🚀 updated emoji\nBody text\nTail\n'),
            ('Line1\nLine2', 'Line1\nLine2'),
            ('single line words here', 'single line BETTER words here'),
        ]
        for old, new in cases:
            with self.subTest(old=old, new=new):
                ops = ce.compute_ot_ops(old, new)
                self.assertEqual(ce.apply_ot_ops_local(old, ops), new)
                if old == new:
                    self.assertEqual(ops, [])

    def test_utf16_len_handles_non_bmp(self):
        self.assertEqual(ce.utf16_len('abc'), 3)
        self.assertEqual(ce.utf16_len('中文'), 2)
        self.assertEqual(ce.utf16_len('😀'), 2)
        self.assertEqual(ce.utf16_len('a😀中'), 4)

    def test_decode_overleaf_doc_line_handles_latin1_packed_utf8_and_plain_unicode(self):
        original = '%% acmart 已加载 hyperref；café 😀'
        wire = original.encode('utf-8').decode('latin-1')
        self.assertEqual(ce.decode_overleaf_doc_line(wire), original)
        self.assertEqual(ce.decode_overleaf_doc_line(original), original)
        self.assertEqual(ce.decode_overleaf_doc_line('plain ascii'), 'plain ascii')

    def test_csrf_and_meta_json_extraction(self):
        html = (
            '<html><head>'
            '<meta name="ol-csrfToken" content="tok-123-abc">'
            '<meta name="ol-ExposedSettings" data-type="json" '
            'content="{&quot;appName&quot;:&quot;Overleaf Community Edition&quot;,&quot;recaptchaDisabled&quot;:{&quot;login&quot;:true}}">'
            '</head></html>'
        )
        self.assertEqual(ce.extract_csrf(html), 'tok-123-abc')
        settings = ce.extract_meta_json(html, 'ol-ExposedSettings')
        self.assertEqual(settings['appName'], 'Overleaf Community Edition')
        self.assertTrue(settings['recaptchaDisabled']['login'])
        with self.assertRaises(WorkspaceError):
            ce.extract_csrf('<html>no token</html>')

    def test_multipart_encoding(self):
        body, ctype = ce.encode_multipart({'name': 'fig.png'}, 'qqfile', 'fig.png', b'\x89PNG', 'image/png')
        self.assertTrue(ctype.startswith('multipart/form-data; boundary='))
        self.assertIn(b'name="qqfile"; filename="fig.png"', body)
        self.assertIn(b'\x89PNG', body)

    def test_flatten_project_and_reject_traversal(self):
        project = {
            '_id': 'proj1',
            'name': 'Paper',
            'rootDoc_id': 'doc1',
            'compiler': 'pdflatex',
            'rootFolder': [{
                '_id': 'root1',
                'name': 'rootFolder',
                'docs': [{'_id': 'doc1', 'name': 'main.tex'}],
                'fileRefs': [{'_id': 'file1', 'name': 'fig.png'}],
                'folders': [{
                    '_id': 'sub1',
                    'name': 'sections',
                    'docs': [{'_id': 'doc2', 'name': 'intro.tex'}],
                    'fileRefs': [],
                    'folders': [],
                }],
            }],
        }
        tree = ce.flatten_project(project)
        self.assertEqual(tree.docs, {'main.tex': 'doc1', 'sections/intro.tex': 'doc2'})
        self.assertEqual(tree.files, {'fig.png': 'file1'})
        self.assertEqual(tree.folders, {'': 'root1', 'sections': 'sub1'})
        self.assertEqual(tree.root_doc_id, 'doc1')

        bad = copy.deepcopy(project)
        bad['rootFolder'][0]['docs'].append({'_id': 'doc3', 'name': '../escape.tex'})
        with self.assertRaises(WorkspaceError):
            ce.flatten_project(bad)

    def test_same_host_redirect_blocks_cross_origin_and_http(self):
        guard = ce._SameHostRedirect('lab.example')
        import urllib.request
        req = urllib.request.Request('https://lab.example/login')
        for target in ('https://evil.example/steal', 'http://lab.example/downgrade'):
            with self.subTest(target=target), self.assertRaises(WorkspaceError):
                guard.redirect_request(req, None, 302, 'Found', {}, target)

    def test_probe_png_is_valid_png_signature(self):
        data = ce.make_probe_png('nonce123')
        self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertIn(b'AIWorkspaceProbe', data)


class FakeCEServer:
    """In-memory mock of Overleaf CE HTTP + Socket.IO endpoints for deterministic tests."""

    def __init__(self, project_id: str, docs: dict[str, str], files: dict[str, bytes]):
        self.project_id = project_id
        self.docs = dict(docs)
        self.doc_versions = {k: 1 for k in docs}
        self.files = dict(files)
        self.doc_ids = {k: f'doc-{i}' for i, k in enumerate(sorted(docs), 1)}
        self.file_ids = {k: f'file-{i}' for i, k in enumerate(sorted(files), 1)}
        self.folders = {'': 'root-folder'}
        self._seq = 100
        self.ot_updates: list[tuple[str, list[dict]]] = []
        self.uploads: list[str] = []
        self.deletes: list[tuple[str, str]] = []
        self.compiles = 0

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f'{prefix}-{self._seq}'

    def project_payload(self) -> dict:
        root = {'_id': 'root-folder', 'name': 'rootFolder', 'docs': [], 'fileRefs': [], 'folders': []}
        folder_nodes = {'': root}

        def ensure_node(folder_path: str) -> dict:
            if folder_path in folder_nodes:
                return folder_nodes[folder_path]
            parent_path = '' if '/' not in folder_path else folder_path.rsplit('/', 1)[0]
            name = folder_path.rsplit('/', 1)[-1]
            parent = ensure_node(parent_path)
            fid = self.folders.setdefault(folder_path, self._next_id('folder'))
            node = {'_id': fid, 'name': name, 'docs': [], 'fileRefs': [], 'folders': []}
            parent['folders'].append(node)
            folder_nodes[folder_path] = node
            return node

        for path, did in sorted(self.doc_ids.items()):
            folder_path = '' if '/' not in path else path.rsplit('/', 1)[0]
            ensure_node(folder_path)['docs'].append({'_id': did, 'name': path.rsplit('/', 1)[-1]})
        for path, fid in sorted(self.file_ids.items()):
            folder_path = '' if '/' not in path else path.rsplit('/', 1)[0]
            ensure_node(folder_path)['fileRefs'].append({'_id': fid, 'name': path.rsplit('/', 1)[-1]})

        return {
            '_id': self.project_id,
            'name': 'Synthetic CE Paper',
            'rootDoc_id': self.doc_ids.get('main.tex'),
            'compiler': 'pdflatex',
            'rootFolder': [root],
        }

    def _folder_path_for_id(self, folder_id: str) -> str:
        for path, fid in self.folders.items():
            if fid == folder_id:
                return path
        raise AssertionError('Unknown folder_id: ' + folder_id)

    def make_session(self) -> ce.CEHttpSession:
        server = self
        sess = ce.CEHttpSession('https://lab.example', cookies=[{'name': 'overleaf.sid', 'value': 'fake'}])
        sess.csrf = 'csrf-ok'

        def fake_request(method, path, *, data=None, json_body=None, headers=None, timeout=30, max_bytes=32 * 1024 * 1024):
            if method == 'GET' and path == f'/project/{server.project_id}':
                return 200, sess.server + path, {}, b'<meta name="ol-csrfToken" content="csrf-ok">'
            if method == 'GET' and path.startswith(f'/project/{server.project_id}/file/'):
                fid = path.rsplit('/', 1)[-1]
                for rel, known in server.file_ids.items():
                    if known == fid:
                        return 200, sess.server + path, {}, server.files[rel]
                return 404, sess.server + path, {}, b'not found'
            if method == 'POST' and path == f'/project/{server.project_id}/folder':
                parent_path = server._folder_path_for_id(json_body['parent_folder_id'])
                rel = f'{parent_path}/{json_body["name"]}' if parent_path else json_body['name']
                fid = server._next_id('folder')
                server.folders[rel] = fid
                return 200, sess.server + path, {}, json.dumps({'_id': fid, 'name': json_body['name']}).encode()
            if method == 'POST' and path == f'/project/{server.project_id}/doc':
                parent_path = server._folder_path_for_id(json_body['parent_folder_id'])
                rel = f'{parent_path}/{json_body["name"]}' if parent_path else json_body['name']
                did = server._next_id('doc')
                server.doc_ids[rel] = did
                server.docs[rel] = ''
                server.doc_versions[rel] = 0
                return 200, sess.server + path, {}, json.dumps({'_id': did, 'name': json_body['name']}).encode()
            if method == 'POST' and path.startswith(f'/project/{server.project_id}/upload?'):
                import urllib.parse
                qs = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
                parent_path = server._folder_path_for_id(qs['folder_id'][0])
                fname = qs['qqfilename'][0]
                rel = f'{parent_path}/{fname}' if parent_path else fname
                # Extract payload after qqfile header
                marker = b'name="qqfile"'
                idx = data.index(marker)
                start = data.index(b'\r\n\r\n', idx) + 4
                boundary = headers['Content-Type'].split('boundary=')[1].encode()
                end = data.index(b'\r\n--' + boundary, start)
                payload = data[start:end]
                fid = server.file_ids.get(rel) or server._next_id('file')
                server.file_ids[rel] = fid
                server.files[rel] = payload
                server.uploads.append(rel)
                return 200, sess.server + path, {}, json.dumps({'success': True, 'entity_id': fid}).encode()
            if method == 'DELETE' and f'/project/{server.project_id}/' in path:
                _, kind, eid = path.rsplit('/', 2)
                if kind == 'doc':
                    for rel, did in list(server.doc_ids.items()):
                        if did == eid:
                            del server.doc_ids[rel]
                            del server.docs[rel]
                            server.deletes.append(('doc', rel))
                            return 204, sess.server + path, {}, b''
                if kind == 'file':
                    for rel, fid in list(server.file_ids.items()):
                        if fid == eid:
                            del server.file_ids[rel]
                            del server.files[rel]
                            server.deletes.append(('file', rel))
                            return 204, sess.server + path, {}, b''
                return 404, sess.server + path, {}, b''
            if method == 'POST' and path == f'/project/{server.project_id}/compile':
                server.compiles += 1
                return 200, sess.server + path, {}, json.dumps({
                    'status': 'success',
                    'outputFiles': [
                        {'type': 'pdf', 'path': 'output.pdf', 'url': f'/project/{server.project_id}/output/output.pdf'},
                        {'type': 'pdf', 'path': 'imgs/fig-eps-converted-to.pdf', 'url': f'/project/{server.project_id}/output/imgs/fig-eps-converted-to.pdf'},
                        {'type': 'log', 'path': 'output.log', 'url': f'/project/{server.project_id}/output/output.log'},
                    ],
                }).encode()
            if method == 'GET' and path == f'/project/{server.project_id}/output/output.pdf':
                return 200, sess.server + path, {}, b'%PDF-1.4\n%synthetic\n'
            if method == 'GET' and path == f'/project/{server.project_id}/output/output.log':
                return 200, sess.server + path, {}, b'This is pdfTeX synthetic log.\n'
            raise AssertionError(f'Unhandled mock request: {method} {path}')

        sess.request = fake_request  # type: ignore[method-assign]
        return sess

    def make_socket_cls(self):
        server = self

        class FakeSocket:
            def __init__(self, session, project_id, timeout=20.0):
                self.project_id = project_id

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def join_project(self):
                return server.project_payload(), 'owner'

            def join_doc(self, doc_id):
                for rel, did in server.doc_ids.items():
                    if did == doc_id:
                        return server.docs[rel].split('\n'), server.doc_versions[rel]
                raise WorkspaceError('Unknown doc_id')

            def leave_doc(self, doc_id):
                return None

            def apply_ot_update(self, doc_id, version, ops):
                for rel, did in server.doc_ids.items():
                    if did == doc_id:
                        if version != server.doc_versions[rel]:
                            raise WorkspaceError('Version mismatch')
                        server.docs[rel] = ce.apply_ot_ops_local(server.docs[rel], ops)
                        server.doc_versions[rel] += 1
                        server.ot_updates.append((rel, ops))
                        return
                raise WorkspaceError('Unknown doc_id')

        return FakeSocket


class OverleafCEIntegrationCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'study'
        initialize(self.root, 'CE Fixture', 'Author')
        (self.root / 'manuscript/overleaf').mkdir(parents=True)
        overleaf.configure(
            Store(self.root), 'fixture',
            server='https://lab.example',
            project_id='proj6915',
            directory='manuscript/overleaf',
            mode='ce',
            approve=True,
        )

    def test_configure_ce_no_password_and_session_roundtrip(self):
        s = Store(self.root)
        cfg = overleaf.config(s)
        self.assertEqual(cfg['mode'], 'ce')
        self.assertFalse(cfg['live_connection_verified'])
        self.assertNotIn('password', cfg)
        self.assertNotIn('cookie', cfg)
        ce.save_session(s, {'server': 'https://lab.example', 'user_email': 'a@b.edu', 'cookies': [{'name': 'overleaf.sid', 'value': 'v1'}]})
        loaded = ce.load_session(s, 'https://lab.example')
        self.assertIn('overleaf.sid=v1', loaded.cookie_header())
        with self.assertRaises(WorkspaceError):
            ce.load_session(s, 'https://other.example')
        out = ce.clear_session(s)
        self.assertTrue(out['session_removed'])
        with self.assertRaises(WorkspaceError):
            ce.load_session(s, 'https://lab.example')

    def test_full_pull_push_conflict_compile_and_verify(self):
        fake = FakeCEServer(
            'proj6915',
            docs={'main.tex': '\\documentclass{article}\n\\begin{document}\nHello.\n\\end{document}\n',
                  'sections/intro.tex': '\\section{Intro}\nOriginal.\n'},
            files={'figures/fig1.png': ce.make_probe_png('fig1')},
        )
        transport = ce.CETransport(Store(self.root), overleaf.config(Store(self.root)), session=fake.make_session())
        with patch.object(ce, 'OverleafSocket', fake.make_socket_cls()):
            # 1. Initial pull into empty manuscript/overleaf
            preview = overleaf.synchronize(Store(self.root), online=True, transport=transport)
            self.assertFalse(preview['synchronized'])
            self.assertEqual(len(preview['changes']), 3)
            self.assertEqual(tree_bytes(self.root / 'manuscript/overleaf'), {})

            pulled = overleaf.synchronize(Store(self.root), 'ai:test', online=True, approve=True, transport=transport)
            self.assertTrue(pulled['synchronized'])
            self.assertEqual((self.root / 'manuscript/overleaf/main.tex').read_text(encoding='utf-8'), fake.docs['main.tex'])
            self.assertEqual((self.root / 'manuscript/overleaf/figures/fig1.png').read_bytes(), fake.files['figures/fig1.png'])
            self.assertEqual(fake.ot_updates, [])

            # 2. Local edit (with CRLF) + new binary + remote edit -> bidirectional OT & upload
            (self.root / 'manuscript/overleaf/main.tex').write_bytes(
                b'\\documentclass{article}\r\n\\begin{document}\r\nUpdated locally.\r\n\\end{document}\r\n'
            )
            (self.root / 'manuscript/overleaf/figures/new.png').write_bytes(ce.make_probe_png('newfig'))
            fake.docs['sections/intro.tex'] = '\\section{Intro}\nUpdated remotely.\n'

            synced = overleaf.synchronize(Store(self.root), 'ai:test', online=True, approve=True, transport=transport)
            self.assertTrue(synced['synchronized'])
            self.assertIn('Updated locally.', fake.docs['main.tex'])
            self.assertNotIn('\r', fake.docs['main.tex'])
            self.assertEqual((self.root / 'manuscript/overleaf/sections/intro.tex').read_text(encoding='utf-8'),
                             '\\section{Intro}\nUpdated remotely.\n')
            self.assertIn('figures/new.png', fake.uploads)
            self.assertTrue(any(path == 'main.tex' for path, _ in fake.ot_updates))

            # 3. Idempotent re-sync makes no further changes
            again = overleaf.synchronize(Store(self.root), 'ai:test', online=True, approve=True, transport=transport)
            self.assertTrue(again['unchanged'])

            # 4. Deletion blocked by default, allowed explicitly
            (self.root / 'manuscript/overleaf/figures/new.png').unlink()
            blocked = overleaf.synchronize(Store(self.root), 'ai:test', online=True, approve=True, transport=transport)
            self.assertIn('figures/new.png', blocked['conflicts'])
            self.assertIn('figures/new.png', fake.files)
            deleted = overleaf.synchronize(Store(self.root), 'ai:test', online=True, approve=True, allow_deletions=True, transport=transport)
            self.assertTrue(deleted['synchronized'])
            self.assertNotIn('figures/new.png', fake.files)

            # 5. Remote compile downloads PDF & log to .rw/builds/
            comp = overleaf.compile_remote(Store(self.root), online=True, transport=transport)
            self.assertTrue(comp['compiled'])
            self.assertTrue(Path(comp['pdf']).read_bytes().startswith(b'%PDF-1.4'))
            self.assertIn('pdfTeX', Path(comp['log']).read_text(encoding='utf-8'))

            # 6. Live connectivity verification (read-only vs roundtrip)
            ro = overleaf.verify_connection(Store(self.root), online=True, transport=transport)
            self.assertEqual(ro['status'], 'readable_via_ce')
            self.assertFalse(ro['verified'])
            self.assertTrue(ro['local_main_matches'])

            with self.assertRaises(WorkspaceError):
                overleaf.verify_connection(Store(self.root), online=True, roundtrip=True, approve=False, transport=transport)

            rt = overleaf.verify_connection(Store(self.root), online=True, roundtrip=True, approve=True, transport=transport)
            self.assertTrue(rt['verified'])
            self.assertTrue(rt['local_to_remote'])
            self.assertTrue(rt['remote_to_local'])
            self.assertTrue(rt['cleanup'])
            self.assertEqual(rt['before_hashes'], rt['after_hashes'])

    def test_cli_parses_ce_subcommands(self):
        p = cli.parser()
        for argv in (
            ['overleaf', 'configure', '--project-id', 'p1', '--directory', 'manuscript/overleaf', '--mode', 'ce'],
            ['overleaf', 'login', '--online', '--server', 'https://nankaivisoverleaf.asia/'],
            ['overleaf', 'logout'],
            ['overleaf', 'projects', '--online'],
            ['overleaf', 'compile', '--online'],
            ['overleaf', 'verify', '--online', '--roundtrip', '--approve'],
        ):
            parsed = p.parse_args(argv)
            self.assertEqual(parsed.command, 'overleaf')


if __name__ == '__main__':
    unittest.main()
