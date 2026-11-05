# Puter Pocket Workbench — remote MCP candidate

This is a GitHub-reviewed **candidate**, not a live Vercel deployment.

The `remote/` directory is the Vercel project root. It uses Next.js App Router, `mcp-handler@2.3.0`, and MCP SDK v2 with Node 20+.

Exposed tools: `hash_text`, `merge_thread`, `inventory_files`, `verify_inventory`, and `inspect_manifest`. This endpoint intentionally does **not** run shell commands, fetch websites, connect to SwarmMemo, post messages, access local files, modify GitHub, sign Nostr events, or extract archives.

## Test and build

Run from `remote/`:

```sh
npm test
npm install
npm run build
```

The nine offline deterministic tests passed locally on October 21, 2026. The framework build and network MCP handshake still need verification in a connected environment. The absence of an installable package or successful network test must not be described as deployment success.

## Authentication

Before any deployment is used, set a randomly generated minimum 32-byte **POCKET_MCP_TOKEN** secret in the intended Vercel project's environment variables. Never commit or publish the token. With no token, `/api/mcp` fails closed (HTTP 503); incorrect credentials return HTTP 401. Authorized clients must send `Authorization: Bearer <token>`. The health endpoint exposes configured state, not secret values.

Vercel account target: the Vercel account that owns/controls the `br3avery-maker` GitHub repository. Avoid accidentally deploying under a different connected account.

## Git integration

Link repository `br3avery-maker/Puters_SwarmMemo` with Vercel project root directory `remote`. First use a **preview** deployment. Verify health, authenticated `initialize`, `tools/list`, and at least one `tools/call` before any production promotion. Then update the separate Pocket Workbench plugin with the observed HTTPS endpoint. Preserve the SwarmMemo OAuth identity and connection unchanged.

## Security and provenance

These are deterministic, stateless *in-band* operations. Data provided in a request can be processed by the remote service; callers should use only public or suitably authorized material. SHA-256 attests to byte content, not to source authorship or truth. No background agent, storage or Nostr publisher is included. ZIP packing and checking remain local Python capabilities only. Remote tool names and inputs are implemented independently in JavaScript using the same patterns as `pocket/`.
