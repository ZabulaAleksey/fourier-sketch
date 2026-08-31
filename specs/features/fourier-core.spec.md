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

### FC-FR-008 — Bounded curve simplification

Project-owned iterative Douglas–Peucker принимает immutable ordered `Curve` до resampling и
возвращает новый source-subsequence с retained source indices, тем же `closed` и explicit tolerance.
Tolerance finite `>=0`; zero удаляет только exact collinear/duplicate interior points. Open curve
сохраняет endpoints. Closed curve сохраняет index `0`, выбирает farthest-from-start second anchor с
lowest-index tie-break, упрощает две cyclic arcs и не добавляет duplicate seam sample. Source
ограничен 250 000 points, distance-evaluation budget explicit/bounded, cancellation cooperative;
budget/cancel не публикуют partial result.

Metrics называют measured source-vertex-to-retained-segment deviation, point/length reduction и не
выдают его за Hausdorff/Fréchet distance или универсальное улучшение shape/Fourier quality.

### FC-FR-009 — Deterministic adaptive sampling

Project-owned adaptive sampler принимает immutable ordered `Curve`, exact output budget `N` и
finite curvature weight `0..100`. После adjacent-duplicate cleanup (и удаления explicit duplicate
closed seam) discrete vertex curvature равна unsigned turning angle, normalized by `π`. Open
endpoints имеют curvature `0`; closed vertices используют cyclic neighbors.

Каждый positive-length source segment получает positive density
`length * (1 + weight * mean(endpoint_curvature))`. Равномерные targets в cumulative density дают
ровно `N` ordered samples; open endpoints и closed start/index `0` назначаются точно, closed seam не
дублируется. `weight=0` или all-zero curvature используют заранее принятую uniform arc-length policy
с explicit provenance. Zero/non-finite total length отклоняется typed; silent fallback запрещён.

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
- FC-AC-006: known/property fixtures подтверждают source subsequence/order/topology, deterministic
  closed seam, tolerance bound, immutable source и controlled invalid/budget/cancel failure.
- FC-AC-007: known/property fixtures подтверждают exact sample budget, deterministic curvature/
  segment density, open endpoints, closed start/closure, finite ordered interpolation, immutable
  source и explicit uniform provenance для zero adaptive signal.

## Планируемая трассировка

Stages `FS-001`–`FS-004`, `FS-009`, `FS-027`, `FS-028`; Behaviors `BH-FOURIER-001`,
`BH-HARMONICS-001`, `BH-SIMPLIFY-001`, `BH-ADAPTIVE-001`.
