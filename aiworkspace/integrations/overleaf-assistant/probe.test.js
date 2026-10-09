'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {runProbe, payload, hash} = require('./probe');

async function fixture(flags = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'rw-probe-test-'));
  await fs.writeFile(path.join(root, 'main.tex'), 'original paper\r\n');
  const remote = new Map(); const operations = [];
  const local = async n => { try { return await fs.readFile(path.join(root, n)); } catch (e) { if (e.code === 'ENOENT') return null; throw e; } };
  const io = {
    snapshot: async () => ({'main.tex': hash(await fs.readFile(path.join(root, 'main.tex')))}),
    localRead: local,
    remoteRead: async n => { if (flags.authError) { const e = new Error('SECRET SHOULD NEVER APPEAR'); e.code = 'NoPermissions'; throw e; } return flags.collision ? Buffer.from('existing') : remote.get(n) || null; },
    localCreate: async (n, b) => { operations.push('localCreate'); await fs.writeFile(path.join(root, n), b, {flag: 'wx'}); if (!flags.noUpload) remote.set(n, Buffer.from(b)); },
    remoteWrite: async (n, b) => { operations.push('remoteWrite'); remote.set(n, Buffer.from(b));
      if (!flags.noDownload) await fs.writeFile(path.join(root, n), b);
      if (flags.paperChanges) await fs.appendFile(path.join(root, 'main.tex'), 'collaborator edit');
      if (flags.probeChanges) { remote.set(n, Buffer.from('another writer')); await fs.writeFile(path.join(root, n), 'another writer'); }
    },
    remoteDelete: async n => { operations.push('remoteDelete'); if (flags.noDelete) return; remote.delete(n); await fs.unlink(path.join(root, n)); }
  };
  return {root, remote, operations, io, cleanup: () => fs.rm(root, {recursive: true})};
}
for (const [label, flags, expected] of [
  ['full simulated plugin roundtrip', {}, 'roundtrip_verified'],
  ['upload timeout never passes', {noUpload: true}, 'incomplete'],
  ['download timeout never passes', {noDownload: true}, 'incomplete'],
  ['delete not propagated never passes', {noDelete: true}, 'incomplete'],
  ['authentication error never passes', {authError: true}, 'incomplete'],
  ['filename collision is preserved', {collision: true}, 'incomplete'],
  ['intervening manuscript edit preserved', {paperChanges: true}, 'incomplete'],
  ['intervening probe edit preserved', {probeChanges: true}, 'incomplete']
]) test(label, async () => {
  const f = await fixture(flags);
  try {
    const r = await runProbe(f.io, {approved: true, timeoutMs: 8, intervalMs: 1});
    assert.equal(r.status, expected); assert.equal(r.verified, expected === 'roundtrip_verified');
    assert.ok(!JSON.stringify(r).includes('SECRET'));
    assert.match(r.probe_file, /^aiworkspace-sync-check-[a-f0-9-]+\.png$/);
    if (flags.noUpload || flags.authError || flags.collision) assert.ok(!f.operations.includes('remoteWrite'));
    if (flags.noDownload || flags.probeChanges) assert.ok(!f.operations.includes('remoteDelete'));
    if (!flags.paperChanges) assert.equal(await fs.readFile(path.join(f.root, 'main.tex'), 'utf8'), 'original paper\r\n');
    else assert.match(await fs.readFile(path.join(f.root, 'main.tex'), 'utf8'), /collaborator edit/);
    if (r.verified) { assert.equal(f.remote.size, 0); assert.deepEqual((await fs.readdir(f.root)).sort(), ['main.tex']); }
  } finally { await f.cleanup(); }
});
test('no approval makes no calls', async () => {
  await assert.rejects(() => runProbe(new Proxy({}, {get: () => { throw new Error('must not access'); }})), /approval/);
});
test('PNG payload has random test-only metadata and is reproducible', () => {
  const a = payload('a'), b = payload('b'); assert.ok(a.subarray(1, 4).equals(Buffer.from('PNG')));
  assert.notEqual(hash(a), hash(b)); assert.deepEqual(a, payload('a')); assert.ok(a.includes(Buffer.from('NOT RESEARCH DATA')));
});
test('invalid time bounds rejected', async () => {
  await assert.rejects(() => runProbe({}, {approved: true, timeoutMs: 60000}), /time bounds/);
});
// Load only pure adapter helpers with a minimal VS Code API contract; this does
// not claim an editor or a logged-in Workshop session was used.
const Module = require('node:module'); const load = Module._load;
const vscodeMock = {Uri: {parse: text => {
  const u = new URL(text);
  const value = {scheme: u.protocol.slice(0,-1), authority: u.host, path: decodeURIComponent(u.pathname), query: u.search.slice(1), fragment: u.hash.slice(1)};
  value.with = o => ({...value, ...o}); return value;
}, joinPath: (base, ...parts) => ({...base, path: base.path + '/' + parts.join('/')})}};
Module._load = function (name, ...args) {
  if (name === 'vscode') return vscodeMock;
  return load.call(this, name, ...args);
};
const adapter = require('./extension'); Module._load = load;
test('normal custom URL parsed', () => assert.deepEqual(adapter.target('https://lab.example:8443/project/p1'), {server:'https://lab.example:8443',host:'lab.example:8443',project_id:'p1'}));
for (const url of ['http://lab.example/project/p1','https://x:secret@lab.example/project/p1','https://lab.example/project/p1?token=x','https://lab.example/read/secret'])
  test('reject unsafe URL ' + url.split('?')[0].replace('secret','redacted'), () => assert.throws(() => adapter.target(url)));
