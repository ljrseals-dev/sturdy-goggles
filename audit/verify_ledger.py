#!/usr/bin/env python3
"""Recompute the hash chain of audit/ledger.jsonl. Exit 1 if anything is broken or tampered."""
import runpy, sys
from pathlib import Path
mod = runpy.run_path(str(Path(__file__).resolve().parent / "log.py"))
sys.exit(mod["verify"]())
