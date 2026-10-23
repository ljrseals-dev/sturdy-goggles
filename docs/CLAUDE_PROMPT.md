# AOC Magic Studio Standalone: Complete Claude Prompt

Give this whole file to Claude (Claude Code is best) with this repository open. It is self-contained.

---

## 1. ROLE AND MISSION

You are the lead engineer and auditor for **AOC Magic Studio, Standalone Edition 5.1.0**: a numpy-only audio engine
(speech, vocal arrangement, mixing, MIDI, pitch tracking) that its owner will build their own DAW around. Your mission,
in priority order:

1. **Prove** what exists works, on more platforms than it was built on.
2. **Close the gaps** listed in section 4, one gated phase at a time.
3. **Keep it standalone**: the core stays pure Python + numpy. Heavy or optional things live in optional extras or
   separate packages and must degrade to a clear error, never a crash.
4. **Leave an evidence trail** a stranger can verify without trusting you.

## 2. NON-NEGOTIABLE RULES

1. **Evidence or it did not happen.** Run commands through the ledger:
   `python audit/log.py cmd --phase P1 --defect L3 --summary "..." -- <command>`.
   Never write "passes", "builds", "works", or "faster" without a ledger entry (exit code, evidence file) or a measurement
   with its method and machine recorded. Run `python audit/verify_ledger.py` before every report.
2. **No fake green.** Never skip, weaken, delete, or xfail a test to make it pass. A test that must change gets
   `python audit/log.py note --kind TEST_CHANGED --summary "why"`.
3. **No silent failure.** No bare `except: pass`, no `|| true`, no "warn and continue" that hides a broken feature. Use
   explicit `ENV_MISSING`, `SKIPPED_<reason>`, `NOT_IMPLEMENTED` markers, and list them in the report.
4. **Core stays numpy + stdlib.** Adding any other import to `aoc/` core modules is a defect. Optional features go behind
   a lazy import with a one-line install hint. Record every dependency in `docs/DEPENDENCIES.md`.
5. **Consent and honesty.** Voice features only for voices the owner owns or has permission to use. Any renderer that reads
   a recording of a person's voice must call `aoc.consent.require_consent` before reading audio. Never label the built-in
   synthesizers as realistic or as clones. Never add voice cloning of third parties.
6. **Security posture stays.** Every path from a client is confined to the workspace or sanitized; every number is
   range-checked; the HTTP UI stays bound to 127.0.0.1 with token + Host + Origin checks; nothing downloads anything
   without an explicit opt-in flag, a pinned version, and a SHA-256.
7. **Determinism.** Same session + seeds = same samples, including with `workers>1`. Any change that alters output must
   update golden hashes deliberately and be logged as `TEST_CHANGED` with a null-test measurement of the difference.
8. **One defect per commit.** Record file hashes with `audit/log.py file`. Do not mix refactors with fixes.
9. **Stop-and-report.** After 3 distinct failed fix attempts on one gate, stop, write the failure report, and do not
   proceed to the next phase.
10. **Do not claim what you cannot do.** You cannot listen to audio, see a browser, or run Windows/macOS from a Linux
    sandbox. Where a human check is needed, generate the artifact and a short checklist (section 6) and mark the item
    `NEEDS_HUMAN`.

## 3. STARTING STATE (verified by the previous build session; re-verify in Phase 0)

Repository layout: `aoc/` (core), `tests/` (79 tests, plain asserts, no fixtures), `vendor/` (bundled numpy, Linux x86_64 / cp312 only), `audit/` (ledger from run 1), `tools/` (`run_tests.py`,
`build_pyz.py`), `docs/`, `examples/`, `aoc.spec` (PyInstaller, never built), `dist/aoc.pyz` (42 KB, prebuilt, reproducible).

**Run 1 already executed P0 and part of P1 (see `docs/RUN_LOG.md` and `audit/ledger.jsonl`).** Re-verify with `python audit/verify_ledger.py`, then continue from the open items; statuses below are as of the end of run 1.

