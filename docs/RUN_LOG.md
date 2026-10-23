# Run log: Claude prompt executed on the standalone build (run 1)

Environment: Linux x86_64, CPython 3.12.3, numpy 2.4.4, **1 CPU**, no network, no espeak-ng, no PyInstaller; Playwright + headless
Chromium, gcc and uv present. Evidence: `audit/ledger.jsonl` (hash chained; `python audit/verify_ledger.py`) and `audit/evidence/`.

## Phase results
| Phase | Result | Notes |
|-------|--------|-------|
| P0 baseline | PASS | 54/54 tests, doctor, environment, baseline hashes. **Finding:** the shipped SHA-256 list failed after a test run (test rebuilt `dist/aoc.pyz`; zipapp embeds timestamps) |
| P1 prove the claims | PARTIAL | see below |
| P2 quality foundations | PARTIAL (run 2) | resampler done, octave smoothing done, voice flow added; LUFS/true-peak/dither NOT STARTED; transient-preserving stretch attempted and reverted |
| P3 - P8 | NOT STARTED | next in `docs/CLAUDE_PROMPT.md` |

## P1 detail
| Gap | Status | Evidence |
|-----|--------|----------|
| L15 reproducible pyz | FIXED | `tools/build_pyz.py` writes sorted, fixed-timestamp entries; two builds and the shipped file hash identically; tests no longer touch `dist/` |
| L2 browser UI | VERIFIED_RUN (headless Chromium) | `tools/ui_smoke.py`: 11/11 steps, no JavaScript errors, screenshots in `audit/evidence/ui_*.png`. Page CSP stays strict (the first harness attempt was blocked by it, which is correct) |
| L16 CI + budgets | PARTIAL | `.github/workflows/ci.yml` (7-job matrix, no `\|\| true`, YAML parses) written but **NOT_RUN_HERE**; budget tests exist and pass (`aoc --help/version` never import numpy; 10-track mix under 12 s, measured about 1.6 s) |
| L1 portability | PARTIAL | Python 3.9 grammar check of 32 files and a grep for 3.10+ APIs: clean. Runtime on 3.9-3.11, numpy 1.21, macOS, Windows: **NOT_RUN_HERE** (only CPython 3.12 installed, no network) |
| L4 PyInstaller | NOT_BUILT_HERE | not installed, no network |
| L5 real espeak-ng | ENV_MISSING | not installed |
| L3 listening | NEEDS_HUMAN | unchanged |

## New in this run
- **Bundled numpy** (`vendor/linux-x86_64-cp312/`, 49.9 MB, 426 files, licenses included) found automatically when the system has no numpy
  (`aoc/__init__.py` uses `find_spec`, so numpy is not imported for `--help`). 61/61 tests also pass with site-packages hidden (`python -S`).
- `aoc doctor` and every command now say clearly when numpy is missing and how to fix it (tested).
- Test count 54 -> 61.

## Models
**None are included.** The engine uses none (formant synthesis, rule-based G2P, YIN), this machine has no speech models, and there
is no network to fetch any. Padding the archive to reach a size would be dishonest; the large part of the bundle is the real numpy runtime.

## Run 2: reference-voice flow + P2 items
Request: make the logic accept a reference vocal WAV for cloning as in AOC v3, and start the next phase. v3/v5 passed `cfg.ref` reference WAVs to
XTTS (zero-shot) or kNN-VC (conversion). Those need torch + weights, which are unavailable here, so the flow was rebuilt numpy-only (`docs/VOICE.md`).

| Item | Result | Evidence |
|------|--------|----------|
| Reference-voice flow (enroll, consent, conversion, provenance, CLI, protocol) | DONE, classical only | `tests/test_voice_clone.py` (11 tests), `tools/eval_voice.py` |
| L8 resampler | FIXED: windowed-sinc; error vs ideal -99 dB (linear -55 dB), alias after 2x decimation -100 dB (linear -31 dB); 10 s resamples in 1.7 s | `tests/test_resample.py` |
| L8 transient-preserving stretch | **OPEN; attempt reverted.** Identity phase locking + transient reset: no gain on harmonics (23.5 dB both), click-train pre-echo 0.67 vs 0.02 (worse) | ledger FINDING |
| L10 pitch tracker | octave-jump smoothing + jitter/noise tests added. **Prompt claim was wrong:** speed was already fine (60 s of audio in about 1.4 s) | `tests/test_midi_pitch.py`, ledger FINDING |
| L9 loudness / true-peak / dither | NOT STARTED | |

Objective voice metrics (synthetic speakers only): exemplar engine -11% to -23% frame distance, spectral distance better 3/3; timbre-only case -44%.
Pitch gaps over 7 semitones are limited (quality). Nothing here has been listened to.
Tests: 54 -> 61 -> 79 (all also pass with system site-packages hidden).
