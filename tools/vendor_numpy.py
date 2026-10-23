#!/usr/bin/env python3
"""Copy the numpy installed in THIS interpreter (plus numpy.libs and its dist-info with licenses) into
vendor/<platform>-cp<XY>/, so the app runs on a machine that has no numpy.

    python tools/vendor_numpy.py

The result is specific to this OS, CPU architecture and Python minor version (compiled extensions). Run the script on
each platform you want to ship (needs numpy installed there). Writes vendor/<tag>/VENDOR_MANIFEST.json with versions and
a SHA-256 for every file; `aoc doctor` and `aoc defense` (when added) can verify it."""
import hashlib, json, os, shutil, sys, sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tag() -> str:
    return f"{sysconfig.get_platform()}-cp{sys.version_info[0]}{sys.version_info[1]}"


def main() -> int:
    import numpy
    base = Path(numpy.__file__).resolve().parent.parent
    dest = ROOT / "vendor" / tag()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    keep = ["numpy", "numpy.libs"] + [p.name for p in base.glob("numpy-*.dist-info")]
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "tests")
    for name in keep:
        src = base / name
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=ignore, symlinks=True)
    files, total = {}, 0
    for p in sorted(dest.rglob("*")):
        if p.is_file() and not p.is_symlink():
            data = p.read_bytes()
            files[p.relative_to(dest).as_posix()] = hashlib.sha256(data).hexdigest()
            total += len(data)
    manifest = {"numpy": numpy.__version__, "python": sys.version.split()[0], "platform": sysconfig.get_platform(),
                "files": len(files), "bytes": total, "sha256": files}
    (dest / "VENDOR_MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(f"vendored numpy {numpy.__version__} -> {dest} ({len(files)} files, {total / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
