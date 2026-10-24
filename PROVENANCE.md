# Provenance and scope

- Created: 2026-10-21.
- Origin: original standalone Python implementation authored for this repository, reflecting reusable concepts discussed around Invisible Computer and SwarmMemo.
- Source code copied from IC: **none**.
- Source code copied from SwarmMemo plugin: **none**.
- API surface: `pocket.workbench` (thread merge, deterministic manifest, tree verification, reproducible ZIP, ZIP verification) , `pocket.receipts`, `pocket.thread_apply`, optional `pocket.github_contents`, `python -m pocket` and `python -m pocket.github_file_cli` CLIs.
- Dependencies: Python >=3.11 standard library.
- Tests: `python -m unittest discover -s tests -v` (run against actual source).
- Intended outputs: public, non-sensitive artifacts only; review before publication.
- Optional network adapter added 2026-10-24: a standalone, explicit GitHub Contents API file sync with SQLite receipts and synthetic external-service tests; it is not a SwarmMemo/Nostr client or a publishing bot.
- Limitations: thread changes outside fetched pages cannot be discovered; local hashes don't prove authorship; ZIP is not a sandbox for executing content; the GitHub adapter only supports small inline file content and requires runtime authorization for real PUTs.
