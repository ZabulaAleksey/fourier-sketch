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

До FS-009 freehand slice использует явно названный baseline `uniform_index`. После удаления
consecutive duplicates для `M` source points строятся `N` samples:

```text
open:   q_j = j(M-1)/(N-1),  j = 0..N-1
closed: q_j = jM/N,          j = 0..N-1
```

В open случае endpoints присваиваются точно из source, а между соседними индексами применяется
linear interpolation. В closed случае индекс циклически переходит с последней точки на первую;
первый output sample не повторяется в конце. One-point input остаётся одним point независимо от
requested count и даёт DC-only signal. Это не arc-length parameterization и не объявляется ею.

Для ordered points `p_j` cumulative length:

```text
s_0 = 0
s_j = Σ(r=1..j) |p_r - p_(r-1)|
u_j = s_j / s_last
```

Closed semantics включают closing segment только по явному contract. Zero total length не
resample-ится и возвращает validation error. Интерполяция сохраняет order и open endpoints.

## Discontinuous curves

`PiecewiseCurve` определяет intervals/segments, для которых может быть:

```text
z(t_i-) ≠ z(t_i+)
```

Fourier representation периодического piecewise signal включает jumps и high-frequency content.
`PEN_UP_RENDERING` запрещает stroke через semantic jump, но не удаляет trajectory из math state.
Никаких asymptotic decay/Gibbs claims не делать без измерения и ссылки на условия fixture.

## 2D image Fourier

Отдельная модель:

```text
f[x,y] ↔ F[k_x,k_y]
```

Её normalization, axes и filters документируются в Stage `FS-020`; она не создаёт epicycle
coefficients `C_k` и не использует 1D chain equality.

## Numerical evidence policy

- finite input проверяется до transform;
- analytical fixtures: constant/DC, circle, ellipse, impulse where applicable;
- reference DFT сравнивается с FFT adapter;
- tolerances указываются в test рядом с scale/N rationale;
- renderer image не является доказательством correctness;
- ускоритель/backend проходит те же golden/property contracts, что reference path.
