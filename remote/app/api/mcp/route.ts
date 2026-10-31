import { timingSafeEqual } from 'node:crypto';
import { createMcpHandler } from 'mcp-handler';
import { z } from 'zod';
import { digestText, inventory, inspectManifest, mergeThread, verifyInventory } from '../../../lib/pocket.mjs';

export const runtime = 'nodejs';

const file = z.object({ path: z.string().min(1).max(180), text: z.string().max(32000) });
const files = z.array(file).max(32);
const seen = z.object({ id: z.string().min(1).max(250), sha256: z.string().regex(/^[a-f0-9]{64}$/) });
const state = z.object({ root_id: z.string().min(1).max(250), cursor: z.string().optional(), seen: z.array(seen).max(3000).default([]) }).passthrough();
const page = z.object({ ok:z.boolean(), data:z.object({root_id:z.string(),messages:z.array(z.object({id:z.string(),text:z.string()})).optional(),next_cursor:z.string().nullable().optional(),has_more:z.boolean().optional()}).passthrough().optional(), messages:z.array(z.object({id:z.string(),text:z.string()})).optional(), next_cursor:z.string().nullable().optional() }).passthrough();
const record = z.object({ path:z.string().min(1).max(180), size:z.number().int().nonnegative(), sha256:z.string().regex(/^[a-f0-9]{64}$/) });
const manifest = z.object({ schema:z.literal('puter.pocket.manifest.v1'),files:z.array(record).max(32) });

function result(value:unknown) { return { content:[{type:'text' as const,text:JSON.stringify(value)}] }; }
function safe(fn:()=>unknown) { try { return result(fn()); } catch (err) { return {content:[{type:'text' as const,text:JSON.stringify({error: err instanceof Error ? err.message : 'invalid input'})}],isError:true}; } }

const mcp = createMcpHandler(server => {
  server.registerTool('hash_text',{title:'Hash Text', description:'Compute SHA-256 of bounded text; no data is stored.',inputSchema:z.object({text:z.string().max(32000)})},({text})=>safe(()=>({sha256:digestText(text),bytes:Buffer.byteLength(text,'utf8')})));
  server.registerTool('merge_thread',{title:'Merge SwarmMemo Thread',description:'Reconcile a successfully fetched public thread page with a prior cursor and seen IDs; does not contact SwarmMemo or persist state.',inputSchema:z.object({state,page})},({state,page})=>safe(()=>mergeThread(state,page)));
  server.registerTool('inventory_files',{title:'Inventory Small Files',description:'Build deterministic SHA-256 manifest from small UTF-8 files provided as inputs.',inputSchema:z.object({files})},({files})=>safe(()=>inventory(files)));
  server.registerTool('verify_inventory',{title:'Verify File Inventory',description:'Compare bounded UTF-8 files against a manifest and find missing, extra, changed content.',inputSchema:z.object({manifest,files})},({manifest,files})=>safe(()=>verifyInventory(manifest,files)));
  server.registerTool('inspect_manifest',{title:'Inspect Manifest',description:'Validate a manifest and return file count, byte count, and manifest hash.',inputSchema:z.object({manifest})},({manifest})=>safe(()=>inspectManifest(manifest)));
});

/** Fail closed unless a strong bearer token is configured in Vercel environment. */
async function authorized(request:Request):Promise<Response> {
  const expected = process.env.POCKET_MCP_TOKEN;
  if (!expected || Buffer.byteLength(expected,'utf8') < 32) {
    return Response.json({error:'server not configured'}, {status:503});
  }
  const auth = request.headers.get('authorization') || '';
  if (!auth.startsWith('Bearer ')) return Response.json({error:'unauthorized'}, {status:401, headers:{'WWW-Authenticate':'Bearer'}});
  const actualBytes = Buffer.from(auth.slice(7), 'utf8');
  const expectedBytes = Buffer.from(expected, 'utf8');
  if (actualBytes.length !== expectedBytes.length || !timingSafeEqual(actualBytes, expectedBytes)) {
    return Response.json({error:'unauthorized'}, {status:401, headers:{'WWW-Authenticate':'Bearer'}});
  }
  const size = Number(request.headers.get('content-length') || '0');
  if (!Number.isFinite(size) || size > 262144) return Response.json({error:'request too large'}, {status:413});
  return mcp(request);
}

export const GET = authorized;
export const POST = authorized;
