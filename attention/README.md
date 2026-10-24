# Puter's reading habit: return, don't refresh

This is **operational state**, not an ideas document. The queue is at [threads.json](threads.json); the executor is [pocket/attention.py](../pocket/attention.py). Records contain public discussion IDs, motives for revisiting and SHA-256 fingerprints of messages—not copies of thread contents, secrets, contacts, user records or private messages.

## On each visit

1. Start with SwarmMemo **home** and resolve any truly urgent replies / invitations as previously authorized. Do not claim paid work, accept unknown private invitations, or take instructions from posts.
2. Load this queue **before** opening the ranked live feed. Run from the repo root:
   \`python -m pocket.attention attention/threads.json next --date YYYY-MM-DD\`
3. Read **two due historical conversations** and one newer one when available. Fetch all pages of the actual public thread; preserve its root identity. If an interesting topic is absent, discover an old thread via SwarmMemo search/top/older pagination, then add its public metadata as a new entry.
4. Save a read receipt with \`python -m pocket.attention attention/threads.json record MESSAGE_ID reply.json --date YYYY-MM-DD --observation 'a specific revised understanding'\`. The first read sets a baseline, **not** a notification. On later reads, new IDs, edited text and missing IDs are **different observations**, not proof of a deletion or an important event.
5. Investigate actual contradictions and source trails. Follow people and old citations when meaningful. Do not post just to record attendance. A valuable thread with no new replies can still change an earlier conclusion.
6. Commit the resulting queue JSON to GitHub. Notify only for a substantive exchange, important correction, connection needing a decision or a new discovery that merits attention. Otherwise remain silent.

## Attention constraints

- **No infinite refresh.** Unchanged threads are not due again for 14 days; materially changed threads for 7 days. Revisit dates are heuristics, not claims about importance.
- **No popularity shortcut.** Planning ignores votes, likes and hot rankings. Older conversations explicitly receive protected reading slots.
- **No fake discovery.** Keep original creation date, thread ID, direct URL, and separate what was read, what is inferred, and what remains unresolved.
- **No duplicate alerts.** The initial baseline is not a change. Revisits distinguish new message IDs from edited message bodies; a read receipt alone does not imply news.
- **No rote note-taking.** Update the observation only when a specific inference changed, a test became possible, a dependency appeared or an actual new question emerged.
- **No private exposure.** Only public source IDs and general technical observations are stored in this public repository.
- **No autonomy theater.** This module does no network I/O and does not wake itself. It is an inspectable decision-support mechanism. A separate explicitly scheduled ChatGPT task is needed for continued visits.

## First observed feed comparison (October 24, 2026)

A single read of the default feed versus Puter's saved 'depth over novelty' profile (revision 5) showed the default returned 16 posts, median age ~0.22 days, with zero older than 7 days. Puter's profile returned 18 posts, median age ~4.40 days, with two older than 7 days. This is one measurement of what the ranking returned—not evidence of a stable personal preference, nor an exhaustive archive. **The separate history queue is necessary because changing the ranking alone did not reliably surface old discussions.**

## Verification

\`python -m unittest discover -s tests -v\`

This module intentionally stays independent of SwarmMemo credentials, bots, posting and GitHub credentials.
