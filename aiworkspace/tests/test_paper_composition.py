"""Source/renderer/Store checks, not a live-agent or aesthetic quality benchmark."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from research_workspace import diagrams, paper_render, upgrade
from research_workspace.model import WorkspaceError, pretty, make_node
from research_workspace.store import Store, atomic_write, file_hash

PACKAGE=Path(__file__).resolve().parents[1]
EXAMPLES=PACKAGE/'examples/vis-hci'

def example(name='method-detail'):
    return json.loads((EXAMPLES/(name+'.json')).read_text(encoding='utf-8'))

def study(root):
    root.mkdir()
    state={'schema_version':1,'revision':0,'project':{'name':'Synthetic composition test','mode':'demo'},
           'nodes':{},'proposals':{},'issues':{},'sync':{},'events':[],'approvals':[],'writers':[],'tasks':[]}
    atomic_write(root/'workspace/state.json',pretty(state))
    atomic_write(root/'manuscript/main.md','Original synthetic manuscript; must be preserved.\n')
    return Store(root)

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.s=example();self.b=(EXAMPLES/'method-detail.svg').read_bytes()
    def reject_svg(self,source):
        with self.assertRaises((paper_render.PaperFigureError,UnicodeError)):
            paper_render.validate_svg(self.s,source)
    def test_examples_have_panel_content_and_final_size(self):
        for name in ('method-detail','interaction-storyboard'):
            s=example(name);r=paper_render.validate_svg(s,(EXAMPLES/(name+'.svg')).read_bytes())
            self.assertGreaterEqual(r['min_text_pt'],7);self.assertEqual(r['width_mm'],180)
            self.assertEqual(len(r['panel_ids']),len(s['panels']))
    def test_missing_panel_plan_refused(self):
        self.s.pop('panels')
        with self.assertRaises(paper_render.PaperFigureError):paper_render.validate(self.s)
    def test_duplicate_panel_refused(self):
        self.s['panels'][1]['id']=self.s['panels'][0]['id']
        with self.assertRaises(paper_render.PaperFigureError):paper_render.validate(self.s)
    def test_source_bound_panel_requires_evidence(self):
        self.s['panels'][0]['source_status']='source-bound'
        with self.assertRaises(paper_render.PaperFigureError):paper_render.validate(self.s)
    def test_unknown_graph_fields_refused(self):
        self.s['rankdir']='LR'
        with self.assertRaises(paper_render.PaperFigureError):paper_render.validate(self.s)
    def test_artwork_does_not_implicitly_verify_arrows(self):
        self.s['edges']=[{'relation':'causal'}]
        with self.assertRaises(paper_render.PaperFigureError):paper_render.validate(self.s)
    def test_script_refused(self):self.reject_svg(self.b.replace(b'</svg>',b'<script>unsafe</script></svg>'))
    def test_dtd_and_entity_refused(self):self.reject_svg(b'<!DOCTYPE svg [<!ENTITY test SYSTEM "file:///etc/passwd">]>'+self.b)
    def test_external_image_refused(self):self.reject_svg(self.b.replace(b'</svg>',b'<image href="https://example.org/img"/></svg>'))
    def test_event_attributes_refused(self):self.reject_svg(self.b.replace(b'<svg ',b'<svg onload="unsafe()" ',1))
    def test_css_refused(self):self.reject_svg(self.b.replace(b'<g ',b'<g style="fill:red" ',1))
    def test_transform_cannot_evade_size_check(self):self.reject_svg(self.b.replace(b'<g ',b'<g transform="scale(0.01)" ',1))
    def test_resource_url_refused(self):self.reject_svg(self.b.replace(b'fill="#216b91"',b'fill="url(https://example.org/x)"',1))
    def test_nested_viewport_refused(self):self.reject_svg(self.b.replace(b'</svg>',b'<svg viewBox="0 0 10 10"></svg></svg>'))
    def test_duplicate_svg_id_refused(self):self.reject_svg(self.b.replace(b'id="panel-b"',b'id="panel-a"'))
    def test_missing_svg_panel_refused(self):self.reject_svg(self.b.replace(b'id="panel-b"',b'id="unmapped"'))
    def test_text_only_panel_refused(self):
        root=ET.fromstring(self.b)
        group=next(e for e in root.iter() if e.get('id')=='panel-a')
        for e in list(group):group.remove(e)
        ET.SubElement(group,'{'+paper_render.SVG+'}text',{'font-size':'20'}).text='Only a module label'
        self.reject_svg(ET.tostring(root))
    def test_tiny_text_rejected_at_final_size(self):self.reject_svg(self.b.replace(b'font-size="16"',b'font-size="6"'))
    def test_nonfinite_geometry_refused(self):self.reject_svg(self.b.replace(b'cx="',b'cx="nan',1))
    def test_oversized_svg_refused(self):self.reject_svg(b' '*(paper_render.MAX_BYTES+1))
    def test_worked_example_is_calculated_and_consistent(self):
        spec=importlib.util.spec_from_file_location('worked',EXAMPLES/'build_examples.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        rows=mod.load();ids=mod.selected(rows)
        self.assertEqual(ids,{'b','c','d'});self.assertEqual(len(rows),8)
        self.assertEqual({g:sum(r['group']==g and r['id'] in ids for r in rows) for g in ('A','B')},{'A':1,'B':2})
        self.assertTrue(all(p['source_status']=='illustrative' for p in self.s['panels']))

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'paper';study(self.root)
        self.s=example();self.s['artwork']='workspace/figures/method.svg';self.path='workspace/figures/composition.json'
        atomic_write(self.root/self.s['artwork'],(EXAMPLES/'method-detail.svg').read_text())
        atomic_write(self.root/self.path,pretty(self.s))
    def hashes(self):return {p.relative_to(self.root).as_posix():file_hash(p) for p in self.root.rglob('*') if p.is_file()}
    def make(self):return diagrams.make(Store(self.root),self.s,approve=True,spec_path=self.path)
    def test_plan_read_only(self):
        before=self.hashes();out=diagrams.plan(Store(self.root),self.s)
        self.assertEqual(before,self.hashes());self.assertTrue(out['source_artwork_hash']);self.assertTrue(out['unlinked'])
    def test_permission_required(self):
        with self.assertRaises(WorkspaceError):diagrams.make(Store(self.root),self.s)
    def test_artwork_scope_refuses_arbitrary_file(self):
        self.s['artwork']='../private.svg'
        with self.assertRaises(WorkspaceError):diagrams.plan(Store(self.root),self.s)
    def test_symlink_refused(self):
        (self.root/self.s['artwork']).unlink();(self.root/self.s['artwork']).symlink_to(EXAMPLES/'method-detail.svg')
        with self.assertRaises(WorkspaceError):diagrams.plan(Store(self.root),self.s)
    def test_source_bound_does_not_trust_unverified_node(self):
        s=Store(self.root)
        s.state['nodes']['CLM-1']=make_node('CLM-1','claim','Test',{'text':'Synthetic claim','strength':'descriptive'})
        s.state['nodes']['SRC-1']=make_node('SRC-1','source','Fixture',{'category':'primary','url':'local:test'})
        s.state['nodes']['EVD-1']=make_node('EVD-1','evidence','Test',{'source':'SRC-1','claim':'CLM-1','quote':'Example','locator':'1','scope':'fixture','relation':'supports'},['SRC-1'])
        s.event('fixture','test');s.commit()
        self.s['panels'][0]['source_status']='source-bound';self.s['claims']=['CLM-1'];self.s['evidence']=['EVD-1']
        with self.assertRaises(WorkspaceError):diagrams.plan(Store(self.root),self.s)
    def test_actual_render_preserves_paper_and_records_all_files(self):
        before=file_hash(self.root/'manuscript/main.md');out=self.make()
        self.assertEqual(before,file_hash(self.root/'manuscript/main.md'))
        for key in ('svg','pdf','preview','editable'):self.assertTrue((self.root/out[key]).is_file())
        self.assertTrue(diagrams.check(Store(self.root),out['record'])['current'])
        self.assertEqual(Store(self.root).state['approvals'],[])
        self.assertTrue(out['editable'].startswith('workspace/results/'))
    def test_changed_original_artwork_invalidates_receipt(self):
        out=self.make();p=self.root/self.s['artwork'];atomic_write(p,p.read_text().replace('Brush B','Brush C'))
        self.assertFalse(diagrams.check(Store(self.root),out['record'])['current'])
    def test_changed_editable_source_invalidates_receipt(self):
        out=self.make();p=self.root/out['editable'];atomic_write(p,p.read_text()+'\n')
        self.assertFalse(diagrams.check(Store(self.root),out['record'])['current'])
    def test_changed_image_invalidates_receipt(self):
        out=self.make();(self.root/out['pdf']).write_bytes(b'changed')
        self.assertFalse(diagrams.check(Store(self.root),out['record'])['current'])
    def test_forged_record_invalidates_receipt(self):
        out=self.make();p=self.root/out['record'];r=json.loads(p.read_text());r['actor']='tampered';atomic_write(p,pretty(r))
        self.assertFalse(diagrams.check(Store(self.root),out['record'])['current'])
    def test_no_silent_scientific_promotion(self):
        out=self.make()
        with self.assertRaises(WorkspaceError):diagrams.propose(Store(self.root),out['record'])
        self.assertFalse(Store(self.root).state['nodes'])
    def test_new_version_does_not_overwrite_previous(self):
        a=self.make();before=file_hash(self.root/a['pdf']);b=self.make()
        self.assertNotEqual(a['pdf'],b['pdf']);self.assertEqual(before,file_hash(self.root/a['pdf']))
    def test_standalone_frozen_bundle_reproduces_image(self):
        out=self.make();folder=(self.root/out['editable']).parent;dest=Path(self.tmp.name)/'reproduced'
        subprocess.run([sys.executable,str(folder/'reproduce.py'),str(folder/'spec.json'),'--output',str(dest)],check=True,capture_output=True)
        self.assertEqual(file_hash(self.root/out['preview']),file_hash(dest/'diagram.png'))
    def test_existing_output_directory_refused(self):
        d=Path(self.tmp.name)/'existing';d.mkdir()
        with self.assertRaises(paper_render.PaperFigureError):paper_render.render(self.s,(self.root/self.s['artwork']).read_bytes(),d)
        self.assertEqual(list(d.iterdir()),[])
    def test_svg_only_exports_no_pdf(self):
        out=diagrams.make(Store(self.root),self.s,approve=True,svg_only=True,spec_path=self.path)
        self.assertIsNone(out['pdf']);self.assertTrue(out['preview'].endswith('.svg'))

class UpgradeTests(unittest.TestCase):
    def test_scoped_assets_upgrade_preserves_filled_work_and_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root=base/'paper';study(root);old=base/'old';new=base/'new/research_workspace/assets'
            mapping={'workspace/skills/research-diagram/SKILL.md':'skills/research-diagram/SKILL.md'}
            for assets in (old,new):
                atomic_write(assets/'release.json',pretty({'manifest_version':1,'schema_version':1,'version':'0.6.0-fixture','files':mapping}))
                atomic_write(assets/'skills/research-diagram/SKILL.md','Original scoped fixture.\n')
            with patch.object(upgrade,'ASSETS',old):upgrade.initialize_baseline(root)
            upgrade.register_host(root,'.agents/skills');atomic_write(root/'.agents/skills/research-diagram/SKILL.md','Original scoped fixture.\n')
            atomic_write(root/'workspace/figures/filled-plan.md','Actual user choices; preserve.\n')
            atomic_write(root/'workspace/rules/project-policy.md','Actual local terminology.\n')
            saved={p:file_hash(root/p) for p in ('workspace/state.json','manuscript/main.md','workspace/figures/filled-plan.md','workspace/rules/project-policy.md')}
            mapping=dict(mapping)
            for name in ('paper-figure-plan','vis-hci-figure-guide'):
                target='workspace/templates/'+name+'.md';mapping[target]='templates/'+name+'.md'
                atomic_write(new/mapping[target],(PACKAGE/'research_workspace/assets'/mapping[target]).read_text())
            atomic_write(new/'skills/research-diagram/SKILL.md','New source-based composition workflow.\n')
            atomic_write(new/'release.json',pretty({'manifest_version':1,'schema_version':1,'version':'0.6.1-fixture','files':mapping}))
            before={p:file_hash(root/p) for p in saved};preview=upgrade.plan_upgrade(root,base/'new')
            self.assertFalse(preview['conflicts']);self.assertEqual(before,{p:file_hash(root/p) for p in saved})
            out=upgrade.apply_upgrade(root,base/'new','test',approve=True)
            self.assertEqual(saved,{p:file_hash(root/p) for p in saved})
            self.assertTrue((root/'workspace/templates/paper-figure-plan.md').exists())
            self.assertIn('New source-based',(root/'.agents/skills/research-diagram/SKILL.md').read_text())
            self.assertFalse(upgrade.apply_upgrade(root,base/'new','test',approve=True)['updated'])
            upgrade.rollback(root,out['backup_id']);self.assertEqual(saved,{p:file_hash(root/p) for p in saved})
            self.assertFalse((root/'workspace/templates/paper-figure-plan.md').exists())

if __name__=='__main__':unittest.main()
