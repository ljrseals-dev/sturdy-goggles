# Voice flow: reference WAV -> profile -> speech/conversion (what it is, and what it is not)

This follows the AOC v3/v5 flow: a reference WAV (or several) goes in; text-to-speech output, or a recording you supply, is
converted toward that voice. v3/v5 did the conversion with neural engines (kNN-VC, XTTS; they need torch and model weights).
This standalone build has **no neural engines**. It ships two classical numpy engines and a registry where a neural engine can be plugged in.

> **It is not a neural clone.** It moves pitch and spectral timbre toward the reference. Measured gains are modest (below), nobody has
> listened to the results, and a person who knows the real voice will not be fooled. Use it with voices you own or have permission to use.

## Use
    aoc voice enroll --name me --sample me1.wav --sample me2.wav --owner "My Name" --scope "my own projects" --attest
    aoc speak "Hello there" --out hello.wav --voice me            # TTS at the profile's pitch, then conversion; writes hello.wav.aoc.json
    aoc convert recording.wav --voice me --out converted.wav
    aoc voice list | show NAME | delete NAME | engines
Protocol ops: `voice.enroll`, `voice.list`, `voice.show`, `voice.delete`, `voice.engines`, `voice.convert`, and `speech.synth` with `voice`.
Profiles live in `~/.aoc_magic/voices` (`$AOC_VOICES`; the protocol uses `<workspace>/voices`).

## Reference recording guidance (enforced where it can be measured)
- Clean speech, one speaker, quiet room, no music or effects. 30 s or more is recommended; **3 s minimum** (the `ltas` engine), **8 s+** for `exemplar`.
- Rejected: under 3 s of speech-level audio, silent or unreadable files, sample rate under 8 kHz, a speech-to-noise-floor range under 12 dB,
  no stable pitch. Warned: 8-16 kHz sample rate, clipping above 0.5% of samples, floor range under 20 dB, under 30 s.
- Any sample rate or channel count is accepted (resampled and downmixed internally).

## Consent and provenance
- Each reference file needs an active consent record (matched by SHA-256) **before its audio is read**. `--attest` records one
  (owner + scope). Revoking a record (`aoc consent revoke ID`) stops conversion with that profile immediately.
- The profile stores no audio: f0 statistics, a mean cepstrum, a bank of up to 8000 per-frame cepstra, and each sample's hash and consent id
  (the bank file is hashed; a modified bank is refused).
- Every converted output gets `<file>.aoc.json` marking it synthetic/converted (engine, profile, consent ids, source and text hashes, UTC time).
  The sidecar can be deleted by anyone; it is a disclosure aid, not a watermark.

## Engines (`aoc voice engines`)
| Engine | What it does | Needs |
|--------|--------------|-------|
| `exemplar` | kNN-VC-style: each source frame's smooth spectral envelope is replaced by the mean of its 6 nearest reference frames (matched on mean-normalised cepstra), keeping the source's excitation, plus pitch transfer | 8 s+ |
| `ltas` | long-term average spectrum matching plus pitch transfer | 3 s+ |
| `knn-vc`, `xtts` | neural engines from v3/v5 | **unavailable** (torch + weights not bundled); `register_engine()` plugs one in and it wins under `auto` |

## Measured on synthetic speakers (`python tools/eval_voice.py`; lower = closer to the target; signal metrics, not listening)
| Target | Output | f0 error (cents) | spectral dist. (dB) | frame distance |
|--------|--------|-----------------|---------------------|----------------|
| low (105 Hz) | raw TTS | -24 | 3.69 | 0.333 |
| | ltas | -14 | **0.21** | 0.375 (worse) |
| | exemplar | -17 | 2.71 | **0.256** |
| mid (150 Hz) | raw TTS | -36 | 2.88 | 0.261 |
| | ltas | 0 | **0.11** | 0.325 (worse) |
| | exemplar | 0 | 2.60 | **0.226** |
| high (215 Hz) | raw TTS | -40 | 2.55 | 0.253 |
| | ltas | 5 | **0.14** | 0.320 (worse) |
| | exemplar | 9 | 2.08 | **0.224** |
`exemplar` improved frame distance by 11-23%; `ltas` matches the average spectrum almost exactly but moves individual frames slightly away.
Timbre-only conversion (same pitch, different vocal tract): frame distance 0.569 -> 0.319 (-44%).

## Known limits
- **Pitch shifts hurt.** A resampling-based shift moves formants and empties the top of the spectrum, so shifts are limited to 7 semitones
  (`max_shift`) and the result is noted. `aoc speak --voice` avoids shifting by synthesizing at the profile's pitch. Converting a recording
  from a very different voice (for example male to female) is poor. Identity phase locking was tried and reverted (see RUN_LOG).
- The envelope swap keeps the source's excitation, so breathiness, glottal quality and speaking style of the source remain.
- Phonetic coverage of a short reference limits `exemplar`; unseen sounds borrow the closest reference frames.
- No browser upload for references (it needs a safe upload path); use the CLI or protocol with files in the workspace.
- Quality is **unverified by ear** (NEEDS_HUMAN). The objective metrics were computed on synthetic speakers made by this package's own
  synthesizer; real recordings of real people have not been tested.
