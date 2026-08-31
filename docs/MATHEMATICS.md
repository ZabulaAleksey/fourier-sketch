# Математический контракт Fourier Sketch

Этот документ определяет единственную convention для 1D complex parametric curves. Изменение
формул является SPEC/ADR change и требует обновления tests и traceability до implementation.

## Координаты и samples

Плоская точка кодируется комплексным числом:

```text
z = x + i y
```

Для `N ≥ 1` ordered samples:

```text
z[n],  n = 0, …, N-1
t_n = n / N
```

`t` в continuous reconstruction нормализован к периоду `[0, 1)`. Open curve при периодическом
Fourier continuation имеет seam между последним и первым sample; это не скрывается.

## DFT и IDFT

Forward coefficient:

```text
C_k = (1/N) Σ(n=0..N-1) z[n] exp(-i 2π k n/N)
```

Inverse at sample grid:

```text
z[n] = Σ(k∈K_N) C_k exp(i 2π k n/N)
```

Continuous periodic reconstruction:

```text
ẑ(t) = Σ(k∈S) C_k exp(i 2π k t)
```

где `S` — явный selected set, а full set `K_N` содержит N signed frequencies.

## Signed frequency mapping

Для FFT storage index `m = 0..N-1`:

```text
k(m) = m       for 0 ≤ m ≤ floor((N-1)/2)
k(m) = m - N   otherwise
```

Для even N Nyquist bin `m=N/2` имеет signed label `k=-N/2`. Этот выбор применяется одинаково в
reference DFT, NumPy adapter, serialization, ordering и labels.

В public `FourierSpectrum.coefficients` complete set хранится в FFT storage order `m`, а каждый
coefficient несёт canonical signed `k(m)`. Математические views/orderings FS-003 не меняют values.
Reference DFT ограничен `N ≤ 2048`, NumPy FFT —
`N ≤ 262144`; backend выбирается явно, без silent fallback.

## Coefficient representation

```text
C_k = A_k exp(i φ_k)
A_k = |C_k|
φ_k = arg(C_k)
```

Для `A_k = 0` phase является convention value `0.0`; code не должен получать смысл из arbitrary
library phase для exact zero.

## Epicycle Vector Chain

Для coefficient `C_k` rotating local vector:

```text
v_k(t) = C_k exp(i 2π k t)
       = A_k exp(i(φ_k + 2π k t))
```

Пусть selected coefficients упорядочены как `q_0, …, q_(M-1)`, `M ≥ 1`, а configured origin
равен `O`. Head-to-tail points:

```text
P_0(t)     = O
P_(j+1)(t) = P_j(t) + v_(q_j)(t)
P_last(t)  = P_M(t)
```

Для каждого rendered vector:

```text
start_j = P_j
end_j = P_(j+1)
circle_center_j = start_j
circle_radius_j = |C_(q_j)|
```

Endpoint relationship:

```text
P_last(t)
= O + Σ(j=0..M-1) v_(q_j)(t)
= O + Σ(k∈S) C_k exp(i 2π k t)
= O + ẑ_S(t)
```

При каноническом `O = 0`:

```text
P_last(t) = Fourier reconstruction ẑ_S(t)
```

Следовательно:

```text
trace(t) = EpicycleChainState.endpoint(t) = P_last(t)
```

Animation renderer не имеет второго алгоритма вычисления `ẑ(t)` для trace. Equality проверяется
с explicit floating-point tolerance; algebraic equality не отменяет rounding accumulation.

## Ordering invariant

Permutation selected vectors меняет промежуточные `P_j` и визуальную вложенность circles, но
коммутативность complex addition сохраняет `P_last` математически. Поддерживаемые orderings:

- signed frequency;
- absolute frequency;
- amplitude descending с детерминированным tie-break;
- interleaved `0,+1,-1,+2,-2,…` с доступными bins;
- explicit complete permutation.

Точные keys FS-003: signed — `frequency`; absolute — `(abs(frequency), frequency)`; amplitude —
`(-amplitude, abs(frequency), frequency)`. Interleaved использует `0,+1,-1,+2,-2,…`, поэтому
единственный even-N Nyquist bin `-N/2` располагается после доступной положительной пары. Explicit
ordering требует каждый bin ровно один раз. Explicit partial set относится к FS-004 selection API,
а не к complete-spectrum view.

Magnitude вычисляется overflow-safe способом. Если finite real/imaginary components образуют
непредставимый finite magnitude/energy, public API возвращает typed validation error, а не
`OverflowError`, `NaN` или `Inf`.

## Partial reconstruction и energy

Partial reconstruction всегда использует ровно переданный set `S`; harmonic count не означает
неявный другой ordering. Retained energy определяется и документируется через squared amplitudes:

```text
E(S) = Σ(k∈S) |C_k|²
retained = E(S) / E(K_N)
```

Для zero-energy signal retained ratio определяется как `1` при full zero reconstruction и `0`
при partial selection; `0/0` не вычисляется. До full/zero fast-path total energy всё равно проходит
finite validation. При непредставимом finite результате возвращается typed error.

