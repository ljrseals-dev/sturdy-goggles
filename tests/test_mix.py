import hashlib
from pathlib import Path
from _util import *
from aoc.harmony import *
from aoc.model import *
from aoc.mix import VocalMixer
from aoc.voice import ParametricRenderer
from aoc.wavio import read_wav


def melody(n=4):
    return [Note(p, i * 0.6, 0.5, 0.8, "la") for i, p in enumerate([60, 62, 64, 67, 65, 64][:n])]


def sess(parts=4):
    s = Session()
    s.tracks = build_stack(melody(), Key(), parts)
    return s


def test_empty_track_does_not_crash_mix_or_export():
    s = Session(); s.tracks = [Track("Empty", "lead", [])]
    assert VocalMixer(s).mix().shape == (1, 2)
    s.tracks = build_stack(melody(), Key(), 2) + [Track("Empty", "background", [])]
    d = tmp()
    paths = VocalMixer(s).export(d)
    assert len({read_wav(p)[0].shape[0] for p in paths.values()}) == 1 and "Empty" in paths


def test_all_muted_is_silent_not_an_error():
    s = sess(2)
    for t in s.tracks:
        t.settings.mute = True
    assert float(np.max(np.abs(VocalMixer(s).mix()))) == 0.0


def test_duplicate_names_rejected_and_unsafe_names_sanitized():
    s = Session(); s.tracks = build_stack(melody(), Key(), 2) + build_stack(melody(), Key(), 2)
    raises(ValueError, s.validate)
    raises(ValueError, lambda: VocalMixer(s).mix())
    s2 = sess(2)
    s2.tracks[0].name, s2.tracks[1].name = "../evil/Lead", "..\\evil\\Lead"
    d = tmp()
    paths = VocalMixer(s2).export(d)
    files = sorted(p.name for p in Path(d).iterdir())
    assert all(Path(p).parent == Path(d) for p in paths.values())
    assert len([f for f in files if f.startswith("stem_")]) == 2 and not any(".." in f for f in files)


def test_each_track_rendered_once_per_export():
    calls = []

    class Counting(ParametricRenderer):
        def render_track(self, track, sr, tempo):
            calls.append(track.name)
            return super().render_track(track, sr, tempo)
    s = sess(4)
    VocalMixer(s, Counting()).export(tmp())
    assert sorted(calls) == sorted(t.name for t in s.tracks)


def test_normalize_flag_and_relative_level():
    s = sess(3)
    m = VocalMixer(s)
    full = m.mix(normalize=False)
    s.track("Harm High").settings.mute = True
    s.track("Harm Low").settings.mute = True
    assert np.max(np.abs(m.mix(normalize=False))) < np.max(np.abs(full))
    assert abs(float(np.max(np.abs(m.mix(normalize=True)))) - 10 ** (-1 / 20)) < 1e-4


def test_determinism_and_parallel_rendering_is_identical():
    h = lambda a: hashlib.sha256(a.tobytes()).hexdigest()
    a = h(VocalMixer(sess()).mix())
    assert a == h(VocalMixer(sess()).mix()) == h(VocalMixer(sess(), workers=2).mix())


def test_editing_one_track_rerenders_only_that_track():
    calls = []

    class Counting(ParametricRenderer):
        def render_track(self, track, sr, tempo):
            calls.append(track.name)
            return super().render_track(track, sr, tempo)
    s = sess(3)
    m = VocalMixer(s, Counting())
    m.mix(); calls.clear()
    s.track("Lead").notes[0].pitch += 1
    m.mix()
    assert calls == ["Lead"]


def test_export_bit_depth_and_equal_lengths():
    s = sess(3) ; d = tmp()
    paths = VocalMixer(s).export(d, bits=24)
    import wave
    assert wave.open(str(paths["mix"])).getsampwidth() == 3
    assert wave.open(str(paths["mix"])).getnchannels() == 2


def test_session_schema_version_roundtrip_future_rejected_legacy_loads():
    import json
    s = sess(3); d = tmp(); p = Path(d) / "s.json"
    s.save(p)
    data = json.loads(p.read_text()); assert data["schema_version"] == SCHEMA_VERSION
    assert Session.load(p) == s
    data["schema_version"] = SCHEMA_VERSION + 1; p.write_text(json.dumps(data))
    raises(ValueError, lambda: Session.load(p))
    data.pop("schema_version"); p.write_text(json.dumps(data))
    assert Session.load(p) == s
