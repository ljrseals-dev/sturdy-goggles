#!/usr/bin/env python3
"""Objective benchmark of the voice flow on synthetic speakers (no listening involved).
    python tools/eval_voice.py
For each target 'speaker' (pitch, vocal-tract scale): enroll about 26 s of reference speech, then measure how far
(a) the built-in TTS output and (b) the converted output are from the target: f0 error (cents), long-term spectral distance (dB),
frame distance (mean cepstral distance to the nearest reference frame). Lower is closer. These numbers describe the signal only."""
import os, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
import numpy as np
from _util import SENTENCES, enroll_synthetic, speaker
from aoc import convert as cv, speech

SR = 22050
rows = []
d = tempfile.mkdtemp()
TARGETS = [("low male-like", 105, 0.85), ("mid", 150, 1.0), ("high female-like", 215, 1.18)]
TEXT = "Good morning, this is a test of the voice."
print(f"{'target':18s} {'engine':9s} | {'f0 err (cents)':>16s} | {'LTAS dist (dB)':>15s} | {'frame dist':>13s} | convert s")
for label, f0, fs in TARGETS:
    prof, _, c = enroll_synthetic(d, label.split()[0] + str(f0), f0, fs)
    raw, sr, _ = speech.synthesize(TEXT, "builtin", pitch_hz=prof.f0["median"])
    b = cv.similarity(raw, sr, prof)
    print(f"{label:18s} {'(raw TTS)':9s} | {b['f0_error_cents']:16.0f} | {b['ltas_distance_db']:15.2f} | {b['frame_distance']:13.3f} |")
    for eng in ("ltas", "exemplar"):
        t = time.time()
        r = cv.speak_as(TEXT, prof, "builtin", eng, consents_path=c)
        dt = time.time() - t
        a = cv.similarity(r.audio, r.sr, prof)
        print(f"{'':18s} {eng:9s} | {a['f0_error_cents']:16.0f} | {a['ltas_distance_db']:15.2f} | {a['frame_distance']:13.3f} | {dt:.2f}")
        rows.append((label, eng, b, a))
better = [(a["ltas_distance_db"] < b["ltas_distance_db"], a["frame_distance"] < b["frame_distance"]) for _, e, b, a in rows if e == "exemplar"]
print("\nexemplar improved LTAS distance in %d/%d targets and frame distance in %d/%d targets" %
      (sum(x for x, _ in better), len(better), sum(y for _, y in better), len(better)))
