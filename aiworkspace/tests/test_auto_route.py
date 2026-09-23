import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from research_workspace import routing, route_hooks, skills, sync, workflow
from research_workspace.model import WorkspaceError, make_node, pretty
from research_workspace.scaffold import initialize
from research_workspace.store import Store, atomic_write, file_hash, recover
from research_workspace.upgrade import ASSETS, apply_upgrade, rollback

NOTE = 'Synthetic test only: examined changed content, dependencies and reconciliation; no real scientific review.'

class RouteCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'study'
        initialize(self.root, 'Synthetic route test', 'Fixture author')
    def s(self): return Store(self.root)
    def edit(self, value='Changed discussion.'): 
        path = self.root / 'manuscript/main.md'
        atomic_write(path, path.read_text().replace('## Discussion', '## Discussion\n\n' + value))
    def capture(self, **kwargs): return routing.capture(self.s(), **kwargs)
    def hashes(self): return {p.relative_to(self.root).as_posix(): file_hash(p) for p in self.root.rglob('*') if p.is_file()}
    def record(self, result): return json.loads((self.root / result['record']).read_text())

    def test_new_study_has_baseline_and_tenth_skill(self):
        self.assertTrue((self.root / routing.SNAPSHOT).exists())
        self.assertIn('auto-route', skills.SKILLS)
        self.assertFalse(self.capture()['captured'])

    def test_dry_run_is_read_only(self):
        self.edit(); before=self.hashes(); result=routing.inspect(self.s())
        self.assertTrue(result['changed']); self.assertEqual(before,self.hashes())

    def test_capture_does_not_change_manuscript_or_scientific_nodes(self):
        self.edit('X is associated with Y.'); before=file_hash(self.root / 'manuscript/main.md'); nodes=copy.deepcopy(self.s().state['nodes'])
        result=self.capture(); rec=self.record(result)
        self.assertTrue(result['captured']); self.assertIn('knowledge-evidence',result['routes'])
        self.assertEqual(before,file_hash(self.root / 'manuscript/main.md')); self.assertEqual(nodes,self.s().state['nodes'])
        self.assertTrue(any('associated' in c.get('diff','') for c in rec['changes']))
        self.assertTrue(result['issue_ids'])

    def test_repeated_capture_no_loop_no_duplicate(self):
        self.edit(); self.capture(); before=self.hashes()
        self.assertFalse(self.capture()['captured']); self.assertEqual(before,self.hashes())

    def test_edit_batches_coalesce_open_tasks_but_preserve_records(self):
        self.edit('First'); first=self.capture(); self.edit('Second'); second=self.capture()
        self.assertNotEqual(first['change_id'],second['change_id'])
        self.assertEqual(first['tasks'],second['tasks'])
        for task in self.s().state['tasks']: self.assertEqual(len(task['change_ids']),2)
        self.assertNotEqual(self.record(first),self.record(second))

    def test_repeated_revert_transitions_get_distinct_history_ids(self):
        path=self.root/'manuscript/main.md';original=path.read_text();changed=original.replace('## Discussion','## Discussion revised')
        ids=[]
        for text in (changed, original, changed, original):
            atomic_write(path,text);ids.append(self.capture()['change_id'])
        self.assertEqual(len(set(ids)),4)

    def test_claim_meaning_is_retained_with_node_change(self):
        s=self.s();s.state['nodes']['CLM-1']=make_node('CLM-1','claim','Fixture',{'text':'X causes Y','strength':'causal','scope':'fixture'})
        s.event('fixture','test');s.commit();self.capture()
        s=self.s();s.node('CLM-1')['data'].update(text='X is associated with Y',strength='association');s.event('fixture','test');s.commit()
        rec=self.record(self.capture());change=next(c for c in rec['changes'] if c['type']=='node' and c['id']=='CLM-1')
        self.assertEqual(change['before']['meaning']['strength'],'causal');self.assertEqual(change['after']['meaning']['strength'],'association')

    def test_notes_are_unconfirmed_context_not_evidence(self):
        nodes=copy.deepcopy(self.s().state['nodes'])
        result=self.capture(note='作者偏好：用 association，当前尚未讨论统计理由。',note_kind='preference')
        self.assertEqual(self.record(result)['note']['status'],'unconfirmed-context')
        self.assertEqual(nodes,self.s().state['nodes']); self.assertFalse(result['issue_ids'])
        self.assertIn('rules-compliance',result['routes'])

    def test_duplicate_note_is_idempotent(self):
        self.capture(note='Candidate alternative, no final decision.'); before=self.hashes()
        self.capture(note='Candidate alternative, no final decision.'); self.assertEqual(before,self.hashes())

    def test_note_does_not_invalidate_scientific_fingerprint(self):
        before=self.s().fingerprint(); self.capture(note='A tentative discussion point.')
        self.assertEqual(before,self.s().fingerprint())

    def test_actual_edit_invalidates_fingerprint(self):
        before=self.s().fingerprint(); self.edit(); self.assertNotEqual(before,self.s().fingerprint())

    def test_conversation_decision_remains_candidate(self):
        r=self.capture(note='Speaker: user. Might compare two methods.',note_kind='decision-candidate')
        self.assertIn('idea-evaluation',r['routes']); self.assertEqual(self.record(r)['note']['status'],'unconfirmed-context')

    def test_source_route_does_not_promote_discovery(self):
        atomic_write(self.root/'workspace/sources/new.txt','Unverified source text.')
        r=self.capture(); self.assertIn('knowledge-evidence',r['routes'])
        self.assertFalse(any(n['kind']=='evidence' for n in self.s().state['nodes'].values()))

    def test_data_change_routes_analysis_and_figures(self):
        atomic_write(self.root/'workspace/data/example.csv','a,b\n1,2\n')
        r=self.capture(); self.assertIn('logic-methodology',r['routes']); self.assertIn('figure-visualization',r['routes'])

    def test_rule_change_global_impact(self):
        atomic_write(self.root/'workspace/rules/project-policy.md','New review requirement.')
        r=self.capture(); self.assertIn('rules-compliance',r['routes']); self.assertEqual(len(r['impact']['sections']),6)

    def test_deleted_file_is_recorded(self):
        p=self.root/'workspace/data/temp.csv';atomic_write(p,'value');self.capture();p.unlink()
        rec=self.record(self.capture());self.assertTrue(any(c.get('path')=='workspace/data/temp.csv' and c['after'] is None for c in rec['changes']))

    def test_shared_claim_changes_propagate_between_sections(self):
        s=self.s();claim=make_node('CLM-1','claim','Fixture',{'text':'X causes Y.','strength':'causal'},status='draft')
        s.state['nodes'][claim['id']]=claim
        for k in ('SEC-DISCUSSION','SEC-ABSTRACT'): s.node(k)['depends_on'].append(claim['id'])
        s.event('fixture','test');s.commit();self.capture()
        self.edit('X is associated with Y.');r=self.capture()
        self.assertIn('CLM-1',r['impact']['affected']);self.assertIn('SEC-ABSTRACT',r['impact']['sections'])

    def test_malformed_markers_are_saved_as_pending_not_discarded(self):
        atomic_write(self.root/'manuscript/main.md','<!-- rw:section SEC-ERROR -->\nunclosed')
        r=self.capture();self.assertTrue(self.record(r)['structure_error']);self.assertTrue(r['needs_confirmation'])
        self.assertFalse(self.capture()['captured'])

    def test_both_sides_conflict_is_preserved(self):
        self.edit();s=self.s();s.node('SEC-DISCUSSION')['data']['text']='Workspace side changed.';s.event('fixture','test');s.commit()
        r=self.capture();self.assertTrue(self.record(r)['conflicts'])
        self.assertEqual(self.s().node('SEC-DISCUSSION')['data']['text'],'Workspace side changed.')

    def test_legacy_lazy_bootstrap_finds_unsynced_text(self):
        (self.root/routing.SNAPSHOT).unlink();self.edit('Preexisting edit.')
        r=self.capture();self.assertTrue(r['captured']);self.assertTrue(r['baseline_initialized'])
        self.assertIn('earlier edits are unknown',self.record(r)['initial_history_limit'])

    def test_reporting_and_captures_do_not_trigger_themselves(self):
        atomic_write(self.root/'workspace/reports/generated.md','Report only.')
        self.assertFalse(self.capture()['captured'])

    def test_review_cycle_preserves_pending_route_tasks(self):
        self.edit();r=self.capture();self.edit('later');skills.cycle(self.s(),'test')
        self.assertTrue(all(t['status']=='open' for t in self.s().state['tasks'] if t['id'] in r['tasks']))

    def test_task_packets_include_pending_route_work(self):
        self.edit();self.capture();p=skills.task_packet(self.s(),'auto-route','Reconcile changes')
        self.assertTrue(p['routed_tasks']);self.assertIn('manuscript',p)

    def test_complete_refuses_unresolved_issues(self):
        self.edit();r=self.capture()
        with self.assertRaises(WorkspaceError): routing.complete(self.s(),r['change_id'],'test',NOTE)

    def test_complete_note_task_does_not_approve_science(self):
        r=self.capture(note='An optional contextual suggestion.');out=routing.complete(self.s(),r['change_id'],'test',NOTE)
        self.assertTrue(out['completed']);self.assertFalse(self.s().state['approvals'])

    def test_complete_group_waits_for_all_change_records(self):
        a=self.capture(note='first');b=self.capture(note='second')
        routing.complete(self.s(),a['change_id'],'test',NOTE)
        self.assertTrue(any(t['status']=='open' for t in self.s().state['tasks']))
        routing.complete(self.s(),b['change_id'],'test',NOTE)
        self.assertFalse(any(t['status']=='open' for t in self.s().state['tasks']))

    def test_complete_refuses_tampered_capture_record(self):
        r=self.capture(note='Original note.');p=self.root/r['record'];rec=json.loads(p.read_text());rec['note']['text']='Changed';atomic_write(p,pretty(rec))
        with self.assertRaises(WorkspaceError): routing.complete(self.s(),r['change_id'],'test',NOTE)

    def test_secret_files_not_in_capture(self):
        atomic_write(self.root/'workspace/data/.env','DO_NOT_CAPTURE=secret')
        atomic_write(self.root/'workspace/sources/credentials.json','secret')
        current=routing.inspect(self.s())['current']
        self.assertNotIn('workspace/data/.env',current['files']);self.assertNotIn('workspace/sources/credentials.json',current['files'])

    def test_symlink_refused_without_advancing_snapshot(self):
        before=file_hash(self.root/routing.SNAPSHOT);(self.root/'workspace/data/link').symlink_to(Path(self.tmp.name))
        with self.assertRaises(WorkspaceError):self.capture()
        self.assertEqual(before,file_hash(self.root/routing.SNAPSHOT))

    def test_lock_protects_capture(self):
        self.edit();before=file_hash(self.root/routing.SNAPSHOT);atomic_write(self.root/'.rw/write.lock','other')
        with self.assertRaises(WorkspaceError):self.capture()
        self.assertEqual(before,file_hash(self.root/routing.SNAPSHOT))

    def test_note_and_manuscript_limits(self):
        with self.assertRaises(WorkspaceError):self.capture(note='a'*8001)
        atomic_write(self.root/'manuscript/main.md','a'*(routing.TEXT_LIMIT+1))
        with self.assertRaises(WorkspaceError):self.capture()

    def test_capture_transaction_recovery(self):
        import research_workspace.store as mod
        self.edit();original=mod.atomic_write;calls=0
        def fail(path,text):
            nonlocal calls
            calls+=1
            if calls==3:raise OSError('simulated interruption')
            original(path,text)
        with patch.object(mod,'atomic_write',side_effect=fail):
            with self.assertRaises(OSError):self.capture()
        recover(self.root);self.assertFalse(self.capture()['captured'])
        self.assertTrue(any(t.get('origin')=='auto-route' for t in self.s().state['tasks']))

