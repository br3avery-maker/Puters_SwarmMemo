# Redistribution and provenance notices

This SDK is a mixture of newly standardized adapter code, source-derived owner-provided application logic, and a bundled third-party cryptography build. Redistribution of the SDK as a public package requires review of the source rights and licenses for the exact modules included. It is supplied to the owner as a portable private/reviewable artifact, **not** an automatic grant of an MIT or public-domain license over all code.

`vendor/nostr.js`: unmodified from owner-supplied `Nsite-Directory-Editor-v1.1.1.zip` → `vendor/nostr.js`. That file includes bundled notice for `@noble/hashes`, `@noble/curves`, `@noble/ciphers`, and `@scure/base` (MIT notices). `vendor/nostr-tools.LICENSE` is the donor's separate Unlicense notice. Preserve both notices when redistributing.

`src/directory/model.js`: exact source copy of the user's Nsite Directory Editor application `app/model.js`; original archive did not contain a standalone project-wide license granting third parties broad redistribution. Treat as owner-provided source; review before public publication.

Other `src` modules are standardized adapters and original implementations based on inspected function contracts from Nsite Directory Editor, Archive Repair, BreBre Web, Pretend Internet, and Nostr Anchor. Their provenance is listed in `provenance/manifest.json`; nothing here claims to replace upstream licenses or the canonical projects.

**Private companion source collection:** contains raw recovered user/archive material, including third-party or AGPL sources. Do not publicly publish this entire collection without reviewing every source's license and privacy contents.

### Additional repository-derived modules (v1.1)

Transformed/ported functionality and user-authored lists from `br3avery-maker/MojiSurvivor` (moderationLists, cryptoStats, nostrEngine), `br3avery-maker/Pretend-Internet` (campaign.js and tools/nsite-archive/chunks.mjs), `br3avery-maker/piShell-` (CampaignDetector.kt), `br3avery-maker/HowAmIADeveloper-Studio` (NsiteSpamFilter.kt), and `br3avery-maker/anchor` (backup.ts, relayIntelligence.ts, nipRegistry.ts). These are user-owned project sources; the SDK's standardized adapters have fresh tests and preserve a source path register. External library implementations such as Hashtree codecs, native Android helpers and vendored third-party media are **not** re-licensed or bundled by this pass.
