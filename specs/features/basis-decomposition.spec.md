# Feature SPEC — Basis Selection and Wavelet Reconstruction

Статус: Принята, planned `FS-032`

## Назначение и область

Добавить явный выбор базиса для 1D complex `Curve` после стабилизации Fourier product path. Первый
non-Fourier basis — project-owned orthonormal Haar transform. Этот SPEC не меняет принятую Fourier
convention, existing `FourierSpectrum`, epicycle chain или FFT2 raster mode.

## Требования

### BS-FR-001 — Explicit basis choice

Пользователь выбирает basis до decomposition: `FOURIER_EPICYCLE` (default) или `HAAR_WAVELET`.
Result, UI state и diagnostics содержат selected basis и term/selection provenance. Unsupported,
unavailable или invalid basis даёт explicit error/disabled state; silent fallback запрещён.

### BS-FR-002 — Fourier compatibility

Fourier mode переиспользует существующие spectrum, selected coefficients, head-to-tail epicycles и
endpoint contract без изменения sign/normalization/order semantics. `trace == endpoint` относится
только к этому mode и не переносится на wavelet view.

### BS-FR-003 — Haar reconstruction

Haar mode принимает bounded finite curve samples, публикует immutable analysis terms с scale/location
provenance и строит reconstruction из explicitly selected terms. Constant, impulse, step и small
curve fixtures проверяют exact/declared-tolerance synthesis; input/output budgets и non-finite values
fail closed.

### BS-FR-004 — Honest animation semantics

Animation Haar показывает activation/order of scale-location terms and the resulting partial curve.
Она не рисует rotating circles, не называет terms frequencies и не заявляет endpoint-trace equivalence.
Fourier epicycle view и Haar reconstruction view имеют distinct accessible labels.

### BS-FR-005 — Comparison boundary

Для одного source curve UI допускает user-requested side-by-side metrics/provenance, но не объявляет
один basis universally better без заданной metric, fixture class и measured evidence. Other wavelet
families и learned bases требуют отдельного SPEC/ADR/stage.

## Acceptance

- BS-AC-001: basis selector сохраняет явный selection и never silently changes it on error/restart.
- BS-AC-002: Fourier fixture сохраняет существующую coefficient/endpoint parity.
- BS-AC-003: Haar analysis/synthesis проходит declared fixture/tolerance matrix и bounded failure cases.
- BS-AC-004: component/live desktop path различает labels and geometry of Fourier epicycles from Haar
  term reconstruction.
- BS-AC-005: full/static/performance/overlay evidence records selected basis, environment and caveats.

## Планируемая трассировка

Stage `FS-032`; behaviors `BH-BASIS-SELECT-001`, `BH-WAVELET-RECONSTRUCTION-001`.
