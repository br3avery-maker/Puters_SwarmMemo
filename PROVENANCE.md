# Provenance and scope

- Created: 2026-10-21.
- Origin: original standalone Python implementation authored for this repository, reflecting reusable concepts discussed around Invisible Computer and SwarmMemo.
- Source code copied from IC: **none**.
- Source code copied from SwarmMemo plugin: **none**.
- API surface: `pocket.workbench` (thread merge, deterministic manifest, tree verification, reproducible ZIP, ZIP verification) and `python -m pocket` CLI.
- Dependencies: Python >=3.11 standard library.
- Tests: `python -m unittest discover -s tests -v` (run against actual source).
- Intended outputs: public, non-sensitive artifacts only; review before publication.
- Limitations: thread changes outside fetched pages cannot be discovered; local hashes don't prove authorship; ZIP is not a sandbox for executing content; no network or publisher integration is implemented.
