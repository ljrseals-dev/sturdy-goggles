# Limitations and what is not verified

## By design
- **Offline engine.** No real-time audio I/O, no plug-in hosting, no live monitoring. Render, then play back.
- **No neural voice cloning or conversion** (kNN-VC, XTTS: need torch and model weights; listed as unavailable, pluggable via
  `register_engine`). The numpy-only voice flow (`docs/VOICE.md`) does classical pitch and timbre transfer with modest measured gains
  and has **never been listened to**. The consent-gated `sample` renderer uses a recording of your own voice, pitched per note.

## Quality limits
- **Built-in speech is experimental and robotic.** Rule-based spelling-to-sound with a formant source. Its intelligibility
  was **not evaluated by a human listener** (the author could only test pitch, timing, spectrum, and determinism). Install
  espeak-ng for clearer speech.
- **Formant singing is a preview**, not a realistic voice.
- **Sample renderer:** best within about +/-7 semitones of the recorded pitch; larger shifts change formants.
- **Pitch tracker:** monophonic solo voices; accurate to a few cents on clean synthetic tones (tested 82-880 Hz); real recordings with noise or
  breathiness will be rougher. No polyphonic transcription.
- **Phase vocoder** time/pitch changes add the usual smearing on transients.
- MIDI writer rounds fractional pitches (no pitch-bend export).

## Not verified in the build environment
- Python 3.9-3.11 and numpy < 2 (built and tested on Python 3.12 + numpy 2.4 only).
- Windows, macOS, Termux, Raspberry Pi. Only Linux was used.
- The PyInstaller executable (not built). espeak-ng itself (tested only with a fake executable that returns a WAV).
- Any listening test of any output (including the voice-conversion flow; its objective metrics were measured on synthetic speakers only).
- Transient-preserving time stretch: attempted (phase locking + transient reset), **worse** than the plain vocoder, reverted.
- Verified in run 1 (see `RUN_LOG.md`): the browser UI in headless Chromium; the reproducible pyz; 61/61 tests, also with system site-packages hidden.
- The bundled numpy (`vendor/`) is Linux x86_64 / CPython 3.12 only. No models are shipped (none are used).

## Performance (one machine, small samples)
10-track arrangement, 12-note lead, about 11.6 s of audio: render + mix about 1.6 s. 100-note single track: about 0.4 s to render (down from 2.2 s before the harmonic-recurrence optimization).
Cost grows with notes and track count; use `workers` for many tracks.