test('metadata identity matches intended custom host', () => {
  const t = adapter.target('https://lab.example/project/p1');
  const m = {uri:'overleaf-workshop://lab.example/Paper?user%3Du1%26project%3Dp1',serverName:'lab.example'};
  const u = adapter.metadataUri(m,t); assert.equal(u.query,'user=u1&project=p1');
  assert.throws(() => adapter.metadataUri(m,{...t,project_id:'p2'}));
  assert.throws(() => adapter.metadataUri({...m,uri:'overleaf-workshop://lab.example/Paper?user=u1&project=p1&token=bad'},t));
});
test('snapshot excludes private metadata and rejects symlinks', async () => {
  const f = await fixture();
  try {
    await fs.writeFile(path.join(f.root,'.env'),'private');
    assert.deepEqual(Object.keys(await adapter.snapshot(f.root)),['main.tex']);
    await fs.symlink(path.join(f.root,'main.tex'),path.join(f.root,'linked.tex'));
    await assert.rejects(() => adapter.snapshot(f.root), /Linked/);
  } finally { await f.cleanup(); }
});
test('only root relative requests accepted', async () => {
  const f = await fixture();
  try { for (const s of ['../x','/x','a\\b','a:b','./a']) await assert.rejects(() => adapter.safe(f.root,s)); }
  finally { await f.cleanup(); }
});

async function editorFixture() {
  const f = await fixture(); const id = 'a'.repeat(32), callbacks = {};
  await fs.mkdir(path.join(f.root, '.rw/overleaf-agent/requests'), {recursive:true});
  await fs.mkdir(path.join(f.root, 'manuscript/.overleaf'), {recursive:true});
  await fs.rename(path.join(f.root,'main.tex'),path.join(f.root,'manuscript/main.tex'));
  await fs.writeFile(path.join(f.root, 'manuscript/.overleaf/settings.json'), JSON.stringify({uri:'overleaf-workshop://lab.example/Paper?user=u1&project=p1',serverName:'lab.example'}));
  await fs.writeFile(path.join(f.root, '.rw/overleaf-agent/requests/'+id+'.json'), JSON.stringify({version:1,id,created_at:new Date().toISOString(),project_url:'https://lab.example/project/p1',directory:'manuscript',main:'main.tex',mode:'read'}));
  let reads = 0;
  vscodeMock.workspace = {isTrusted:true, workspaceFolders:[{uri:{scheme:'file',fsPath:f.root}}], fs:{readFile:async () => {reads++;return Buffer.from('original paper\r\n');}}};
  vscodeMock.extensions = {getExtension:() => ({isActive:true,packageJSON:{version:'test-fixture'}})};
  vscodeMock.window = {showWarningMessage:async () => undefined, showInformationMessage:() => {}, registerUriHandler:h => {callbacks.uri=h;return {};}};
  vscodeMock.commands = {registerCommand:(n,fn) => {callbacks.check=fn;return {};}};
  adapter.activate({subscriptions:[]});
  return {...f,id,callbacks,reads:()=>reads,report:async()=>JSON.parse(await fs.readFile(path.join(f.root,'.rw/overleaf-agent/reports/'+id+'.json'),'utf8'))};
}
test('editor cancellation records cancelled and does not read remote', async () => {
  const f=await editorFixture();try {await f.callbacks.check(f.id);assert.equal((await f.report()).status,'cancelled');assert.equal(f.reads(),0);}finally{await f.cleanup();}
});
test('editor trust gate blocks before remote access', async () => {
  const f=await editorFixture();try {vscodeMock.workspace.isTrusted=false;await assert.rejects(()=>f.callbacks.check(f.id),/Trust/);assert.equal(f.reads(),0);}finally{await f.cleanup();}
});
test('overlapping editor requests cannot run concurrently', async () => {
  const f=await editorFixture();try {
    let accept, entered;const reached=new Promise(r=>entered=r);
    vscodeMock.window.showWarningMessage=()=>{entered();return new Promise(r=>accept=r);};
    const first=f.callbacks.check(f.id);await reached;
    await assert.rejects(()=>f.callbacks.check(f.id), e=>e.code==='CHECK_BUSY');
    accept(undefined);await first;assert.equal((await f.report()).status,'cancelled');
  }finally{await f.cleanup();}
});
test('read-only adapter report never claims roundtrip', async () => {
  const f=await editorFixture();try {vscodeMock.window.showWarningMessage=async()=> '允许本次验证';await f.callbacks.check(f.id);const r=await f.report();assert.equal(r.status,'readable_via_plugin');assert.equal(r.verified,false);assert.equal(f.reads(),1);}finally{await f.cleanup();}
});
test('a completed request is not executed a second time', async () => {
  const f=await editorFixture();try {await f.callbacks.check(f.id);const before=await f.report();await f.callbacks.check(f.id);assert.deepEqual(await f.report(),before);assert.equal(f.reads(),0);}finally{await f.cleanup();}
});
