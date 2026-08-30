# FS-023 hardening evidence

## Environment and measured baseline

- Date: 2026-08-30.
- OS: Windows 10.0.19045; Python 3.12.5; NumPy 2.5.2; PySide6 6.11.2.
- CPU identifier: Intel64 Family 6 Model 140 Stepping 1, GenuineIntel.
- Large transform: `N=65,536`, FFT→IDFT `1.311 s`, maximum round-trip error `2.04e-15`.
- Python-managed peak during transform: `17,050,172` bytes (`tracemalloc`; native NumPy/Qt totals are
  outside this measurement).
- Stress timeline: `K=4096`, `N=4096`, `0.112 s`; previous scalar implementation measured `4.893 s`
  on the same host before optimization.
- Offscreen QPainter median: default K `0.0048 s`, stress K=4096 `0.0501 s`. Cancel request measured
  `2.87e-05 s` under a broad `0.25 s` catastrophic limit. This does not prove
  visible Windows GUI/DPI performance.

`tools/fs023_hardening.py` records the environment, dirty commit state, budgets, measurements and
caveats as versioned JSON. Its broad wall-clock limits detect catastrophic regressions; they are not
marketing or cross-hardware frame-time claims.

## Verification matrix

| Gate | Result |
|---|---|
| Targeted hardening/export/desktop | 43 passed |
| Full pytest | 566 passed in 126.34 s; one pytest-cache permission warning |
| Branch-aware coverage | 76%; configured floor 75% |
| Desktop cancellation | harness `2.87e-05 s` (`<0.25 s` broad limit); real 120-frame GIF worker finishes with no artifact/temp |
| Frozen sync / Ruff / strict mypy | PASS |
| `uv lock --check` / universal tree / `uv pip check` | PASS; 38 packages compatible |
| `pip-audit 2.10.1` | no known vulnerabilities; unpublished project skipped |
| CycloneDX 1.5 export | PASS; 37 dependency components |
| Isolated wheel | build, dependency install, package/resource import and desktop `--help` PASS |

## Packaging decision and residual limits

FS-023 selects the fully runnable frozen source-run path and a recoverable wheel smoke. It does not
select or claim a bundled installer/public release. The repository has no approved project license or
third-party notice bundle; PySide6/shiboken6 redistribution obligations require explicit LGPL/license
compliance work. The lexical path guard still cannot prove that a mapped drive or reparse target is
physically local. No optional FS-024+, Android FS-031 or basis FS-032 work is included.