При проверке retained energy selection принадлежит spectrum по value semantics: совпадают
`sample_count`, signed frequency и exact immutable coefficient value. Python object identity не
является частью математического provenance. Caller order хранится в `CoefficientSelection` и
используется reconstruction напрямую, хотя commutativity сохраняет итоговую сумму.

Sample-grid reconstruction допускает не более `262144` output points и `16777216` вычисляемых
coefficient terms за один вызов. Эти limits проверяются до output allocation; увеличение требует
отдельного non-interactive budget/evidence.

## Error metrics

Для aligned reference/reconstruction points и complex error `e[n] = z[n] - ẑ[n]`:

```text
MSE       = (1/N) Σ |e[n]|²
RMSE      = sqrt(MSE)
max_error = max |e[n]|
normalized_error = ||e||₂ / ||z - mean(z)||₂
```

Если denominator normalized error равен zero, результат: `0` для exact reconstruction, иначе
typed undefined/degenerate metric state; silent `NaN` запрещён.

## Arc-length parameterization

Freehand slice сохраняет явно названный baseline `uniform_index`. После удаления
consecutive duplicates для `M` source points строятся `N` samples:

```text
open:   q_j = j(M-1)/(N-1),  j = 0..N-1
closed: q_j = jM/N,          j = 0..N-1
```

В open случае endpoints присваиваются точно из source, а между соседними индексами применяется
linear interpolation. В closed случае индекс циклически переходит с последней точки на первую;
первый output sample не повторяется в конце. One-point input остаётся одним point независимо от
requested count и даёт DC-only signal. Это не arc-length parameterization и не объявляется ею.

FS-009 добавляет отдельный `arc_length`. Для ordered points `p_j` cumulative length:

```text
s_0 = 0
s_j = Σ(r=1..j) |p_r - p_(r-1)|
u_j = s_j / s_last
```

Для open Curve targets равны `jL/(N-1)` и первый/последний output назначаются exact source
endpoints. Для closed Curve closing segment `p_(M-1) → p_0` входит в `L`, targets равны `jL/N`, а
первый output не повторяется в конце. Linear interpolation сохраняет source order.

Zero/non-finite total length не resample-ится и возвращает typed validation error; silent fallback
на index method запрещён. `N=1` для non-zero path возвращает первый point, а spacing diagnostics
явно недоступны из-за отсутствия segment.

Spacing diagnostics измеряют фактические adjacent distances output Curve (для closed — вместе с
seam): segment count, total/mean/min/max, population standard deviation и coefficient of variation
`CV = σ/mean`. Они сравнивают конкретный fixture и не доказывают универсальное улучшение Fourier
approximation. Для fixture `x=(0,0.1,1,4), N=16`: index `CV≈0.917196816392`, arc-length `CV=0`.
Если segment spacing не представим как positive finite `float` (включая underflow), typed
application result оставляет обе spacing metrics недоступными; ancillary diagnostics не блокируют
принятый resampling/timeline path.

## Curve simplification

FS-027 применяет iterative Douglas–Peucker к ordered source vertices до resampling. Для retained
segment `a→b` interior vertex `p` сравнивается с finite Euclidean distance до bounded segment, а не
до бесконечной line. Split выполняется только при `max_distance > tolerance`; tie выбирает меньший
source index. Поэтому `tolerance=0` удаляет exact collinear interior vertices, но не допускает
positive deviation.

Open curve фиксирует first/last indices. Closed curve не дублирует seam: index `0` остаётся первым,
second anchor — farthest vertex from start с lowest-index tie-break; две cyclic arcs упрощаются тем
же open algorithm, а retained indices объединяются в исходном cyclic order. Для non-degenerate
closed input сохраняются минимум три source indices. Метрика deviation — maximum/RMS расстояние
source vertex до соответствующего retained-order segment. Это bounded discrete diagnostic, не
Hausdorff/Fréchet distance.

Original и simplified curves отдельно resample-ятся по arc length к одинаковому `N`. Pointwise
sampled error сравнивает их aligned periodic samples; baseline и simplified Fourier reconstruction
сравниваются с одной baseline sampled reference при одинаковом `K`. Эти measured значения не
доказывают универсальное улучшение после simplification.

## Adaptive sampling

FS-028 измеряет unsigned discrete turning angle в source vertex. Для non-zero incoming/outgoing
vectors `a,b`:

```text
κ_i = acos(clamp((a·b)/(|a||b|), -1, 1)) / π,  0 ≤ κ_i ≤ 1
```

Open endpoints получают `κ=0`; closed curve использует cyclic neighbors. Для segment `i→i+1`
adaptive density равна `w_i = length_i * (1 + α(κ_i+κ_(i+1))/2)`, где explicit `0≤α≤100`.
Базовый множитель `1` сохраняет positive weight каждому positive-length segment. Output targets
равномерны в cumulative `w`; interpolation внутри segment линейна по доле его weight.

Open curve использует targets `jW/(N-1)` и exact source endpoints. Closed curve использует `jW/N`,
exact source start и не повторяет seam. Поэтому total output budget всегда ровно `N`, order/closure
сохранены. При `α=0` или all-zero curvature policy явно помечается
`uniform_arc_length_zero_adaptive_signal`; это заранее принятый uniform fallback, а не silent
algorithm substitution. Zero/non-finite geometric length остаётся typed failure.

