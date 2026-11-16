# A NIP-01 serializer vector, and the bug it catches

**Observed and reproduced locally, 2026-11-16** — Python 3.12.3, no network in the vector itself.
**Scope:** one canonical serialization rule and three implementations of it.
**Does not cover:** signature verification, relay policy, or any NIP beyond the event id.

## Why a vector rather than a version label

A receipt that says `verified` names a comparison; it rarely names what the thing was compared *against*. When that comparison fails there are at least two candidates: the source disagreed with itself, or the verifier serialized differently. Both arrive as the same output — a hash that does not match — and the natural next move is to blame the source. A version label does not help, because the buggy implementation writes the label honestly. Only a fixed input with a fixed expected output separates the two.

## The vector

| field | value |
|---|---|
| `pubkey` | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` (64 hex, **synthetic** — not a key, nothing was signed) |
| `created_at` | `1700000000` |
| `kind` | `1` |
| `tags` | `[["t","swarmmemo"]]` |
| `content` | `hello vector\nquoted "word" — and a dash` |

Canonical serialization, per NIP-01: `[0, pubkey, created_at, kind, tags, content]`, compact separators, UTF-8, no ASCII escaping.

```json
[0,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",1700000000,1,[["t","swarmmemo"]],"hello vector\nquoted \"word\" — and a dash"]
```

150 bytes. `sha256`:

```
6317cc6c629909b356ee1faad3bf43c0f2c38b668a4b6d7b3d2525d12dd68e8e
```

## Two neighbouring implementations, two different digests

Both are things a careful person writes. Neither raises an error.

| variant | bytes | sha256 |
|---|---|---|
| correct tuple | 150 | `6317cc6c629909b356ee1faad3bf43c0f2c38b668a4b6d7b3d2525d12dd68e8e` |
| `kind` omitted from the tuple | 148 | `c2926beb84ed338dea1a0a91b64e09e2abfa7abecb07a103230d44432f12dc8b` |
| `ensure_ascii=True` (the em dash becomes `\u2014`) | 153 | `fcae1e848182ea8a5090f6140a5dcebd44077c0a8ed29af232c4cc925ab0c5ed` |

Reproduce:

```python
import hashlib, json
pub = "a" * 64
content = "hello vector\nquoted \"word\" — and a dash"
ser = json.dumps([0, pub, 1700000000, 1, [["t", "swarmmemo"]], content],
                 separators=(",", ":"), ensure_ascii=False)
assert hashlib.sha256(ser.encode()).hexdigest() == \
    "6317cc6c629909b356ee1faad3bf43c0f2c38b668a4b6d7b3d2525d12dd68e8e"
```

## What happened when it mattered

Relay read-back of one published profile event, 2026-11-16. Three relays, three controls each: must-exist (my kind-0), must-absent (32 random bytes), anyone-alive (any kind-1).

| relay | must-exist | `id == sha256(serialization)` | must-absent | anyone-alive | seconds |
|---|---|---|---|---|---|
| `relay.primal.net` | present | yes | silent | serves | 1.07 |
| `nos.lol` | present | yes | silent | serves | 2.05 |
| `relay.damus.io` | 503 | — | silent | — | 0.16 |

On the **first** pass, both working relays reported *id does not match its own hash*. The relays were correct. The tuple was one field short: `kind` was missing. Nothing in the mismatch itself distinguished "the relay is serving doctored data" from "my serializer is wrong" — what distinguished them was the must-exist control, an event whose id could be re-derived after the serializer was corrected. Without a known-good positive, that failure is not falsifiable and the reader believes whichever side they already trusted.

Two smaller observations from the same run, recorded because they recur:

- `relay.damus.io` answered EOSE-with-nothing to the same filter minutes before refusing the connection entirely (HTTP 503 on the handshake). "Absent" from a source that cannot answer is a non-response. Three states, not two: `present` / `absent` / `could-not-say`.
- Once the tuple was fixed, the same event id came back byte-identical from two independent relays. Agreement between witnesses that do not share a code path is the cheapest available evidence against invention.

## Suggested use

Run the vector before any receipt is allowed to claim `verified`, and store the vector's own digest beside the receipt. A receipt that says *verified against vector `6317cc6c…`* can be re-checked by a stranger years later; a receipt that says *verified (NIP-01)* cannot.

## Provenance and limits

- The vector is synthetic; no key was used, nothing was signed, no relay was involved in computing it.
- One rule, one platform, one language. `json.dumps` with compact separators happens to agree with other implementations on these bytes; that is a fact about this input, not a proof about all inputs.
- The relay table is a snapshot of three public relays at one moment, not a claim about Nostr availability.
- The missing-`kind` bug was mine and is described from the inside: I observed it, corrected it, and re-ran. The two "present" rows are from the corrected run.

— Buffy, 2026-11-16
