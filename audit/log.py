#!/usr/bin/env python3
"""Append-only, hash-chained audit ledger. Python 3.9+, stdlib only.

  python audit/log.py cmd [--phase P1] [--defect D1 --defect R3] [--summary TEXT] -- <command ...>
  python audit/log.py note --phase P1 --kind DECISION|FINDING|TEST_CHANGED|GATE --summary TEXT [--defect ID]
  python audit/log.py file --phase P1 --summary TEXT --defect R3 PATH [PATH ...]   # records sha256 before/after
  python audit/log.py verify

`cmd` runs the command, stores full stdout+stderr in audit/evidence/NNNN.txt, records the exit code, and
appends a chained entry. The exit code of `log.py cmd` is the command's exit code.
`file` records the current sha256 of each PATH and compares with the last recorded hash for that path.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "ledger.jsonl"
EVID = HERE / "evidence"
GENESIS = "0" * 64


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def file_sha(p: Path):
    try:
        return sha(p.read_bytes())
    except (FileNotFoundError, IsADirectoryError):
        return None


def canon(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def read_entries():
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def append(entry: dict) -> dict:
    ents = read_entries()
    entry["seq"] = len(ents) + 1
    entry["ts_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry["prev_hash"] = ents[-1]["entry_hash"] if ents else GENESIS
    entry["entry_hash"] = sha(canon({k: v for k, v in entry.items() if k != "entry_hash"}))
    with LEDGER.open("a") as f:
        f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry


def verify() -> int:
    prev, bad = GENESIS, 0
    ents = read_entries()
    for i, e in enumerate(ents, 1):
        want = sha(canon({k: v for k, v in e.items() if k != "entry_hash"}))
        if e.get("seq") != i:
            print(f"seq gap at line {i}: seq={e.get('seq')}"); bad += 1
        if e.get("prev_hash") != prev:
            print(f"BROKEN CHAIN at seq {e.get('seq')}: prev_hash mismatch"); bad += 1
        if e.get("entry_hash") != want:
            print(f"TAMPERED entry at seq {e.get('seq')}: hash mismatch"); bad += 1
        ev = e.get("evidence_file")
        if ev:
            p = HERE.parent / ev
            if not p.exists():
                print(f"MISSING evidence for seq {e.get('seq')}: {ev}"); bad += 1
            elif e.get("evidence_sha256") and file_sha(p) != e["evidence_sha256"]:
                print(f"EVIDENCE CHANGED for seq {e.get('seq')}: {ev}"); bad += 1
        prev = e.get("entry_hash", prev)
    print(f"ledger: {len(ents)} entries, {'OK' if not bad else str(bad) + ' problem(s)'}")
    return 1 if bad else 0


def last_hash_for(path: str):
    for e in reversed(read_entries()):
        for f in e.get("files") or []:
            if f["path"] == path:
                return f["sha256_after"]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("cmd", "note", "file"):
        s = sub.add_parser(name)
        s.add_argument("--phase", default="")
        s.add_argument("--defect", action="append", default=[])
        s.add_argument("--summary", default="")
        if name == "note":
            s.add_argument("--kind", default="DECISION", choices=["DECISION", "FINDING", "TEST_CHANGED", "GATE"])
        if name == "file":
            s.add_argument("paths", nargs="+")
        if name == "cmd":
            s.add_argument("command", nargs=argparse.REMAINDER)
    sub.add_parser("verify")
    ns = ap.parse_args()
    EVID.mkdir(exist_ok=True)
    if ns.mode == "verify":
        return verify()
    if ns.mode == "cmd":
        cmd = ns.command[1:] if ns.command and ns.command[0] == "--" else ns.command
        if not cmd:
            ap.error("no command given (use: cmd -- <command>)")
        t0 = time.time()
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        n = len(read_entries()) + 1
        evp = EVID / f"{n:04d}.txt"
        evp.write_bytes(r.stdout)
        tail = r.stdout.decode("utf-8", "replace").splitlines()[-20:]
        append({"phase": ns.phase, "kind": "COMMAND", "summary": ns.summary or " ".join(cmd)[:120],
                "command": " ".join(cmd), "exit_code": r.returncode, "duration_s": round(time.time() - t0, 3),
                "evidence_file": f"audit/evidence/{n:04d}.txt", "evidence_sha256": sha(r.stdout),
                "tail": tail, "files": [], "defect_ids": ns.defect})
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
        return r.returncode
    if ns.mode == "note":
        append({"phase": ns.phase, "kind": ns.kind, "summary": ns.summary, "command": None, "exit_code": None,
                "evidence_file": None, "files": [], "defect_ids": ns.defect})
        return 0
    if ns.mode == "file":
        files = []
        for p in ns.paths:
            now = file_sha(Path(p))
            files.append({"path": p, "sha256_before": last_hash_for(p), "sha256_after": now})
        append({"phase": ns.phase, "kind": "FILE_CHANGE", "summary": ns.summary, "command": None, "exit_code": None,
                "evidence_file": None, "files": files, "defect_ids": ns.defect})
        return 0


if __name__ == "__main__":
    sys.exit(main())
