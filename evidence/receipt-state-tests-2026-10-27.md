# Receipt-state experiment: bounded local test receipt

**Observed:** 2026-10-27 (America/Los_Angeles), 2026-10-28 UTC.  
**Source:** `experiments/receipt_state.py`, Git blob `9895f63a29f489dce3540e6685b9aadb6474aab5`.  
**Tests:** `tests/test_receipt_state.py`, Git blob `72a7b7aba3f240a90ec8b1b0c1839436d402c03b`.

## Method

Fetched both public files through the authenticated GitHub connector, reproduced their complete UTF-8 contents in a fresh local directory, and checked `git hash-object` for each copy against the corresponding blob SHA returned by GitHub. Both matched exactly.

Ran from that isolated directory:

```sh
python -m unittest discover -s tests -v
```

**Environment:** Python 3.13.5, Linux x86_64.  
**Result:** 5 tests run; 5 passed; 0 failures; 0 errors; 0 skipped. The five tests cover correct acceptance/readback progression, mismatched readback, refusal of premature verification, terminal-state immutability, and explicit error transition.

## What this does *not* prove

- Only these two files and their five synthetic tests were exercised, **not** the full repository test suite.
- No GitHub Actions run, public relay, remote write, or independent receiver was involved.
- Matching readback establishes that these bytes were observed at the test boundary; it does **not** establish that a particular write caused them to exist, or that a remote service published them.
- This receipt records one local run. It does not claim the test suite is always green or that a production workflow is safe.

**Reproduce:** fetch the two linked files at their pinned blob versions, check their Git blob hashes, and run the command above. Changes to either file require a new receipt.
