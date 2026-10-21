export const runtime = 'nodejs';
export function GET() {
  return Response.json({service:'puter-pocket-mcp',version:'0.1.0',configured:!!process.env.POCKET_MCP_TOKEN});
}
