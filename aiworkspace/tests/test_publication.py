"""Offline publication contracts and actual local Git/TeX workflows. No private login."""
import copy
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from datetime import datetime, timezone
from research_workspace import venues, latex_project as latex, overleaf, routing, sync, workflow, review, skills
from research_workspace.model import WorkspaceError, make_node, pretty
from research_workspace.publication_io import archive_path, unpack, sha, tree_bytes, public_url, download
from research_workspace.scaffold import initialize
from research_workspace.store import Store, atomic_write, file_hash
from research_workspace.upgrade import apply_upgrade

NOTE='Fixture verification only: reviewed concrete changes and preserved original scientific records.'
TEX=r'''\documentclass{article}
\usepackage{amsmath,graphicx}
\title{Synthetic manuscript}
\author{Source author}
\begin{document}
\maketitle
\begin{abstract}A synthetic manuscript for software validation.\end{abstract}
\section{Introduction}\label{sec:intro}
An example citation \cite{doe2020}. See Section~\ref{sec:intro}.
\input{sections/method}
\bibliographystyle{plain}
\bibliography{refs}
\end{document}
'''
METHOD=r'''\section{Method}
No real experiment is claimed. The identity is $a+b=b+a$.
'''
BIB=b'@article{doe2020, title={Synthetic test reference}, author={Doe, Jane}, journal={Fixture Journal}, year={2020}}\n'
POLICY='Fixture Conference 2026. Anonymous review. Paper format 6 pages. Submission deadline 2026-03-31 23:59 UTC-12. Supplementary material permitted. Ethics review applies.\n'

def template_zip(files=None):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for n,b in (files or {'main.tex':TEX.encode(),'sections/method.tex':METHOD.encode(),'refs.bib':BIB,'LICENSE':b'Fixture only'}).items():z.writestr(n,b)
    return out.getvalue()

def profile(venue_id='fixture-2026-review',family='article'):
    return {'profile_version':1,'id':venue_id,'name':'Fixture Conference','year':2026,'submission_year':2026,'track':'full','stage':'review','anonymous':True,
      'sources':[{'id':'venue','role':'venue','url':'https://venue.example.org/2026/authors'}],
      'template':{'url':'https://venue.example.org/template.zip','main':'main.tex','license_note':'Synthetic fixture, no publisher endorsement','class_options':'','bibliography_style':'plain'},
      'requirements':[{'topic':'anonymity','source':'venue','quote':'Anonymous review.'}],
      'deadlines':[{'label':'Paper','source':'venue','quote':'Submission deadline 2026-03-31 23:59 UTC-12.','at':'2026-03-31T23:59:00-12:00'}]}

class PublicationCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.root=self.base/'study'
        initialize(self.root,'Publication fixture','Fixture Author')
        self.sources=self.base/'sources';self.sources.mkdir();(self.sources/'venue.txt').write_text(POLICY)
        self.archive=self.base/'template.zip';self.archive.write_bytes(template_zip())
    def s(self):return Store(self.root)
    def install(self,p=None):return venues.install(self.s(),p or profile(),'fixture',approve=True,archive=self.archive,sources_dir=self.sources)
    def native(self):
        entry=self.install();latex.adopt(self.s(),entry['working_directory'],'main.tex','fixture',approve=True);return entry['working_directory']
    def hashes(self):return {p.relative_to(self.root).as_posix():file_hash(p) for p in self.root.rglob('*') if p.is_file()}

    def test_real_template_bytes_copied_and_rules_captured(self):
        result=self.install();self.assertEqual((self.root/result['working_directory']/'refs.bib').read_bytes(),BIB)
        self.assertEqual((self.root/result['template_original']/'template-original.zip').read_bytes(),self.archive.read_bytes())
        d=json.loads((self.root/result['rules']/'dossier.json').read_text());self.assertEqual(d['status'],'requires-review');self.assertEqual(d['coverage']['ai_policy']['status'],'unknown')
        self.assertTrue((self.root/result['working_directory']/'LICENSE').exists())
    def test_offline_sources_not_claimed_live(self):
        d=venues.source_dossier(profile(),sources_dir=self.sources);self.assertFalse(d['sources'][0]['live_fetched'])
    def test_install_requires_approval(self):
        before=self.hashes()
        with self.assertRaises(WorkspaceError):venues.install(self.s(),profile(),'f',archive=self.archive,sources_dir=self.sources)
        self.assertEqual(before,self.hashes())
    def test_install_refuses_overwrite(self):
        self.install();before=self.hashes()
        with self.assertRaises(WorkspaceError):self.install()
        self.assertEqual(before,self.hashes())
    def test_rules_refresh_keeps_old_and_invalidates_changed_quote(self):
        result=self.install();before=(self.root/result['rules']/'dossier.json').read_bytes()
        (self.sources/'venue.txt').write_text(POLICY.replace('Anonymous review.','Single-blind review.').replace('2026-03-31 23:59 UTC-12','2026-04-02 23:59 UTC-12'))
        preview=venues.refresh(self.s(),profile()['id'],'f',sources_dir=self.sources);self.assertTrue(preview['changed']);self.assertFalse(preview['applied'])
        out=venues.refresh(self.s(),profile()['id'],'f',sources_dir=self.sources,approve=True)
        d=json.loads((self.root/out['rules_dir']/'dossier.json').read_text());self.assertEqual(len(d['invalidated_structured_entries']),2);self.assertEqual(d['deadlines'],[])
        self.assertEqual((self.root/result['rules']/'dossier.json').read_bytes(),before)
    def test_deadline_timezone_and_past(self):
        d=profile()['deadlines'][0];self.assertEqual(venues.deadline_status(d,datetime(2026,9,26,tzinfo=timezone.utc)),'past')
        self.assertIn('20260401T115900Z',venues.calendar(venues.source_dossier(profile(),sources_dir=self.sources)))
        p=profile();p['deadlines'][0]['at']='2026-03-31T23:59:00'
        with self.assertRaises(WorkspaceError):venues.validate_profile(p)
    def test_missing_deadline_never_assumes_midnight(self):
        self.assertEqual(venues.deadline_status({'label':'unknown'}),'time-or-timezone-unresolved')
    def test_wrong_quote_blocked(self):
        p=profile();p['requirements'][0]['quote']='Invented publisher rule'
        with self.assertRaises(WorkspaceError):self.install(p)
        self.assertFalse((self.root/'workspace/venues/index.json').exists())
    def test_edition_is_not_inferred(self):
        p=profile();p['year']=2027;d=venues.source_dossier(p,sources_dir=self.sources);self.assertFalse(d['sources'][0]['edition_mentioned']);self.assertEqual(d['status'],'requires-review')
    def test_specific_venue_source_required(self):
        p=profile();p['sources'][0]['role']='publisher'
        with self.assertRaises(WorkspaceError):venues.validate_profile(p)
    def test_ambiguous_main_rejected(self):
        with self.assertRaises(WorkspaceError):venues.detect_main({'a.tex':TEX.encode(),'b.tex':TEX.encode()})
    def test_pin_mismatch_blocks(self):
        p=profile();p['template']['sha256']='0'*64
        with self.assertRaises(WorkspaceError):self.install(p)
    def test_discovery_real_interface_with_recorded_transport(self):
        transport=lambda u:(b'<html><p>2026 paper submission</p><a href="/template.zip">template</a></html>',{'url':u,'content_type':'text/html'})
        result=venues.discover(self.s(),'Fixture',2026,'Full','f',urls=['https://venue.example.org/2026'],online=True,transport=transport)
        self.assertIn('https://venue.example.org/template.zip',result['candidate_links']);self.assertTrue((self.root/result['record']).exists())
    def test_discovery_unknown_seed_does_not_guess_previous_year(self):
        with self.assertRaises(WorkspaceError):venues.discover(self.s(),'VIS',2027,'Full','f',online=True)
    def test_native_adoption_is_previewable(self):
        e=self.install();before=self.hashes();out=latex.adopt(self.s(),e['working_directory'],'main.tex','f');self.assertTrue(out['section_ids']);self.assertEqual(before,self.hashes())
    def test_native_adoption_keeps_old_markdown_and_inputs(self):
        old_sections=copy.deepcopy({k:n for k,n in self.s().state['nodes'].items() if n['kind']=='section'})
        before=(self.root/'manuscript/main.md').read_bytes();directory=self.native()
        self.assertEqual(before,(self.root/'manuscript/main.md').read_bytes());self.assertEqual((self.root/directory/'sections/method.tex').read_text(),METHOD)
        self.assertFalse(sync.plan(self.s())['changes']);self.assertFalse(sync.plan(self.s())['outside_changed'])
        archived=json.loads(next((self.root/'workspace/history/latex').glob('ADOPT-*.json')).read_text())
        self.assertEqual(archived['previous_sections'],old_sections)
    def test_native_external_tex_edit_syncs_and_routes(self):
        directory=self.native();routing.capture(self.s());path=self.root/directory/'rw-content.tex';path.write_text(path.read_text().replace('No real experiment','No population inference or real experiment'))
        r=routing.capture(self.s());self.assertIn('manuscript-sync',r['routes']);self.assertTrue(r['issue_ids'])
        proposal=sync.propose_sync(self.s(),'f');workflow.apply(self.s(),proposal['id'],'f',NOTE,approve=True)
        self.assertFalse(sync.plan(self.s())['changes']);self.assertTrue(any('No population inference' in n['data'].get('text','') for n in self.s().state['nodes'].values()))
    def test_native_graph_to_tex_sync(self):
        directory=self.native();s=self.s();key=next(k for k,n in s.state['nodes'].items() if n['kind']=='section' and n['status']!='retired');n=copy.deepcopy(s.node(key));n['data']['text']+='\nAn authorized bounded edit.\n'
        p=workflow.propose(s,[{'op':'upsert','node':n}],'f','Fixture');workflow.apply(self.s(),p['id'],'f',NOTE,approve=True)
        p=sync.propose_sync(self.s(),'f');workflow.apply(self.s(),p['id'],'f',NOTE,approve=True)
        self.assertIn('An authorized bounded edit.',(self.root/directory/'rw-content.tex').read_text());self.assertFalse(sync.plan(self.s())['changes'])
    def test_native_conflict_pauses(self):
        directory=self.native();path=self.root/directory/'rw-content.tex';path.write_text(path.read_text().replace('An example citation','An external citation'))
        s=self.s();key=next(k for k,n in s.state['nodes'].items() if 'An example citation' in n['data'].get('text',''));s.node(key)['data']['text']=s.node(key)['data']['text'].replace('An example citation','An internal citation');s.event('fixture','f');s.commit()
        with self.assertRaises(WorkspaceError):sync.propose_sync(self.s(),'f')
        self.assertTrue(sync.plan(self.s())['conflicts'])
    def test_native_preamble_edit_requires_acknowledgment(self):
        directory=self.native();path=self.root/directory/'main.tex';path.write_text(path.read_text().replace('Source author','Other author'))
        with self.assertRaises(WorkspaceError):sync.propose_sync(self.s(),'f')
        p=sync.propose_sync(self.s(),'f',acknowledge_outside=True);self.assertIn('MANUSCRIPT',p['sync_commit']['semantic_review'])
    def test_writer_receives_native_manuscript(self):
        self.native();packet=skills.task_packet(self.s(),'writing-language','Inspect');self.assertIn('Synthetic manuscript',packet['manuscript']);self.assertIn('venue_dossiers',packet)
    def test_latex_citation_keys_supported(self):
        self.assertEqual(review.citation_ids(r'Text \citep[see][3]{a,b} \citet{c}'),{'a','b','c'})
    def test_comment_and_verbatim_citations_ignored(self):
        text='Real \\cite{yes}. % \\cite{no}\n'+r'\verb|\cite{no2}|'
        self.assertEqual(set(latex.inventory(text)['citations']),{'yes'})
    def test_recursive_input_and_cyclic_guard(self):
        self.assertIn('No real experiment',latex.expand({'main.tex':TEX.encode(),'sections/method.tex':METHOD.encode()},'main.tex'))
        with self.assertRaises(WorkspaceError):latex.expand({'main.tex':b'\\input{main}'},'main.tex')
    def test_dynamic_input_guard(self):
        for text in (r'\input{\computed}',r'\input{../secret}',r'\import{root}{file}'):
            with self.assertRaises(WorkspaceError):latex.expand({'main.tex':text.encode()},'main.tex')
    def test_transfer_retains_inventories_and_original_bytes(self):
        first=self.install();target=self.install(profile('target-2026-review'));before=tree_bytes(self.root/first['working_directory'])
        result=latex.transfer(self.s(),first['working_directory'],'main.tex','target-2026-review','f',approve=True)
        after=tree_bytes(self.root/result['destination']);self.assertEqual(before,tree_bytes(self.root/first['working_directory']));self.assertEqual(BIB,after['refs.bib'])
        self.assertEqual(latex.inventory(latex.expand(before,'main.tex')),latex.inventory(latex.expand(after,'main.tex')))
        self.assertNotIn('Source author',after['main.tex'].decode());self.assertIn('Anonymous authors',after['main.tex'].decode());self.assertNotIn('latex',self.s().state['project'])
    def test_transfer_preview_no_writes(self):
        e=self.install();self.install(profile('target'));before=self.hashes();latex.transfer(self.s(),e['working_directory'],'main.tex','target','f');self.assertEqual(before,self.hashes())
    def test_transfer_missing_bib_key_refused(self):
        e=self.install();self.install(profile('target'));(self.root/e['working_directory']/'refs.bib').write_text('')
        with self.assertRaises(WorkspaceError):latex.transfer(self.s(),e['working_directory'],'main.tex','target','f',approve=True)
    def test_transfer_unknown_class_refused(self):
        e=self.install();p=profile('target');raw=template_zip({'main.tex':TEX.replace('{article}','{unknownclass}').encode(),'sections/method.tex':METHOD.encode(),'refs.bib':BIB});self.archive.write_bytes(raw);self.install(p)
        with self.assertRaises(WorkspaceError):latex.transfer(self.s(),e['working_directory'],'main.tex','target','f')
    def test_pack_excludes_workspace_and_private_metadata(self):
        d=self.native();folder=self.root/d;(folder/'.overleaf').mkdir();(folder/'.overleaf/settings.json').write_text('{"secret":"not uploaded"}')
        out=latex.pack(self.s(),str(self.base/'paper.zip'))
        with zipfile.ZipFile(out['zip']) as z:
            self.assertIn('main.tex',z.namelist());self.assertFalse(any(n.startswith(('.','workspace/')) for n in z.namelist()))
    def test_pack_credentials_filename_refused(self):
        d=self.native();(self.root/d/'credentials.json').write_text('{}')
        with self.assertRaises(WorkspaceError):latex.pack(self.s(),str(self.base/'paper.zip'))
    def test_build_requires_permission(self):
        self.native()
        with self.assertRaises(WorkspaceError):latex.build(self.s())
    @unittest.skipUnless(shutil.which('pdflatex') and (shutil.which('bibtex') or shutil.which('bibtex.original')),'TeX distribution unavailable')
    def test_actual_tex_compile_and_stale_receipt(self):
        d=self.native();result=latex.build(self.s(),allow_exec=True);self.assertTrue(result['compiled'],(self.root/'.rw/builds'/result['build_id']/'build-log.txt').read_text());self.assertFalse(result['unresolved_references']);self.assertEqual(latex.integrity_issues(self.s()),[])
        p=self.root/d/'rw-content.tex';p.write_text(p.read_text()+'\n% modification\n');self.assertTrue(latex.integrity_issues(self.s()))
    def test_old_study_gets_new_skills_without_research_overwrite(self):
        s=self.s();skills.install_skills(s,'.agents/skills');baseline=self.root/'.rw/framework.json';d=json.loads(baseline.read_text());d['version']='0.2.0'
        for key in list(d['files']):
            if any('/'+n+'/' in key for n in ('venue-setup','venue-transfer','overleaf-sync')):d['files'].pop(key);(self.root/key).unlink()
        atomic_write(baseline,pretty(d));protected=['workspace/state.json','manuscript/main.md','workspace/research/idea-evaluation.md','workspace/rules/project-policy.md'];before={n:file_hash(self.root/n) for n in protected}
        apply_upgrade(self.root,None,'f',approve=True);self.assertEqual(before,{n:file_hash(self.root/n) for n in protected});self.assertTrue((self.root/'.agents/skills/venue-setup/SKILL.md').exists())


    def test_transfer_graphics_and_table_content_retained(self):
        original=self.install();folder=self.root/original['working_directory']
        import base64
        image=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK5kAAAAASUVORK5CYII=')
        (folder/'figure.png').write_bytes(image)
        main=folder/'main.tex';main.write_text(main.read_text().replace(r'\input{sections/method}',r'\input{sections/method}'+'\n'+r'\begin{figure}\includegraphics{figure.png}\caption{Synthetic pixel}\label{fig:test}\end{figure}'+'\n'+r'\begin{tabular}{cc}A&B\\1&2\end{tabular}'))
        before=tree_bytes(folder);self.install(profile('target'))
        moved=latex.transfer(self.s(),original['working_directory'],'main.tex','target','f',approve=True)
        target=self.root/moved['destination'];self.assertEqual((target/'figure.png').read_bytes(),image)
        self.assertEqual(moved['inventories']['graphics'],['figure.png']);self.assertIn(r'\begin{tabular}{cc}A&B\\1&2\end{tabular}',(target/'rw-transfer-body.tex').read_text())
        self.assertEqual(before,tree_bytes(folder))

    def test_acm_transfer_draft_suppresses_placeholder_publication_metadata(self):
        original=self.install()
        self.archive.write_bytes(template_zip({'main.tex':TEX.replace('{article}','{acmart}').encode(),'sections/method.tex':METHOD.encode(),'refs.bib':BIB}))
        p=profile('target-acm');p['template']['class_options']='manuscript,review,anonymous';self.install(p)
        moved=latex.transfer(self.s(),original['working_directory'],'main.tex',p['id'],'f',approve=True)
        main=(self.root/moved['destination']/'main.tex').read_text()
        self.assertIn(r'\acmDOI{}',main);self.assertIn(r'\settopmatter{printacmref=false}',main)
        self.assertNotIn(r'\usepackage{amssymb}',main);self.assertTrue(any('ACM draft' in x for x in moved['blockers']))