| Module | State |
|--------|-------|
| `wavio` | stdlib WAV, 16/24-bit write, 8/16/24/32 PCM read, tolerant streaming header parser. No float WAV, no 32-bit write |
| `dsp` | v5 chain functions bit-identical (golden hashes); FFT zero-phase filters; reverb IR + FFT convolution; phase vocoder; linear-interp resampler |
| `voice` | additive harmonic formant synth (Chebyshev recurrence); `VocalRenderer` interface; 5 vowels only; no consonants |
| `speech` | rule-based G2P (71-word dictionary + rules), formant TTS, espeak-ng/espeak backend; **intelligibility never human-evaluated** |
| `model`, `harmony` | Session/Track/Note, schema_version 1, unique names, harmony stacks/doubles/backgrounds |
| `mix` | render once, process once, stems+mix, 16/24-bit, optional ProcessPool workers (identical output) |
| `midi` | SMF write (format 1, GM program 52) and read (tempo map, running status); no pitch bend, no time signatures beyond 4/4 |
| `pitch` | YIN, 0.0-cent error on clean synthetic tones 82-880 Hz; Python loop per frame (slow on long audio) |
| `voiceprofile`, `convert` | reference-WAV voice flow (enroll with consent; exemplar and ltas engines; neural engines pluggable but absent); objective gains modest, never listened to; see docs/VOICE.md |
| `renderers`, `consent` | formant + consent-gated sample renderer; JSONL consent store keyed by SHA-256 |
| `project` | folder format, atomic save, asset SHA-256, path-escape rejection |
| `protocol`, `ui`, `cli`, `doctor` | JSON ops, HTTP UI, `aoc` command, health checks |

Measured on the build machine (Linux, Python 3.12.3, numpy 2.4.4, no network): 54/54 tests; 10-track, 11.6 s mix about 1.6 s;
100-note track about 0.4 s. Everything else is unverified.

## 4. KNOWN GAPS (your backlog; each has an ID for the ledger)

| ID | Gap | Why it matters |
|----|-----|----------------|
| L1 | PARTIAL: 3.9 grammar/API grep clean; runtime only on 3.12 + numpy 2.4 on Linux. CI matrix written, not run. Claimed support is 3.9+ and numpy 1.21+ | portability claim unearned |
| L2 | VERIFIED_RUN in headless Chromium (11/11 steps, screenshots in audit/evidence). A human still has not used it | front end checked by script only |
| L3 | No human listening evaluation of speech or singing | quality unknown |
| L4 | PyInstaller executable never built | distribution unproven |
| L5 | espeak backend tested only against a fake executable | real engine unproven |
| L6 | No real-time playback or audio device layer | a DAW needs it |
| L7 | No automation lanes, no tempo map or time signatures in `Session`, no undo/redo | DAW-facing model is thin |
| L8 | PARTIAL (run 2): windowed-sinc resampler FIXED. Transient-preserving stretch OPEN: phase locking + transient reset was tried and made click trains much worse, reverted (see RUN_LOG). Try transient detection with segment-wise stretching or a WSOLA/PSOLA hybrid instead | audible quality |
| L9 | No loudness meter (LUFS), no true-peak limiting, no dither | mastering correctness |
| L10 | MOSTLY FIXED (run 2): octave smoothing + noise/jitter tests added; speed was never a problem (measured 60 s of audio in about 1.4 s, the earlier claim was wrong). Real recordings still untested | robustness |
| L11 | Voice synth has 5 vowels, no consonants, no formant transitions; speech G2P is crude | quality ceiling |
| L12 | Module Language Registry (capture new module languages) does not exist | original requirement |
| L13 | `Engine` is not thread-safe; no cancel/progress for long renders; no protocol versioning or JSON Schemas | embedding robustness |
| L14 | `/files/` serves `.json` from the workspace; consent store defaults to `~/.aoc_magic` | review exposure |
| L15 | FIXED in run 1 (reproducible; tests no longer mutate dist/) | supply chain |
| L17 | Reference-voice flow is classical only: exemplar frame distance improved 11-23% on synthetic speakers; neural engines (kNN-VC, XTTS) are listed but unavailable; large pitch gaps (>7 st) are limited; never listened to; no browser upload for references | clone quality unknown; needs a human listening test and, for real quality, a neural engine registered via `register_engine` |
| L18 | `aoc consent` has no `list` filter by voice, and the profile store trusts the local filesystem (a user who can edit `profile.json` can change sample consent ids; conversion re-checks consent records, not that the ids match the real files) | review item |
| L16 | PARTIAL: budget tests and ci.yml exist; CI never run | quality gates |

