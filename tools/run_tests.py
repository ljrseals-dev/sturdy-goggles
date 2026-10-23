#!/usr/bin/env python3
"""Minimal runner for environments without pytest: executes plain test_* functions that need no fixtures.
Usage: python tools/run_tests.py [tests/test_x.py ...]   (default: every tests/test_*.py)
Prefer real pytest wherever it is available."""
import importlib.util, inspect, sys, traceback
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root)); sys.path.insert(0, str(root / "tests"))
bad = ok = skipped = 0
files = sys.argv[1:] or sorted(str(p.relative_to(root)) for p in (root / 'tests').glob('test_*.py'))
for f in files:
    path = (root / f) if not Path(f).is_absolute() else Path(f)
    spec = importlib.util.spec_from_file_location(path.stem, path); m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception as exc:
        print(f"IMPORT-FAIL {path.name}: {exc!r}"); bad += 1; continue
    for name, fn in sorted(vars(m).items()):
        if name.startswith("test_") and callable(fn):
            if inspect.signature(fn).parameters:
                print(f"SKIP (needs fixtures) {path.name}::{name}"); skipped += 1; continue
            try:
                fn(); print(f"PASS {path.name}::{name}"); ok += 1
            except Exception:
                print(f"FAIL {path.name}::{name}\n{traceback.format_exc()}"); bad += 1
print(f"passed={ok} failed={bad} skipped={skipped}")
sys.exit(1 if bad else 0)
