export default function Home() {
  return <main style={{maxWidth:640,margin:'3rem auto',fontFamily:'system-ui',lineHeight:1.7}}>
  <h1>^_^ Puter Pocket Workbench</h1><p>Small deterministic MCP tools. No IC installation required.</p>
  <p>Health: <a href="/api/health">/api/health</a>. MCP endpoint: <code>/api/mcp</code> (bearer authorization required).</p>
  <p><a href="https://github.com/br3avery-maker/Puters_SwarmMemo">Source and provenance</a></p></main>;
}
