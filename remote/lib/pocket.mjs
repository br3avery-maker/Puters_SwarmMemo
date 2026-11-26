import { createHash } from 'node:crypto';

export const SCHEMA = 'puter.pocket.manifest.v1';

export function digestText(text) {
  if (typeof text !== 'string') throw new TypeError('text must be a string');
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

export function digestBytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

export function validPath(path) {
  if (typeof path !== 'string' || !path || path.length > 180 || path.startsWith('/') || path.includes('\\') || path.includes('//') || path.endsWith('/') || /[\u0000-\u001f\u007f]/.test(path)) throw new TypeError('invalid relative path');
  if (path.split('/').some(part => part === '.' || part === '..' || part === '')) throw new TypeError('unsafe relative path');
  return path;
}

export function canonicalJSON(value) {
  const sorted = (v) => Array.isArray(v) ? v.map(sorted) : (v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sorted(v[k])])) : v);
  return JSON.stringify(sorted(value)) + '\n';
}

export function mergeThread(state, page) {
  if (!state || typeof state !== 'object' || !state.root_id || typeof state.root_id !== 'string') throw new TypeError('state.root_id required');
  if (!page || page.ok !== true) throw new TypeError('unsuccessful thread read; state not advanced');
  const data = page.data || {};
  if (data.root_id !== state.root_id) throw new TypeError('thread root mismatch; state not advanced');
  const messages = data.messages ?? page.messages ?? [];
  if (!Array.isArray(messages) || messages.length > 100) throw new TypeError('invalid messages array');
  const seen = new Map();
  for (const entry of state.seen ?? []) {
    if (!entry || typeof entry.id !== 'string' || !/^[a-f0-9]{64}$/i.test(entry.sha256 || '')) throw new TypeError('invalid state.seen');
    seen.set(entry.id, entry.sha256);
  }
  const newly = [], changed = [];
  for (const msg of messages) {
    if (!msg || typeof msg.id !== 'string' || !msg.id || typeof msg.text !== 'string' || msg.text.length > 32000) throw new TypeError('invalid message');
    const hash = digestText(msg.text);
    if (!seen.has(msg.id)) newly.push(msg.id);
    else if (seen.get(msg.id) !== hash) changed.push(msg.id);
    seen.set(msg.id, hash);
  }
  const updated = {
    ...state,
    seen: [...seen].sort(([a],[b]) => a.localeCompare(b)).map(([id,sha256]) => ({id,sha256})),
  };
  const cursor = page.next_cursor ?? data.next_cursor;
  if (cursor !== undefined && cursor !== null) updated.cursor = cursor;
  return {state: updated, new_ids: [...new Set(newly)].sort(), changed_ids: [...new Set(changed)].sort(), has_more: !!data.has_more};
}

export function inventory(files) {
  if (!Array.isArray(files) || files.length > 32) throw new TypeError('files must be an array of no more than 32 entries');
  const found = new Set();
  const items = files.map(file => {
    if (!file || typeof file.text !== 'string' || file.text.length > 32000) throw new TypeError('invalid file input');
    const path = validPath(file.path);
    if (found.has(path)) throw new TypeError('duplicate path');
    found.add(path);
    const buffer = Buffer.from(file.text, 'utf8');
    return { path, size: buffer.byteLength, sha256: digestBytes(buffer) };
  }).sort((a,b) => a.path.localeCompare(b.path));
  return { schema: SCHEMA, files: items };
}

export function inspectManifest(manifest) {
  if (!manifest || manifest.schema !== SCHEMA || !Array.isArray(manifest.files) || manifest.files.length > 32) throw new TypeError('unrecognized manifest');
  const paths = new Set();
  let total_bytes = 0;
  for (const entry of manifest.files) {
    if (!entry || typeof entry.path !== 'string' || !Number.isSafeInteger(entry.size) || entry.size < 0 || !/^[a-f0-9]{64}$/.test(entry.sha256 || '')) throw new TypeError('invalid file record');
    validPath(entry.path);
    if (paths.has(entry.path)) throw new TypeError('duplicate path');
    paths.add(entry.path);
    total_bytes += entry.size;
    if (!Number.isSafeInteger(total_bytes)) throw new TypeError('manifest size overflow');
  }
  return { files: manifest.files.length, bytes: total_bytes, manifest_sha256: digestText(canonicalJSON(manifest)) };
}

export function verifyInventory(manifest, files) {
  inspectManifest(manifest);
  const actual = inventory(files);
  const expected = new Map(manifest.files.map(r => [r.path, r]));
  const present = new Map(actual.files.map(r => [r.path, r]));
  const missing = [...expected.keys()].filter(p => !present.has(p)).sort();
  const extra = [...present.keys()].filter(p => !expected.has(p)).sort();
  const modified = [...expected.keys()].filter(p => present.has(p) && (expected.get(p).size !== present.get(p).size || expected.get(p).sha256 !== present.get(p).sha256)).sort();
  return {ok: !missing.length && !extra.length && !modified.length, missing, extra, modified};
}
