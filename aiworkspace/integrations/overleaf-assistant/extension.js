'use strict';
// All remote I/O is provided by iamhyc.overleaf-workshop's VS Code FS provider.
// No HTTP client, credential reader, private plugin database or second sync loop.
const vscode = require('vscode');
const fs = require('node:fs/promises');
const path = require('node:path');
const {runProbe, hash} = require('./probe');
const EXTENSION = 'iamhyc.overleaf-workshop';
const URI_AUTHORITY = 'aiworkspace-local.overleaf-assistant';
let busy = false;

function ensure(value, message) { if (!value) throw new Error(message); }
async function safe(root, relative) {
  ensure(typeof relative === 'string' && relative && !relative.includes('\\') && !relative.includes(':') &&
    !relative.startsWith('/') && relative.split('/').every(p => p && p !== '.' && p !== '..'), 'Unsafe relative path');
  let current = root;
  ensure(!(await fs.lstat(root)).isSymbolicLink(), 'Linked root refused');
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    try { ensure(!(await fs.lstat(current)).isSymbolicLink(), 'Linked path refused'); }
    catch (e) { if (e.code !== 'ENOENT') throw e; }
  }
  return current;
}
async function readSmall(file) {
  const st = await fs.lstat(file);
  ensure(st.isFile() && !st.isSymbolicLink() && st.size <= 65536, 'Invalid metadata file');
  return JSON.parse(await fs.readFile(file, 'utf8'));
}
async function rootFolder() {
  const folders = vscode.workspace.workspaceFolders;
  ensure(folders && folders.length === 1 && folders[0].uri.scheme === 'file', 'Select one local project window');
  let root = folders[0].uri.fsPath;
  ensure(!(await fs.lstat(root)).isSymbolicLink(), 'Linked workspace refused');
  // A single-folder Replica window is often required by Workshop. Only its
  // explicitly opened manuscript's direct parent is considered, never a scan.
  if (path.basename(root) === 'manuscript') {
    const parent = path.dirname(root);
    const candidate = await safe(parent, 'aiworkspace');
    ensure((await fs.stat(candidate)).isDirectory(), 'Select the paper root');
    root = parent;
  }
  return root;
}
function target(url) {
  ensure(typeof url === 'string' && url.length < 4000 && !/[\x00-\x20\x7f]/.test(url), 'Invalid project URL');
  const u = new URL(url), m = /^\/project\/([A-Za-z0-9_-]{1,128})\/?$/.exec(u.pathname);
  ensure(u.protocol === 'https:' && !u.username && !u.password && !u.search && !u.hash && m, 'Use credential-free HTTPS project URL');
  return {server: u.origin, host: u.host, project_id: m[1]};
}
function metadataUri(metadata, expected) {
  ensure(typeof metadata.uri === 'string', 'Missing replica URI');
  const uri = vscode.Uri.parse(metadata.uri, true);
  let query = uri.query;
  if (!query.includes('=') && /%3d/i.test(query)) query = decodeURIComponent(query);
  const q = new URLSearchParams(query);
  ensure(uri.scheme === 'overleaf-workshop' && uri.authority === expected.host &&
    metadata.serverName === expected.host && !uri.fragment, 'Replica belongs to another server');
  ensure([...q.keys()].every(k => k === 'project' || k === 'user') &&
    q.getAll('project').length === 1 && q.get('project') === expected.project_id &&
    q.getAll('user').length === 1 && /^[A-Za-z0-9_-]+$/.test(q.get('user')), 'Invalid replica project identity');
  ensure(/^\/[^/]+\/?$/.test(uri.path), 'Expected project root URI');
  return uri.with({query: q.toString(), path: uri.path.replace(/\/$/, '')});
}
async function localRead(file) {
  try {
    const st = await fs.lstat(file);
    ensure(st.isFile() && !st.isSymbolicLink() && st.size <= 33554432, 'Invalid local file');
    return await fs.readFile(file);
  } catch (e) { if (e.code === 'ENOENT') return null; throw e; }
}
async function bounded(fn) {
  let timer;
  try { return await Promise.race([fn(), new Promise((_, reject) => {
    timer = setTimeout(() => { const e = new Error('Plugin request timed out'); e.code = 'PROBE_TIMEOUT'; reject(e); }, 10000);
  })]); } finally { clearTimeout(timer); }
}
async function remoteRead(uri) {
  try { return Buffer.from(await bounded(() => vscode.workspace.fs.readFile(uri))); }
  catch (e) { if (e.code === 'FileNotFound') return null; throw e; }
}
async function snapshot(root, ignore = new Set()) {
  const entries = {}; let size = 0;
  async function walk(relative = '') {
    const folder = relative ? await safe(root, relative) : root;
    for (const name of (await fs.readdir(folder)).sort()) {
      if (name.startsWith('.')) continue; // Never inspect local metadata, Git, .env or credentials.
      ensure(!/^(credentials|secrets|tokens|passwords)(\.|$)/i.test(name), 'Private material is inside the manuscript; resolve the scope');
      const rel = relative ? relative + '/' + name : name;
      if (ignore.has(rel)) continue;
      const file = await safe(root, rel), st = await fs.lstat(file);
      if (st.isDirectory()) await walk(rel);
      else {
        ensure(st.isFile() && st.size <= 33554432 && Object.keys(entries).length < 2000, 'Unsupported or oversized manuscript');
        size += st.size; ensure(size <= 100663296, 'Manuscript exceeds check limit');
        entries[rel] = hash(await fs.readFile(file));
      }
    }
  }
  await walk(); return entries;
}
async function persist(root, id, report) {
  const relative = '.rw/overleaf-agent/reports/' + id + '.json';
  const file = await safe(root, relative);
  await fs.mkdir(path.dirname(file), {recursive: true, mode: 0o700});
  await fs.writeFile(file, JSON.stringify(report, null, 2) + '\n', {flag: 'wx', mode: 0o600});
}
async function check(id) {
  if (busy) { const e = new Error('Another check is running'); e.code = 'CHECK_BUSY'; throw e; }
  busy = true;
  try { return await checkOnce(id); } finally { busy = false; }
}
async function checkOnce(id) {
  ensure(vscode.workspace.isTrusted, 'Trust this project through the editor first');
  ensure(typeof id === 'string' && /^[a-f0-9]{32}$/.test(id), 'Invalid request ID');
  const root = await rootFolder();
  const requestPath = await safe(root, '.rw/overleaf-agent/requests/' + id + '.json');
  const request = await readSmall(requestPath);
  try { await fs.lstat(await safe(root, '.rw/overleaf-agent/reports/' + id + '.json'));
    vscode.window.showInformationMessage('这次请求已有结果；请让 Agent 读取报告或准备新检查。'); return;
  } catch (e) { if (e.code !== 'ENOENT') throw e; }
  ensure(request.version === 1 && request.id === id && Object.keys(request).every(k =>
    ['version','id','created_at','project_url','directory','main','mode'].includes(k)), 'Invalid request');
  const age = Date.now() - Date.parse(request.created_at);
  ensure(Number.isFinite(age) && age >= -60000 && age < 600000, 'Request expired; ask the agent to prepare a new one');
  ensure(request.mode === 'read' || request.mode === 'roundtrip', 'Unknown check mode');
  ensure(request.directory === 'manuscript' || request.directory.startsWith('manuscript/'), 'Choose only the paper subtree');
  ensure(request.directory.split('/').every(p => !p.startsWith('.')), 'Hidden scope refused');
  const localRoot = await safe(root, request.directory);
  const expected = target(request.project_url);
  const metaPath = await safe(localRoot, '.overleaf/settings.json');
  const metadata = await readSmall(metaPath); // No server login or cookie store is read.
  const remoteRoot = metadataUri(metadata, expected);
  ensure(typeof request.main === 'string' && request.main.endsWith('.tex'), 'Select the actual main file');
  ensure(request.main.split('/').every(p => !p.startsWith('.')), 'Hidden main refused');
  const mainFile = await safe(localRoot, request.main);
  const extension = vscode.extensions.getExtension(EXTENSION);
  ensure(extension, 'Overleaf-Workshop needs to be installed by the agent');
  ensure(extension.isActive, 'Open and authorize the actual Workshop Replica first');
  const answer = await vscode.window.showWarningMessage(
    request.mode === 'roundtrip'
      ? `验证 ${expected.server} 的项目 ${expected.project_id}：通过 Overleaf-Workshop 创建、修改并清理一个临时同步测试文件，不改论文。临时文件可能保留在远端历史。`
      : `通过 Overleaf-Workshop 读取项目 ${expected.project_id} 的主文件并与本地比较，不写远端。`,
    {modal: true}, '允许本次验证');
  if (answer !== '允许本次验证') {
    await persist(root, id, {version: 1, id, status: 'cancelled', verified: false}); return;
  }
  let report = {version: 1, id, ...expected, directory: request.directory, main: request.main,
    transport: EXTENSION, extension_version: extension.packageJSON.version,
    checked_at: new Date().toISOString(), status: 'not_verified', verified: false,
    replica_binding_sha256: hash(await fs.readFile(metaPath))};
  try {
    // Do not activate an idle sync engine as a side effect of a check.
    ensure(extension.isActive, 'Workshop became inactive');
    const mainLocal = await localRead(mainFile), mainRemote = await remoteRead(vscode.Uri.joinPath(remoteRoot, request.main));
    ensure(mainLocal !== null && mainLocal.length && mainRemote !== null && mainRemote.length, 'Main source missing');
    ensure(hash(mainLocal) === hash(mainRemote), 'Main files differ; reconcile before probing');
    report.main_sha256 = hash(mainLocal);
    report.metadata_matched = true;
    // A cached main document alone cannot prove live server connectivity.
    report.status = 'readable_via_plugin';
    if (request.mode === 'roundtrip') {
      const old = await fs.readdir(localRoot);
      ensure(!old.some(n => /^aiworkspace-sync-check-.*\.png$/.test(n)), 'Resolve an earlier probe before retrying');
      const ignore = new Set();
      const probe = await runProbe({
        snapshot: () => snapshot(localRoot, ignore),
        localRead: async n => localRead(await safe(localRoot, n)),
        localCreate: async (n, bytes) => { ignore.add(n); await fs.writeFile(await safe(localRoot, n), bytes, {flag: 'wx'}); },
        remoteRead: n => remoteRead(vscode.Uri.joinPath(remoteRoot, n)),
        remoteWrite: (n, bytes) => bounded(() => vscode.workspace.fs.writeFile(vscode.Uri.joinPath(remoteRoot, n), bytes)),
        remoteDelete: n => bounded(() => vscode.workspace.fs.delete(vscode.Uri.joinPath(remoteRoot, n), {recursive: false, useTrash: false}))
      }, {approved: true});
      report = {...report, ...probe};
      if (hash(await fs.readFile(metaPath)) !== report.replica_binding_sha256) {
        report.verified = false; report.status = 'binding_changed';
        report.message = '验证期间插件绑定发生变化，请重新核对目标项目。';
      }
    }
  } catch (_) {
    report.status = 'blocked'; report.verified = false;
    report.message = '插件、登录、稿件一致性或传输检查未完成。请让 Agent 查看当前插件状态；不要向聊天发送凭据。';
  } finally {
    await persist(root, id, report);
  }
  vscode.window.showInformationMessage(report.verified ? '本轮 Overleaf-Workshop 文件双向收发验证通过。' : '检查结果已保存，请回到 Agent 继续处理。');
}
function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand('aiworkspace.overleaf.check', check));
  context.subscriptions.push(vscode.window.registerUriHandler({async handleUri(uri) {
    try {
      ensure(uri.authority === URI_AUTHORITY && uri.path === '/check', 'Unknown operation');
      const q = new URLSearchParams(uri.query);
      ensure([...q.keys()].length === 1 && q.has('id'), 'Invalid URI arguments');
      await check(q.get('id'));
    } catch (error) {
      if (error && error.code === 'CHECK_BUSY') { vscode.window.showWarningMessage('另一项验收正在进行；请等待本次结果。'); return; }
      // Only a valid locally prepared request gets a diagnostic file. Never
      // echo URL/query/exception strings that might contain credentials.
      try {
        const id = new URLSearchParams(uri.query).get('id');
        if (/^[a-f0-9]{32}$/.test(id || '')) {
          const root = await rootFolder();
          await readSmall(await safe(root, '.rw/overleaf-agent/requests/' + id + '.json'));
          await persist(root, id, {version: 1, id, status: 'blocked', verified: false,
            message: '检查窗口、请求有效期、插件是否可用，以及真实 Replica 的项目身份。'});
        }
      } catch (_) { /* An existing report or an invalid root is preserved. */ }
      vscode.window.showWarningMessage('无法开始验证。请让 Agent 检查已打开的论文窗口、请求时间和插件副本；不需要自行运行代码。');
    }
  }}));
}
module.exports = {activate, target, metadataUri, safe, snapshot};
