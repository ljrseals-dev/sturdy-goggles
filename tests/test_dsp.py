import hashlib
from _util import *
from aoc import dsp, wavio

SR = 44100
X = (np.random.default_rng(0).standard_normal(8192).astype(np.float32) * 0.5)
H = lambda a: hashlib.sha256(np.asarray(a).tobytes()).hexdigest()


def rms(y):
    return float(np.sqrt(np.mean(np.asarray(y, np.float64) ** 2)))


def sine(f, d=1.0, sr=SR):
    return np.sin(2 * np.pi * f * np.arange(int(d * sr)) / sr).astype(np.float32)


def test_v5_chain_functions_are_bit_identical_to_the_earlier_build():
    # golden hashes computed from the v5 dsp.py on the same seeded noise
    assert H(dsp.compressor(X.copy(), -20.0, 4.0)) == "75f1cc897f2ade7185257d02932bfed6aebb3e2f7273ce99504b951006b9d0ba"
    assert H(dsp.limiter(X.copy(), -1.0)) == "bcd4f0ec314147892a31480c82ee13583343a4da4e7f2de36dcce699eae845b3"
    assert H(dsp.peak_normalize(X.copy(), -1.0)) == "08c1b18c150ab761afda9b1bd9ddf4e42c9f8ab6cd19f997b4c08083a21e7ffc"
    assert H(dsp.soft_saturate(X.copy(), 1.5)) == "a188422aa264f032a56f57708801a497758f331b90bcc31f4fc04acc8e06e48b"


def test_filters_have_the_expected_response():
    assert rms(dsp.highpass(sine(50), SR, 90)) / rms(sine(50)) < 0.4
    assert abs(rms(dsp.highpass(sine(1000), SR, 90)) / rms(sine(1000)) - 1) < 0.02
    assert abs(rms(dsp.lowpass(sine(1000), SR, 6000)) / rms(sine(1000)) - 1) < 0.02
    assert rms(dsp.lowpass(sine(10000), SR, 6000)) / rms(sine(10000)) < 0.45
    bp = dsp.bandpass(sine(4000), SR, 2500, 6000)
    assert rms(bp) / rms(sine(4000)) > 0.8
    assert rms(dsp.bandpass(sine(200), SR, 2500, 6000)) / rms(sine(200)) < 0.05


def test_eq_single_pass_matches_two_pass():
    a = dsp.eq_vocal(X, SR)
    b = dsp.highpass(X, SR, 90)
    b = b + 0.25 * dsp.bandpass(b, SR, 2500, 6000)
    assert float(np.max(np.abs(a - b))) < 5e-3


def test_time_stretch_changes_length_not_pitch():
    y = sine(440, 2.0)
    out = dsp.time_stretch(y, 1.15)
    assert abs(len(out) / len(y) - 1 / 1.15) < 0.002
    assert abs(peak_freq(out[2000:-2000], SR) - 440) < 3


def test_pitch_shift_is_correct_and_length_preserving():
    y = sine(440, 2.0)
    for st in (12, -12, 2, -5):
        out = dsp.pitch_shift(y, SR, st)
        assert len(out) == len(y)
        want = 440 * 2 ** (st / 12)
        assert abs(peak_freq(out[3000:-3000], SR) - want) < max(2.0, want * 0.01), (st, want)


def test_character_chain_and_finalize_are_finite_and_bounded():
    out = dsp.finalize(dsp.character(sine(200, 1.0), SR))
    assert np.isfinite(out).all() and np.max(np.abs(out)) <= 1.0


def test_reverb_ir_is_cached_normalized_and_read_only():
    a, b = dsp.reverb_ir(SR), dsp.reverb_ir(SR)
    assert a is b and abs(float(np.sum(a.astype(np.float64) ** 2)) - 1.0) < 1e-3
    raises(ValueError, lambda: a.__setitem__(0, 1.0))


def test_wav_roundtrip_16_24_and_stereo():
    d = tmp()
    a = (X[:4000] * 0.5).astype(np.float32)
    wavio.write_wav(d + "/a16.wav", a, SR, 16)
    b, sr = wavio.read_wav(d + "/a16.wav")
    assert sr == SR and float(np.max(np.abs(a - b))) < 1e-4       # 16-bit quantization (+ the 32767/32768 convention)
    wavio.write_wav(d + "/a24.wav", a, SR, 24)
    b, _ = wavio.read_wav(d + "/a24.wav")
    assert float(np.max(np.abs(a - b))) < 5e-7
    st = np.stack([a, a * 0.5], 1)
    wavio.write_wav(d + "/s.wav", st, SR)
    assert wavio.read_wav(d + "/s.wav")[0].shape == (4000, 2)
    raises(ValueError, lambda: wavio.write_wav(d + "/x.wav", a, SR, 12))
    raises(ValueError, lambda: wavio.parse_wav_bytes(b"not a wav file at all" * 4))


def test_empty_and_tiny_inputs_do_not_crash():
    e = np.zeros(0, np.float32)
    for fn in (lambda: dsp.highpass(e, SR, 90), lambda: dsp.deess(e, SR), lambda: dsp.pitch_shift(e, SR, 2),
               lambda: dsp.time_stretch(e, 1.2), lambda: dsp.fft_convolve(e, X)):
        assert len(fn()) == 0
