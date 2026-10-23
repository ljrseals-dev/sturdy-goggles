from _util import *
from aoc import dsp

SR = 44100


def err_db(out, f, r, sr=SR):
    p = np.arange(len(out)) * r
    ideal = np.sin(2 * np.pi * f * p / sr)
    e = out[300:-300] - ideal[300:-300]
    return 20 * np.log10(np.sqrt(np.mean(e ** 2)) / np.sqrt(np.mean(ideal[300:-300] ** 2)))


def test_sinc_is_far_more_accurate_than_linear_at_fractional_ratios():
    x = np.sin(2 * np.pi * 1000 * np.arange(SR) / SR).astype(np.float32)
    for r in (1.5, 0.75, 1.0595):
        lin, sinc = err_db(dsp.resample(x, r, SR, "linear"), 1000, r), err_db(dsp.resample(x, r, SR), 1000, r)
        assert sinc < -90 and sinc < lin - 30, (r, lin, sinc)


def test_decimation_is_anti_aliased():
    hi = np.sin(2 * np.pi * 18000 * np.arange(SR) / SR).astype(np.float32)
    o = dsp.resample(hi, 2.0, SR)
    assert 20 * np.log10(np.sqrt(np.mean(o[300:-300] ** 2)) / np.sqrt(np.mean(hi ** 2))) < -80
    lin = dsp.resample(hi, 2.0, SR, "linear")
    assert 20 * np.log10(np.sqrt(np.mean(lin[300:-300] ** 2)) / np.sqrt(np.mean(hi ** 2))) > -45     # the old one does alias


def test_passband_is_flat_and_length_is_exact():
    t = np.arange(SR) / SR
    for f in (500, 5000, 9000):
        o = dsp.resample(np.sin(2 * np.pi * f * t).astype(np.float32), 1.25, SR)
        assert abs(float(np.max(np.abs(o[300:-300]))) - 1.0) < 0.01, f
    for r in (0.5, 0.9, 1.0, 1.7, 3.0):
        assert len(dsp.resample(np.zeros(10001, np.float32), r, SR)) == int(np.floor(10000 / r)) + 1


def test_edge_cases_and_validation():
    assert len(dsp.resample(np.zeros(0, np.float32), 1.5, SR)) == 0
    assert len(dsp.resample(np.ones(1, np.float32), 1.5, SR)) == 1
    raises(ValueError, lambda: dsp.resample(np.ones(100, np.float32), 0.0, SR))
    raises(ValueError, lambda: dsp.resample(np.ones(100, np.float32), 1.5, SR, "cubic"))
    x = (np.random.default_rng(1).standard_normal(5000) * 0.1).astype(np.float32)
    assert np.array_equal(dsp.resample(x, 1.3, SR), dsp.resample(x, 1.3, SR))           # deterministic
    assert np.isfinite(dsp.resample(x, 0.2, SR)).all() and np.isfinite(dsp.resample(x, 6.0, SR)).all()
