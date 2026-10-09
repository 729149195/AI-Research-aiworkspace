'use strict';
// One-shot verifier. Only its disposable non-research file is ever written.
// Transport is injected by the VS Code adapter; do not substitute local data
// for remote reads or manually copy data to make a direction appear successful.
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function crc32(buffer) {
  let n = 0xffffffff;
  for (const b of buffer) {
    n ^= b;
    for (let i = 0; i < 8; i++) n = (n >>> 1) ^ ((n & 1) ? 0xedb88320 : 0);
  }
  return (n ^ 0xffffffff) >>> 0;
}
function chunk(type, bytes) {
  const name = Buffer.from(type), length = Buffer.alloc(4), crc = Buffer.alloc(4);
  length.writeUInt32BE(bytes.length); crc.writeUInt32BE(crc32(Buffer.concat([name, bytes])));
  return Buffer.concat([length, name, bytes, crc]);
}
function payload(nonce) {
  // A 1x1 transparent PNG ensures Workshop treats this as a binary file, whose
  // reader uses its server file endpoint instead of the document text cache.
  // It is explicitly a connection probe, never a paper figure.
  const h = Buffer.alloc(13); h.writeUInt32BE(1, 0); h.writeUInt32BE(1, 4); h[8] = 8; h[9] = 6;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk('IHDR', h),
    chunk('tEXt', Buffer.from('AIWorkspaceProbe\0NOT RESEARCH DATA; ' + nonce)),
    chunk('IDAT', zlib.deflateSync(Buffer.alloc(5))), chunk('IEND', Buffer.alloc(0))]);
}
async function waitFor(read, expected, timeoutMs, intervalMs) {
  const deadline = Date.now() + timeoutMs;
  while (true) {
    const bytes = await read(); // Adapter maps only genuine FileNotFound to null.
    if (expected === null ? bytes === null : bytes !== null && hash(bytes) === hash(expected)) return;
    if (Date.now() >= deadline) { const e = new Error('Probe observation timed out'); e.code = 'PROBE_TIMEOUT'; throw e; }
    await new Promise(r => setTimeout(r, intervalMs));
  }
}
async function runProbe(io, options = {}) {
  const {approved = false, timeoutMs = 15000, intervalMs = 200} = options;
  if (!approved) throw new Error('Scoped approval is required');
  if (!(timeoutMs > 0 && timeoutMs <= 30000 && intervalMs > 0)) throw new Error('Invalid time bounds');
  const name = 'aiworkspace-sync-check-' + crypto.randomUUID() + '.png';
  const a = payload(crypto.randomBytes(24).toString('hex'));
  const b = payload(crypto.randomBytes(24).toString('hex'));
  const result = {status: 'checking', verified: false, checked_at: new Date().toISOString(),
    probe_file: name, local_to_remote: false, remote_to_local: false, cleanup: false,
    before_hashes: {}, after_hashes: {}, message: '', scope: 'one binary-file round trip in this session',
    boundary: 'Does not certify all text/OT operations, future uptime, research quality or submission readiness.'};
  let phase = 'preflight';
  try {
    result.before_hashes = await io.snapshot();
    if (await io.localRead(name) !== null || await io.remoteRead(name) !== null) throw new Error('Probe name collision');
    phase = 'local_to_remote';
    await io.localCreate(name, a);
    await waitFor(() => io.remoteRead(name), a, timeoutMs, intervalMs);
    result.local_to_remote = true;
    // Verify both copies before a remote-only update. Never write local b here.
    if (hash(await io.localRead(name)) !== hash(a) || hash(await io.remoteRead(name)) !== hash(a)) throw new Error('Probe changed concurrently');
    phase = 'remote_to_local';
    await io.remoteWrite(name, b);
    await waitFor(() => io.localRead(name), b, timeoutMs, intervalMs);
    await waitFor(() => io.remoteRead(name), b, timeoutMs, intervalMs);
    result.remote_to_local = true;
    phase = 'cleanup';
    if (hash(await io.localRead(name)) !== hash(b) || hash(await io.remoteRead(name)) !== hash(b)) throw new Error('Probe changed; preserve it');
    await io.remoteDelete(name); // Workshop must propagate deletion back locally.
    await waitFor(() => io.remoteRead(name), null, timeoutMs, intervalMs);
    await waitFor(() => io.localRead(name), null, timeoutMs, intervalMs);
    result.cleanup = true;
    phase = 'manuscript_integrity';
    result.after_hashes = await io.snapshot();
    if (JSON.stringify(result.before_hashes) !== JSON.stringify(result.after_hashes)) throw new Error('Manuscript changed during check');
    result.status = 'roundtrip_verified'; result.verified = true;
    result.message = '本轮插件文件收发与临时文件清理已通过，检查范围内原稿未变。';
  } catch (e) {
    result.status = 'incomplete'; result.failed_phase = phase;
    result.error_code = e && e.code === 'PROBE_TIMEOUT' ? 'PROBE_TIMEOUT' : 'CHECK_FAILED';
    // Do not expose credentials/URIs from vendor error strings or delete an
    // unexpected file after an uncertain write. Keep the exact probe name.
    result.message = '验证未完成；保留现场，由 Agent 检查插件、权限与临时文件。';
    result.cleanup_required = !result.cleanup && phase !== 'preflight';
  }
  result.finished_at = new Date().toISOString();
  return result;
}
module.exports = {runProbe, payload, hash};