Uniform и adaptive samples сравниваются при одинаковых `N/K/speed` и одной uniform sampled
reference. Spacing/RMSE описывают только конкретный fixture и не доказывают universal superiority.

## Route optimization cost

FS-029 не меняет graph coverage или cyclic route definition. Для odd set `O` improved heuristic
повторяет, пока `O` не пуст: берёт lowest-key `u`, находит weighted shortest paths по original raw
links, выбирает `v` с minimum `(distance(u,v), key(v))`, удаляет `u,v` и дублирует path `u→v`.
Edge weight — Euclidean length в общем normalized raster transform. Expansion budget общий для всех
components; exhaustion не создаёт route.

После pairing используется existing Hierholzer walk. Поэтому каждый original link покрыт ровно один
раз, duplicated paths делают degrees even, а inter-component/closing bridges остаются FS-017.
Reported objective:

```text
added_length = duplicated_length + bridge_length
delta = improved.added_length - baseline.added_length
```

Negative delta означает measured improvement только на данном graph/corpus. Greedy pairing не
является proof global matching, Chinese Postman или component-order optimum.

## Discontinuous curves

`PiecewiseCurve` определяет intervals/segments, для которых может быть:

```text
z(t_i-) ≠ z(t_i+)
```

Fourier representation периодического piecewise signal включает jumps и high-frequency content.
`PEN_UP_RENDERING` запрещает stroke через semantic jump, но не удаляет trajectory из math state.
Никаких asymptotic decay/Gibbs claims не делать без измерения и ссылки на условия fixture.

FS-018 выделяет каждому segment минимум один sample по explicit equal/proportional policy и
сохраняет exact total budget. Closed segment при allocation больше одного получает materialized
`start == end`, поэтому его closing seam принадлежит segment trajectory, а следующий sample уже
образует explicit jump. Boundary ledger хранит flattened left/right sample indices, endpoints,
distance и флаг cyclic last→first. Оба render modes получают один и тот же concatenated sequence,
DFT, reconstruction и endpoint history; различается только grouping source-stroke artists.

FS-019 определяет `log_amplitude = log10(max(amplitude, log_floor))`, где positive finite floor
записан в result. Explicit ascending unique K sweep применяет один `SpectrumOrdering`; retained
energy и reconstruction RMSE переиспользуют FS-004 APIs. Эти значения описывают только recorded
finite fixture и не являются доказательством общего decay law или Gibbs theorem.

## 2D image Fourier

Отдельная модель:

```text
f[x,y] ↔ F[k_x,k_y]
```

Её normalization, axes и filters документируются в Stage `FS-020`; она не создаёт epicycle
coefficients `C_k` и не использует 1D chain equality.

FS-020 использует NumPy backward normalization, axes `(row,column)`, unshifted canonical
coefficients и `fftshift` только для magnitude/log-magnitude/phase views. `FFT2Raster` и
`FFT2Spectrum` immutable/readonly и separate; IFFT real reconstruction отклоняет asymmetric mask,
если imaginary residual превышает explicit tolerance.

## Orthonormal Haar basis

FS-032 применяет Haar только к complex 1D curve samples. Canonical analysis length равна `N=1` или
power of two `N=2^L≤4096`; padding отсутствует. Для каждой adjacent pair текущего level:

```text
a[j] = (x[2j] + x[2j+1]) / √2
d[j] = (x[2j] - x[2j+1]) / √2
```

Pairwise analysis повторяется над `a`, пока не останется root scaling coefficient. Inverse одного
level:

```text
x[2j]   = (a[j] + d[j]) / √2
x[2j+1] = (a[j] - d[j]) / √2
```

Каждый immutable term хранит kind (`scaling`/`detail`), level, location и complex value. Detail
`level=0` — finest pairs исходного grid, `level=L-1` — coarsest detail. Canonical activation order:
root scaling, затем detail levels `L-1..0`, внутри level ascending location. Partial selection первых
`K` terms синтезируется с нулём только на невыбранных canonical coefficients; исходный coefficient
array и source Curve не изменяются. Full selection восстанавливает analysis samples с tolerance
`1e-12` на bounded analytical fixtures scale `≤1`.

Desktop не выдаёт arbitrary stroke length за Haar-compatible grid: one-point Curve анализируется
напрямую, non-degenerate multi-point source отдельно arc-length-resample-ится к 128 samples с
recorded provenance; raw source budget равен 10 000 points до resampling. Haar reconstruction
является curve-on-grid, а не rotating-vector sum;
`trace == endpoint` к нему не применяется.

## Numerical evidence policy

- finite input проверяется до transform;
- analytical fixtures: constant/DC, circle, ellipse, impulse where applicable;
- reference DFT сравнивается с FFT adapter;
- tolerances указываются в test рядом с scale/N rationale;
- renderer image не является доказательством correctness;
- ускоритель/backend проходит те же golden/property contracts, что reference path.