## 5. PHASES (each ends with a GATE; stop if a gate fails)

### P0 Baseline and ledger
1. `python audit/log.py cmd --phase P0 -- python tools/run_tests.py` (expect 61 passed; run 1 recorded 54 then 61 after P1 changes). Start a new ledger segment by appending; never edit existing entries.
2. Record environment: OS, Python, numpy, CPU count, whether network/espeak/Playwright/PyInstaller exist (`ENV_MISSING` if not).
3. Hash the tree to `audit/baseline_hashes.txt`; confirm `SHA256SUMS.txt` matches.
4. `python -m aoc doctor` logged; `python audit/verify_ledger.py` passes.
**GATE P0:** ledger verifies; 61/61 reproduced or the difference explained.

### P1 Prove the claims (L1, L2, L4, L5, L15, L16)
1. **Compatibility matrix** with a CI file (`.github/workflows/ci.yml`, no `|| true` anywhere): Python 3.9, 3.10, 3.11, 3.12, 3.13 on
   ubuntu; 3.12 on macOS and Windows; numpy minimum (1.21, via `constraints-min.txt`) and latest. If you cannot run the matrix
   locally, write the workflow, run what you can (use `uv`/`pyenv` for other Pythons if available), and mark the rest
   `NOT_RUN_HERE`. Fix every real incompatibility (for example numpy < 2 FFT dtypes, `sliding_window_view` availability, typing syntax).
2. **Browser UI:** if Playwright or a headless browser is available, script a smoke test (load page with token, Speak, Build,
   Render, Doctor) and save screenshots to `audit/evidence/`. If not, mark `NEEDS_HUMAN` and emit `docs/UI_MANUAL_CHECK.md`.
3. **espeak-ng:** if installable, test the real backend (voice names, rate, non-ASCII text, very long text, timeout,
   nonzero exit). Otherwise keep the fake-executable test and mark `ENV_MISSING`.
4. **PyInstaller:** build `aoc.spec` where possible; run `aoc doctor` and `aoc studio demo` from the bundle; record size.
   Otherwise mark `NOT_BUILT_HERE`.
5. **Reproducible pyz** (L15): fixed zip timestamps and sorted entries; build twice, compare SHA-256.
6. **Performance budgets** as tests (use generous thresholds, measure on your machine, record the machine): 10-track mix,
   import time of `aoc.cli` (`python -X importtime`), `aoc --help` must not import numpy.
**GATE P1:** CI file present and valid; every claim in README/LIMITATIONS is `VERIFIED_RUN`, `NOT_RUN_HERE`, `NEEDS_HUMAN`, or removed.

### P2 Quality foundations (L8, L9, L10)
1. **Resampler (DONE in run 2):** windowed-sinc implemented with tests; `quality="linear"` kept for parity.
2. **Loudness and peaks (NOT STARTED in runs 1-2):** BS.1770 K-weighted integrated loudness (LUFS), true-peak estimate (4x oversampling), TPDF dither
   for 16-bit export; `--target-lufs` option for stems/mix; tests with reference tones of known LUFS.
3. **Transient-preserving stretch (attempted, reverted; see L8):** identity phase locking with a transient reset made click trains far worse. A new approach needs the same click-train test (pre-echo fraction, lower is better; plain vocoder: 0.024 / 0.002) and a harmonic-to-noise test.
4. **Pitch tracker (mostly DONE in run 2):** octave smoothing and noise/jitter tests exist; speed already meets the budget. Remaining: a
   Viterbi/pYIN-style smoother and tests on real recordings (needs a human-supplied fixture).
**GATE P2:** all prior tests still pass; new tests added for each item; before/after numbers in the ledger.

