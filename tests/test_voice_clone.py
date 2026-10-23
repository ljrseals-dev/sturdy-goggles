import json, os
from pathlib import Path
from _util import *
from aoc import consent, convert as cv, speech, voiceprofile as vp, wavio

SR = 22050


def test_enrollment_requires_consent_before_reading_audio_and_records_provenance():
    d = tmp(); ref = speaker(105, 0.85, SENTENCES[:8]); p = d + "/ref.wav"; c = d + "/c.jsonl"
    wavio.write_wav(p, ref, SR)
    raises(consent.ConsentError, lambda: vp.enroll("x", p, c))                    # no consent record => refuses
    rec = consent.add_consent(p, "me", "unit test", True, c)
    prof = vp.enroll("x", p, c)
    assert prof.samples[0]["consent_id"] == rec["consent_id"] and prof.samples[0]["sha256"] == rec["file_sha256"]
    assert 90 < prof.f0["median"] < 120 and prof.voiced_seconds > 10 and prof.engines_ok == {"ltas": True, "exemplar": True}
    consent.revoke(rec["consent_id"], c)                                          # revoked => conversion stops
    raises(consent.ConsentError, lambda: cv.convert(speaker(190, 1.1, SENTENCES[8:9], 5), SR, prof, consents_path=c))


def test_enrollment_quality_gates():
    d = tmp(); c = d + "/c.jsonl"
    def enroll_audio(y, sr=SR, name="g"):
        p = f"{d}/{name}.wav"; wavio.write_wav(p, y, sr); consent.add_consent(p, "me", "t", True, c); return vp.enroll(name, p, c)
    raises(vp.EnrollmentError, lambda: enroll_audio(np.zeros(SR * 5, np.float32) + 1e-6, name="silent"))
    raises(vp.EnrollmentError, lambda: enroll_audio(speaker(105, 0.85, SENTENCES[:1])[: int(1.2 * SR)], name="short"))
    noisy = speaker(105, 0.85, SENTENCES[:6]) * 0.05 + (np.random.default_rng(0).standard_normal(SR * 20) * 0.03).astype(np.float32)[: len(speaker(105, 0.85, SENTENCES[:6]))]
    raises(vp.EnrollmentError, lambda: enroll_audio(noisy.astype(np.float32), name="noisy"))
    raises(vp.EnrollmentError, lambda: enroll_audio(np.random.default_rng(1).standard_normal(SR * 6).astype(np.float32) * 0.0001 + 0.0, name="noise"))
    low = wavio.write_wav(d + "/low.wav", np.zeros(100, np.float32) + 0.1, 4000); consent.add_consent(d + "/low.wav", "me", "t", True, c)
    raises(vp.EnrollmentError, lambda: vp.enroll("low", d + "/low.wav", c))
    ok = enroll_audio(speaker(105, 0.85, SENTENCES[:3]), name="mid")              # about 9 s: ltas yes, exemplar warning
    assert isinstance(ok.warnings, list)
    clipped = np.clip(speaker(105, 0.85, SENTENCES[:8]) * 8, -1, 1)
    assert any("clipped" in w for w in enroll_audio(clipped, name="clip").warnings)
    raises(ValueError, lambda: vp.enroll("bad name!", d + "/mid.wav", c))
    raises(vp.EnrollmentError, lambda: vp.enroll("none", [], c))


def test_stereo_and_other_sample_rates_enroll():
    d = tmp(); c = d + "/c.jsonl"; y = speaker(105, 0.85, SENTENCES[:8])
    for sr, name in ((16000, "sr16"), (44100, "sr44")):
        yy = dsp_resample(y, sr)
        p = f"{d}/{name}.wav"; wavio.write_wav(p, np.stack([yy, yy * 0.5], 1), sr); consent.add_consent(p, "me", "t", True, c)
        prof = vp.enroll(name, p, c)
        assert abs(prof.f0["median"] - 102) < 12 and prof.voiced_seconds > 10, (sr, prof.f0)


def dsp_resample(y, sr):
    from aoc import dsp
    return dsp.resample(y, SR / sr, SR)


def test_profile_roundtrip_tamper_detection_and_name_safety():
    d = tmp(); prof, p, c = enroll_synthetic(d)
    root = d + "/voices"; prof.save(root)
    q = vp.VoiceProfile.load("tgt", root)
    assert q.f0 == prof.f0 and np.array_equal(q.bank, prof.bank) and q.samples == prof.samples
    assert [x["name"] for x in vp.list_profiles(root)] == ["tgt"]
    with open(root + "/tgt/bank.npz", "ab") as f:
        f.write(b"x")
    raises(ValueError, lambda: vp.VoiceProfile.load("tgt", root))                 # bank changed => refuses
    raises(ValueError, lambda: vp.VoiceProfile.load("../tgt", root))
    raises(ValueError, lambda: vp.delete_profile("../x", root))
    assert vp.delete_profile("tgt", root) and not vp.delete_profile("tgt", root)


