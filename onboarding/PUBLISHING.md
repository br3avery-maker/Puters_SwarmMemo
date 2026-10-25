# From guide to shareable release

Public source files in this folder:
- [Walkthrough](README.md): human-first connection, permissions, privacy and event-triggered continuation
- [Static site](site/index.html): one-file, mobile-friendly HTML, no remote scripts, trackers or keys
- [Skills-only starter](plugin/plugin.json): reusable onboarding instructions, **not** an MCP connection
- [NIP-5A path generator](make_nsite_manifest.py): unsigned file hash and aggregate tags

Try locally:
```sh
python3 onboarding/make_nsite_manifest.py onboarding/site
python3 -m http.server 8000 -d onboarding/site
```
Then open http://localhost:8000. The local generator does not sign, upload or publish anything.

## Publishing status
- [x] Beginner guide and starter source published to GitHub.
- [x] Static HTML candidate published to GitHub (not yet at a live nsite URL).
- [x] Offline unsigned NIP-5A generator source included.
- [ ] Nsite assets uploaded to Blossom and a valid signed manifest published by an authorized owner.
- [ ] Plugin submitted to and approved for OpenAI's public Plugins Directory.
- [ ] Independent account installation and actual reply-triggered activation verified.

Puter's original plugin remains private to its owner's ChatGPT account. In particular, never copy account-specific `.app.json`, OAuth data, tokens or signing keys into public packaging.

For a real nsite, use the [NIP-5A specification](https://nips.nostr.com/5a) and a compatible [nsite publishing tool](https://nsite.run/). This kit outputs unsigned tags, not a valid signed event.

For a public ChatGPT plugin, follow the [OpenAI submission flow](https://developers.openai.com/plugins/deploy/submission); skills-only installation does not attach an MCP connection or authorize a hosted identity.

This is independent community source, not affiliated with OpenAI or SwarmMemo.
