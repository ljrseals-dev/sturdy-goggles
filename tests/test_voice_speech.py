import os, stat
from _util import *
from aoc import speech
from aoc.model import Note, Track, TrackSettings
from aoc.voice import ParametricRenderer, VOWELS


def test_renderer_pitch_is_correct():
    t = Track("L", "lead", [Note(69, 0, 1.0)], TrackSettings(vibrato_depth_cents=0, breath=0.0))
    y = ParametricRenderer().render_track(t, 44100, 100)
    assert np.isfinite(y).all() and abs(fundamental(y[4410:], 44100) - 440) < 6


def test_renderer_vowels_differ_spectrally_and_empty_track_is_empty():
    def centroid(v):
        t = Track("v", "lead", [Note(57, 0, 1.0, 0.8, v)], TrackSettings(vibrato_depth_cents=0, breath=0))
        y = ParametricRenderer().render_track(t, 44100, 100)[8000:30000]
        S = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        return float((S * np.fft.rfftfreq(len(y), 1 / 44100)).sum() / S.sum())
    c = {v: centroid(v) for v in VOWELS}
    assert len({round(x) for x in c.values()}) == 5 and c["a"] > c["u"]
    assert len(ParametricRenderer().render_track(Track("e", "lead", []), 44100, 100)) == 0


def test_renderer_is_deterministic_per_seed_and_handles_late_notes():
    t = lambda seed: Track("x", "lead", [Note(60, 0, 0.3), Note(62, 5.0, 0.3)], TrackSettings(seed=seed))
    a, b, c = (ParametricRenderer().render_track(t(s), 22050, 100) for s in (1, 1, 2))
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_g2p_rules():
    g = lambda w: " ".join(speech.g2p_word(w))
    assert g("cake") == "K EY K" and g("phone") == "F OW N" and g("city") == "S IH T IY" and g("stage") == "S T EY JH"
    assert g("hello") == "HH AH L OW" and g("") == "" and g("123") == ""


def test_builtin_speech_basic_properties():
    a, sr, used = speech.synthesize("Hello world. Testing one two three?", "builtin")
    assert used == "builtin" and sr == 22050 and np.isfinite(a).all()
    assert 1.0 < len(a) / sr < 8.0 and 0.5 < np.max(np.abs(a)) <= 1.0
    i = int(np.argmax(np.abs(a)))
    f = fundamental(a[max(i - 700, 0):i + 700], sr, 60, 300)
    assert 90 < f < 160, f                                     # voiced pitch near the 118 Hz default


def test_builtin_speech_is_deterministic_and_rate_changes_duration():
    a1 = speech.synthesize("same text here", "builtin", seed=3)[0]
    a2 = speech.synthesize("same text here", "builtin", seed=3)[0]
    assert np.array_equal(a1, a2)
    slow = speech.synthesize("same text here", "builtin", rate=0.7)[0]
    fast = speech.synthesize("same text here", "builtin", rate=1.6)[0]
    assert len(slow) > len(a1) > len(fast)


def test_speech_input_validation():
    raises(ValueError, lambda: speech.synthesize("", "builtin"))
    raises(ValueError, lambda: speech.synthesize("x" * 6000, "builtin"))
    raises(ValueError, lambda: speech.synthesize("hi", "nonsense"))
    raises(ValueError, lambda: speech.synth_espeak("hi", voice="en; rm -rf /"))


def test_espeak_backend_with_a_fake_executable():
    d = tmp(); exe = os.path.join(d, "espeak-ng")
    open(exe, "w").write("#!/usr/bin/env python3\nimport sys,struct,math\nsys.stdin.read()\nsr=22050\n"
                         "pcm=b''.join(struct.pack('<h',int(8000*math.sin(2*math.pi*300*i/sr))) for i in range(sr//5))\n"
                         "sys.stdout.buffer.write(b'RIFF'+struct.pack('<I',0xFFFFFFFF)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16)+b'data'+struct.pack('<I',0xFFFFFFFF)+pcm)\n")
    os.chmod(exe, 0o755)
    old = os.environ["PATH"]
    os.environ["PATH"] = d + os.pathsep + old
    try:
        a, sr, used = speech.synthesize("hi there")
        assert used == "espeak" and sr == 22050 and abs(len(a) / sr - 0.2) < 0.01
        assert speech.synthesize("hi there", "builtin")[2] == "builtin"
    finally:
        os.environ["PATH"] = old
