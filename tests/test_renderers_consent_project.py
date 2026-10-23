import json, os
from pathlib import Path
from _util import *
from aoc import consent, renderers, wavio
from aoc.harmony import *
from aoc.model import *
from aoc.project import Project

SR = 44100


def make_sample(d, f=220.0):
    t = np.arange(SR) / SR
    y = (0.4 * np.sin(2 * np.pi * f * t) + 0.15 * np.sin(4 * np.pi * f * t)).astype(np.float32)
    p = d + "/me.wav"
    wavio.write_wav(p, y, SR)
    return p


def test_sample_renderer_requires_consent_and_follows_the_file():
    d = tmp(); wp = make_sample(d); cp = d + "/c.jsonl"
    raises(consent.ConsentError, lambda: renderers.SampleRenderer(wp, consents_path=cp))
    raises(consent.ConsentError, lambda: consent.add_consent(wp, "me", "personal", attested=False, consents_path=cp))
    rec = consent.add_consent(wp, "me", "personal arrangement", attested=True, consents_path=cp)
    R = renderers.SampleRenderer(wp, consents_path=cp)
    assert abs(R.root - 57) < 0.1
    y = R.render_track(Track("L", "lead", [Note(69, 0, 1.0)], TrackSettings()), SR, 100)
    assert abs(fundamental(y[6000:], SR) - 440) < 8
    consent.revoke(rec["consent_id"], cp)
    raises(consent.ConsentError, lambda: renderers.SampleRenderer(wp, consents_path=cp))
    consent.add_consent(wp, "me", "again", attested=True, consents_path=cp)
    open(wp, "ab").write(b"\0\0")                                   # file changed => hash changed => no consent
    raises(consent.ConsentError, lambda: renderers.SampleRenderer(wp, consents_path=cp))


def test_sample_renderer_long_notes_loop_and_bad_samples_rejected():
    d = tmp(); wp = make_sample(d); cp = d + "/c.jsonl"
    consent.add_consent(wp, "me", "x", attested=True, consents_path=cp)
    R = renderers.SampleRenderer(wp, root_midi=57, consents_path=cp)
    y = R.render_track(Track("L", "lead", [Note(57, 0, 4.0)], TrackSettings()), SR, 100)
    assert len(y) > 4 * SR and np.isfinite(y).all() and np.max(np.abs(y[3 * SR:])) > 0.1     # sustains past the sample length
    short = d + "/short.wav"; wavio.write_wav(short, np.zeros(1000, np.float32), SR)
    consent.add_consent(short, "me", "x", attested=True, consents_path=cp)
    raises(ValueError, lambda: renderers.SampleRenderer(short, consents_path=cp))


def test_renderer_registry():
    raises(ValueError, lambda: renderers.get_renderer("nope"))
    raises(ValueError, lambda: renderers.get_renderer("sample"))
    assert renderers.get_renderer("formant").label.startswith("preview")


def test_project_save_open_verify_and_tamper_detection():
    d = tmp() + "/p1"
    p = Project.create(d, "demo")
    p.session.tracks = build_stack([Note(60, 0, .5)], Key(), 3)
    p.add_clip(np.zeros(1000, np.float32) + 0.1, 22050, "my clip!", "hi", "builtin")
    p.add_clip(np.zeros(10, np.float32), 22050, "my clip!")
    p.save()
    q = Project.open(d)
    assert q.session == p.session and [c["file"] for c in q.clips] == ["assets/my_clip.wav", "assets/my_clip_2.wav"] and q.verify() == []
    open(d + "/assets/my_clip.wav", "ab").write(b"x")
    os.remove(d + "/assets/my_clip_2.wav")
    probs = {x["file"]: x["problem"] for x in q.verify()}
    assert probs == {"assets/my_clip.wav": "modified", "assets/my_clip_2.wav": "missing"}


def test_project_rejects_unsafe_paths_and_future_schema():
    d = tmp() + "/p2"; Project.create(d)
    j = json.loads(Path(d, "project.json").read_text())
    j["clips"] = [{"name": "x", "file": "../../etc/passwd", "sr": 1, "sha256": "0"}]
    Path(d, "project.json").write_text(json.dumps(j))
    raises(ValueError, lambda: Project.open(d))
    j["clips"] = []; j["schema_version"] = 99
    Path(d, "project.json").write_text(json.dumps(j))
    raises(ValueError, lambda: Project.open(d))


def test_project_save_is_atomic_no_temp_left_behind():
    d = tmp() + "/p3"; p = Project.create(d); p.save()
    assert sorted(os.listdir(d)) == ["assets", "project.json"]