def test_exemplar_engine_moves_frames_and_spectrum_toward_the_reference_timbre_only_case():
    d = tmp(); prof, _, c = enroll_synthetic(d, f0=105, fs=0.85)
    src = speaker(105, 1.15, SENTENCES[8:10], seed=5)                               # same pitch, different vocal tract
    before = cv.similarity(src, SR, prof)
    ex = cv.similarity(cv.convert(src, SR, prof, "exemplar", consents_path=c).audio, SR, prof)
    lt = cv.similarity(cv.convert(src, SR, prof, "ltas", consents_path=c).audio, SR, prof)
    assert ex["frame_distance"] < 0.75 * before["frame_distance"], (before, ex)    # measured about 0.57 -> 0.32
    assert lt["ltas_distance_db"] < 0.5 * before["ltas_distance_db"], (before, lt)  # measured about 5.1 -> 0.6


def test_speak_as_closes_pitch_gap_and_improves_timbre_match():
    d = tmp(); prof, _, c = enroll_synthetic(d, f0=105, fs=0.85)
    raw, sr, _ = speech.synthesize("Good morning, this is a test of the voice.", "builtin", pitch_hz=prof.f0["median"])
    before = cv.similarity(raw, sr, prof)
    r = cv.speak_as("Good morning, this is a test of the voice.", prof, "builtin", consents_path=c)
    after = cv.similarity(r.audio, r.sr, prof)
    assert abs(after["f0_error_cents"]) < 100, after
    assert after["ltas_distance_db"] < before["ltas_distance_db"] and after["frame_distance"] < before["frame_distance"], (before, after)
    assert r.provenance["synthetic_or_converted"] and r.provenance["consent_ids"] and r.info["tts_engine"] == "builtin"


def test_pitch_transfer_accuracy_and_clamp_note():
    d = tmp(); prof, _, c = enroll_synthetic(d, f0=105, fs=0.85)
    near = cv.convert(speaker(130, 1.0, SENTENCES[8:10], 5), SR, prof, "ltas", consents_path=c)
    assert abs(cv.similarity(near.audio, SR, prof)["f0_error_cents"]) < 40 and "pitch_note" not in near.info
    far = cv.convert(speaker(220, 1.0, SENTENCES[8:10], 5), SR, prof, "ltas", consents_path=c)
    assert far.info["shift_semitones"] == -7.0 and "limited" in far.info["pitch_note"]
    off = cv.convert(speaker(220, 1.0, SENTENCES[8:10], 5), SR, prof, "ltas", pitch_strength=0.0, consents_path=c)
    assert off.info["shift_semitones"] == 0.0


def test_engine_selection_registry_and_plugin_priority():
    d = tmp(); prof, _, c = enroll_synthetic(d)
    src = speaker(110, 1.0, SENTENCES[8:9], 5)
    assert cv.convert(src, SR, prof, consents_path=c).engine == "exemplar"
    short, _, _ = enroll_synthetic(d, "shortv", texts=SENTENCES[:3])
    assert short.voiced_seconds < vp.MIN_SECONDS["exemplar"] and cv.convert(src, SR, short, consents_path=c).engine == "ltas"
    assert any("exemplar" in n for n in cv.convert(src, SR, short, consents_path=c).info["fallback_notes"])
    raises(ValueError, lambda: cv.convert(src, SR, short, "exemplar", consents_path=c))
    raises(ValueError, lambda: cv.convert(src, SR, prof, "knn-vc", consents_path=c))          # neural engines are listed but unavailable
    raises(ValueError, lambda: cv.convert(src, SR, prof, "nope", consents_path=c))
    names = {e["name"]: e for e in cv.engines_status(prof)}
    assert not names["knn-vc"]["available"] and not names["xtts"]["available"] and names["exemplar"]["available"]

    class Fake(cv.ConversionEngine):
        name, kind, priority = "fake-neural", "external", 1000
        def run(self, y_shifted, y_orig, profile, k, strength):
            return y_shifted * 0.5
    cv.register_engine(Fake())
    try:
        assert cv.convert(src, SR, prof, consents_path=c).engine == "fake-neural"            # a registered engine wins under auto
    finally:
        cv._REG.pop("fake-neural")


