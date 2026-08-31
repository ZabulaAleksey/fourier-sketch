# Feature SPEC — Basis Selection and Wavelet Reconstruction

Статус: Принята, completed `FS-032`; integrated in `main` and published to `origin/main`

## Назначение и область

Добавить явный выбор базиса для 1D complex `Curve` после стабилизации Fourier product path. Первый
non-Fourier basis — project-owned orthonormal Haar transform. Этот SPEC не меняет принятую Fourier
convention, existing `FourierSpectrum`, epicycle chain или FFT2 raster mode.

## Требования

### BS-FR-001 — Explicit basis choice

Пользователь выбирает basis до decomposition: `FOURIER_EPICYCLE` (default) или `HAAR_WAVELET`.
Result, UI state и diagnostics содержат selected basis и term/selection provenance. Unsupported,
unavailable или invalid basis даёт explicit error/disabled state; silent fallback запрещён.
После начала stroke selector locked до explicit Clear; Clear удаляет текущий displayed result и
открывает selector. Поэтому selected combo value всегда соответствует recorded displayed basis.

### BS-FR-002 — Fourier compatibility

Fourier mode переиспользует существующие spectrum, selected coefficients, head-to-tail epicycles и
endpoint contract без изменения sign/normalization/order semantics. `trace == endpoint` относится
только к этому mode и не переносится на wavelet view.

### BS-FR-003 — Haar reconstruction

Haar mode принимает bounded finite curve samples, публикует immutable analysis terms с scale/location
provenance и строит reconstruction из explicitly selected terms. Constant, impulse, step и small
curve fixtures проверяют exact/declared-tolerance synthesis; input/output budgets и non-finite values
fail closed.

Canonical Haar analysis принимает `N=1` или power-of-two `N≤4096`. Desktop adapter не изменяет
source `Curve`: one-point source анализируется напрямую, а non-degenerate multi-point source
arc-length-resample-ится в отдельную recorded 128-sample analysis curve. Degenerate/non-finite или
raw source `>10,000` points отклоняется явно до resampling; padding и silent basis/resampling
fallback запрещены.

Forward/inverse используют orthonormal pairwise normalization `1/√2`. Stable term order — root
scaling term, затем detail levels от coarsest к finest, внутри level по ascending location. Selection
содержит первые `K`, `1≤K≤N`, и записывает basis, total term count, ordering и exact selected term
identities. Full `K=N` восстанавливает analysis curve в declared tolerance `1e-12` для fixture scale
`≤1`; production finite validation остаётся обязательной независимо от tolerance.

### BS-FR-004 — Honest animation semantics

Animation Haar показывает activation/order of scale-location terms and the resulting partial curve.
Она не рисует rotating circles, не называет terms frequencies и не заявляет endpoint-trace equivalence.
Fourier epicycle view и Haar reconstruction view имеют distinct accessible labels.
Haar frame содержит source curve, recorded analysis curve, selected-term reconstruction и contribution
текущего scale/location term. Play/Pause/Restart и bounded speed управляют только term activation;
никакие Fourier coefficients, circles, endpoint или trace ledger для Haar не создаются.
Activation rate равен 4 terms/second × существующий desktop speed `0.01..1.00×`; completion
останавливается на `K=N`, Pause сохраняет K, Restart возвращает K=1. Slider задаёт current K.
FS-032 selector применяется к новому completed freehand Curve; при выбранном Haar image input явно
disabled, поскольку FFT2/image basis routing остаётся вне этого stage.

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
- BS-AC-006: restart сохраняет selected basis, возвращает Haar к first root-scaling term и не меняет
  source/analysis curves; Fourier restart сохраняет существующий endpoint/trace contract.

## Планируемая трассировка

Stage `FS-032`; behaviors `BH-BASIS-SELECT-001`, `BH-WAVELET-RECONSTRUCTION-001`.
