import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np


def raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    raise AssertionError(f"expected {exc.__name__}")


def tmp():
    return tempfile.mkdtemp(prefix="aoc_test_")


def fundamental(y, sr, lo=40, hi=800):
    seg = y[: min(len(y), 8820)]
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lag = int(np.argmax(ac[int(sr / hi):int(sr / lo)])) + int(sr / hi)
    return sr / lag


def peak_freq(y, sr):
    Y = np.abs(np.fft.rfft(y * np.hanning(len(y))))
    return float(np.fft.rfftfreq(len(y), 1 / sr)[Y.argmax()])


SENTENCES = ["The quick brown fox jumps over the lazy dog.", "She sells sea shells by the sea shore.",
             "How much wood would a woodchuck chuck?", "Peter Piper picked a peck of pickled peppers.",
             "A big black bug bit a big black bear.", "Red leather, yellow leather, red leather.",
             "Few free fruit flies fly fast.", "Seven silver swans swam silently seaward.",
             "Where were you while we were away in Wales?", "Good morning, this is a test of the voice."]


def speaker(f0, formant_scale, texts, seed=0, sr=22050):
    """A synthetic 'speaker' (the built-in synthesizer with a given pitch and vocal-tract scale) saying several sentences."""
    from aoc import speech
    b = speech.BuiltinSpeech(sr, f0, 1.0, seed, formant_scale)
    gap = np.zeros(int(0.25 * sr), np.float32)
    return np.concatenate([np.concatenate([b.synth(t), gap]) for t in texts])


def enroll_synthetic(d, name="tgt", f0=105, fs=0.85, texts=None, consents=None):
    """Write a reference WAV for a synthetic speaker, record consent, enroll, return (profile, wav_path, consents_path)."""
    from aoc import consent, voiceprofile as vp, wavio
    consents = consents or d + "/consents.jsonl"
    ref = speaker(f0, fs, texts or SENTENCES[:8])
    path = f"{d}/{name}.wav"
    wavio.write_wav(path, ref, 22050)
    consent.add_consent(path, "test-owner", "unit test", True, consents)
    return vp.enroll(name, path, consents), path, consents
