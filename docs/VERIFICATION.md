# What was run (Linux, Python 3.12.3, numpy 2.4.4, no network)

`python tools/run_tests.py`: **54 passed, 0 failed** across DSP (including golden hashes proving the v5 chain functions are
bit-identical), speech and voice, arrangement and harmony, mixer (empty tracks, duplicate and unsafe names, single render,
determinism, parallel identity, partial re-render, bit depth), MIDI (round trip, tempo map, running status, polyphony), pitch
(accuracy 82-880 Hz, weak fundamental, silence/noise), consent and sample renderer, projects (tamper and path-escape
detection, atomic save), the JSON protocol (validation and confinement), the HTTP UI server (token, Host, Origin, size,
traversal), the CLI (commands, exit codes, closed pipe), the .pyz build, and both examples.

Measured: mixer 6.9 s -> 1.6 s after the FFT-size and single-pass-EQ optimizations and the Chebyshev harmonic recurrence
(same output hashes between runs); pitch tracker error 0.0 cents on synthetic tones after fixing a correlation-direction bug.
