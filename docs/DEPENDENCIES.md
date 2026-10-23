# Dependencies

| Component | Version | License | Where | Notes |
|-----------|---------|---------|-------|-------|
| Python | 3.9+ (tested only 3.12.3) | PSF | system | stdlib only otherwise |
| numpy | >=1.21 required; bundled copy is 2.4.4 | BSD-3-Clause (see `vendor/*/numpy-2.4.4.dist-info/licenses/`) | system, or `vendor/linux-x86_64-cp312/` | the only third-party runtime dependency |
| OpenBLAS (`libscipy_openblas64_`), libgfortran, libquadmath | as built into the numpy 2.4.4 wheel | BSD-3 (OpenBLAS), GPL-3.0 with GCC Runtime Library Exception (libgfortran, libquadmath) | `vendor/*/numpy.libs/` | shipped unmodified with their license texts in numpy's `LICENSE.txt` |
| pytest | optional | MIT | dev only | `tools/run_tests.py` needs no pytest |
| Playwright + Chromium | optional | Apache-2.0 / BSD | dev only | `tools/ui_smoke.py` (headless browser test) |
| PyInstaller | optional, not used here | GPL-2.0 with bootloader exception | dev only | for `aoc.spec` |

No models, no network, no GPU. The bundled `vendor/` folder is specific to Linux x86_64 and CPython 3.12; regenerate it per platform
with `python tools/vendor_numpy.py`. `vendor/<tag>/VENDOR_MANIFEST.json` holds a SHA-256 for every bundled file (checked by `tests/test_vendor.py`).
Review the licenses above before redistributing a bundle.
