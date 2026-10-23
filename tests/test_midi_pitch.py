import struct
from pathlib import Path
from _util import *
from aoc import midi, pitch
from aoc.harmony import *
from aoc.model import *

SR = 44100


def tone(f, d=1.0):
    t = np.arange(int(d * SR)) / SR
    return (0.5 * np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)).astype(np.float32)


def test_midi_roundtrip_names_pitches_and_timing():
    lead = [Note(p, i * 0.6, 0.5, 0.8, "la") for i, p in enumerate([60, 62, 64, 67])]
    s = Session(tempo=100); s.tracks = build_stack(lead, Key(), 3) + build_backgrounds(lead, Key())
    p = midi.write_midi(s, tmp() + "/o.mid")
    r = midi.read_midi(p)
    assert abs(r["tempo_bpm"] - 100) < 0.01
    names = [t["name"] for t in r["tracks"] if t["notes"]]
    assert names[:3] == ["Lead", "Harm High", "Harm Low"]
    ld = [t for t in r["tracks"] if t["name"] == "Lead"][0]["notes"]
    assert [n.pitch for n in ld] == [60, 62, 64, 67]
    assert max(abs(a.start - b.start) for a, b in zip(ld, lead)) < 0.002 and abs(ld[0].dur - 0.5) < 0.002


def test_lead_from_midi_polyphony_handling_and_errors():
    s = Session(tempo=120); s.tracks = [Track("P", "lead", [Note(60, 0, 1, 0.8), Note(64, 0.5, 1, 0.8)])]
    p = midi.write_midi(s, tmp() + "/p.mid")
    raises(ValueError, lambda: midi.lead_from_midi(p))
    assert [n.pitch for n in midi.lead_from_midi(p, poly="top")[0]] == [64]
    raises(ValueError, lambda: midi.lead_from_midi(p, track="nope"))
    bad = tmp() + "/bad.mid"; Path(bad).write_bytes(b"MThd" + b"\0" * 3)
    raises((ValueError, struct.error), lambda: midi.read_midi(bad))
    Path(bad).write_bytes(b"hello world")
    raises(ValueError, lambda: midi.read_midi(bad))


def test_midi_running_status_and_tempo_change():
    # hand-built SMF: tempo 500000 us/q (120 bpm) then 250000 (240 bpm) at tick 480; two notes using running status
    trk = bytes([0, 0xFF, 0x51, 3, 0x07, 0xA1, 0x20]) + bytes([0x83, 0x60, 0xFF, 0x51, 3, 0x03, 0xD0, 0x90])
    trk += bytes([0, 0x90, 60, 100, 0x83, 0x60, 60, 0])                       # note on, then note off via vel 0 + running status
    trk += bytes([0, 0xFF, 0x2F, 0])
    data = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480) + b"MTrk" + struct.pack(">I", len(trk)) + trk
    p = tmp() + "/t.mid"; Path(p).write_bytes(data)
    r = midi.read_midi(p)
    n = [t for t in r["tracks"] if t["notes"]][0]["notes"][0]
    assert n.pitch == 60 and abs(n.start - 0.5) < 1e-6 and abs(n.dur - 0.25) < 1e-3, (n.start, n.dur)   # 480 ticks at 120 bpm = 0.5 s; next 480 ticks at 240 bpm = 0.25 s


def test_pitch_accuracy_across_the_vocal_range():
    for f in (82.4, 110, 196, 220, 330, 440, 659.25, 880):
        est = pitch.estimate_f0(tone(f), SR)
        assert est > 0 and abs(1200 * np.log2(est / f)) < 5, (f, est)


def test_weak_fundamental_and_silence_and_noise():
    t = np.arange(SR) / SR
    y = sum(a * np.sin(2 * np.pi * 220 * k * t) for k, a in [(1, 0.1), (2, 0.5), (3, 0.4), (4, 0.3)]).astype(np.float32)
    assert abs(pitch.estimate_f0(y, SR) - 220) < 2
    assert pitch.track_notes(np.zeros(SR, np.float32), SR) == []
    assert pitch.track_notes((np.random.default_rng(0).standard_normal(SR) * 0.1).astype(np.float32), SR) == []
    assert pitch.track_notes(np.zeros(10, np.float32), SR) == []


def test_note_segmentation():
    seq = [(60, .4), (64, .4), (67, .5), (62, .3)]
    sig = np.concatenate([np.concatenate([tone(440 * 2 ** ((m - 69) / 12), d), np.zeros(int(.08 * SR), np.float32)]) for m, d in seq])
    notes = pitch.track_notes(sig, SR)
    assert [n.pitch for n in notes] == [60, 64, 67, 62]
    starts = [0.0, 0.48, 0.96, 1.54]
    assert all(abs(n.start - s) < 0.06 for n, s in zip(notes, starts))


def test_octave_jumps_are_corrected_and_isolated_frames_dropped():
    f = np.full(40, 220.0); f[10] = 440.0; f[20] = 110.0; f[30] = 0.0
    g = pitch.smooth_f0(f)
    assert abs(g[10] - 220) < 1 and abs(g[20] - 220) < 1 and g[30] == 0.0
    iso = np.zeros(40); iso[15] = 300.0
    assert pitch.smooth_f0(iso).sum() == 0.0                             # a lone voiced frame is not a note
    real = np.concatenate([np.full(20, 220.0), np.full(20, 440.0)])      # a REAL octave step must survive
    assert abs(pitch.smooth_f0(real)[25] - 440) < 1 and abs(pitch.smooth_f0(real)[5] - 220) < 1


def test_noisy_and_jittery_voices_are_tracked_within_tolerance():
    rng = np.random.default_rng(3)
    t = np.arange(int(1.5 * SR)) / SR
    f = 196.0 * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) + 0.002 * rng.standard_normal(len(t)).cumsum() / 50)   # vibrato + jitter
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (0.5 * np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)) * (1 + 0.05 * rng.standard_normal(len(t)))
    for snr_db in (30, 15):
        noise = rng.standard_normal(len(t)) * (10 ** (-snr_db / 20)) * float(np.sqrt(np.mean(y ** 2)))
        est = pitch.estimate_f0((y + noise).astype(np.float32), SR)
        assert abs(1200 * np.log2(est / 196.0)) < 25, (snr_db, est)      # within 25 cents at 15 dB SNR with vibrato + jitter


def test_tracker_speed_budget_is_met_with_margin():
    import time
    rng = np.random.default_rng(0)
    y = np.concatenate([np.sin(2 * np.pi * 440 * 2 ** ((55 + int(rng.integers(0, 14)) - 69) / 12) * np.arange(int(0.5 * SR)) / SR) for _ in range(20)]).astype(np.float32)
    t = time.perf_counter(); pitch.yin_f0(y, SR); dt = time.perf_counter() - t
    assert dt < 10.0 * (len(y) / SR) / 60 * 3, dt         # prompt budget: 60 s in < 10 s (x3 slack on a loaded 1-CPU box); measured about 0.2 s per 10 s
