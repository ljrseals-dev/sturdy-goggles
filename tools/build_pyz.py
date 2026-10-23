#!/usr/bin/env python3
"""Build a reproducible one-file app: dist/aoc.pyz (pure Python; needs numpy on the target, or the vendored copy).

    python tools/build_pyz.py [OUT]          default OUT = dist/aoc.pyz
    python aoc.pyz doctor

Reproducible: entries sorted, fixed timestamps and permissions, no host metadata. Same source = same SHA-256."""
import io, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXED = (1980, 1, 1, 0, 0, 0)
SHEBANG = b"#!/usr/bin/env python3\n"
MAIN = "import sys\nfrom aoc.cli import main\nsys.exit(main())\n"


def build(out) -> Path:
    files = {}
    for p in sorted((ROOT / "aoc").rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            files[p.relative_to(ROOT).as_posix()] = p.read_bytes()
    files["__main__.py"] = MAIN.encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            zi = zipfile.ZipInfo(name, FIXED)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zi.create_system = 3
            z.writestr(zi, files[name])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(SHEBANG + buf.getvalue())
    out.chmod(0o755)
    return out


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "aoc.pyz"
    p = build(dest)
    print(f"built {p} ({p.stat().st_size / 1024:.0f} KB). Requires python3 >= 3.9 and numpy (or the vendored copy).")
