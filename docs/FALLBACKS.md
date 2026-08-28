# Fallbacks Fourier Sketch

Этот документ содержит только project-specific delta к глобальной Fallback Policy.

## 1D Fourier transform backends (FS-002)

| Поле | Контракт |
|---|---|
| Primary working path | явный вызов `fft_dft` (NumPy) |
| Correctness oracle | отдельный явный `reference_dft`, `N ≤ 2048` |
| Primary budget | `1 ≤ N ≤ 262144`, finite complex samples |
| Failure signal | `DomainValidationError` для input/budget/result; `FourierBackendError` для backend failure |
| Retry | отсутствует: local deterministic operation не retry-ится |
| Automatic fallback | запрещён |
| Degraded result | отсутствует; incomplete/non-finite spectrum не возвращается |
| Provenance | `FourierSpectrum.source_metadata["backend"]` |
| Recovery | исправить input/dependency и повторить выбранную operation явно |
| Tests | backend failure, budgets, non-finite input/result, reference/NumPy parity |

Reference implementation не заменяет недоступный NumPy backend автоматически: при большом input
это нарушило бы resource budget, а при backend defect скрыло бы фактическую причину отказа.