class HooksCase(unittest.TestCase):
    setUp = RouteCase.setUp
    s = RouteCase.s
    edit = RouteCase.edit

    def test_hook_preview_does_not_create_settings(self):
        result=route_hooks.configure(self.s())
        self.assertFalse(result['applied']);self.assertFalse((self.root/route_hooks.SETTINGS).exists())
        self.assertIn('-I -m research_workspace',result['command'])

    def test_install_preserves_unrelated_hooks_and_permissions(self):
        path=self.root/route_hooks.SETTINGS
        prior={'permissions':{'allow':['Read']},'env':{'PRIVATE_FIXTURE':'DO_NOT_ECHO'},'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo existing'}]}]}}
        atomic_write(path,pretty(prior))
        result=route_hooks.configure(self.s(),approve=True);data=json.loads(path.read_text())
        self.assertTrue(result['applied']);self.assertEqual(data['permissions'],prior['permissions'])
        self.assertEqual(data['env'],prior['env']);self.assertNotIn('DO_NOT_ECHO',pretty(result))
        self.assertEqual(len(data['hooks']['Stop']),2)

    def test_install_is_idempotent(self):
        route_hooks.configure(self.s(),approve=True);path=self.root/route_hooks.SETTINGS;before=file_hash(path)
        self.assertFalse(route_hooks.configure(self.s(),approve=True)['changed']);self.assertEqual(before,file_hash(path))

    def test_remove_only_own_handlers(self):
        path=self.root/route_hooks.SETTINGS
        prior={'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo existing'}]}]},'permissions':{'allow':['Read']}}
        atomic_write(path,pretty(prior));route_hooks.configure(self.s(),approve=True)
        route_hooks.configure(self.s(),approve=True,remove=True);self.assertEqual(json.loads(path.read_text()),prior)

    def test_remove_missing_is_noop(self):
        self.assertFalse(route_hooks.configure(self.s(),approve=True,remove=True)['changed'])
        self.assertFalse((self.root/route_hooks.SETTINGS).exists())

    def test_stop_records_edits_without_restarting(self):
        self.edit();out=route_hooks.handle(self.root,io.StringIO(json.dumps({'hook_event_name':'Stop','stop_hook_active':True})))
        self.assertEqual(out,{'suppressOutput':True})
        self.assertTrue(any(t.get('origin')=='auto-route' for t in self.s().state['tasks']))

    def test_hook_ignores_prompts_transcripts_and_tool_commands(self):
        self.edit();out=route_hooks.handle(self.root,io.StringIO(json.dumps({'hook_event_name':'PostToolUse','prompt':'DO_NOT_STORE','transcript_path':'/nonexistent/private','tool_input':{'command':'DO_NOT_EXECUTE'}})))
        self.assertIn('hookSpecificOutput',out)
        for p in (self.root/routing.HISTORY).glob('*.json'):
            self.assertNotIn('DO_NOT_STORE',p.read_text());self.assertNotIn('DO_NOT_EXECUTE',p.read_text())

    def test_no_change_tool_hook_silent_even_with_pending_tasks(self):
        self.edit();routing.capture(self.s())
        out=route_hooks.handle(self.root,io.StringIO('{"hook_event_name":"PostToolUse"}'))
        self.assertEqual(out,{'suppressOutput':True})

    def test_hook_failure_nonblocking_visible_and_does_not_advance(self):
        self.edit();before=file_hash(self.root/routing.SNAPSHOT);atomic_write(self.root/'.rw/write.lock','writer')
        out=route_hooks.handle(self.root,io.StringIO('{"hook_event_name":"UserPromptSubmit"}'))
        self.assertIn('systemMessage',out);self.assertNotIn('decision',out);self.assertEqual(before,file_hash(self.root/routing.SNAPSHOT))

    def test_bad_or_large_event_safe(self):
        for event in ('not json','{}','x'*70000):
            self.assertIn('systemMessage',route_hooks.handle(self.root,io.StringIO(event)))

    def test_invalid_settings_left_untouched(self):
        path=self.root/route_hooks.SETTINGS;atomic_write(path,'{broken');before=file_hash(path)
        with self.assertRaises(ValueError):route_hooks.configure(self.s(),approve=True)
        self.assertEqual(before,file_hash(path))

