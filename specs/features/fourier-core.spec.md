# Feature SPEC — Fourier Core

Статус: Принята, v0.1

## Назначение и область

Определить domain model, complex conversion, DFT/FFT/IDFT, spectrum, coefficient selection,
reconstruction, parameterization и error metrics. Rendering, image decoding и UI не входят.

## Требования

### FC-FR-001 — Domain values

`Point2D` хранит finite `x/y`. `Curve` хранит не менее одной ordered point и явный `closed` flag.
`PiecewiseCurve` хранит не менее одного непустого segment без неявных bridges.

### FC-FR-002 — Complex conversion

Преобразование `Point2D(x, y) ↔ complex(x, y)` должно быть взаимно-однозначным в пределах
floating-point representation и сохранять порядок samples.

### FC-FR-003 — DFT/IDFT

Reference DFT и FFT-backed implementation используют одну formula, normalization и signed
frequency mapping из `docs/MATHEMATICS.md`; inverse восстанавливает N samples.

### FC-FR-004 — Coefficients and spectrum

`FourierCoefficient` предоставляет frequency, complex value, real, imaginary, amplitude и phase.
`FourierSpectrum` фиксирует N, normalization, convention и source metadata без user payload logs.

### FC-FR-005 — Selection/order

Поддерживаются signed, absolute-frequency, amplitude-descending, interleaved
`0,+1,-1,+2,-2,...` и explicit unique frequency set. Selection содержит 1..N coefficients.

### FC-FR-006 — Reconstruction and metrics

Full/partial reconstruction вычисляется из переданного coefficient set. MSE, RMSE, max point
error и normalized error используют документированные formulas и определённое поведение при
нулевой norm reference.

### FC-FR-007 — Parameterization

Arc-length resampling сохраняет open endpoints, closed semantics и order; zero-length input
возвращает typed validation error, а не NaN.

## Численные свойства

- `IDFT(DFT(z)) ≈ z`;
- translation изменяет DC coefficient и не меняет non-DC coefficients сверх tolerance;
- complex scaling масштабирует coefficients;
- FFT-backed result эквивалентен reference DFT;
- full selection reconstructs input; increasing K evaluation reports measured error without
  необоснованного monotonicity claim для любого ordering.

Tolerance задаётся тестом как `atol + rtol * |expected|` и масштабируется с N/fixture; renderer
не определяет численную корректность.

## Ошибки

Empty samples, non-finite values, duplicate explicit frequencies, unknown ordering и invalid K
fail with typed/domain errors. Один sample даёт только stationary DC coefficient.

## Acceptance

- FC-AC-001: analytical constant, circle и impulse fixtures соответствуют convention.
- FC-AC-002: reference/FFT parity и round-trip проходят unit/property tests.
- FC-AC-003: все orderings содержат один и тот же selected set без duplicates.
- FC-AC-004: metric edge cases не возвращают silent NaN/Inf.
- FC-AC-005: math package не импортирует UI/render/imaging modules.

## Планируемая трассировка

Stages `FS-001`–`FS-004`, `FS-009`; Behavior `BH-FOURIER-001`, `BH-HARMONICS-001`.
