# Building and distributing

**Run from source:** `pip install numpy` then `python -m aoc ...`.

**One-file app (verified):** `python tools/build_pyz.py` -> `dist/aoc.pyz` (about 41 KB). Run `python aoc.pyz ...` on any
machine with Python 3.9+ and numpy. Exit codes are preserved. Tested here by `tests/test_build.py`.

**Bundled executable (NOT built or tested here):** `pip install pyinstaller numpy` then `pyinstaller aoc.spec` on each
target OS (PyInstaller does not cross-compile). Expect the size to be dominated by numpy (here: about 6.3 MB zipped,
21.3 MB installed for numpy 2.4.4 on Linux/CPython 3.12). Use the executable's own `doctor` command to check it.
Alternatives: Nuitka, or embedding the official Python "embeddable" zip plus numpy wheels on Windows.

**Python wheel:** `pip install .` uses `pyproject.toml` (not exercised here).

**Tests:** `python tools/run_tests.py` (no pytest needed) or `pytest -q tests`.

## Bundled numpy (no system numpy needed)
`python tools/vendor_numpy.py` copies the numpy installed in the running interpreter (plus `numpy.libs` and the dist-info licenses)
into `vendor/<platform>-cp<XY>/`. At import, `aoc` uses it automatically when `import numpy` would fail (also from `dist/aoc.pyz` when
`vendor/` is beside `dist/` or the parent of the .pyz, or when `AOC_VENDOR` points at it). The shipped bundle contains the Linux x86_64 /
CPython 3.12 copy (about 50 MB unzipped). Compiled extensions are not portable: run the tool on each OS, architecture and Python minor
version you ship. Test with `python -S tools/run_tests.py` (hides site-packages).

## Reproducible one-file app
`python tools/build_pyz.py [OUT]` is byte-reproducible (sorted entries, fixed timestamps); `tests/test_build.py` checks it and checks
that the shipped `dist/aoc.pyz` is not stale.

## Browser UI smoke test
`python tools/ui_smoke.py audit/evidence` (needs `pip install playwright` and a Chromium); exits 0 only if all steps pass.