def test_input_validation_shapes_and_determinism():
    d = tmp(); prof, _, c = enroll_synthetic(d)
    src = speaker(120, 1.0, SENTENCES[8:9], 5)
    raises(ValueError, lambda: cv.convert(src[: SR // 10], SR, prof, consents_path=c))
    raises(ValueError, lambda: cv.convert(np.zeros(SR, np.float32), SR, prof, consents_path=c))
    bad = src.copy(); bad[100] = np.nan
    raises(ValueError, lambda: cv.convert(bad, SR, prof, consents_path=c))
    raises(ValueError, lambda: cv.convert(src, SR, prof, pitch_strength=1.5, consents_path=c))
    a = cv.convert(src, SR, prof, consents_path=c); b = cv.convert(src, SR, prof, consents_path=c)
    assert np.array_equal(a.audio, b.audio) and len(a.audio) == len(src) and np.isfinite(a.audio).all() and np.max(np.abs(a.audio)) <= 0.99
    st = cv.convert(np.stack([src, src], 1), SR, prof, consents_path=c)                      # stereo input is downmixed
    assert st.audio.ndim == 1 and len(st.audio) == len(src)
    for sr in (16000, 44100):
        x = dsp_resample(src, sr)
        out = cv.convert(x, sr, prof, consents_path=c)
        assert out.sr == sr and len(out.audio) == len(x)
    rms = lambda y: float(np.sqrt(np.mean(y ** 2)))
    assert abs(rms(a.audio) / rms(src) - 1) < 0.1                                           # loudness preserved


def test_provenance_sidecar_and_fingerprint_fields():
    d = tmp(); prof, _, c = enroll_synthetic(d)
    r = cv.speak_as("hello world", prof, "builtin", consents_path=c)
    out = d + "/o.wav"; wavio.write_wav(out, r.audio, r.sr)
    side = cv.write_provenance(out, r.provenance)
    j = json.loads(side.read_text())
    assert side.name == "o.wav.aoc.json" and j["synthetic_or_converted"] is True and j["voice_profile"] == "tgt"
    assert j["consent_ids"] == [s["consent_id"] for s in prof.samples] and j["engine"] in ("exemplar", "ltas") and "notice" in j
    assert len(j["text_sha256"]) == 64 and len(j["source_sha256"]) == 64


def test_protocol_and_cli_voice_flow():
    import subprocess, sys
    from aoc.protocol import Engine
    d = tmp(); ws = d + "/ws"; Path(ws).mkdir()
    wavio.write_wav(ws + "/ref.wav", speaker(105, 0.85, SENTENCES[:8]), SR)
    os.environ["AOC_CONSENTS"] = d + "/consents.jsonl"
    try:
        e = Engine(ws); c = e.handle
        assert c({"op": "voice.enroll", "name": "p1", "samples": ["ref.wav"]})["error"]["code"] == "consent_required"      # no attestation, no consent
        r = c({"op": "voice.enroll", "name": "p1", "samples": ["ref.wav"], "attested": True, "owner": "me", "scope": "unit test"})
        assert r["ok"] and r["result"]["engines_ok"]["exemplar"]
        assert c({"op": "voice.enroll", "name": "p2", "samples": ["../x.wav"], "attested": True, "owner": "me", "scope": "t"})["error"]["code"] in ("bad_path", "not_found")
        assert [v["name"] for v in c({"op": "voice.list"})["result"]["voices"]] == ["p1"]
        s = c({"op": "speech.synth", "text": "hello there", "engine": "builtin", "voice": "p1", "out": "v.wav"})
        assert s["ok"] and s["result"]["voice"] == "p1" and (Path(ws) / "v.wav.aoc.json").exists(), s
        wavio.write_wav(ws + "/in.wav", speaker(130, 1.1, SENTENCES[8:9], 5), SR)
        k = c({"op": "voice.convert", "path": "in.wav", "voice": "p1", "out": "conv.wav"})
        assert k["ok"] and k["result"]["engine"] == "exemplar"
        assert c({"op": "voice.convert", "path": "in.wav", "voice": "../p1"})["error"]["code"] in ("invalid", "bad_request")
        assert c({"op": "voice.engines", "name": "p1"})["ok"]
        env = dict(os.environ, AOC_VOICES=d + "/cli_voices", AOC_CONSENTS=d + "/cli_consents.jsonl")   # separate consent store from the protocol steps above
        run = lambda *a: subprocess.run([sys.executable, "-m", "aoc", *a], capture_output=True, text=True, env=env, timeout=300,
                                        cwd=Path(__file__).resolve().parent.parent)
        assert run("voice", "enroll", "--name", "c1", "--sample", ws + "/ref.wav").returncode == 2                         # needs consent / --attest
        r1 = run("voice", "enroll", "--name", "c1", "--sample", ws + "/ref.wav", "--owner", "me", "--scope", "t", "--attest")
        assert r1.returncode == 0 and "enrolled c1" in r1.stdout, r1.stderr
        r2 = run("speak", "hello from the command line", "--out", d + "/cli.wav", "--voice", "c1", "--engine", "builtin")
        assert r2.returncode == 0 and "provenance" in r2.stdout and Path(d, "cli.wav.aoc.json").exists(), r2.stderr
        r3 = run("convert", ws + "/in.wav", "--voice", "c1", "--out", d + "/cv.wav")
        assert r3.returncode == 0 and Path(d, "cv.wav").stat().st_size > 1000, r3.stderr
        assert run("convert", ws + "/in.wav", "--out", d + "/x.wav").returncode == 2                                        # --voice required
        assert run("voice", "show", "nope").returncode == 2
    finally:
        os.environ.pop("AOC_CONSENTS", None)