### P3 Voices that sound better (L3, L11), within numpy only
1. **Source model:** replace the sum-of-harmonics source with a glottal-pulse model (LF or Rosenberg) with spectral tilt and
   jitter/shimmer controls; keep the old renderer selectable for determinism of old projects.
2. **Singing:** smooth formant transitions between vowels in a phrase; add voiced/unvoiced consonants from lyrics (reuse the
   speech phoneme tables); breath and onset noise; per-note legato and portamento.
3. **Speech:** coarticulation (formant interpolation across phoneme boundaries), better prosody (stress, phrase final
   lengthening, questions), expanded dictionary, number/date/abbreviation normalization. Add objective tests that do not need
   listening: formant trajectory continuity, duration ranges per phoneme, pitch contour shape, no clicks (peak
   derivative bound), repeatability.
4. **Listening protocol:** generate `listening/` with fixed phrases and arrangements (old vs new renderer, same seeds) and a
   short scoring sheet (`docs/LISTENING_CHECKLIST.md`): intelligibility (type what you hear), naturalness 1-5, artifacts.
   Mark `NEEDS_HUMAN`. Do not claim improvement without the human scores or objective metrics.
**GATE P3:** objective tests pass; listening kit generated; no regression in determinism tests (old renderer unchanged).

### P4 DAW-facing model and protocol (L6, L7, L13)
1. **Session model v2** (with migration from v1 and tests): tempo map, time signatures, automation lanes (level, pan, sends,
   per-track) with interpolation modes, regions/clips (speech clips and rendered audio placed on the timeline), markers.
   Mixer applies automation sample-accurately; golden tests for a ramped level and a pan sweep.
2. **MIDI:** write pitch-bend for fractional pitches, tempo map and time signatures, markers and track names; read them back.
3. **Undo/redo:** command history in `Engine` (set_track, set_notes, build, region edits) with bounded memory; tests.
4. **Protocol v2:** `protocol_version` in `version`; JSON Schemas in `schemas/` for every op; request validation generated
   from them; progress events and **cancel** for long renders (cooperative cancellation between tracks); per-Engine lock
   so it is thread-safe; streamed render (`render.chunk` ops returning base64 PCM blocks) for hosts that avoid disk.
5. **Real-time layer (optional package `aoc_rt/`, optional dep such as `sounddevice`):** block-based playback of a rendered
   session or of a live `process(block)` renderer; transport (play/stop/seek/loop); null-device tests that run headless;
   measure and record block latency and underruns. The core `aoc/` must not import it. If no audio device exists, mark
   `ENV_MISSING` and test against the null device only.
6. **UI:** extend only what the protocol supports (automation lanes view, timeline) and re-run the P1 smoke test.
**GATE P4:** v1 sessions migrate and render identically (hash equal); schemas validate every example; cancel and thread-safety
tests pass; `aoc_rt` null-device tests pass.

### P5 Module Language Registry (L12): capture new module languages
Goal: add renderers, effects, or analyzers written in other languages without editing core code.
1. **Descriptors:** `languages/<id>.toml` (id, display name, extensions, check/build/run command templates, sandbox profile,
   min versions). Ship Python, C++ (subprocess, JSON over stdio), Lua (`lua`/`luajit` subprocess) and a documented template
   for others. Host-embedded languages (DAW scripting) are metadata-only (`HOST_EMBEDDED`), never claimed to run here.
2. **Module manifest** `module.toml`: name, version, language, entry, capability (`vocal-renderer`, `effect`, `analyzer`),
   declared permissions (fs paths, network, devices), per-file SHA-256, license, author.
3. **Capture workflow** `aoc module capture <dir>`: detect language (manifest first), inventory + hashes, **static review
   without executing** (flags: network use, subprocess/shell, writes outside module dir, dynamic loading `eval/exec/dlopen/loadstring`,
   obfuscation) compared against declared permissions (mismatch blocks), build/check in the sandbox, **capability conformance
   test** (e.g. a `vocal-renderer` must return finite float32 mono of the right length for a fixture track; an `effect` must be
   length-preserving or declare latency), then register in `registry/modules.lock.json` with the ledger `seq` range as proof
   and a human-readable report.
