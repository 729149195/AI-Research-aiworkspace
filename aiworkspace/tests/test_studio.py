"""Executed recipes, provenance, editor leads and used-project compatibility.

The fixture is an explicit Schema 1 study, not a fabricated scientific review.
"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from research_workspace import figure_render as fr, studio
from research_workspace.model import WorkspaceError, digest, make_node, pretty
from research_workspace.store import Store, atomic_write, file_hash


def fixture(root):
    for name in ('workspace/data','workspace/results','workspace/research','workspace/rules','workspace/reports','workspace/history','workspace/skills','workspace/templates','workspace/sync','manuscript/figures','.rw'):
        (root/name).mkdir(parents=True,exist_ok=True)
    atomic_write(root/'workspace/state.json',pretty({'schema_version':1,'revision':0,
       'project':{'name':'SYNTHETIC STUDIO FIXTURE','author':'Software test','mode':'demo'},
       'nodes':{},'proposals':{},'issues':{},'events':[],'approvals':[],'writers':[],'tasks':[],
       'sync':{'sections':{},'outside_hash':digest('')}}))
    atomic_write(root/'manuscript/main.md','# Synthetic result\n\nA bounded observation has n = 12.\n')
    atomic_write(root/'workspace/data/data.csv','id,x,y,group\na,1,3,A\nb,2,4,A\nc,3,4,B\nd,4,6,B\n')
    return Store(root)


def recipe(kind='scatter'):
    spec={'id':'FIG-TEST','kind':kind,'input':'workspace/data/data.csv','title':'Synthetic observations',
          'purpose':'Test an inspectable software figure, not a scientific result.','caption':'Artificial values for software validation only.',
          'alt_text':'Artificial measurements used to test plotting behavior.','x':'x','y':'y',
          'xlabel':'Baseline (arbitrary units)','ylabel':'Candidate (arbitrary units)','unit':'arbitrary units',
          'claims':[],'evidence':[],'width_mm':100,'height_mm':80}
    if kind in ('distribution','line','scatter'):spec['group']='group'
    if kind=='paired':spec['pair_id']='id'
    if kind=='interval':spec.update(label='id',lower='lower',upper='upper',interval_definition='Supplied synthetic 95% confidence intervals; no inference performed by renderer.')
    if kind=='heatmap':spec.update(row='id',column='group',value='y',width_mm=160)
    if kind=='workflow':
        spec.pop('input');spec.update(steps=['Read sources','Analyze data','Review claims'],workflow_status='planned',width_mm=180,height_mm=55)
    return spec


class Preparation(unittest.TestCase):
    data=b'id,x,y,group\na,1,3,A\nb,2,4,A\nc,3,4,B\n'
    def bad(self,spec,data=None):
        with self.assertRaises(fr.FigureError):fr.prepare(spec,self.data if data is None else data)
    def test_each_numeric_recipe(self):
        for k in ('scatter','line','distribution','paired','heatmap'):
            with self.subTest(kind=k):self.assertEqual(fr.prepare(recipe(k),self.data)[1]['used_rows'],3)
    def test_workflow_is_explicitly_nonempirical(self):
        self.assertIn('schematic',fr.prepare(recipe('workflow'))[1]['transformation'])
    def test_unknown_recipe(self):s=recipe();s['kind']='hidden-inference';self.bad(s)
    def test_unknown_options_refused(self):s=recipe();s['filter']='y>3';self.bad(s)
    def test_no_external_tex(self):s=recipe();s['usetex']=True;self.bad(s)
    def test_no_missing_headers(self):s=recipe();s['x']='missing';self.bad(s)
    def test_duplicate_headers(self):self.bad(recipe(),b'id,x,y,y\na,1,2,3\n')
    def test_ragged_table(self):self.bad(recipe(),b'id,x,y,group\na,1,2\n')
    def test_empty_table(self):self.bad(recipe(),b'id,x,y,group\n')
    def test_nan_default_fails(self):self.bad(recipe(),b'id,x,y,group\na,1,nan,A\n')
    def test_infinity_never_omitted(self):
        s=recipe();s.update(missing='omit',omission_reason='Missing observation analysis decision.')
        self.bad(s,b'id,x,y,group\na,1,inf,A\n')
    def test_omission_requires_explanation(self):s=recipe();s['missing']='omit';self.bad(s)
    def test_omission_records_csv_rows(self):
        s=recipe();s.update(missing='omit',omission_reason='Instrument unavailable at this observation.')
        rows,meta=fr.prepare(s,b'id,x,y,group\na,1,3,A\nb,2,,A\n')
        self.assertEqual(len(rows),1);self.assertEqual(meta['omitted_csv_rows'],[3])
    def test_line_missing_stays_gap(self):
        s=recipe('line');s.update(missing='omit',omission_reason='Instrument gap, not interpolated.')
        rows,meta=fr.prepare(s,b'id,x,y,group\na,1,3,A\nb,2,,A\nc,3,4,A\n')
        self.assertEqual(meta['missing_line_gaps'],[3]);self.assertEqual(len(rows),3);self.assertTrue(__import__('math').isnan(rows[1]['y']))
    def test_missing_line_x_refused(self):
        s=recipe('line');s.update(missing='omit',omission_reason='Unknown x cannot be placed.')
        self.bad(s,b'id,x,y,group\na,1,3,A\nb,,2,A\n')
    def test_duplicate_line_x_refused(self):self.bad(recipe('line'),b'id,x,y,group\na,1,3,A\nb,1,4,A\n')
    def test_duplicate_pairs_refused(self):self.bad(recipe('paired'),b'id,x,y,group\na,1,3,A\na,2,4,A\n')
    def test_pair_descriptive_difference(self):self.assertEqual(fr.prepare(recipe('paired'),self.data)[1]['paired_mean_difference'],5/3)
    def test_intervals_require_definition(self):
        s=recipe('interval');s['interval_definition']='';self.bad(s,b'id,x,lower,upper\na,3,2,4\n')
    def test_reversed_interval_refused(self):self.bad(recipe('interval'),b'id,x,lower,upper\na,3,4,5\n')
    def test_asymmetric_intervals_preserved(self):
        rows,_=fr.prepare(recipe('interval'),b'id,x,lower,upper\na,3,1,4\n');self.assertEqual((rows[0]['lower'],rows[0]['upper']),(1,4))
    def test_duplicate_cells_refused(self):self.bad(recipe('heatmap'),b'id,x,y,group\na,1,3,A\na,2,4,A\n')
    def test_missing_heatmap_cells_are_visible(self):self.assertEqual(fr.prepare(recipe('heatmap'),self.data)[1]['absent_cells'],3)
    def test_unsafe_font_path(self):s=recipe();s['font_family']='../secret';self.bad(s)
    def test_too_small_font_refused(self):s=recipe();s['font_size']=3;self.bad(s)
    def test_nonfinite_width_refused(self):s=recipe();s['width_mm']=float('inf');self.bad(s)
    def test_workflow_requires_status(self):s=recipe('workflow');s.pop('workflow_status');self.bad(s)
    def test_workflow_rejects_quantitative_data(self):self.bad(recipe('workflow'))
    def test_too_many_groups(self):self.bad(recipe(),('id,x,y,group\n'+''.join(f'a{i},{i},2,g{i}\n' for i in range(7))).encode())
    def test_bom_supported(self):self.assertEqual(fr.prepare(recipe(),b'\xef\xbb\xbf'+self.data)[1]['used_rows'],3)


class StudioCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'study';fixture(self.root)
    def s(self):return Store(self.root)
    def hashes(self):return {p.relative_to(self.root).as_posix():file_hash(p) for p in self.root.rglob('*') if p.is_file()}
    def test_preview_reads_only(self):
        before=self.hashes();p=studio.figure_plan(self.s(),recipe());self.assertTrue(p['exploratory']);self.assertEqual(before,self.hashes())
    def test_data_profile_reads_only(self):
        before=self.hashes();p=studio.inspect_data(self.s(),'workspace/data/data.csv');self.assertEqual(p['rows'],4);self.assertEqual(p['columns'][1]['type'],'numeric');self.assertEqual(before,self.hashes())
    def test_invalid_source_scope(self):
        spec=recipe();spec['input']='.env'
        with self.assertRaises(WorkspaceError):studio.figure_plan(self.s(),spec)
    def test_traversal_refused(self):
        spec=recipe();spec['input']='workspace/data/../../.env.csv'
        with self.assertRaises(WorkspaceError):studio.figure_plan(self.s(),spec)
    def test_symlink_refused(self):
        source=self.root/'workspace/data/link.csv';source.symlink_to(self.root/'workspace/data/data.csv')
        spec=recipe();spec['input']='workspace/data/link.csv'
        with self.assertRaises(WorkspaceError):studio.figure_plan(self.s(),spec)
    def test_approval_required(self):
        with self.assertRaises(WorkspaceError):studio.figure_make(self.s(),recipe())
    def test_unknown_claim_fails(self):
        spec=recipe();spec['claims']=['CLM-404']
        with self.assertRaises(WorkspaceError):studio.figure_plan(self.s(),spec)
    def test_unknown_kind_is_safe(self):
        spec=recipe();spec['kind']='shell'
        with self.assertRaises(fr.FigureError):studio.figure_plan(self.s(),spec)
    def test_resume_no_state_mutation(self):
        before=self.hashes();out=studio.resume(self.s());self.assertFalse(out['brief_present']);self.assertEqual(before,self.hashes())
    def test_audit_exposes_unsupported_claim(self):
        s=self.s();s.state['nodes']['CLM-1']=make_node('CLM-1','claim','Fixture assertion',{'text':'Synthetic observation.','strength':'descriptive','scope':'fixture'},status='confirmed');s.event('test','fixture');s.commit()
        before=self.hashes();r=studio.audit(self.s());self.assertFalse(r['claims'][0]['valid_support']);self.assertEqual(before,self.hashes())
    def test_user_brief_reused(self):
        atomic_write(self.root/studio.BRIEF,'Keep observed results separate from hypotheses.')
        self.assertIn('hypotheses',studio.audit(self.s())['brief'])
    def test_audit_export_is_report_only(self):
        before=file_hash(self.root/'workspace/state.json');r=studio.audit(self.s());saved=studio.save_report(self.s(),'writing-audit',r)
        self.assertTrue((self.root/saved['markdown']).is_file());self.assertEqual(before,file_hash(self.root/'workspace/state.json'))
    def test_response_does_not_mark_done_from_prose(self):
        r=studio.responses(self.s(),{'comments':[{'id':'R1','comment':'Please explain sampling.','response':'We have fixed it.','status':'done'}]})
        self.assertEqual(r['comments'][0]['status'],'response_draft')
    def test_response_requires_current_hash(self):
        loc={'path':'manuscript/main.md','quote':'bounded observation','sha256':'old'}
        r=studio.responses(self.s(),{'comments':[{'id':'R1','comment':'Clarify.','response':'Revised.','locations':[loc]}]})
        self.assertTrue(r['comments'][0]['issues'])
    def test_response_locates_actual_text(self):
        loc={'path':'manuscript/main.md','quote':'bounded observation','sha256':file_hash(self.root/'manuscript/main.md')}
        r=studio.responses(self.s(),{'comments':[{'id':'R1','comment':'Clarify.','response':'Clarified the bounded observation.','action':'Reword text.','locations':[loc]}]})
        self.assertEqual(r['comments'][0]['status'],'located_for_review');self.assertEqual(r['comments'][0]['locations'][0]['line'],3)
    def test_invented_quote_fails(self):
        loc={'path':'manuscript/main.md','quote':'Experiment never performed','sha256':file_hash(self.root/'manuscript/main.md')}
        r=studio.responses(self.s(),{'comments':[{'id':'R1','comment':'Clarify.','response':'Revised.','locations':[loc]}]})
        self.assertIn('absent',r['comments'][0]['issues'][0])
    def test_response_cannot_read_credentials(self):
        with self.assertRaises(WorkspaceError):studio.responses(self.s(),{'comments':[{'id':'R1','comment':'Clarify.','locations':[{'path':'.env','quote':'secret'}]}]})
    def test_duplicate_comment_id_refused(self):
        with self.assertRaises(WorkspaceError):studio.responses(self.s(),{'comments':[{'id':'R1','comment':'a'},{'id':'R1','comment':'b'}]})
    def test_response_original_preserved(self):
        original='Do not paraphrase this reviewer wording; explain the comparator.'
        self.assertEqual(studio.responses(self.s(),{'comments':[{'id':'R1','comment':original}]})['comments'][0]['comment'],original)


@unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'Install the optional figures extra to execute rendering tests.')
class DrawingCase(unittest.TestCase):
    setUp = StudioCase.setUp
    s = StudioCase.s
    hashes = StudioCase.hashes
    def draw(self,kind='scatter'):return studio.figure_make(self.s(),recipe(kind),approve=True)
    def test_real_formats_and_pdf_size(self):
        r=self.draw();self.assertTrue((self.root/r['pdf']).read_bytes().startswith(b'%PDF'))
        self.assertIn(b'<svg',(self.root/r['svg']).read_bytes());self.assertTrue((self.root/r['preview']).read_bytes().startswith(b'\x89PNG'))
        self.assertTrue(studio.figure_check(self.s(),r['record'])['current']);self.assertFalse(self.s().state['approvals'])
    def test_data_snapshot_kept_outside_manuscript(self):
        r=self.draw();record=json.loads((self.root/r['record']).read_text())
        self.assertEqual((self.root/record['provenance']/'input.csv').read_bytes(),(self.root/'workspace/data/data.csv').read_bytes())
        self.assertFalse(list((self.root/'manuscript').rglob('*.csv')))
    def test_changed_input_stales_figure(self):
        r=self.draw();atomic_write(self.root/'workspace/data/data.csv','id,x,y,group\nz,1,9,A\n')
        self.assertFalse(studio.figure_check(self.s(),r['record'])['current'])
    def test_changed_image_stales_figure(self):
        r=self.draw();(self.root/r['svg']).write_text('modified')
        self.assertFalse(studio.figure_check(self.s(),r['record'])['current'])
    def test_changed_record_detected(self):
        r=self.draw();p=self.root/r['record'];v=json.loads(p.read_text());v['status']='approved';p.write_text(pretty(v))
        self.assertFalse(studio.figure_check(self.s(),r['record'])['current'])
    def test_changed_reproduction_script_detected(self):
        r=self.draw();v=json.loads((self.root/r['record']).read_text());(self.root/v['provenance']/'reproduce.py').write_text('changed')
        self.assertFalse(studio.figure_check(self.s(),r['record'])['current'])
    def test_new_versions_do_not_overwrite_old(self):
        r=self.draw();before=file_hash(self.root/r['pdf']);r2=self.draw();self.assertNotEqual(r['record'],r2['record']);self.assertEqual(before,file_hash(self.root/r['pdf']))
    def test_standalone_regeneration(self):
        r=self.draw('paired');v=json.loads((self.root/r['record']).read_text());folder=self.root/v['provenance']
        out=subprocess.run([sys.executable,str(folder/'reproduce.py'),str(folder/'spec.json'),'--data',str(folder/'input.csv'),'--output',str(folder/'regenerated')],text=True,capture_output=True)
        self.assertEqual(out.returncode,0,out.stderr+out.stdout)
        self.assertEqual((folder/'regenerated/figure.png').read_bytes(),(self.root/r['preview']).read_bytes())
    def test_unlinked_figure_cannot_be_research_node(self):
        r=self.draw()
        with self.assertRaises(WorkspaceError):studio.figure_propose(self.s(),r['record'])
    def test_no_approvals_or_experiments_created(self):
        self.draw();self.assertFalse(self.s().state['nodes']);self.assertFalse(self.s().state['approvals'])
    def test_registered_figure_is_proposal_only(self):
        s=self.s();s.state['nodes']['CLM-1']=make_node('CLM-1','claim','Synthetic',{'text':'Synthetic result.','strength':'descriptive'})
        s.state['nodes']['RUN-1']=make_node('RUN-1','result','Fixture result',{'boundary':'structural fixture, unverified'})
        s.event('fixture','test');s.commit();spec=recipe();spec.update(claims=['CLM-1'],evidence=['RUN-1'])
        r=studio.figure_make(self.s(),spec,approve=True);p=studio.figure_propose(self.s(),r['record'])
        self.assertEqual(p['status'],'pending');self.assertNotIn('FIG-TEST',self.s().state['nodes'])
    def test_workflow_really_renders_without_axes(self):
        r=self.draw('workflow');self.assertTrue(studio.figure_check(self.s(),r['record'])['current'])
    def test_invalid_font_keeps_existing_project(self):
        s=recipe();s['font_family']='THIS_FONT_DOES_NOT_EXIST_2026';before=self.hashes()
        with self.assertRaises(fr.FigureError):studio.figure_make(self.s(),s,approve=True)
        self.assertEqual(before,self.hashes())
    def test_existing_render_dir_refused(self):
        target=Path(self.temp.name)/'existing';target.mkdir()
        with self.assertRaises(fr.FigureError):fr.render(recipe(),Preparation.data,target)
    def test_concurrent_edit_not_registered(self):
        original=fr.render
        def changed(spec,data,out):
            result=original(spec,data,out);atomic_write(self.root/'manuscript/main.md','Concurrent author edit.');return result
        with patch.object(fr,'render',side_effect=changed),self.assertRaises(WorkspaceError):self.draw()
        self.assertFalse(list((self.root/studio.RECORDS).glob('FGR-*')))


class EditingLeads(unittest.TestCase):
    def test_numbers_are_contextual_not_auto_corrected(self):
        r=studio.audit_text('Cohort A: n = 12.\n\nCohort B: n = 20.')
        self.assertEqual(len(r['numeric_ledger']),2);self.assertFalse(r['findings'])
    def test_causality_is_review_lead(self):self.assertEqual(studio.audit_text('This causes the outcome.')['findings'][0]['status'],'editing_lead')
    def test_code_fence_ignored(self):self.assertFalse(studio.audit_text('```python\n# TODO\nprint(123)\n```')['findings'])
    def test_tex_comment_ignored(self):self.assertFalse(studio.audit_text('% TODO and causes outcomes',latex=True)['findings'])
    def test_markdown_percentages_are_preserved(self):
        r=studio.audit_text('Accuracy: 95% versus 80%.')
        self.assertEqual([n['literal'] for n in r['numeric_ledger']],['95%', '80%'])
    def test_original_line_numbers(self):self.assertEqual(studio.audit_text('One.\n\nTODO explain.')['findings'][0]['line'],3)
    def test_exact_text_remains_unmodified(self):
        source='This proves an effect: n = 12.';saved=source;studio.audit_text(source);self.assertEqual(source,saved)


class StudioIntegration(unittest.TestCase):
    setUp = StudioCase.setUp
    s = StudioCase.s
    hashes = StudioCase.hashes
    def test_new_assets_are_additive_and_schema_one(self):
        from research_workspace.upgrade import owned
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'research_workspace/assets/release.json').read_text())
        self.assertEqual(manifest['schema_version'],1)
        for name in ('writing-brief','reviewer-response','figure-brief'):
            dest='workspace/templates/'+name+'.md'
            self.assertIn(dest,manifest['files']);self.assertTrue(owned(dest))
        self.assertNotIn('workspace/research/writing-brief.md',manifest['files'])
    def test_matplotlib_is_optional(self):
        import tomllib
        config=tomllib.loads((Path(__file__).resolve().parents[1]/'pyproject.toml').read_text())
        self.assertEqual(config['project']['dependencies'],[])
        self.assertIn('matplotlib',config['project']['optional-dependencies']['figures'][0])
    def _packet(self,skill):
        # Isolate the unchanged venue/LaTeX context adapters; use actual files,
        # current Store and actual new packet preference code. Not a native-TeX test.
        import types
        from research_workspace import skills
        latex=types.ModuleType('research_workspace.latex_project');latex.read_manuscript=lambda store:(store.root/'manuscript/main.md').read_text()
        venue=types.ModuleType('research_workspace.venues');venue.context=lambda store:[]
        for name in ('writing-language','reviewer'):
            target=self.root/'workspace/skills'/name/'SKILL.md';target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text((Path(skills.__file__).parent/'assets/skills'/name/'SKILL.md').read_text())
        with patch.dict(sys.modules,{'research_workspace.latex_project':latex,'research_workspace.venues':venue}):
            return skills.task_packet(self.s(),skill,'Inspect actual supplied material.')
    def test_writer_packet_reuses_brief(self):
        atomic_write(self.root/studio.BRIEF,'Author preference: concise, keep scope.')
        packet=self._packet('writing-language')
        self.assertIn('keep scope',packet['non_evidentiary_writing_preferences'][studio.BRIEF])
    def test_reviewer_does_not_receive_extra_author_brief(self):
        atomic_write(self.root/studio.BRIEF,'Author prefers a more persuasive narrative.')
        self.assertNotIn('non_evidentiary_writing_preferences',self._packet('reviewer'))
    def test_writer_reuses_existing_glossary(self):
        atomic_write(self.root/'workspace/rules/glossary.md','Use association; causality is unestablished.')
        self.assertIn('workspace/rules/glossary.md',self._packet('writing-language')['non_evidentiary_writing_preferences'])
    def test_oversized_preferences_fail_instead_of_truncating(self):
        atomic_write(self.root/studio.BRIEF,'x'*210000)
        with self.assertRaises(WorkspaceError):self._packet('writing-language')
    def test_incremental_update_and_rollback_protect_user_research(self):
        from research_workspace import upgrade
        base=Path(self.temp.name);old=base/'old';new=base/'new/research_workspace/assets'
        for folder in (old,new):
            folder.mkdir(parents=True)
            atomic_write(folder/'AGENTS.md','Original entry.\n')
            atomic_write(folder/'release.json',pretty({'manifest_version':1,'schema_version':1,'version':'0.4.0-test',
                         'files':{'AGENTS.md':'AGENTS.md'}}))
        with patch.object(upgrade,'ASSETS',old):upgrade.initialize_baseline(self.root)
        atomic_write(self.root/studio.BRIEF,'Existing author instructions must survive.')
        protected={n:file_hash(self.root/n) for n in ('workspace/state.json','manuscript/main.md',studio.BRIEF,'workspace/data/data.csv')}
        cfg=json.loads((new/'release.json').read_text());cfg['version']='0.5.0-test'
        for name in ('writing-brief','reviewer-response','figure-brief'):
            dest='workspace/templates/'+name+'.md';src='templates/'+name+'.md';cfg['files'][dest]=src
            atomic_write(new/src,'Empty framework template: '+name)
        atomic_write(new/'release.json',pretty(cfg))
        before=self.hashes();upgrade.plan_upgrade(self.root,base/'new');self.assertEqual(before,self.hashes())
        result=upgrade.apply_upgrade(self.root,base/'new','Fixture author',approve=True)
        self.assertEqual(protected,{n:file_hash(self.root/n) for n in protected})
        self.assertTrue((self.root/'workspace/templates/figure-brief.md').exists())
        self.assertFalse(upgrade.apply_upgrade(self.root,base/'new','Fixture author',approve=True)['updated'])
        upgrade.rollback(self.root,result['backup_id'])
        self.assertFalse((self.root/'workspace/templates/figure-brief.md').exists())
        self.assertEqual(protected,{n:file_hash(self.root/n) for n in protected})
    def test_cli_read_only_audit_actual_subprocess(self):
        before=self.hashes()
        proc=subprocess.run([sys.executable,'-m','research_workspace.studio','--project',str(self.root),'audit'],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(json.loads(proc.stdout)['project'],'SYNTHETIC STUDIO FIXTURE')
        self.assertEqual(before,self.hashes())


if __name__=='__main__':unittest.main()