class ArchiveCase(unittest.TestCase):
    def test_traversal_nonportable_paths(self):
        for name in ('../x.tex','/x.tex','a/../x.tex','a\\x.tex','C:x.tex','CON.tex','x.','a//b.tex'):
            with self.subTest(name=name),self.assertRaises(WorkspaceError):archive_path(name)
    def test_login_html_is_not_zip(self):
        with self.assertRaises(WorkspaceError):unpack(b'<html>login</html>')
    def test_case_collision_and_duplicates_rejected(self):
        with self.assertRaises(WorkspaceError):unpack(template_zip({'main.tex':TEX.encode(),'MAIN.tex':TEX.encode()}))
    def test_zip_symlink_rejected(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            info=zipfile.ZipInfo('link.tex');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'/private')
        with self.assertRaises(WorkspaceError):unpack(out.getvalue())
    def test_execution_settings_not_installed(self):
        files,skipped=unpack(template_zip({'main.tex':TEX.encode(),'.latexmkrc':b'exec','postinstall.sh':b'exec','LICENSE':b'rights'}));self.assertNotIn('.latexmkrc',files);self.assertIn('postinstall.sh',skipped);self.assertIn('LICENSE',files)
    def test_source_url_credentials_and_wrong_host_blocked(self):
        for value in ('http://x.org/a','https://secret@x.org/a','https://x.org/a?token=secret','https://other.org/a'):
            with self.assertRaises(WorkspaceError):public_url(value,{'x.org'},resolve=False)
    def test_private_ip_download_rejected(self):
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(WorkspaceError):public_url('https://x.org/a',{'x.org'})
    def test_network_is_opt_in(self):
        with self.assertRaises(WorkspaceError):download('https://x.org/a',{'x.org'},online=False)

