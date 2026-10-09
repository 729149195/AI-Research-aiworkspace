"""Local request/VSIX tests, not a live editor or authenticated server test."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
sp = importlib.util.spec_from_file_location('overleaf_agent', PACKAGE / 'scripts/overleaf_agent.py')
agent = importlib.util.module_from_spec(sp); sp.loader.exec_module(agent)
URL = 'https://lab.example/project/p1'

class OverleafAgentCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'manuscript/.overleaf').mkdir(parents=True)
        self.main = self.root/'manuscript/main.tex'
        self.main.write_bytes(b'\\documentclass{article}\r\n\\begin{document}Original paper.\\end{document}\r\n')
        self.meta = self.root/'manuscript/.overleaf/settings.json'
        self.meta.write_text(json.dumps({'uri':'overleaf-workshop://lab.example/Paper?user=u1&project=p1','serverName':'lab.example'}))
    def prepare(self, mode='roundtrip'):
        return agent.prepare(self.root, URL, mode=mode)
    def report(self, request):
        ident=request['request_id']; h=hashlib.sha256(self.main.read_bytes()).hexdigest()
        return {'version':1,'id':ident,'server':'https://lab.example','project_id':'p1',
                'transport':'iamhyc.overleaf-workshop','status':'roundtrip_verified','verified':True,
                'directory':'manuscript','main':'main.tex','metadata_matched':True,
                'local_to_remote':True,'remote_to_local':True,'cleanup':True,
                'before_hashes':{'main.tex':h},'after_hashes':{'main.tex':h},
                'replica_binding_sha256':hashlib.sha256(self.meta.read_bytes()).hexdigest(),
                'finished_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    def write_report(self, r):
        p=self.root/f'.rw/overleaf-agent/reports/{r["id"]}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r))
    def test_default_request_uses_existing_manuscript(self):
        r=self.prepare(); self.assertFalse(r['verified'])
        q=json.loads((self.root/f'.rw/overleaf-agent/requests/{r["request_id"]}.json').read_text())
        self.assertEqual(q['directory'],'manuscript'); self.assertEqual(q['main'],'main.tex')
        self.assertIn('vscode://aiworkspace-local.overleaf-assistant/check?id=',r['launch_uri'])
    def test_missing_replica_never_claims_ready(self):
        self.meta.unlink();r=self.prepare();self.assertEqual(r['status'],'awaiting_workshop_replica')
        self.assertFalse((self.root/'.rw').exists())
    def test_multiple_main_files_ask_once(self):
        (self.root/'manuscript/supplement.tex').write_bytes(self.main.read_bytes())
        r=self.prepare();self.assertEqual(r['status'],'needs_main_selection');self.assertEqual(len(r['candidates']),2)
    def test_actual_main_can_be_supplied_by_agent(self):
        (self.root/'manuscript/supplement.tex').write_bytes(self.main.read_bytes())
        self.assertEqual(agent.prepare(self.root,URL,main='main.tex')['status'],'request_prepared')
    def test_prepare_never_changes_manuscript(self):
        before={p.relative_to(self.root).as_posix():p.read_bytes() for p in (self.root/'manuscript').rglob('*') if p.is_file()}
        self.prepare()
        self.assertEqual(before,{p.relative_to(self.root).as_posix():p.read_bytes() for p in (self.root/'manuscript').rglob('*') if p.is_file()})
    def test_other_project_binding_is_preserved(self):
        (self.root/'.rw').mkdir();p=self.root/'.rw/overleaf.json'
        p.write_text(json.dumps({'mode':'workshop','server':'https://lab.example','project_id':'other','directory':'manuscript'}));before=p.read_bytes()
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(p.read_bytes(),before)
    def test_git_is_not_an_automatic_fallback(self):
        (self.root/'.rw').mkdir();(self.root/'.rw/overleaf.json').write_text('{"mode":"git"}')
        with self.assertRaises(ValueError):self.prepare()
    def test_unsafe_urls(self):
        for u in ['http://lab.example/project/p1','https://user:password@lab.example/project/p1','https://lab.example/project/p1?token=secret','https://lab.example/read/share','https://lab.example/project/p1\n']:
            with self.subTest(u=u),self.assertRaises(ValueError):agent.target(u)
    def test_unsafe_paths(self):
        for rel in ['../main.tex','/main.tex','a\\b','a:b','./a']:
            with self.subTest(rel=rel),self.assertRaises(ValueError):agent.safe(self.root,rel)
    def test_symlink_main_rejected(self):
        self.main.unlink();self.main.symlink_to('/etc/hosts')
        with self.assertRaises(ValueError):self.prepare()
    def test_no_report_means_waiting_not_connected(self):
        r=self.prepare();self.assertEqual(agent.status(self.root,r['request_id'])['status'],'awaiting_editor')
    def test_readonly_cannot_be_promoted(self):
        q=self.prepare('read');self.write_report(self.report(q))
        with self.assertRaises(ValueError):agent.status(self.root,q['request_id'])
    def test_missing_phase_is_not_verified(self):
        q=self.prepare();r=self.report(q);r['cleanup']=False;self.write_report(r)
        with self.assertRaises(ValueError):agent.status(self.root,q['request_id'])
    def test_fixture_report_checks_hashes(self):
        q=self.prepare();self.write_report(self.report(q));r=agent.status(self.root,q['request_id'])
        self.assertTrue(r['verified']);self.assertFalse(r['historical'])
        self.main.write_bytes(self.main.read_bytes()+b'% new edit')
        self.assertTrue(agent.status(self.root,q['request_id'])['historical'])
    def test_new_file_stales_old_report(self):
        q=self.prepare();self.write_report(self.report(q));(self.root/'manuscript/added.tex').write_text('new')
        self.assertIn('added.tex',agent.status(self.root,q['request_id'])['changed_since_check'])
    def test_changed_replica_binding_stales_report(self):
        q=self.prepare();self.write_report(self.report(q));self.meta.write_text('{}')
        self.assertIn('replica_binding',agent.status(self.root,q['request_id'])['changed_since_check'])
    def test_old_report_is_historical(self):
        q=self.prepare();r=self.report(q);r['finished_at']=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=1)).isoformat();self.write_report(r)
        self.assertTrue(agent.status(self.root,q['request_id'])['historical'])
    def test_build_is_exact_zip_and_no_install(self):
        p=self.root/'helper.vsix';r=agent.build_vsix(p);self.assertFalse(r['installed'])
        with zipfile.ZipFile(p) as z:
            self.assertEqual(set(z.namelist()), {'[Content_Types].xml','extension.vsixmanifest', *{'extension/'+n for n in agent.FILES}})
            ET.fromstring(z.read('[Content_Types].xml')); ET.fromstring(z.read('extension.vsixmanifest'))
            self.assertEqual(json.loads(z.read('extension/package.json'))['publisher'],'aiworkspace-local')
        with self.assertRaises(ValueError):agent.build_vsix(p)
    def test_user_guide_has_no_terminal_homework(self):
        text=(PACKAGE/'docs/OVERLEAF.md').read_text()
        for forbidden in ['```bash','```python','pip install','rw overleaf configure','RW_OVERLEAF_TOKEN']:
            self.assertNotIn(forbidden,text)
        self.assertIn('自然语言',text);self.assertIn('Overleaf-Workshop',text)
    def test_agent_policy_requires_real_results(self):
        text=(PACKAGE/'docs/OVERLEAF_AGENT.md').read_text()
        for required in ['remote_to_local','local_to_remote','cleanup','computer use','缓存']:
            self.assertIn(required,text)

if __name__=='__main__':unittest.main()
