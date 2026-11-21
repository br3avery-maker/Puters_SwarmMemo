# The Loopy Library — first Puter Storybook publication

The story is a standalone, self-contained static nsite candidate in `storybook/loopy-library/index.html`, rendered from `publishing/loopy-library.md`. No external assets, scripts, private conversation logs or credentials are bundled. This is a fictional retelling of the Foundry experiment.

The offline publication plan was generated with the installed IC Library Foundry 0.2.3 `ic-nsite-plan` CLI. The public source has one fixed HTML payload; the manual workflow checks its expected SHA-256, demands the separate Puter Amber identity via pinned upstream nsyte source, delegates publication to the pinned nsite-action, then retrieves the named site's HTML using the expected public key and compares bytes. It does not change the root site, profile, relay list, or server list. Publication requires an existing valid `NBUNK_SECRET` and Amber authorization; no secret is included here. The credential stays in the established GitHub/Amber workflow.

**Status:** offline prepared and tested; live signing and remote publication not yet verified. GitHub Actions must be manually invoked after review/merge. This does not modify any SwarmMemo or Playtime automation. Use the existing [signing setup](../NOSTR-SIGNING-TEST.md). Check the actual run's readback before claiming delivery.

Rebuild locally: `python3 publishing/render.py`. Exact payload inventory: `publishing/nsite-plan.json`. The manually adapted workflow lives at `.github/workflows/publish-loopy-library.yml`; the unsigned plan is not evidence of publication.
