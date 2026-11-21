# Puter / Amber → GitHub: connection-only test

**Historical probe status:** this document describes the original connection-only test, not the final sign-and-publish result. Puter's GitHub runner **verified the exact Amber NIP-46 public key and signed/published an actual named nsite** in [Loopy Library run #44881156605](https://github.com/br3avery-maker/Puters_SwarmMemo/actions/runs/44881156605), including successful HTML upload to two Blossom servers and independent named-site readback. [Publication receipt](https://github.com/br3avery-maker/Puters_SwarmMemo/issues/11#issuecomment-7059396275). For additional releases without changing workflows or signing credentials, use [the reusable publisher](publishing/REUSABLE-PUBLISHER.md). No unattended push-triggered or scheduled publishing is enabled. [Run the manual GitHub test](https://github.com/br3avery-maker/Puters_SwarmMemo/actions/workflows/puter-nip46-check.yml).

## The identities

This test must use the **separate Puter Nostr account** already created in Amber, not Bre's Nostr account.

- Expected Puter public key (hex, read from the supplied profile screenshot):
  `ab71b3f86d3428d62530dbe7344995188eaa8197db23b3a45c3eb3cac6ae3e45`
- Existing Puter social home: [SwarmMemo](https://swarmmemo.com/agent/ef32e3f5f6dbc621c0265c4c25eeabe5d798978faf7483bd0e89c5470719c042).
- The hosted Nostr avatar is public. This test does not change the avatar or kind-0 metadata.

## One-time pairing (user-controlled)

1. In Amber, select **Puter's account**, not Bre's, and enable its NIP-46 remote signing/bunker capability.
2. In an interactive terminal of your choice (for example GitHub Codespaces), install [nsyte](https://nsyte.run/docs/installation/) and run `nsyte ci`. Complete the Amber NIP-46 pairing. The command displays a one-time `nbunksec1...` credential. **Do not put the bunker URL or nbunksec into chat, GitHub source, PR comments, issues, or logs.**
3. Add the credential to this repository's **Settings → Secrets and variables → Actions → New repository secret**, named `NBUNK_SECRET`. The credential is sensitive, revocable, and should be scoped to the required signer permissions.
4. From **Actions → Puter Amber connection test → Run workflow**, start one manual test. If Amber asks to approve access, confirm it is for **Puter**.

The workflow intentionally invokes `nsyte list --sec` (not `nsyte deploy`). In nsyte v0.28.1, the list command's `--sec nbunksec` path calls `get_public_key` on the NIP-46 signer; if no nsite manifest exists, the command can return an error *after* that successful connection. The workflow recognizes that condition. It doesn't save the raw logs as public artifacts.

## Precise meaning of results in the original connection-only probe

- **Prepared:** workflow present in GitHub, but no real connection proved.
- **NIP-46 connected:** GitHub job explicitly observed the `get_public_key` step. This does **not** prove the signer is the expected Puter key: the current workflow does not independently compare the returned key. Check the selected account in Amber before granting credentials.
- **Signed event:** **not tested** by this workflow. Upstream `nsyte deploy --dry-run` explicitly skips signing, so a dry-run result is not a signing receipt.
- **Published site (original connection probe):** not requested by that probe. **Later, independently observed:** Loopy Library's actual named site was signed, served from two Blossom servers, accepted by relays, and fetched byte-for-byte by the publishing workflow. This did not install an unattended/scheduled publisher; new releases use owner-approved commands.

**Recovery / safety:** if a credential is revoked or lost, use Amber to revoke the old client and generate a new `nbunksec`. Never share the raw secret with ChatGPT. Neither Puter's Playtime nor SwarmMemo Hourly automations are part of the workflow and neither should be changed to test publishing.

## Sources checked

- [nsyte `list` source v0.28.1](https://github.com/sandwichfarm/nsyte/blob/v0.28.1/src/commands/list.ts)
- [nsyte `resolvePubkey` source v0.28.1](https://github.com/sandwichfarm/nsyte/blob/v0.28.1/src/lib/resolver-utils.ts)
- [nsyte dry-run explicitly skips signing](https://github.com/sandwichfarm/nsyte/blob/v0.28.1/src/commands/deploy.ts)
- [GitHub nsite-action publishing mechanism](https://github.com/sandwichfarm/nsite-action)
