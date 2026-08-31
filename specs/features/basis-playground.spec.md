# Feature SPEC — Indexed Bases and Harmonic Playground

Статус: Выполнена, проверена, интегрирована в `main` и опубликована в `origin/main` для `FS-033`

## Назначение и область

Расширить desktop basis selector двумя явными ортонормированными базисами для комплексной 1D
`Curve` и добавить отдельную Fourier-only лабораторию, где пользователь собирает кривую из
собственных гармоник. Stage не меняет Fourier convention, существующий Haar contract, Android и
canonical six-step Educational Mode.

## Требования

### BP-FR-001 — Explicit indexed basis choice

К существующим `FOURIER_EPICYCLE` и `HAAR_WAVELET` добавляются `DCT_II` и
`WALSH_HADAMARD`. Fourier остаётся default. Unsupported/invalid basis завершается явной ошибкой без
silent fallback. Selector locking, Clear и source ownership сохраняют контракт `BS-FR-001`.

### BP-FR-002 — Orthonormal complex DCT-II

DCT-II применяет один и тот же вещественный ортонормированный basis к real и imaginary частям
комплексных samples:

`C_k = alpha_k * sum(n=0..N-1) z[n] cos(pi*(n+1/2)*k/N)`,

где `alpha_0=1/sqrt(N)`, `alpha_k=sqrt(2/N)` для `k>0`. Synthesis использует транспонированный
ортонормированный basis. Canonical term order — ascending index `0..N-1`; first-K selection не
меняет complete decomposition. Math boundary принимает finite `1<=N<=1024`.

### BP-FR-003 — Orthonormal Walsh–Hadamard

Walsh–Hadamard использует Sylvester natural order и normalization `1/sqrt(N)` для analysis и
synthesis. `N` равно `1` или power-of-two `N<=4096`. Canonical term order — natural index
`0..N-1`; padding, sequency relabeling и silent fallback запрещены.

### BP-FR-004 — Honest indexed-basis reconstruction view

Desktop adapter сохраняет immutable source `Curve`; one-point input анализируется напрямую, а
остальной accepted source отдельно arc-length-resample-ится к recorded 128-sample analysis curve
при raw source budget `<=10,000`. DCT/Walsh frame показывает source, selected-term reconstruction
и contribution последнего selected indexed term. Play/Pause/Restart, Terms, speed `0.01..1.00x`,
zoom/pan и Original/Reconstruction переиспользуют существующие bounded controls.

DCT/Walsh terms не называются signed Fourier frequencies и не рисуются как circles/vectors,
endpoint или trace. Inspector, Solo, Build-Up, canonical Educational Mode, image input и export
явно disabled. Completion `K=N` ставит timeline на pause; Restart возвращает paused `K=1`.

### BP-FR-005 — Manual harmonic authoring

Отдельный `Harmonic Playground` позволяет задать ordered set из `1..16` уникальных Fourier terms.
Каждый term содержит signed integer `k` в canonical `N=128` диапазоне `-64..63`, amplitude
`0<A<=4` и phase `-pi<=phi<=pi`; сумма amplitudes не превышает `8`:

`z[n] = sum_j A_j exp(i*(phi_j + 2*pi*k_j*n/N))`.

Upsert сохраняет позицию существующего `k`, новый `k` добавляется в конец; remove/clear явны.
Любое invalid/over-budget изменение отклоняется transactionally. Отображаемая
`CoefficientSelection` использует exact explicit row order, а не amplitude/signed sorting.

### BP-FR-006 — Playground lifecycle and isolation

Вход в Playground сохраняет текущий normal desktop result, если он существует, и начинает с
paused canonical circle term `k=1, A=1, phi=0`. Apply rebuilds actual Fourier curve/timeline,
pauses at `t=0` and resets only mode-local trace. Play/Pause/Restart, speed, canvas navigation,
circles/vectors/endpoint/reconstruction visibility и read-only inspector работают над authored
terms; generated source layer hidden и disabled как не-captured input.

Пока Playground активен, source/basis editing, harmonic-count slider, Solo, Build-Up, canonical
Educational Mode и export locked. Exit восстанавливает exact previous timeline/result или empty
state, если baseline отсутствовал. Playground не мутирует baseline Curve, coefficients, timeline,
trace, zoom/pan или animation state. No second timer создаётся.

## Ошибки и границы

- Non-finite samples/parameters, invalid N/K/index, foreign selection ownership и over-budget input
  fail closed without stale/partial publication.
- DCT/Walsh analysis failure не переключает basis.
- Playground edit failure сохраняет previous authored terms и displayed timeline.
- New basis and Playground do not enable image raster transforms or Android code.

## Acceptance

- BP-AC-001: analytical constant/impulse/small fixtures and randomized bounded full selections prove
  DCT-II and Walsh round-trip within `1e-12` for desktop fixtures scale `<=1`; max-bound DCT may use
  documented `1e-10` tolerance.
- BP-AC-002: every partial reconstruction equals the sum of exactly its canonical selected term
  contributions; decomposition/selection ownership rejects altered copied terms.
- BP-AC-003: actual desktop component/E2E paths distinguish all four basis labels and geometry;
  Fourier/Haar regressions remain unchanged and no non-Fourier fake epicycle state appears.
- BP-AC-004: a user enters Playground, applies at least two ordered terms, animates the actual chain,
  inspects authored `k`, exits and receives the exact prior result.
- BP-AC-005: invalid/over-budget authoring is transactional; composer edits do not mutate the saved
  baseline or presentation view.
- BP-AC-006: focused/full/static/overlay checks and independent read-only review pass; offscreen Qt
  evidence is not described as manual visible Windows GUI/DPI evidence.

## Out of scope

Daubechies/biorthogonal/continuous wavelets, learned bases, cross-basis quality ranking, basis export,
quiz/scoring, freehand coefficient painting, Android and public plugin architecture.

## Трассировка

Stage `FS-033`; behaviors `BH-INDEXED-BASIS-001`, `BH-HARMONIC-PLAYGROUND-001`.

## История

- 2026-08-31: initial accepted FS-033 contract for bounded DCT-II, Walsh–Hadamard and manual
  Fourier harmonic authoring.
