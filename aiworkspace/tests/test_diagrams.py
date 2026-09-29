"""Local diagram/Schema-1 integration checks; scientific content is synthetic."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from research_workspace import diagram_render as dr, diagrams as dg, diagram_templates as dt
from research_workspace.model import WorkspaceError, make_node, pretty, digest
from research_workspace.store import Store, atomic_write, file_hash
from research_workspace import workflow

HAS_RENDER = bool(shutil.which('dot') and importlib.util.find_spec('cairosvg'))


def study(root):
    (root/'workspace').mkdir(parents=True);(root/'manuscript').mkdir()
    state={'schema_version':1,'revision':0,'project':{'name':'SYNTHETIC diagram test','author':'Fixture','mode':'demo'},'nodes':{},'proposals':{},'issues':{},'events':[],'approvals':[],'writers':[],'tasks':[], 'sync':{'sections':{},'outside_hash':digest('')}}
    atomic_write(root/'workspace/state.json',pretty(state));atomic_write(root/'manuscript/main.md','Synthetic test manuscript.\n')
    return Store(root)


class ValidationCase(unittest.TestCase):
    def test_all_templates_validate_without_mutating(self):
        for kind in dr.KINDS:
            raw=dt.template(kind);before=copy.deepcopy(raw);s=dr.validate(raw)
            self.assertEqual(raw,before);self.assertEqual(s['kind'],kind)
    def test_independent_template_copies(self):
        a=dt.template('pipeline');a['nodes'].clear();self.assertTrue(dt.template('pipeline')['nodes'])
    def test_empty_and_dense_graphs_refused(self):
        for nodes in ([],dt.template('pipeline')['nodes']*8):
            s=dt.template('pipeline');s['nodes']=nodes
            with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_missing_endpoint(self):
        s=dt.template('pipeline');s['edges'][0]['target']='missing'
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_duplicate_identifiers(self):
        s=dt.template('pipeline');s['nodes'][1]['id']=s['nodes'][0]['id']
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_no_arbitrary_attributes_or_images(self):
        for key in ('image','href','command','url','stylesheet'):
            s=dt.template('pipeline');s['nodes'][0][key]='do-not-use'
            with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_unknown_top_field(self):
        s=dt.template('pipeline');s['shell']='forbidden'
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_bad_numeric_fields(self):
        for value in (float('inf'),float('nan'),True,0,'180'):
            s=dt.template('pipeline');s['width_mm']=value
            with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_unknown_style(self):
        s=dt.template('pipeline');s['style']='official-nature-certified'
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_causality_not_just_a_solid_arrow(self):
        s=dt.template('pipeline');s['edges'][0]['relation']='causal'
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_reported_requires_reference(self):
        s=dt.template('pipeline');s['edges'][0]['certainty']='reported'
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_hypothesis_dashes_and_inhibition_bar(self):
        source=dr.dot_source(dr.validate(dt.template('mechanism')))
        self.assertIn('"dashed"',source);self.assertIn('"tee"',source);self.assertIn('"none"',source)
    def test_invalid_group_and_rank(self):
        for mode in ('group','rank'):
            s=dt.template('pipeline')
            if mode=='group':s['nodes'][0]['group']='missing'
            else:s['ranks']=[['input','qc'],['input','compare']]
            with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_font_is_a_family_not_a_path(self):
        s=dt.template('pipeline');s['font_family']='../secret.ttf'
        with self.assertRaises(dr.DiagramError):dr.validate(s)
    def test_layout_overlap_check(self):
        bad={'objects':[{'name':'a','pos':'0,0','width':'1','height':'1'},{'name':'b','pos':'1,1','width':'1','height':'1'}]}
        with self.assertRaises(dr.DiagramError):dr.overlap_check(bad)
    def test_labels_escaped_in_dot(self):
        s=dt.template('pipeline');s['nodes'][0]['label']='<script> & "text"'
        dot=dr.dot_source(dr.validate(s));self.assertIn('&lt;script&gt;',dot);self.assertNotIn('<script>',dot)
    def test_template_cli_works_without_a_paper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=subprocess.run([sys.executable,'-m','research_workspace.diagrams','--project',tmp,'template','pipeline'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['kind'],'pipeline')
            self.assertFalse(list(Path(tmp).iterdir()))


@unittest.skipUnless(HAS_RENDER, 'Install Graphviz and diagrams extra for rendering tests')
class RenderCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.reports={}
        for kind in dr.KINDS:cls.reports[kind]=dr.render(dt.template(kind),cls.root/kind)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_seven_templates_produce_all_formats(self):
        for kind in dr.KINDS:
            self.assertEqual(set(self.reports[kind]['files']),{'diagram.svg','diagram.pdf','diagram.png','diagram.dot','diagram.drawio','layout.json'})
    def test_svg_has_editable_text_and_accessibility(self):
        for kind in dr.KINDS:
            x=ET.parse(self.root/kind/'diagram.svg');tags=[e.tag.split('}')[-1] for e in x.iter()]
            self.assertIn('text',tags);self.assertIn('desc',tags);self.assertNotIn('script',tags);self.assertNotIn('foreignObject',tags)
    def test_drawio_nodes_edges_are_editable(self):
        for kind in dr.KINDS:
            s=dt.template(kind);x=ET.parse(self.root/kind/'diagram.drawio');cells=x.findall('.//mxCell');allids={c.get('id') for c in cells}
            self.assertEqual(len(allids),len(cells));self.assertEqual(len([c for c in cells if c.get('edge')=='1']),len(s['edges']))
            for e in cells:
                if e.get('edge')=='1':self.assertIn(e.get('source'),allids);self.assertIn(e.get('target'),allids)
    def test_groups_preserved(self):
        text=(self.root/'graphical-abstract/diagram.svg').read_text()
        for label in ('RESEARCH PROBLEM','PROPOSED APPROACH','EVALUATION PLAN'):self.assertIn(label,text)
    def test_output_sizes_and_pdf_header(self):
        for kind in dr.KINDS:
            report=self.reports[kind];self.assertGreaterEqual(report['dimensions']['minimum_label_pt'],6.5)
            self.assertTrue((self.root/kind/'diagram.pdf').read_bytes().startswith(b'%PDF'))
    def test_existing_directory_never_overwritten(self):
        path=self.root/'pipeline';before=file_hash(path/'diagram.png')
        with self.assertRaises(dr.DiagramError):dr.render(dt.template('pipeline'),path)
        self.assertEqual(before,file_hash(path/'diagram.png'))
    def test_small_output_fails_before_persistent_write(self):
        s=dt.template('pipeline');s['width_mm']=70
        with self.assertRaises(dr.DiagramError):dr.render(s,self.root/'tiny')
        self.assertFalse((self.root/'tiny').exists())
    def test_standalone_reproduction_png_identical(self):
        bundle=self.root/'reproduce';bundle.mkdir();(bundle/'reproduce.py').write_bytes(Path(dr.__file__).read_bytes());(bundle/'spec.json').write_text(pretty(dt.template('pipeline')))
        p=subprocess.run([sys.executable,str(bundle/'reproduce.py'),str(bundle/'spec.json'),'--output',str(bundle/'new')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual((bundle/'new/diagram.png').read_bytes(),(self.root/'pipeline/diagram.png').read_bytes())
    def test_grayscale_style(self):
        s=dt.template('pipeline');s['style']='mono';dr.render(s,self.root/'mono')
        x=ET.parse(self.root/'mono/diagram.svg')
        for e in x.iter():
            for key in ('fill','stroke'):
                val=e.get(key,'')
                if len(val)==7 and val.startswith('#'):self.assertEqual(val[1:3].lower(),val[3:5].lower());self.assertEqual(val[3:5].lower(),val[5:7].lower())
    def test_svg_only_has_no_fake_pdf(self):
        report=dr.render(dt.template('response'),self.root/'svg-only',svg_only=True)
        self.assertIsNone(report['cairosvg']);self.assertFalse((self.root/'svg-only/diagram.pdf').exists())
    def test_missing_graphviz_stops(self):
        with patch.object(dr.shutil,'which',return_value=None):
            with self.assertRaises(dr.DiagramError):dr.run_dot('digraph {a->b}','svg')
    def test_symlink_output_refused(self):
        path=self.root/'link';path.symlink_to(self.root/'pipeline',target_is_directory=True)
        with self.assertRaises(dr.DiagramError):dr.render(dt.template('pipeline'),path/'new')


@unittest.skipUnless(HAS_RENDER, 'Install Graphviz and diagrams extra for integration tests')
class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'study';study(self.root)
    def s(self):return Store(self.root)
    def spec(self):return dt.template('mechanism')
    def hashes(self):return {p.relative_to(self.root).as_posix():file_hash(p) for p in self.root.rglob('*') if p.is_file()}
    def make(self,raw=None,**kwargs):return dg.make(self.s(),raw or self.spec(),'ai:synthetic-test',approve=True,**kwargs)
    def evidence(self):
        s=self.s();source=make_node('SRC-1','source','Synthetic text',{'category':'primary','url':'local:synthetic','snapshot':'workspace/sources/synthetic.txt'})
        claim=make_node('CLM-1','claim','Synthetic hypothesis',{'strength':'descriptive','text':'Synthetic text.','scope':'Test fixture only'},['EVD-1'])
        ev=make_node('EVD-1','evidence','Synthetic passage',{'source':'SRC-1','claim':'CLM-1','quote':'Synthetic text.','locator':'line 1','scope':'Test fixture only','relation':'supports'},['SRC-1'])
        s.state['nodes'].update({n['id']:n for n in (source,claim,ev)});s.event('fixture.created','test');s.commit()
        atomic_write(self.root/'workspace/sources/synthetic.txt','Synthetic text.\n')
        note='SIMULATION ONLY: matched synthetic fixture content; no real scientific verification.'
        workflow.verify(self.s(),'SRC-1','Fixture verifier',note,human=True);workflow.verify(self.s(),'EVD-1','Fixture verifier',note,human=True)
    def test_preview_is_read_only(self):
        before=self.hashes();dg.plan(self.s(),self.spec());self.assertEqual(before,self.hashes())
    def test_approval_required(self):
        with self.assertRaises(WorkspaceError):dg.make(self.s(),self.spec())
    def test_render_does_not_change_scientific_nodes_or_manuscript(self):
        before=file_hash(self.root/'manuscript/main.md');nodes=copy.deepcopy(self.s().state['nodes']);res=self.make()
        self.assertEqual(before,file_hash(self.root/'manuscript/main.md'));self.assertEqual(nodes,self.s().state['nodes']);self.assertTrue(dg.check(self.s(),res['record'])['current']);self.assertFalse(self.s().state['approvals'])
    def test_unlinked_proposal_refused(self):
        r=self.make()
        with self.assertRaises(WorkspaceError):dg.propose(self.s(),r['record'])
    def test_output_tampering_detected(self):
        r=self.make();atomic_write(self.root/r['svg'],'changed');self.assertFalse(dg.check(self.s(),r['record'])['current'])
    def test_editable_source_changes_detected(self):
        r=self.make();atomic_write(self.root/r['editable'],'changed');self.assertFalse(dg.check(self.s(),r['record'])['current'])
    def test_record_forgery_detected(self):
        r=self.make();p=self.root/r['record'];d=json.loads(p.read_text());d['status']='approved';atomic_write(p,pretty(d))
        self.assertFalse(dg.check(self.s(),r['record'])['current'])
    def test_source_spec_change_detected(self):
        path='workspace/figures/test.json';raw=self.spec();atomic_write(self.root/path,pretty(raw));r=self.make(raw,spec_path=path);raw['title']='Later change';atomic_write(self.root/path,pretty(raw))
        self.assertFalse(dg.check(self.s(),r['record'])['current'])
    def test_reported_evidence_must_exist(self):
        raw=self.spec();raw['edges'][0].update(certainty='reported',evidence=['EVD-MISSING'])
        with self.assertRaises(WorkspaceError):dg.plan(self.s(),raw)
    def test_causal_arrow_rejects_association_strength(self):
        self.evidence();raw=self.spec();raw.update(claims=['CLM-1'],evidence=['EVD-1']);raw['edges'][0].update(certainty='reported',evidence=['EVD-1'])
        with self.assertRaises(WorkspaceError):dg.plan(self.s(),raw)
    def test_linked_figure_proposal_is_draft(self):
        self.evidence();raw=self.spec();raw.update(claims=['CLM-1'],evidence=['EVD-1']);r=self.make(raw);p=dg.propose(self.s(),r['record'])
        self.assertEqual(p['status'],'pending');self.assertEqual(p['operations'][0]['node']['status'],'draft');self.assertFalse(self.s().state['approvals'])
    def test_changed_claim_invalidates_receipt(self):
        self.evidence();raw=self.spec();raw.update(claims=['CLM-1'],evidence=['EVD-1']);r=self.make(raw);s=self.s();s.node('CLM-1')['data']['text']='Changed assertion';s.event('fixture','test');s.commit()
        self.assertFalse(dg.check(self.s(),r['record'])['current'])
    def test_new_versions_do_not_overwrite(self):
        a=self.make();before=file_hash(self.root/a['svg']);b=self.make();self.assertNotEqual(a['svg'],b['svg']);self.assertEqual(before,file_hash(self.root/a['svg']))
    def test_failed_registration_never_approves(self):
        with patch.object(Store,'commit',side_effect=OSError('simulated interrupted registration')):
            with self.assertRaises(OSError):self.make()
        self.assertFalse(self.s().state['events']);self.assertFalse(self.s().state['approvals']);self.assertFalse(list((self.root/'workspace/history/diagrams').glob('*.json')))
    def test_private_sources_outside_manuscript(self):
        r=self.make();self.assertTrue(r['editable'].startswith('workspace/'));self.assertFalse(list((self.root/'manuscript').rglob('*.py')));self.assertFalse(list((self.root/'manuscript').rglob('*.drawio')))
    def test_unknown_receipt_path(self):
        with self.assertRaises(WorkspaceError):dg.check(self.s(),'../../secret.json')



class AssetUpgradeCase(unittest.TestCase):
    def test_used_study_gains_skill_and_brief_without_overwriting(self):
        from research_workspace import upgrade
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'study';study(root);old=base/'old';new=base/'release/research_workspace/assets'
            original={'manifest_version':1,'version':'0.5.0-scoped-fixture','schema_version':1,'files':{'AGENTS.md':'AGENTS.md','workspace/skills/figure-visualization/SKILL.md':'skills/figure-visualization/SKILL.md'}}
            for folder in (old,new):
                atomic_write(folder/'release.json',pretty(original));atomic_write(folder/'AGENTS.md','Original project instructions.\n');atomic_write(folder/'skills/figure-visualization/SKILL.md','Original skill\n')
            with patch.object(upgrade,'ASSETS',old):upgrade.initialize_baseline(root)
            upgrade.register_host(root,'.agents/skills');atomic_write(root/'.agents/skills/figure-visualization/SKILL.md','Original skill\n')
            atomic_write(root/'workspace/skills/figure-visualization/SKILL.md','Original skill\nUser customization\n')
            protected=['workspace/state.json','manuscript/main.md','workspace/research/diagram-brief.md','workspace/data/measurements.csv','workspace/skills/figure-visualization/SKILL.md']
            for f in protected[2:4]:atomic_write(root/f,'Existing research — preserve this.\n')
            before={p:file_hash(root/p) for p in protected};manifest=copy.deepcopy(original);manifest['version']='0.6.0-scoped-fixture'
            assets=Path(dr.__file__).parent/'assets'
            for target,source in [('workspace/skills/research-diagram/SKILL.md','skills/research-diagram/SKILL.md'),('workspace/templates/diagram-brief.md','templates/diagram-brief.md')]:
                manifest['files'][target]=source;atomic_write(new/source,(assets/source).read_text())
            atomic_write(new/'release.json',pretty(manifest));result=upgrade.apply_upgrade(root,base/'release','Fixture author',approve=True)
            self.assertEqual(before,{p:file_hash(root/p) for p in protected});self.assertTrue((root/'.agents/skills/research-diagram/SKILL.md').is_file())
            self.assertFalse(upgrade.apply_upgrade(root,base/'release','Fixture',approve=True)['updated'])
            upgrade.rollback(root,result['backup_id']);self.assertEqual(before,{p:file_hash(root/p) for p in protected});self.assertFalse((root/'workspace/templates/diagram-brief.md').exists())
    def test_registry_and_release_contain_new_skill(self):
        from research_workspace import skills,upgrade
        self.assertIn('research-diagram',skills.SKILLS)
        manifest=json.loads((Path(dr.__file__).parent/'assets/release.json').read_text())
        for path in ('workspace/skills/research-diagram/SKILL.md','workspace/templates/diagram-brief.md'):
            self.assertIn(path,manifest['files']);self.assertTrue(upgrade.owned(path))
    def test_new_skill_has_contract_sections(self):
        p=Path(dr.__file__).parent/'assets/skills/research-diagram/SKILL.md';s=p.read_text()
        for text in ('name: research-diagram','## Inputs','## Workflow','## Outputs','## Boundaries','## Evaluation'):self.assertIn(text,s)


@unittest.skipUnless(HAS_RENDER, 'Install diagram dependencies for review tests')
class ReviewIntegrationCase(unittest.TestCase):
    setUp = WorkspaceCase.setUp
    s = WorkspaceCase.s
    spec = WorkspaceCase.spec
    make = WorkspaceCase.make
    evidence = WorkspaceCase.evidence
    # Only the new gate branch is tested here. Existing native LaTeX adapters are
    # isolated, not represented as fully re-executed publication acceptance.
    def test_gate_checks_receipt_and_draft_review(self):
        from research_workspace import review
        self.evidence();raw=self.spec();raw.update(claims=['CLM-1'],evidence=['EVD-1']);r=self.make(raw);proposal=dg.propose(self.s(),r['record'])
        workflow.apply(self.s(),proposal['id'],'Fixture author','SYNTHETIC fixture approval only; no real scientific judgment.',approve=True)
        adapter=types.ModuleType('research_workspace.latex_project');adapter.read_manuscript=lambda store:(store.root/'manuscript/main.md').read_text();adapter.integrity_issues=lambda store:[];adapter.inventory=lambda text:{'citations':[]}
        with patch.dict(sys.modules,{'research_workspace.latex_project':adapter}):
            codes={x['code'] for x in review.review(self.s())['issues']};self.assertIn('DIAGRAM_REVIEW_PENDING',codes)
            atomic_write(self.root/r['editable'],'Changed geometry by a later editor')
            codes={x['code'] for x in review.review(self.s())['issues']};self.assertIn('DIAGRAM_STALE',codes)

if __name__=='__main__':unittest.main()
