# JSON protocol

One request per line on stdin (`aoc serve --workspace DIR`) or via `aoc.protocol.Engine(workspace).handle(dict)`.
Response: `{"ok": true, "result": {...}}` or `{"ok": false, "error": {"code": "...", "message": "..."}}`; an `id` in the
request is echoed. All paths are **relative to the workspace** and cannot escape it. Request lines are capped at 1 MB.

Error codes: `bad_request`, `out_of_range`, `bad_path`, `not_found`, `bad_note`, `unknown_op`, `invalid`, `empty`,
`no_project`, `consent_required`, `too_large`, `bad_json`, `internal` (no traceback is ever returned).

| op | fields (defaults) | result |
|----|-------------------|--------|
| `ping`, `version`, `doctor`, `engines.list` | | |
| `speech.synth` | `text`, `engine` (auto/builtin/espeak), `rate` (1.0; 0.4-2.5), `pitch_hz` (118; 60-300), `character` (false), `bits` (16/24), `out` ("speech.wav"), `add_to_project` | `file, sr, duration_s, engine` |
| `studio.build` | `lead` (notes) **or** `midi` (path, `track`, `poly` reject/top), `parts` (4; 2/3/4/6), `key` ("C"), `mode` (major/minor), `doubles` (0-8), `bg` (airy/soulful/rhythmic/powerful/none), `tempo` (20-300) | session summary |
| `studio.state` | `include_notes` | session |
| `studio.set_track` | `name`, `set`: `level_db -60..24, pan -1..1, reverb 0..1, echo 0..1, echo_ms 20..2000, delay_ms -500..500, timing_ms 0..100, tuning_cents 0..100, vibrato_depth_cents 0..100, vibrato_rate_hz 0..12, breath 0..1, brightness 0..1, mute, solo, seed` | changed fields |
| `studio.set_notes` | `name`, `notes` | `note_count` |
| `studio.set_renderer` | `name` (formant/sample), `path`, `root_midi` | needs a consent record for `sample` |
| `studio.render` | `out_dir` ("render"), `bits`, `normalize` (true), `stems` (true), `workers` (0-8) | `files, duration_s, sr, renderer` |
| `midi.export` | `out` ("arrangement.mid") | `file` |
| `midi.import_lead` | `path`, `track`, `poly` | `tempo_bpm, notes` |
| `pitch.track` | `path` (.wav), `quantize` | `notes` |
| `project.create/open/save/verify` | `dir`, `name` | |
| `voice.enroll` | `name`, `samples` (workspace WAV paths, 1-20), and either an existing consent record or `attested: true` + `owner` + `scope` | `name, voiced_seconds, f0, engines_ok, warnings` |
| `voice.list` / `voice.show` / `voice.delete` / `voice.engines` | `name` (show, delete; optional for engines) | profiles / one profile / `deleted` / engine availability |
| `voice.convert` | `path` (WAV), `voice`, `out` ("converted.wav"), `engine` (auto/exemplar/ltas), `pitch_strength`, `timbre_strength` (0-1) | `file, provenance, engine, info` (writes `<out>.aoc.json`) |
| `speech.synth` with `voice` | as `speech.synth` plus `voice`, `voice_engine`, `pitch_strength`, `timbre_strength` | adds `voice, tts_engine, provenance` |
| `consent.add` | `file`, `owner`, `scope`, `attested: true` | `consent_id` |

A note is `[pitch, start_s, dur_s, vel=0.8, lyric="ah"]` or an object with those keys. Pitch 0-127 (fractional = cents),
start >= 0, dur 0.01-60, vel 0-1, lyric up to 16 characters, at most 5000 notes per request.
