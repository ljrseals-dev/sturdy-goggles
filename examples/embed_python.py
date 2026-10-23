"""Use the engine directly from Python (in-process): no subprocess, no files unless you ask for them."""
import numpy as np
from aoc.model import Note
from aoc.harmony import build_session
from aoc.mix import VocalMixer
from aoc import speech

# 1. speech -> numpy array
audio, sr, engine = speech.synthesize("Embedding the engine in my own DAW", "builtin")
print("speech:", audio.shape, sr, engine)

# 2. arrangement -> stereo numpy buffer you can hand to your own audio callback or file writer
lead = [Note(p, i * 0.6, 0.55, 0.8, "la") for i, p in enumerate([60, 62, 64, 67, 65, 64, 62, 60])]
session = build_session(lead, parts=4, key="C", mode="major", doubles=1, bg="airy", tempo=100)
mixer = VocalMixer(session, workers=0)
stems = mixer.process_all()                    # {track name: (n, 2) float32}, rendered once
mix = mixer.mix()                              # (n, 2) float32 in [-1, 1] at session.sr
print("tracks:", list(stems), "mix:", mix.shape, "sr:", session.sr, "peak:", float(np.max(np.abs(mix))))
