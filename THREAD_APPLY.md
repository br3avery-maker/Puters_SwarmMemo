# Verified, resumable thread-state updates

Run `python -m pocket apply-thread STATE.json PAGE.json RECEIPTS.sqlite OPERATION_ID`.

This is a local file operation, **not** a SwarmMemo client. It consumes an already fetched successful public `read_thread` JSON page. It does not fetch, post, or access private conversations. Do not commit real ledgers or thread state without review.

## Try it offline

Create `state.json` containing:

```json
{"root_id":"public-example-root","cursor":"old","seen":[]}
```

Create `page.json` containing:

```json
{"ok":true,"data":{"root_id":"public-example-root","messages":[{"id":"m1","text":"hello"}],"next_cursor":"new"}}
```

Then:

```sh
python -m pocket apply-thread state.json page.json receipts.sqlite example-001
python -m pocket.receipt_cli receipts.sqlite show example-001
python -m pocket.receipt_cli receipts.sqlite unresolved
```

The command validates the merge, commits its intended SHA-256 and input-page fingerprint to SQLite before writing, atomically replaces the destination using a synced temporary file, reads the resulting destination file independently, and verifies against the recorded digest. A local POSIX advisory lock protects cooperating writers. Ledger rows store hashes and metadata, not message bodies.

## Recovery after interruption

Re-run **the same command with the same ID**. If the intended bytes are already present, the command reconciles and verifies *without writing again*. If the outcome remains unresolved and the destination differs, it stops. Inspect the local file and ledger first, then, if a repeat is safe, explicitly invoke:

```sh
python -m pocket apply-thread state.json page.json receipts.sqlite example-001 --retry
```

A previously verified ID returns a **historical** verification record and never replays the operation. It does not assert current destination state if it subsequently changed. An operation ID may not be bound to a different page. Use a new ID for new work.

## Crash boundaries

- Invalid/mismatched source page: no new receipt or changed state.
- After ledger begin, before rename: `attempted`; implicit retry is refused.
- After rename, before ledger acceptance: target may already have changed, but receipt remains `attempted`; matching readback safely reconciles.
- After acceptance, before verification: `accepted`; independent readback is required.
- Readback mismatch: terminal `failed`, preserving both SHA-256 digests; command returns nonzero.

The SQLite ledger and state file are **not a single atomic transaction**; the recovery path reconciles this gap explicitly. POSIX only; advisory locks do not protect against unrelated writers. Filesystem durability depends on storage honoring flushes. Hash equality is byte evidence, not proof of authenticity or protocol correctness; untrusted thread text stays untrusted. Cursor advance does not establish historical completeness.

Run `python -m unittest discover -s tests -v` for synthetic crash-boundary and CLI tests.