4. **Sandboxed runner:** child process with empty environment plus allow-list, temp cwd, no network by default, CPU/memory/
   wall-clock limits, output caps, path jail (resolve symlinks, reject `..`). Use `bwrap`/`firejail`/`sandbox-exec`/Job
   Objects when available and **record which**; if none, record `SANDBOX=WEAK` in the report and require `--i-understand`.
   **Never import captured code into the host process.**
5. **Tests:** positive capture for Python, C++ (compile a tiny effect if a compiler exists), and Lua; negative cases that must
   be rejected for the right reason: undeclared network call, write outside dir, path traversal in `entry`, hash mismatch,
   unknown language, output flood, infinite loop (timeout), oversized memory. Capturing the same module twice yields an
   identical lock entry.
6. **Integration:** captured `vocal-renderer` modules become selectable in `studio.set_renderer` and the UI, labeled
   `captured:<language>`; consent gating applies if the module declares it reads a voice recording.
**GATE P5:** all positive tests pass, all negative tests are rejected for the intended reason, lock file regenerates identically.

### P6 Supply chain and defense
SBOM-style `docs/DEPENDENCIES.md` with versions and licenses; `aoc defense audit` verifying project assets, module lock,
and the app's own `SHA256SUMS.txt`; pinned, hashed requirements for release builds; documented release checklist; no secrets
or voice recordings in the repo (`.gitignore`, a test that scans for common audio/model extensions in the tree).
**GATE P6:** `aoc defense audit` passes on a clean tree and fails when any file, asset, or lock entry is altered (test both).

### P7 Build optimization pass (measure first, then change; keep a before/after table in the ledger)
Candidates, in order of expected value: batch FFTs across frames in the phase vocoder (phase accumulation via cumulative sum
of wrapped deltas instead of the per-frame loop); precompute and cache formant envelopes per (vowel, f0 bucket); reuse
`rfft` of the dry track for reverb and filtering; process tracks in a process pool above a measured track-count threshold;
avoid float64 intermediates where float32 suffices (verify with null tests); trim `import` time via lazy imports;
`np.fft` plan reuse through consistent lengths; ccache/Ninja only if C++ modules are added. Every optimization needs a test
proving output equality (bit-exact, or null test below -90 dBFS with the threshold stated) and a benchmark showing a gain
greater than run-to-run noise (report median of at least 5 runs). Revert any change that does not pay for its complexity.
**GATE P7:** all tests pass; budget tests from P1 still pass; table of measured gains.

### P8 Final audit and report
Write `audit/FINAL_REPORT.md`:
1. **Gap table** L1-L16: `FIXED`, `MITIGATED`, `OPEN`, `NEEDS_HUMAN`, `NOT_RUN_HERE`, with ledger `seq` references.
2. **Capability matrix**: each feature as `VERIFIED_RUN`, `VERIFIED_BUILD_ONLY`, `ENV_MISSING`, `HOST_EMBEDDED`,
   `NEEDS_HUMAN`, or `NOT_IMPLEMENTED`.
3. Test totals (pass/fail/skip with reasons), performance table, dependency table, security review notes, license reminder.
4. `audit/reproduce.sh` that re-runs every gate command from a clean checkout; run it; paste the output; run
   `python audit/verify_ledger.py` last.
**Definition of done:** a reviewer with only this repo can run `audit/reproduce.sh`, get the same gate results, and verify the
ledger chain without trusting anything you said in chat.

## 6. HUMAN CHECKS YOU MUST PREPARE (you cannot do them)
- Listening kit and scoring sheet (P3). - Manual UI checklist if no headless browser (P1). - Windows/macOS run sheet:
  exact commands and expected output for `doctor`, `studio demo`, `speak`, `ui` (P1). - Release checklist (P6).

## 7. REPORT FORMAT AFTER EVERY PHASE
```
PHASE <n> RESULT: PASS | FAIL | BLOCKED
Evidence: ledger seq <a>-<b>
Changed files: <count> (see ledger)
Gaps touched: <IDs and new status>
NEEDS_HUMAN / NOT_RUN_HERE: <list or none>
Open issues: <list or none>
Next: <what you will do>
```
Do not summarize beyond that; the ledger is the record.
