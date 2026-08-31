# Roadmap Fourier Sketch

Roadmap — краткий индекс. Полный scope/PASS contract каждого этапа находится только в
`prompts/STAGES.md`. Status подтверждается `docs/AI_STATUS.md`, а не этим списком.

## Выполнено

| Stage | Результат | Статус |
|---|---|---|
| `FS-000` | Repository, project overlay, Python/tooling scaffold, smoke evidence | `completed` |
| `FS-001` | Immutable Domain Model, typed validation, public imports | `completed` |
| `FS-002` | Complex conversion, reference/NumPy DFT and IDFT | `completed` |
| `FS-003` | Fourier Spectrum energy and deterministic ordering views | `completed` |
| `FS-004` | Partial Reconstruction and metrics | `completed` |
| `FS-005` | Epicycle Mathematics and endpoint equivalence | `completed` |
| `FS-006` | Diagnostic Matplotlib Epicycle Renderer | `completed` |
| `FS-007` | Freehand Input | `completed` |
| `FS-008` | First live freehand-to-trace MVP | `completed` |
| `FS-009` | Arc-Length Parameterization | `completed` |
| `FS-010` | Validated image input, grayscale, threshold | `completed` |
| `FS-011` | Explicit threshold-boundary and Canny edge diagnostics | `completed` |
| `FS-012` | Dominant contour to normalized curve and diagnostic endpoint trace | `completed` |
| `FS-013` | Live image-to-epicycle-trace MVP | `completed` |
| `FS-014` | Explicit Lee skeletonization diagnostic | `completed` |
| `FS-015` | Deterministic traversal-neutral skeleton graph | `completed` |
| `FS-016` | Multiple Components / PiecewiseCurve | `completed` |
| `FS-017` | Forced Continuous Routing | `completed` |
| `FS-018` | Discontinuous Fourier Mode | `completed` |
| `FS-019` | Discontinuity Spectrum Analysis | `completed` |
| `FS-020` | Separate 2D Fourier Image Mode | `completed` |
| `FS-021` | PySide6 GUI with central Epicycles view | `completed` |
| `FS-022` | Data/image/GIF and capability-gated MP4 export | `completed` |
| `FS-023` | Numerical, performance, cancellation and source-package hardening | `completed` |
| `FS-024` | Read-only frequency-keyed Harmonic Inspector | `completed` |
| `FS-025` | Frequency Solo | `completed` |
| `FS-026` | Harmonic Build-Up Animation | `completed` |
| `FS-027` | Curve Simplification | `completed` |
| `FS-028` | Adaptive Sampling | `completed` |
| `FS-029` | Better Single-Stroke Optimization | `completed` |
| `FS-030` | Actual-state canonical-circle Educational Mode | `completed` |
| `FS-032` | Explicit Fourier/Haar selection and bounded wavelet reconstruction | `completed` |

## Текущий этап

`FS-023` завершён, интегрирован в `main` и опубликован в `origin/main`. Selected record `FS-024`
Harmonic Inspector завершён, интегрирован в `main` и опубликован в `origin/main`; independent review
GO. `FS-025` Frequency Solo завершён, интегрирован в `main` и опубликован в `origin/main`; selected
record `FS-026` Harmonic Build-Up Animation завершён, интегрирован в `main` и опубликован в
`origin/main`; independent review GO. Selected record `FS-027` Curve Simplification завершён,
интегрирован в `main` и опубликован в `origin/main`; independent review GO. Selected record `FS-028`
Adaptive Sampling завершён, интегрирован в `main` и опубликован в `origin/main`; independent review
GO. Selected record `FS-029` Better Single-Stroke Optimization завершён, интегрирован в `main` и
опубликован в `origin/main`; independent review GO. Selected record `FS-030` Educational Mode
завершён, интегрирован в `main` и опубликован в `origin/main`; independent review GO. FS-032
завершён и validated на feature branch с independent re-review GO; разрешённый МДП ещё выполняется.
FS-031 не начат.

## Image-to-curve pipeline

| Stage | Результат |
|---|---|

## Product shell, export and hardening

| Stage | Результат |
|---|---|
| `FS-021` | PySide6 GUI with central Epicycles view |
| `FS-022` | Data/image/GIF and capability-gated MP4 export |
| `FS-023` | Numerical, performance, cancellation and packaging hardening |

## Optional extensions

Эти stages не являются обязательными для milestone `FS-023`; `FS-025`–`FS-030` опубликованы, а
`FS-032` завершён на feature branch и ожидает МДП.

| Stage | Результат |
|---|---|
| `FS-025` | Frequency Solo |
| `FS-026` | Harmonic Build-Up Animation |
| `FS-027` | Curve Simplification |
| `FS-028` | Adaptive Sampling |
| `FS-029` | Better Single-Stroke Optimization |
| `FS-030` | Educational Mode |
| `FS-032` | Basis Selection and Haar Wavelet Reconstruction |

## Mobile expansion

| Stage | Результат | Статус |
|---|---|---|
| `FS-031` | Offline Android finger/stylus drawing → Fourier vectors → epicycle animation | `planned` |

## Milestones

- M1: `FS-005` — mathematics proves endpoint equivalence.
- M2: `FS-008` — freehand live E2E.
- M3: `FS-013` — image live E2E.
- M4: `FS-022` — desktop/export live E2E.
- M5: `FS-023` — hardened core product.
- M6: `FS-031` — installable offline Android touch-to-epicycles MVP.
