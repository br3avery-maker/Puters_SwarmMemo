# Puter's repeatable Chat → GitHub → Amber → Blossom → Nostr publisher

**Status:** Generic publisher source and offline validation. This *new* dynamic workflow must pass GitHub CI and a separately authorized live publication before it can be described as live-tested. Its underlying signing/deployment route is already live-tested by Loopy Library [run #44881156605](https://github.com/br3avery-maker/Puters_SwarmMemo/actions/runs/44881156605), with a verified [issue #11 receipt](https://github.com/br3avery-maker/Puters_SwarmMemo/issues/11#issuecomment-7059396275). The phone screenshot establishes successful gateway rendering and discovery of that specific published story. Those results are not evidence that every future site works automatically.

## Why the old workflow was restricted

The first working workflow, `publish-loopy-library.yml`, deliberately fixed one `index.html` and one SHA-256 while testing the GitHub connector, Puter's revocable NIP-46 Amber credential, the real upstream nsite Action, Blossom uploads and Nostr manifest readback. **There is no Nostr, Amber or GitHub requirement to limit Puter to that story.** Keep it as regression evidence; the new `publish-nsites.yml` is the general path. Both use the **same** GitHub secret `NBUNK_SECRET` and Puter's verified Nostr account; the new publisher never reads, copies or prints that secret.

## Publish any static artifact, without editing the workflow

A release is an immutable *request for specific site bytes*, not a rule that permits only a particular story. Each site may be a Storybook story, game, website, app UI, archive, gallery or other browser-ready static bundle.

1. Prepare finished, self-contained static files in a repository directory such as `storybook/my-story`, `arcade/my-game`, `web/my-site` or `sites/my-project`. A compiled game/webapp must be **built first**. The directory must contain `index.html`; it can also have any number of hashed assets within safety/runner limits. No NIP-46 keys belong in these files.
2. Run `python3 publishing/release_gate.py prepare --id my-game-v1 --directory arcade/my-game --name my-game --title 'My Game' --description 'A game by Puter'` from the repo root (or invoke the same Python module directly in IC). This inventories the actual bytes and writes `publishing/releases/my-game-v1.json`. For later updates, create `my-game-v2` (new release ID, same `name`); for an independent nsite, use another `name`. It prints the exact owner authorization comment; **do not use a prior release ID to overwrite an existing release record**.
3. Commit the site **and** the release JSON in a reviewed branch; test and merge to `main`. Run `python3 publishing/release_gate.py validate --id my-game-v1` against the target repository state. Release JSON includes site name/title/description, directory, full path/hash/size inventory. It contains no credential, command, external checkout ref or deployment destination.
4. **Only after the owner authorizes that release**, Chat uses the connected GitHub issue-comment capability to post the generated `/publish-release my-game-v1 sha256:<release-JSON-SHA256>` command to the existing publisher inbox [issue #11](https://github.com/br3avery-maker/Puters_SwarmMemo/issues/11). Alternatively the owner can use GitHub Actions `workflow_dispatch` with `release_id` and `manifest_sha256`. Chat need not read the GitHub secret. A message in SwarmMemo alone is not a GitHub publication request.
5. GitHub checks repository, main branch, owner/sender/triggering actor, exact command, JSON manifest digest, site name, **every file path/hash/size**, and absence of unlisted files or unsafe symlinks. It then verifies that the existing revocable `NBUNK_SECRET` resolves through Amber to Puter's exact expected public key before any upload. No arbitrary repo URL, shell command, filename from comment, signer key, profile changes or unreviewed branch contents are allowed.
6. The upstream pinned `sandwichfarm/nsite-action` runs `nsyte v0.28.1` with `sync: true` to backfill missing content-addressed files to the already-proven Blossom endpoints `https://nostr.download` and `https://blossom.primal.net`. It uses the release's **named** NIP-5A site. It signs and publishes the manifest to configured Nostr relays, never Puter's root site or profile.
7. On a separate credential-free validation step, `nsyte get` retrieves **every declared path** using Puter's public key and the named site; the downloaded bytes must match the approved per-file SHA-256 and size. A separate receipt job posts VERIFIED/NOT VERIFIED, site name, release ID/digest, and run URL back to issue #11. Receipts never contain the nbunksec, unpublished private files or raw signing logs.

**Result:** A new project needs a static output directory, a reviewed release JSON, and an owner-approved comment. **No new workflow, CI secret, signer pairing or hardcoded story rule for each new piece.** The supported operation remains limited to publishing static files under Puter's identity; it is not arbitrary shell execution or authorization to publish on other people's behalf.

## Why these controls remain

Owner authorization controls *what* gets publicly published, and Puter's revocable signer controls *whose signature* is requested. An unauthorized user cannot choose a release by commenting on the issue; the gate compares the GitHub owner identity and original commenter to the workflow actor. The command binds the release JSON digest, and that JSON binds exact site bytes already merged to `main`. The release gate refuses symlinks, repository traversal, developer/credential filenames and changes after approval. The upstream secrets scan stays enabled. These are publication safety and reproducibility constraints, **not content or project-category restrictions**.

A named nsite can be updated without affecting other nsites under the same npub. The only frozen identity is **Puter's Amber account**. A different agent or GitHub repository would need its own expected identity, authorized repo and isolated secret configuration. Do not reuse Puter's bunker credential across identities.

## Lessons from actual first publication (not theoretical)

| Boundary | Observed result | Reusable rule |
|---|---|---|
| Chat → GitHub issue comment | Authorized comment triggered workflow; non-owner PR checks did not publish | Keep a bounded owner-checked request inbox; do not require Chat to dispatch Actions directly |
| GitHub `NBUNK_SECRET` | First live run failed without a valid CI credential | Store the revocable `nbunksec1…` **only** in GitHub Actions secret; never in Chat, commits, logs or receipts |
| Amber NIP-46 public key | GitHub verified Puter's key; signer approved upload-auth/manifest events | Check public key **before** uploading/signing for the wrong identity; do not confuse connection with signing |
| Old Blossom servers | `cdn.hzrd149.com` and `cdn.sovbit.host` stored 0/1 file, despite a signed manifest accepted by relays | Never treat manifest acceptance as content availability; select observed working storage endpoints |
| `nsyte` existing manifest | A subsequent retry failed `No new files to upload` after a manifest existed | `sync: 'true'` is required for missing-blobs backfill; don't blindly republish without checking |
| Verified server pair | `nostr.download` and `blossom.primal.net` each uploaded 1/1 file | Configure both, check actual upload and independent readback; a third endpoint failed and is omitted |
| Named site event | Signed kind 35128 accepted by multiple relays; readback matched exact Loopy HTML | Root and named sites have different identities; preserve `name` and verify the correct one |
| Android reader/discovery | Owner supplied screenshot of rendered story and discovery card | A GitHub readback is not a gateway/UI test; label device/browser observation separately |

**Initial evidence:** [successful Actions run](https://github.com/br3avery-maker/Puters_SwarmMemo/actions/runs/44881156605) · [public result](https://49tvx5d84crykxl5dbj9fad5ryzaewzvvleeh0ywe3swam5mbploopy-library.nsite.lol/) · [source/receipt](https://github.com/br3avery-maker/Puters_SwarmMemo/issues/11).

## Failure handling / claims

- `credential missing`: no signature or publication. Restore/revoke CI bunker via Amber and GitHub Secrets without putting it in Chat.
- `identity mismatch`, denied/expired NIP-46 session: stop; no upload.
- `Blossom upload fails`: a manifest may **already be signed and sent** by nsyte. Check exact event and file state before retry; enable `sync` to backfill missing blobs.
- `no new files to upload`: check the stored manifest and whether the target servers actually hold the declared content; use `sync`, not an unverified success claim.
- `relay accepted but nsyte get fails`: keep NOT VERIFIED. Inspect manifest identity and missing blob/path mapping. Follow the nsyte CLI's actual return code and independent byte hashes.
- `nsyte get succeeds but phone display fails`: publishing and gateway/device usability are different evidence levels. Inspect gateway routing/assets/mime, not the signer secret.
- `receipt success`: the named manifest was retrievable **for all declared files** through the configured read path and their downloaded bytes matched the approved inventory. It is not proof that every possible gateway or browser works.

## Scope and recovery

This adds a new **reusable workflow**, not a new signing service or automation. It neither changes Puter's hourly SwarmMemo/Playtime jobs nor publishes a new site simply by merging the code. Site publication always requires a separate specific owner-approved release request. For a future IC integration, reuse this module's `prepare`, `validate`, and gated `stage` contract with the existing IC library-foundry/nsite planning and nsyte publisher skills; do not create another signer or store the `nbunksec` inside IC.
