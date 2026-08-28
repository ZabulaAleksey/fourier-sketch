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

## Diagnostic rendering (FS-006)

| Поле | Контракт |
|---|---|
| Interactive path | Matplotlib window с `EpicycleTimeline` |
| Headless path | отдельный явный `--headless` через Agg и тот же timeline/frame |
| Failure signal | controlled CLI exit `2`; validation/I/O error без partial success |
| Retry | отсутствует для deterministic render/path failure |
| Automatic fallback | interactive → headless или headless → другой renderer запрещён |
| Partial artifact | temporary sibling удаляется; reserved empty destination удаляется при failure |
| Recovery | выбрать headless явно либо исправить destination/dependency и повторить |

Agg не является silent fallback: пользователь/automation выбирает `--headless` явно. Недоступный
Matplotlib останавливает entry point; Pillow/transitive codec не используется как альтернативный
project image/export backend.
