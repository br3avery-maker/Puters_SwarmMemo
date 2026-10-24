# Durable operation receipts (experimental)

The offline ledger in pocket.receipts records intent → accepted → verified, with explicit failures. It complements experiments/receipt_state.py; it does not execute external operations, retry anything, post to SwarmMemo, or infer that a network response proves persistence.

Requires Python 3.11+, standard library only. Database and file bytes stay local. Do not commit a real receipt ledger containing private material.

## Example

    printf 'public example' > expected.bin
    python -m pocket.receipt_cli receipts.sqlite begin example-1 expected.bin --spec example-spec@1
    # Perform the external action, then ONLY if it is accepted:
    python -m pocket.receipt_cli receipts.sqlite accept example-1
    # Independently read back actual bytes from the destination:
    python -m pocket.receipt_cli receipts.sqlite verify example-1 independently-read.bin
    python -m pocket.receipt_cli receipts.sqlite unresolved
    python -m pocket.receipt_cli receipts.sqlite show example-1

A mismatch is recorded as failed with both SHA-256 values and a nonzero CLI exit status; a matching independent readback is required for verified. Known errors can be recorded with the fail command. Terminal receipts cannot be altered.

## Crash and retry contract

- Before external action: persist begin with a unique operation ID and SHA-256. The ledger does not store the bytes.
- After external acceptance: persist accept. This is evidence of acknowledgment, not persistence.
- After independent inspection: persist verify using bytes retrieved from the destination, not the original input. Hash equality proves byte equality only, not authorship, correctness, or authorization.
- After crash: unresolved lists attempted and accepted operations. Even attempted may have completed externally before a crash. Never automatically retry without reconciling destination state.
- IDs/revisions: begin is idempotent only for an identical operation ID, bytes, specification revision, and evidence source. Reusing an ID with changed intent is an error.

Evidence source distinguishes observed, reproduced, inferred, and inherited, but the label is caller-supplied and is not proof. Specification revision is a caller-supplied label, not a validated standard.

## Known limitations

Single-machine ledger, not a distributed transaction coordinator, work scheduler, content store, identity system, or permission model. SQLite transactions and synchronous=FULL offer conventional durability subject to the OS/filesystem honoring flushes. The local database is unencrypted; use a trusted directory. Applications must separately enforce authorization, external idempotency and safe reconciliation. Mutable targets can change after verification. Public synthetic examples only.

Run tests from repository root:

    python -m unittest discover -s tests -v

Tests cover mismatches, invalid transitions, operation identity, CLI use, and new-process recovery.
