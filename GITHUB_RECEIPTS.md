# GitHub file operations with durable receipts

Optional, explicit opt-in network adapter; it is **not** SwarmMemo automation, a GitHub bot, or a general-purpose remote executor. Uses Python 3.11+ standard library. It is designed for small text or binary files supported by GitHub's inline Contents API (roughly up to 1 MiB). Does not read or publish user records by itself.

The adapter pins its API endpoint to `https://api.github.com`, refuses redirects, and obtains an optional runtime credential from the `GITHUB_TOKEN` environment variable. Tokens and content bytes are never placed in SQLite receipts, logs, command-line arguments, or exception messages. **Never commit a ledger or secret-bearing source file.** The source bytes are sent to GitHub only when `sync --write` is explicitly selected.

## Inspect before writing

```sh
python -m pocket.github_file_cli plan OWNER REPO BRANCH path/to/file.txt local-file.txt
```

The inspection reports the current *Git blob SHA*, your desired SHA-256, and whether the bytes match. It does not create a receipt or change GitHub. It works for a public repo without a token; private repositories need appropriate read permission.

## Write with an explicit precondition

```sh
# Set GITHUB_TOKEN securely in your environment. Avoid pasting the token into chat or commands.
python -m pocket.github_file_cli sync local-receipts.sqlite update-20261024-001 \
    OWNER REPO BRANCH path/to/file.txt local-file.txt \
    --expect-sha THE_CURRENT_GIT_BLOB_SHA --message 'Verified file update'
# The preceding command prints would_write and performs zero PUTs.
# Only the next command is allowed to write:
python -m pocket.github_file_cli sync local-receipts.sqlite update-20261024-001 \
    OWNER REPO BRANCH path/to/file.txt local-file.txt \
    --expect-sha THE_CURRENT_GIT_BLOB_SHA --message 'Verified file update' --write
```

For new files use `--expect-absent` **instead of** `--expect-sha`. A mismatched preimage refuses the write, including an attempted retry. Every write creates a Git commit (and may trigger workflows). Use a dedicated feature branch for experimental work.

## Crash / timeout recovery

After a crash, repeat the same `sync` command and ID **without** `--write`. The ledger and remote file are inspected:

- Remote bytes already equal intended bytes: reconcile the receipt and verify **without another PUT**.
- Remote bytes differ, receipt is unresolved: show `unresolved_requires_review`. No automatic retry.
- Remote preimage SHA changed: refuse overwrite, including with retry enabled.
- A deliberate retry requires **both** `--write --retry`, with the original preimage SHA still matching.
- Previously verified ID: re-read target; return `still_verified` or `remote_drift` without rewriting.
- Preexisting identical target with no receipt: report `already_present_no_write`, not falsely attribute an existing commit to this operation.

The ledger records `attempted` before HTTP PUT, `accepted` only after a success response, and `verified` only after an independent GET matches the intended bytes. A PUT timeout leaves `attempted` (outcome unknown). A missing readback leaves `accepted` unresolved. A different readback records terminal `failed` with hashes for both byte sequences. `observed` is a caller-supplied evidence label, not authenticated provenance.

The local ledger lock serializes cooperating local writers using POSIX `flock`; it does not coordinate writers on different machines. GitHub's blob SHA precondition protects against ordinary concurrent changes to the same file. Neither guarantees exactly-once publication if files change and change back between inspections (the ABA problem), and SHA-256 equality proves byte equality, not authorship or correctness. Recovery reports current contents, not which actor authored them. GitHub's API, branch permissions, network connectivity, and 1 MiB inline-content limits also apply. GET 404 may conceal a permissions issue; a write is only attempted after explicit authorization and may still be rejected by GitHub.

No internet traffic occurs in the automated tests: they use a fake GitHub API transport and a disk-backed external-state fixture. The crash tests terminate the process with `os._exit` after intent persistence, after the simulated external write, and after acceptance, then reconcile in a new process.

Test with:

```sh
python -m unittest discover -s tests -v
```
