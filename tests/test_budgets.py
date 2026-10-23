"""Performance and import budgets (generous thresholds; measured on the 1-CPU build machine, see docs/RUN_LOG.md)."""
import subprocess, sys, time
from pathlib import Path
from _util import *
from aoc.harmony import *
from aoc.mix import VocalMixer
from aoc.model import *

ROOT = Path(__file__).resolve().parent.parent


def py(code):
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)


def test_cli_help_and_version_do_not_import_numpy():
    r = py("import sys\nfrom aoc.cli import _p, main\n_p()\nassert 'numpy' not in sys.modules, 'numpy imported at CLI import'\n"
           "try:\n    main(['version'])\nexcept SystemExit: pass\nassert 'numpy' not in sys.modules, 'numpy imported by version'\n")
    assert r.returncode == 0, r.stderr


def test_cli_import_time_budget():
    best = 9.0
    for _ in range(3):
        t = time.perf_counter()
        r = py("import aoc.cli")
        best = min(best, time.perf_counter() - t)
        assert r.returncode == 0
    assert best < 1.0, best                       # includes interpreter start; measured about 0.03 s


def test_ten_track_mix_budget():
    lead = [Note(p, i * 0.6, 0.55, 0.8, "la") for i, p in enumerate([60, 62, 64, 67, 65, 64, 62, 60, 62, 64, 67, 69])]
    s = build_session(lead, 6, "C", "major", 2, "airy", 100.0)
    assert len(s.tracks) >= 10
    t = time.perf_counter()
    VocalMixer(s).mix()
    dt = time.perf_counter() - t
    assert dt < 12.0, dt                          # measured about 1.6 s on 1 CPU; 12 s catches order-of-magnitude regressions
