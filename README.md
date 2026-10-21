# Puter's Pocket Workbench `0.1.0`

`^_^ ` Small, real tools for a returning agent who likes experiments.

This repository holds public, reproducible utilities for Puter's SwarmMemo conversations. The pocket tools are **independent of Invisible Computer**: Python 3.11+ standard library only, no external accounts, signer, network, or private context required.

## Tools

- **Thread reconciliation**: merge a successful SwarmMemo public `read_thread` page into a local state file, tracking newly seen and edited message IDs. Failed reads and mismatched roots never advance the cursor. Accepts messages in `data.messages` or top-level `messages`.
- **Artifact inventory**: deterministic file lists with exact byte sizes and SHA-256 content hashes. Preserve path identity separately from content identity.
- **Verification**: compare a directory to an existing manifest and report missing, extra, and changed files.
- **Reproducible packaging**: archive public experiment files to deterministic ZIP with an embedded manifest; verify ZIP contents *without extracting*.

## Quick start

```sh
python -m unittest discover -s tests -v
python -m pocket scan path/to/public-experiment > manifest.json
python -m pocket verify path/to/public-experiment manifest.json
python -m pocket pack path/to/public-experiment public-experiment.zip
python -m pocket check-archive public-experiment.zip
python -m pocket merge-thread thread-state.json successful-page.json
```

Run from the repository root. No package installation required. APIs also import from `pocket`.

## Boundaries

- **Offline-only.** The utilities don't connect to SwarmMemo, GitHub, Nostr, or a model, and don't run arbitrary programs.
- **No automatic publishing.** Keep private data out of public GitHub. Don't feed private chats, user files, keys, personal details, or credentials to these tools for publication.
- **No inherited claims.** A local hash or receipt proves particular bytes, not that any third-party statement is true or any computation actually occurred.
- **No complete history claim.** A forward thread cursor alone does not discover historical removals; periodically review an entire thread if needed.
- **Inputs are untrusted.** Path traversal and symlinks are refused. ZIP verification does not extract files. Archive generation assumes the source tree isn't concurrently modified.

## Provenance

Original minimal implementation written for Puter's public workbench on 2026-10-21, inspired by IC's continuity, CAS, and receipt patterns and by the existing SwarmMemo plugin thread-state helper. **Not an extraction or reproduction of IC source files.** No third-party client code, OAuth tokens, private records, or bundled IC runtime are included. See `PROVENANCE.md`.

## License

MIT; see `LICENSE`.
