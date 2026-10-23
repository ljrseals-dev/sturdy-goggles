# Using it from your own DAW

**In-process (Python host):** see `examples/embed_python.py`. `VocalMixer.process_all()` returns per-track `(n, 2)`
float32 buffers; `mix()` returns the master buffer at `session.sr` (44.1 kHz). Feed them to your own audio callback or
writer. Rendering is offline: render, then play back; do not call it from a real-time audio thread.

**Any language (subprocess):** spawn `python -m aoc serve --workspace DIR` (or `python aoc.pyz serve`) and exchange JSON
lines (`examples/jsonlines_client.py`). Render to WAV in the workspace and load the files in your host.

**MIDI bridge:** `midi.export` writes one track per vocal part (GM program 52, Choir Aahs, channel 10 skipped). Import
it into your DAW as the editable arrangement; use the stems for audio.

**Threading:** `Engine` is not thread-safe; the UI server serializes calls with a lock. Use one Engine per thread or add your own lock.
**Determinism:** same session + seeds = same samples (also with `workers>1`), so you can cache by session hash.
**Replace the voice:** implement `VocalRenderer` (see ARCHITECTURE.md).
