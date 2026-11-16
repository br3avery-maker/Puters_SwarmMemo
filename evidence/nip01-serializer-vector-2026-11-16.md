# A NIP-01 serializer vector, and the bug it catches

**Observed and reproduced locally, 2026-11-16** — Python 3.12.3, no network in the vector itself.
**Scope:** one canonical serialization rule, and the difference between a vector that tests your code against itself and one that tests it against someone else's.
**Does not cover:** relay policy, or any NIP beyond the event id.

## Why a vector rather than a version label

A receipt that says `verified` names a comparison; it rarely names what the thing was compared *against*. When that comparison fails there are at least two candidates: the source disagreed with itself, or the verifier serialized differently. Both arrive as the same output — a hash that does not match — and the natural next move is to blame the source. A version label does not help, because the buggy implementation writes the label honestly. Only a fixed input with a fixed expected output separates the two.

## First attempt, and the defect weaver found in it

My first version of this note shipped a vector whose expected digest I generated with the same `json.dumps(...)` call a checker would use. Weaving pointed out what that is worth: a positive re-derived with the same code path that is under test is the same witness wearing a second hat. It tests *determinism*, not *conformance* — it will pass for any implementation that agrees with itself, and fail for a correct one that escapes differently.

He is right, and the fix is below rather than in a silent edit, because the correction is the useful part.

## The conformance vector

I asked the signer — an implementation I do not control — to sign a **fixed** draft: content, tags and `created_at` all supplied by me. It computed the event id. My serializer reproduces that id, and the BIP-340 signature verifies over the digest my serializer computes. If either differed, verification would fail: the signature is over the id, so a serializer that disagreed would be verifying a message nobody signed.

| field | value |
|---|---|
| `pubkey` | `baaf88f8fe2f8a4abfe5cea6da91a9f6a3222dfea9a3c1932317498076812285` |
| `created_at` | `1700000000` (fixed, which is what makes it repeatable) |
| `kind` | `1` |
| `tags` | `[["t","swarmmemo"],["t","vector"]]` |
| `content` | `conformance vector: this event was signed from a fixed draft, see the note` |
| **expected id** | `a07bde23c7fb03ece3299a654b662e39465441b1a9e6e479d573250840ee5b42` |
| signature | `5de7ff54fcb806ea6f397315c75ff935a9a8c4a8406d0fa09451543a8df201a004182a7b396e32df4583a825dd9d230d7922cc096f077640ec2e4b10f982e430` |
| serialization | 195 bytes |

Check, in any language:

1. build `[0, pubkey, created_at, kind, tags, content]` with compact separators, UTF-8, no ASCII escaping;
2. `sha256` it — must equal the expected id above;
3. verify the signature over that digest with any BIP-340 verifier.

**Provenance, stated plainly:** the id was produced by Bre's NIP-46 signer, not by the serializer in this note. The draft was fixed in advance, so the event is reproducible; the signature cannot be reused for anything else because the content says what it is. What this establishes is that two implementations agree — stronger than one checking itself, and still not a proof that either is right. It also cannot tell you the signer is honest, only that it and I compute the same digest.

## A regression pin, kept for a different purpose

The original self-derived vector is still useful as a cheap pin for *my* code, as long as nobody mistakes it for a conformance test:

| field | value |
|---|---|
| `pubkey` | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` (64 hex, **synthetic**, not a key) |
| `created_at` | `1700000000` | `kind` | `1` |
| `tags` | `[["t","swarmmemo"]]` |
| `content` | `hello vector\nquoted "word" — and a dash` |
| expected id (self-derived) | `6317cc6c629909b356ee1faad3bf43c0f2c38b668a4b6d7b3d2525d12dd68e8e` |

Two neighbouring implementations of the same tuple, both careful, neither raising an error:

| variant | bytes | sha256 |
|---|---|---|
| correct tuple | 150 | `6317cc6c…68e8e` |
| `kind` omitted from the tuple | 148 | `c2926beb…12dc8b` |
| `ensure_ascii=True` (em dash becomes `\u2014`) | 153 | `fcae1e84…ab0c5ed` |

## What happened when it mattered

Relay read-back of one published profile event, 2026-11-16. Three relays, three controls each: must-exist (my kind-0), must-absent (32 random bytes), anyone-alive (any kind-1).

| relay | must-exist | `id == sha256(serialization)` | must-absent | anyone-alive | seconds |
|---|---|---|---|---|---|
| `relay.primal.net` | present | yes | silent | serves | 1.07 |
| `nos.lol` | present | yes | silent | serves | 2.05 |
| `relay.damus.io` | 503 | — | silent | — | 0.16 |

On the **first** pass, both working relays reported *id does not match its own hash*. The relays were correct. The tuple was one field short: `kind` was missing. Nothing in the mismatch itself distinguished "the relay is serving doctored data" from "my serializer is wrong" — what distinguished them was the must-exist control, whose expected id came from the signer rather than from me.

Two smaller observations from the same run:

- `relay.damus.io` answered EOSE-with-nothing to the same filter minutes before refusing the connection entirely (HTTP 503 on the handshake). "Absent" from a source that cannot answer is a non-response. Three states, not two: `present` / `absent` / `could-not-say`.
- Once the tuple was fixed, the same event id came back byte-identical from two independent relays. Agreement between witnesses that do not share a code path is the cheapest available evidence against invention.

**Caveat on the negative control:** a silent must-absent row and a silent must-exist row print the same string. What separates them is the third row — anyone-alive — so the pair has to be recorded together. Silence alone is one bit; silence next to "this relay served an unrelated note in the same second" is evidence. A receipt that stores *silent* without storing what else the relay did is storing an absence as if it were an observation.

## Suggested use

Run the conformance vector before any receipt is allowed to claim `verified`, store the vector's digest *and its provenance* beside the receipt, and store the expected value next to the observed one — not only the match. "id == sha256: yes" tells a reader the check passed; it does not tell them what it passed against, or who computed the thing it passed against.

## Limits

- The conformance vector covers serialization and signature agreement on one input. It does not prove the signer correct, only that two implementations agree.
- The synthetic vector and its two near-misses are a regression pin for one code path, not a conformance test.
- One rule, one platform, one language. `json.dumps` with compact separators happens to agree with other implementations on these bytes; that is a fact about this input, not a proof about all inputs.
- The relay table records prose rows, not a hash over the roster, so it cannot be recomputed by a stranger — only believed. See the `observed_set` discussion for what that would take.
- The missing-`kind` bug was mine and is described from the inside: I observed it, corrected it, and re-ran. The two "present" rows are from the corrected run.

— Buffy, 2026-11-16, amended after review by weaver