class UpgradeRouteCase(unittest.TestCase):
    def test_old_study_incrementally_gains_route_skill_with_customizations_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'study';initialize(root,'Synthetic legacy','Fixture')
            skills.install_skills(Store(root),'.agents/skills')
            baseline=root/'.rw/framework.json';d=json.loads(baseline.read_text());d['version']='0.1.0'
            for key in list(d['files']):
                if '/auto-route/' in key:
                    d['files'].pop(key);(root/key).unlink()
            atomic_write(baseline,pretty(d));(root/routing.SNAPSHOT).unlink()
            filled=root/'workspace/research/idea-evaluation.md';atomic_write(filled,filled.read_text()+'\nExisting research text.\n')
            local=root/'workspace/skills/researcher/SKILL.md';atomic_write(local,local.read_text()+'\nLocal research preference.\n')
            protected=[root/'workspace/state.json',root/'manuscript/main.md',filled,local,root/'workspace/rules/project-policy.md']
            before={str(p):file_hash(p) for p in protected}
            result=apply_upgrade(root,None,'Fixture',approve=True)
            self.assertEqual(before,{str(p):file_hash(p) for p in protected})
            self.assertTrue((root/'workspace/skills/auto-route/SKILL.md').exists());self.assertTrue((root/'.agents/skills/auto-route/SKILL.md').exists())
            rollback(root,result['backup_id']);self.assertEqual(before,{str(p):file_hash(p) for p in protected})
            self.assertFalse((root/'workspace/skills/auto-route/SKILL.md').exists())

if __name__ == '__main__': unittest.main()
