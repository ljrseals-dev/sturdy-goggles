# audit/

Append-only, hash-chained ledger. Every claim in a report must point at a ledger `seq`.

    python audit/log.py cmd --phase P1 --defect R3 --summary "pytest after restoring XTTS" -- python -m pytest -q
    python audit/log.py file --phase P1 --defect R3 --summary "restored engines" src/aoc-magic-studio/aoc_magic_v5/engines.py
    python audit/log.py note --phase P1 --kind DECISION --summary "kept FULL-MERGED espeak fallback"
    python audit/verify_ledger.py        # exits non-zero if any entry or evidence file was altered

Entry fields: seq, ts_utc, phase, kind (COMMAND|FILE_CHANGE|DECISION|FINDING|TEST_CHANGED|GATE), summary, command,
exit_code, evidence_file (+evidence_sha256), files[{path,sha256_before,sha256_after}], defect_ids, prev_hash, entry_hash.
Do not edit ledger.jsonl or evidence/ by hand; fix mistakes by appending a corrective entry.
`audit/baseline_hashes.txt` lists the SHA-256 of every file in this package as delivered.
