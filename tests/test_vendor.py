import hashlib, json, shutil, subprocess, sys, sysconfig
from pathlib import Path
from _util import *

ROOT = Path(__file__).resolve().parent.parent
TAG = f"{sysconfig.get_platform()}-cp{sys.version_info[0]}{sys.version_info[1]}"
VENDOR = ROOT / "vendor" / TAG


def run(args, cwd=ROOT, env=None):
    # -S: do not load site-packages, so a system numpy is invisible and only the bundled copy (if any) can satisfy `import numpy`
    return subprocess.run([sys.executable, "-S", *args], cwd=cwd, capture_output=True, text=True, timeout=300, env=env)


def test_numpy_missing_gives_clear_errors_and_numpy_free_commands_still_work():
    d = tmp()
    shutil.copytree(ROOT / "aoc", d + "/aoc", ignore=shutil.ignore_patterns("__pycache__"))      # a tree with no vendor/ beside it
    assert run(["-m", "aoc", "version"], cwd=d).returncode == 0
    r = run(["-m", "aoc", "speak", "hello", "--out", d + "/x.wav", "--engine", "builtin"], cwd=d)
    assert r.returncode == 2 and "numpy is required" in r.stderr and "pip install numpy" in r.stderr, r.stderr
    r = run(["-m", "aoc", "doctor"], cwd=d)
    assert r.returncode == 1 and "[FAIL] numpy" in r.stdout and "fix:" in r.stdout, r.stdout


def test_bundled_numpy_is_used_when_present_and_verified_by_manifest():
    if not VENDOR.exists():
        # no bundle for this platform: the app must say so (covered above) and the tool must be able to create one
        assert (ROOT / "tools" / "vendor_numpy.py").exists()
        return
    r = run(["-c", "import aoc, numpy; print(numpy.__version__); print(numpy.__file__)"])
    assert r.returncode == 0, r.stderr
    assert str(VENDOR) in r.stdout, r.stdout                                  # imported from vendor/, not from the system
    assert run(["-m", "aoc", "doctor"]).returncode == 0
    d = tmp()
    s = run(["-m", "aoc", "studio", "demo", "--out", d + "/demo"])
    assert s.returncode == 0 and (Path(d) / "demo" / "vocal_mix.wav").stat().st_size > 10_000, s.stderr
    man = json.loads((VENDOR / "VENDOR_MANIFEST.json").read_text())
    assert man["files"] == len(man["sha256"]) > 100
    for rel, want in man["sha256"].items():
        assert hashlib.sha256((VENDOR / rel).read_bytes()).hexdigest() == want, f"vendor file changed: {rel}"
    lic = list((VENDOR).glob("numpy-*.dist-info/licenses/LICENSE.txt"))
    assert lic, "numpy license must ship with the bundled copy"


def test_pyz_finds_the_bundled_numpy_next_to_it_and_via_AOC_VENDOR():
    if not VENDOR.exists():
        return                                                                  # nothing bundled for this platform (see first test)
    import os
    shipped = ROOT / "dist" / "aoc.pyz"                                         # dist/aoc.pyz sits beside vendor/ in the repo layout
    d = tmp()
    r = run([str(shipped), "speak", "pyz with bundled numpy", "--out", d + "/a.wav", "--engine", "builtin"], cwd=d)
    assert r.returncode == 0 and Path(d, "a.wav").stat().st_size > 1000, r.stderr
    from importlib import util
    out = d + "/elsewhere.pyz"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_pyz.py"), out], check=True, capture_output=True)
    env = dict(os.environ, AOC_VENDOR=str(ROOT / "vendor"))
    r = run([out, "speak", "env override", "--out", d + "/b.wav", "--engine", "builtin"], cwd=d, env=env)
    assert r.returncode == 0 and Path(d, "b.wav").stat().st_size > 1000, r.stderr
