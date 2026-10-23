import subprocess, sys
from pathlib import Path
from _util import *

ROOT = Path(__file__).resolve().parent.parent


def test_pyz_builds_and_runs_outside_the_source_tree():
    import hashlib
    d = tmp()
    out1, out2 = d + "/a.pyz", d + "/b.pyz"                       # never touch the tracked dist/ artifact
    for out in (out1, out2):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_pyz.py"), out], capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
    h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert h(out1) == h(out2), "pyz build is not reproducible"
    pyz = Path(out1)
    assert 10_000 < pyz.stat().st_size < 400_000
    v = subprocess.run([sys.executable, str(pyz), "version"], cwd=d, capture_output=True, text=True, timeout=60)
    assert v.returncode == 0 and "standalone" in v.stdout
    s = subprocess.run([sys.executable, str(pyz), "speak", "pyz test", "--out", d + "/a.wav", "--engine", "builtin"], cwd=d,
                       capture_output=True, text=True, timeout=120)
    assert s.returncode == 0 and Path(d, "a.wav").stat().st_size > 1000
    e = subprocess.run([sys.executable, str(pyz), "speak", "", "--out", d + "/b.wav"], cwd=d, capture_output=True, text=True, timeout=60)
    assert e.returncode == 2                                        # exit codes survive the zipapp wrapper


def test_examples_run():
    env = dict(__import__("os").environ, PYTHONPATH=str(ROOT))
    for ex in ("embed_python.py", "jsonlines_client.py"):
        r = subprocess.run([sys.executable, str(ROOT / "examples" / ex)], capture_output=True, text=True, timeout=300, env=env)
        assert r.returncode == 0, (ex, r.stderr[-400:])


def test_shipped_pyz_matches_a_fresh_build():
    import hashlib
    shipped = ROOT / "dist" / "aoc.pyz"
    if not shipped.exists():
        return
    d = tmp(); out = d + "/fresh.pyz"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_pyz.py"), out], check=True, capture_output=True)
    assert hashlib.sha256(Path(out).read_bytes()).hexdigest() == hashlib.sha256(shipped.read_bytes()).hexdigest(), \
        "dist/aoc.pyz is stale: rebuild with python tools/build_pyz.py"