class Remote:
    def __init__(self,files):self.files=copy.deepcopy(files);self.commit='a'*40;self.pushes=0
    def read(self):return copy.deepcopy(self.files),self.commit
    def push(self,files,parent):
        if parent!=self.commit:raise WorkspaceError('Remote advanced')
        self.files=copy.deepcopy(files);self.pushes+=1;self.commit=sha(pretty({k:sha(v) for k,v in files.items()}).encode())[:40];return self.commit

class OverleafCase(PublicationCase):
    # Inherit setup helpers, not the parent test methods (suite construction below).
    def setup_remote(self,mode='git'):
        entry=self.install();d=entry['working_directory'];overleaf.configure(self.s(),'f',project_id='project123',directory=d,mode=mode,approve=True)
        return d,Remote(tree_bytes(self.root/d))
    def test_configuration_custom_host_no_secret(self):
        d,remote=self.setup_remote();c=overleaf.config(self.s());self.assertEqual(c['server'],'https://nankaivisoverleaf.asia');self.assertIn('/git/project123',c['git_url']);self.assertFalse(c['live_connection_verified']);self.assertFalse('password' in c)
    def test_wrong_host_and_embedded_token_rejected(self):
        for u in ('https://git:token@nankaivisoverleaf.asia/git/p','https://evil.org/git/p'):
            with self.assertRaises(WorkspaceError):overleaf.checked_git_url(overleaf.DEFAULT_SERVER,'p',u)
    def test_sync_preview_no_paper_mutation(self):
        d,r=self.setup_remote();r.files['remote.txt']=b'new';before=tree_bytes(self.root/d);out=overleaf.synchronize(self.s(),online=True,transport=r);self.assertFalse(out['synchronized']);self.assertEqual(before,tree_bytes(self.root/d));self.assertEqual(r.pushes,0)
    def test_bidirectional_sync_and_idempotence(self):
        d,r=self.setup_remote();overleaf.synchronize(self.s(),online=True,approve=True,transport=r);(self.root/d/'local.txt').write_bytes(b'local');r.files['remote.txt']=b'remote'
        out=overleaf.synchronize(self.s(),online=True,approve=True,transport=r);self.assertTrue(out['synchronized']);self.assertEqual(r.files['local.txt'],b'local');self.assertEqual((self.root/d/'remote.txt').read_bytes(),b'remote')
        pushes=r.pushes;out=overleaf.synchronize(self.s(),online=True,approve=True,transport=r);self.assertTrue(out['unchanged']);self.assertEqual(pushes,r.pushes)
    def test_overlap_conflict_keeps_both(self):
        d,r=self.setup_remote();overleaf.synchronize(self.s(),online=True,approve=True,transport=r);(self.root/d/'refs.bib').write_bytes(b'local');r.files['refs.bib']=b'remote'
        out=overleaf.synchronize(self.s(),online=True,approve=True,transport=r);self.assertIn('refs.bib',out['conflicts']);self.assertEqual((self.root/d/'refs.bib').read_bytes(),b'local');self.assertEqual(r.files['refs.bib'],b'remote')
    def test_explicit_resolution_and_deletion(self):
        d,r=self.setup_remote();overleaf.synchronize(self.s(),online=True,approve=True,transport=r);(self.root/d/'refs.bib').write_bytes(b'local');r.files['refs.bib']=b'remote'
        overleaf.synchronize(self.s(),online=True,approve=True,transport=r,resolutions={'refs.bib':'local'});self.assertEqual(r.files['refs.bib'],b'local')
        r.files.pop('refs.bib');out=overleaf.synchronize(self.s(),online=True,approve=True,transport=r);self.assertIn('refs.bib',out['conflicts'])
        overleaf.synchronize(self.s(),online=True,approve=True,transport=r,allow_deletions=True);self.assertFalse((self.root/d/'refs.bib').exists())
    def test_nonoverlapping_text_merge(self):
        result=overleaf.merge_files({'f.tex':b'A\nB\nC\nD\nE\n'},{'f.tex':b'LOCAL\nB\nC\nD\nE\n'},{'f.tex':b'A\nB\nC\nD\nREMOTE\n'});self.assertFalse(result['conflicts']);self.assertIn(b'LOCAL',result['files']['f.tex']);self.assertIn(b'REMOTE',result['files']['f.tex'])
    def test_binary_conflict_stops(self):
        r=overleaf.merge_files({'f.png':b'\x89PNG\x00'},{'f.png':b'\x89PNG\x01'},{'f.png':b'\x89PNG\x02'});self.assertTrue(r['conflicts'])
    def test_unknown_push_outcome_recoverable(self):
        d,r=self.setup_remote();overleaf.synchronize(self.s(),online=True,approve=True,transport=r);(self.root/d/'new.txt').write_bytes(b'data');push=r.push
        def unknown(files,parent):push(files,parent);raise WorkspaceError('connection lost after push')
        r.push=unknown
        with self.assertRaises(WorkspaceError):overleaf.synchronize(self.s(),online=True,approve=True,transport=r)
        self.assertTrue((self.root/overleaf.PENDING).exists());out=overleaf.recover_sync(self.s(),online=True,transport=r);self.assertTrue(out['synchronized'])
    def test_intervening_edit_preserved_on_recovery(self):
        d,r=self.setup_remote();overleaf.synchronize(self.s(),online=True,approve=True,transport=r);(self.root/d/'new.txt').write_bytes(b'data');push=r.push
        def unknown(files,parent):push(files,parent);raise WorkspaceError('lost')
        r.push=unknown
        with self.assertRaises(WorkspaceError):overleaf.synchronize(self.s(),online=True,approve=True,transport=r)
        (self.root/d/'new.txt').write_bytes(b'later edit')
        with self.assertRaises(WorkspaceError):overleaf.recover_sync(self.s(),online=True,transport=r)
        self.assertEqual((self.root/d/'new.txt').read_bytes(),b'later edit')
    def test_workshop_rejects_second_engine(self):
        d,r=self.setup_remote('workshop')
        with self.assertRaises(WorkspaceError):overleaf.synchronize(self.s(),online=True,approve=True,transport=r)
    def test_new_active_template_blocks_old_remote(self):
        d,r=self.setup_remote();s=self.s();s.state['project']['latex']={'directory':'manuscript/other','main':'main.tex'};s.event('fixture','f');s.commit()
        with self.assertRaises(WorkspaceError):overleaf.synchronize(self.s(),online=True,transport=r)
    def test_credential_files_not_sent(self):
        d,r=self.setup_remote();(self.root/d/'credentials.json').write_bytes(b'secret')
        with self.assertRaises(WorkspaceError):overleaf.synchronize(self.s(),online=True,approve=True,transport=r)
        self.assertNotIn('credentials.json',r.files)
    def test_plugin_preview_has_real_extension_id(self):
        out=overleaf.install_plugin();self.assertIn('iamhyc.overleaf-workshop@0.15.10',out['command']);self.assertFalse(out['installed'])
    def test_replica_binding_preserves_settings(self):
        d=self.native();overleaf.configure(self.s(),'f',project_id='project123',directory=d,mode='workshop',approve=True);replica='manuscript/replicas/test';shutil.copytree(self.root/d,self.root/replica);folder=self.root/replica/'.overleaf';folder.mkdir();data={'serverName':'nankaivisoverleaf.asia','uri':'overleaf-workshop://nankaivisoverleaf.asia/test?user%3Duser%26project%3Dproject123'};(folder/'settings.json').write_text(json.dumps(data));out=overleaf.bind_replica(self.s(),replica,'f',approve=True);self.assertTrue(out['applied']);self.assertEqual(json.loads((folder/'settings.json').read_text()),data)
    @unittest.skipUnless(shutil.which('git'),'Git unavailable')
    def test_actual_local_bare_git_transport_fetch_push(self):
        d,r=self.setup_remote();origin=self.base/'origin';origin.mkdir()
        def git(*args):return subprocess.run(['git','-C',str(origin),*args],capture_output=True,check=True).stdout
        git('init','-b','main');git('config','user.name','Fixture');git('config','user.email','f@example.invalid');git('config','commit.gpgsign','false')
        for name,data in r.files.items():p=origin/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (origin/'.hidden-setting').write_text('preserved');git('add','.');git('commit','-m','Fixture')
        bare=self.base/'remote.git';subprocess.run(['git','clone','--bare',str(origin),str(bare)],capture_output=True,check=True)
        transport=overleaf.GitTransport(self.s(),overleaf.config(self.s()));transport.remote=str(bare) # Test-only local origin, no public CLI bypass.
        out=overleaf.synchronize(self.s(),online=True,approve=True,transport=transport);self.assertTrue(out['synchronized'])
        (self.root/d/'local.txt').write_bytes(b'actual upload');out=overleaf.synchronize(self.s(),online=True,approve=True,transport=transport)
        data=subprocess.run(['git','--git-dir',str(bare),'show','main:local.txt'],capture_output=True,check=True).stdout;self.assertEqual(data,b'actual upload')
        self.assertEqual(subprocess.run(['git','--git-dir',str(bare),'show','main:.hidden-setting'],capture_output=True,check=True).stdout,b'preserved')

# Avoid rerunning inherited PublicationCase tests under OverleafCase.
def load_tests(loader,tests,pattern):
    suite=unittest.TestSuite()
    for cls in (PublicationCase,ArchiveCase,OverleafCase):
        for name in sorted(cls.__dict__):
            if name.startswith('test_'):suite.addTest(cls(name))
    return suite

if __name__=='__main__':unittest.main()
