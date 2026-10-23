# Architecture

    aoc/
      wavio.py      WAV read/write (stdlib wave; 16/24-bit; tolerant streaming-header parser)
      dsp.py        numpy DSP: FFT zero-phase filters, compressor/limiter/saturator (bit-identical to AOC v5),
                    de-esser, reverb (cached IR + FFT convolution), echo, pan, phase-vocoder time/pitch, character chain
      voice.py      additive harmonic formant synth (Chebyshev recurrence) + VocalRenderer interface + ParametricRenderer
      speech.py     speech: rule-based G2P -> formant synth (builtin), espeak-ng/espeak backend (stdin text, validated args)
      model.py      Note / TrackSettings / Track / Session (schema_version, validation: unique names)
      harmony.py    scale-aware harmonizer, stacks, doubles, backgrounds, build_session()
      mix.py        VocalMixer: render once, process once, stems + mix; optional ProcessPool workers (identical output)
      midi.py       SMF writer/reader (stdlib)
      pitch.py      YIN f0 tracker + note segmentation
      renderers.py  renderer registry: formant (preview) and sample (consent-gated recording of your voice)
      consent.py    consent records (JSONL, SHA-256 keyed, revocable)
      project.py    project folder, atomic save, asset manifest, path-escape rejection
      protocol.py   JSON command engine + JSON-lines server (workspace-confined)
      ui.py         localhost HTTP server + single-page UI
      doctor.py     environment checks
      cli.py        `aoc` command

Design rules: numpy + stdlib only; every user-supplied number is range-checked; every path is confined or sanitized;
nothing downloads anything; deterministic output for a given seed (also with workers); replaceable renderer interface.

Data flow (studio): lead notes -> `build_session` -> `Session` (tracks with notes + settings) -> `VocalMixer`
(renderer.render_track per track -> EQ/de-ess/comp/sat -> level -> reverb/echo sends -> pan) -> sum -> master soft
limiter (+ optional peak normalize) -> WAV/MIDI/session.json.

Writing a renderer: subclass `aoc.voice.VocalRenderer`, implement `render_track(track, sr, tempo) -> float32 mono`
and register it in `aoc/renderers.py::get_renderer`. If it uses a recording of a person's voice, call
`aoc.consent.require_consent(path)` before reading the file.
