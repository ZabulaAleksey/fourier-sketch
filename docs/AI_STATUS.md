# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-027` on the working branch, awaiting publication.
- Active Stage ID: `FS-027`, lifecycle `completed`; automated gates PASS and independent review GO,
  awaiting the already-authorized MDP publication.
- Integration: touch/rainbow `cb323e2`, export `ceaa6c7` and fixed-center canvas maintenance
  `02c026b`, and FS-023 hardening `a2d7a2c` are integrated in `main` and published to `origin/main`.
  FS-024 Harmonic Inspector `e480382` is also integrated in `main` and published to `origin/main`.
  FS-025 Frequency Solo `517b7d8` is integrated in `main` and published to `origin/main`.
  FS-026 Harmonic Build-Up `fe46cac` is integrated in `main` and published to `origin/main`.
  No PR, release or deployment was performed.
- Scope: только FS-027 Curve Simplification; FS-028+, FS-031 и FS-032 не начинались.
- Blockers: FS-021 terminal blockers отсутствуют. Windows Graphics Capture still returns
  `SetIsBorderRequired failed (0x80004002)`, but the user independently confirmed the manual visible
  DPI/resize and physical-touch checklist; automated capture was not represented as that evidence.

## FS-027 progress

- Project-owned iterative Douglas–Peucker упрощает immutable ordered curve до resampling, сохраняет
  open endpoints или closed index `0`/closure, source-subsequence provenance и deterministic anchors.
  Tolerance, 250 000-point ceiling, bounded distance-evaluation budget и cancellation дают typed
  all-or-nothing failures без partial result.
- Existing contour CLI получил opt-in comparison: original/simplified geometry независимо
  arc-length-resample-ятся к одному N, используют одинаковые K/speed и две actual timelines.
  Atomic 2x2 PNG и localized summary показывают reduction, retained-segment deviation, sampled RMSE
  и обе reconstruction RMSE против одной baseline reference; legacy path без option не изменён.
- Focused FS-027 regression: `21 passed`; full repository suite: `628 passed in 169.56s`. Frozen sync
  checked 38 packages; Ruff, strict mypy (214 source files), diff and overlay PASS. Bounded sanity:
  250 000 collinear points → 2 points in `0.899786s`; 50 000-point zigzag with budget 1000 → typed
  resource limit in `0.002319s`. Independent read-only review: `GO`, no P0/P1/P2.
- Full-suite diagnosis also corrected an incomplete legacy property assertion: for a constant
  reference, non-zero floating-point residual correctly permits documented
  `UNDEFINED_ZERO_REFERENCE` while retaining the absolute error bound. Production math is unchanged.

## FS-026 progress

- `HarmonicBuildUpSession` проецирует immutable baseline в deterministic first-K sequence для всех
  четырёх non-explicit orderings. Target ограничен `1..min(sample_count, 4096)`, dwell —
  `0.10..5.00 s`; каждый transition показывает actual reconstruction/chain и singleton trace.
- Build-Up Play/Pause/Restart/Completed используют existing QTimer только как dwell clock. Baseline
  time/state/speed/selection/trace не меняются; Exit раскрывает exact baseline object и running
  timeline возобновляется без catch-up. Inspector показывает latest signed `k`, retained energy и
  measured RMSE; Solo, manual K, configuration и export gated до Exit.
- Focused desktop regression: `52 passed`; full repository suite: `607 passed in 152.55s`. Frozen
  sync checked 38 packages; Ruff, strict mypy (206 source files), diff and overlay PASS. Maximum
  bounded `K=4096` one-step projection measured `0.094405s`, 4096 vectors, singleton trace.
  Independent read-only review: `GO`, no P0/P1/P2. Actual-Qt offscreen evidence is not manual visible
  Windows GUI/DPI or screen-reader evidence.

## FS-025 progress

- Desktop inspector now provides an explicit accessible `Solo selected harmonic` / `Exit Solo`
  control and localized `SOLO — active set: k=…` mode label. FS-025 intentionally supports one
  frequency; multi-select/build-up remains FS-026.
- `FrequencySoloSession` projects the selected signed `k` into a real one-coefficient explicit
  selection with canonical reconstruction, chain endpoint and a bounded mode-local trace. Baseline
  timeline selection/K, complete spectrum, state/time/speed/visibility and trace remain unchanged;
  exit reveals the exact current baseline frame.
- Harmonic-count and export controls are disabled and defensively gated during Solo. Animation,
  restart, speed, visibility and presentation zoom/pan continue through existing owners; new/stale
  timeline provenance clears the analysis session without retargeting it.
- Targeted unit/property/component/actual-Qt offscreen E2E: `62 passed`; post-review focused set:
  `21 passed`; full repository suite: `589 passed in 141.98s`. Frozen sync checked 38 packages; Ruff,
  strict mypy (201 source files), diff and overlay PASS. Independent re-review: `GO`, no remaining
  blocking findings. Offscreen Qt evidence is not manual visible Windows GUI/DPI or screen-reader
  evidence.

## FS-024 progress

- Ready desktop frame now exposes a read-only Harmonic Inspector with an ordered keyboard-focusable
  list and localized values for selection position, signed `k`, amplitude, phase, angular velocity
  and current complex local contribution.
- Stable identity is signed frequency. Canvas vector/circle click uses deterministic device-space
  hit testing with current zoom/pan/Y transform; click and drag-pan are separated by the Qt drag
  threshold. Off-harmonic click, K shrink, stale identity and a new timeline clear explicitly.
- Selection is presentation-only. Unit/component regressions prove exact aligned coefficient/vector
  mapping, K-grow/time persistence, animation value refresh and unchanged Curve, coefficients, chain,
  endpoint, timeline, speed and trace. Harmonic slider UI synchronization blocks its own signal.
- Targeted unit/component/actual-Qt offscreen E2E: `32 passed`; focused post-self-review assertions:
  `7 passed`; full repository suite: `573 passed in 146.79s`. Frozen sync checked 38 packages; Ruff,
  strict mypy (198 source files), diff and overlay PASS. Independent reviewer reran `7` focused and
  `42` desktop/timeline tests: `GO`, no P0/P1/P2. Offscreen evidence is not manual visible GUI/DPI or
  screen-reader evidence.

## FS-023 progress

- Complete/sparse inverse grid переведён с Python `O(N×K)` summation на bounded NumPy IFFT с теми же
  signed-frequency/normalization semantics. Scalar `reconstruct_at` остаётся reference oracle;
  small/reference, representative `N=16,384` и stress `K=4096` parity regressions PASS.
- Qt Cancel больше не блокирует GUI ожиданием и не вызывает `QThread.terminate()`. Generation guard
  подавляет late publication; owned worker сохраняется до `finished`, а close откладывается до его
  normal completion. Correctness regressions проверяют state/cleanup без wall-clock assertion;
  harness измерил cancel request `2.87e-05 s` при broad catastrophic limit `0.25 s`. Real GIF test
  дожидается worker cleanup. Atomic export cleanup, Unicode/space JSON+GIF paths и privacy-safe FFT2
  CLI failure covered by regressions.
- Named Windows baseline: Python 3.12.5, NumPy 2.5.2, PySide6 6.11.2, Intel64 Family 6 Model 140;
  `N=65,536` FFT round-trip `1.311 s`, max error `2.04e-15`, traced Python peak `17,050,172` bytes;
  stress `K=4096` timeline `0.112 s`, offscreen paint median `0.050 s` versus default `0.0048 s`.
  These are local/offscreen measurements, not visible GUI/DPI or native-total-memory claims.
- Narrow hardening/export/desktop suite: `43 passed`; full suite: `566 passed in 126.34s` with one
  pre-existing pytest-cache permission warning. Branch-aware coverage: `76%`, configured floor `75%`.
  Frozen sync, Ruff, strict mypy, lock/tree/pip compatibility and isolated wheel import/resource/
  desktop-help smoke PASS. `pip-audit 2.10.1` reported no known vulnerabilities for auditable
  dependencies; project itself was skipped because it is not published on PyPI.
- Independent read-only review found two P2 test-harness issues (a brittle component wall-clock
  assertion and missing wait after close); both were fixed. Final re-review: `GO`, no P0/P1/P2.
- Packaging decision: source-run plus recoverable wheel is the supported artifact/path. Bundled
  installer/public redistribution remain unselected and blocked by missing project license/third-party
  notices and unresolved PySide6 LGPL redistribution obligations; this is not an installer failure
  because SPEC does not require an installer for FS-023.

## FS-022 progress

- EXPORT page activates only for a ready timeline and writes the current original Curve or current
  ordered coefficient selection as schema-versioned JSON/CSV, reconstruction/spectrum PNG, or a
  bounded Pillow GIF generated from the same `EpicycleChainState` selection/endpoint semantics.
- GIF is bounded to `2..120` frames and `20..1000 ms`; endpoint-history metadata reopens with the
  artifact and matches actual frame endpoints. Progress/cancel use the existing worker lifecycle.
  Sibling-temp atomic publication, default no-overwrite, explicit overwrite and codec/cancel cleanup
  are covered. MP4 is visibly unavailable with no subprocess or silent GIF fallback.
- Targeted unit/integration/component/live export command: `37 passed in 5.34s`. Full repository
  regression: `557 passed in 113.67s`. Reviewer reruns independently reached `37 passed in 4.90s`
  and `557 passed in 145.58s`. `uv sync --all-groups --frozen`, Ruff, strict mypy, diff check and
  overlay validator PASS; dependency graph remains 37 packages. Independent read-only review: `GO`.

## FS-021 progress

- Latest maintenance delta uses center-anchored zoom for wheel/slider/pinch with proportional pan
  correction that preserves the scene-coordinate under the geometric canvas center, resets
  every accepted freehand curve to `1.00×`/zero pan, and maps its source-field-relative coordinate
  extent instead of fitting its own bounds. `Original` is disabled/unchecked without a ready frame
  and exactly mirrors `frame.visibility.original` thereafter. Desktop speed is `0.01..1.00×` in
  `0.01×` steps. Desktop component suite: `24 passed`; full suite: `558 passed in 129.07s`; frozen
  sync, Ruff, strict mypy, diff and overlay PASS. Independent read-only review: `GO`; its full-suite
  rerun reached `558 passed in 117.39s` with no P0/P1/P2 findings.
- Vector/circle colors now use a stable deterministic rainbow palette by selection position: existing
  colors remain unchanged when K grows and each pair uses the same color. `EpicycleCanvas` accepts
  one-finger touch pan and two-finger fixed-center pinch through the same `0.01..100.00×` zoom synchronized
  with wheel/slider; reset clears zoom/pan/active gesture state. Component logic verifies presentation-only
  isolation from frame/timeline/trace/animation. Targeted desktop suite: `19 passed`; full repository:
  `543 passed in 130.51s`; Ruff, strict mypy, frozen sync and overlay validator PASS locally. Native
  physical-touch delivery and visible Windows GUI/DPI/resize remain outside automated evidence and
  were confirmed manually by the user.
- Independent read-only re-review: `GO`; the earlier fractional pinch-anchor correction had no remaining
  P0/P1/P2 finding and no scope creep into FS-022, FS-023, FS-031 or FS-032 was found.
- In normal `1200×760` desktop geometry the freehand field is vertically centered with the epicycle
  canvas. The instruction now wraps rather than forcing the source column wider than the renderer.
  Presentation zoom is numerically bounded at `0.01..100.00×`, which is practically unrestricted for
  mouse-wheel navigation while keeping finite QPainter transforms. Component evidence is `16 passed`;
  full repository regression, Ruff and strict mypy PASS locally. This delta is integrated in `main`.
- Freehand source now converts screen Y to Cartesian Y before timeline construction, while its source
  canvas maps it back for display; this preserves the vertical orientation of the user stroke in the
  epicycle canvas. The canvas supports fixed-center wheel zoom and LMB-drag pan; reset restores
  `1.00×` and zero pan. Component evidence drives both event paths. This delta is integrated in `main`.
- Desktop image source now defaults to dark-ink/light-background preprocessing and exposes an explicit
  reverse-polarity opt-out. This prevents a light source background from becoming the dominant outer
  contour. The central canvas also has persisted presentation-only `0.01..100.00×` zoom and reset to
  `1.00×`; neither control mutates Fourier/timeline state. Targeted component evidence is `13 passed`;
  full repository regression, Ruff and strict mypy PASS locally. This delta is integrated in `main`.
- PySide6 source-run shell, freehand/image dispatch, background worker, canvas controls, renderer-control
  checks and source-workflow component slice are implemented, committed, merged, and pushed.
- Targeted desktop component tests, Ruff, mypy, frozen sync and overlay validator pass.
- Offscreen desktop component path теперь вызывает реальные mouse callbacks freehand canvas и file-picker
  callback для локального PNG: оба проходят через существующие application/worker boundaries до
  timeline/frame. `QSettings` заменяется test-local in-memory adapter, поэтому проверки не меняют
  пользовательские preference. Связанный component+integration набор: `14 passed in 2.17s`.
  Это component evidence, а не ручная visual/DPI проверка видимого Windows окна.
- Добавлены проверки корректного ресайза/готовности canvas, guard от stale-job после cancel и сохранения
  базовых UI-предпочтений; это закрывает большую часть step 6 lifecycle/persistence gates.
- Historical FS-021 review fixed cancelled state, restored window size and job ownership. FS-023
  supersedes its bounded-terminate implementation: forced termination is removed, cancellation is
  non-blocking and close is deferred until the still-owned job finishes.
- Current full repository regression: `543 passed in 130.51s`; Ruff, strict mypy, frozen sync and overlay PASS.
- Renderer profile (offscreen, Windows-10-10.0.19045-SP0, 8 vCPU): fast core remains `≈0.31 ms/frame`; full
  QPainter paint now measures `≈1.55 ms/frame` default (K=25, N=1024, 300 frames, 1200×760) and
  `≈4.55 ms/frame` stress (K=256, N=4096, 1001 frames, 1200×760), with p99 `6.63` и `11.81 ms/frame`.
  Endpoint parity and deterministic replay were verified by double-run equality check.
- Authorized renderer-control delta removes persistent trace from desktop bounds/paint/toggle while
  retaining the application ledger; desktop speed is capped for smoother interaction at
  `0.01..1.00×`, currently mapped with `0.01×` resolution.
- Comparable K=25/600-frame offscreen paint improved `≈3.66→2.00 ms/frame`; retained ledger ended
  at 601 points. Targeted component/Ruff/mypy/overlay PASS.
- FS-021 static scene cache is now implemented: original/reconstruction geometry and scene bounds are
  cached until curve/reconstruction/selection changes; dynamic vectors are painted each frame.
- Dynamic chain geometry is now pre-batched per frame (`QLineF`/circle cache) before paint, reducing
  per-paint allocations in dynamic epicycle drawing.
- Step 4 stress profile completed and evidence recorded for this hardware tuple; no target breach
  against a 16.67 ms/frame interactive budget in default or stress buckets.
- Reviewer P1 continuous paused redraw fixed: animation timer is inactive without/running-off
  timeline, starts on Play and stops on Pause/Restart. Targeted desktop suite is 3 PASS; final full
  repository suite after the fix is `527 passed in 161.13s`.
- Independent re-review: `GO`; no remaining P0/P1/P2 findings for this bounded delta.
- Bounded renderer-control delta committed locally: `0faf8fc`.

## Подтверждённо реализовано

- `FS-000`–`FS-009`: scaffold, immutable domain/Fourier/epicycle model, diagnostic renderer,
  bounded freehand MVP и arc-length parameterization.
- `FS-010`–`FS-013`: safe local PNG/JPEG preprocessing, explicit edge modes, deterministic dominant
  contour и cohesive image-to-epicycle Matplotlib MVP.
- `FS-014`: explicit scikit-image 0.26.x Lee skeletonization, typed provenance, generation-safe
  controller и atomic skeleton/preview PNG.
- `FS-015`: project-owned `corner-suppressed-8-v1` skeleton graph, raw degree roles, compressed
  junction regions/degree-2 chains, explicit components, pure-loop anchors, parallel/self edges,
  exact pixel ownership, raw cycle provenance и canonical traversal-neutral JSON.
- Local graph diagnostic проходит реальный `PNG/JPEG → FS-010 → Lee → graph → JSON/overlay` path;
  CLI не создаёт PiecewiseCurve, component bridge или forced route.
- `FS-016`: all-or-nothing graph→PiecewiseCurve conversion для path/loop/isolated components,
  shared raster transform, exact provenance, explicit pen-up boundaries и отдельный diagnostic CLI;
  branched/complex topology не создаёт partial route.
- `FS-017`: shared raw adjacency, exact Euler/tree T-join traversal, cyclic explicit bridges,
  aligned original/duplicated/bridge provenance, metrics и real route→Fourier diagnostic.
- `FS-018`: exact equal/proportional PiecewiseCurve sampling, materialized closed seams, indexed
  jump ledger, shared discontinuous FFT/timeline, distinct strict/pen-up rendering и same-budget
  forced-route comparison.
- `FS-019`: immutable finite amplitude/log-amplitude analysis, explicit K sweep with retained
  energy/RMSE, partial resource status и live discontinuous-vs-continuous chart.
- `FS-020`: dedicated readonly FFT2 raster/spectrum types, recorded convention, low/high/selected
  filters, controlled real IFFT, safe local-image diagnostic и atomic export.
- `FS-021`: integrated PySide6 source-run workflow, bounded worker/cancellation lifecycle, central
  optimized Epicycles canvas, controls/persistence/i18n, mouse/touch navigation and stable rainbow pairs;
  automated quality gates, independent review and user-confirmed manual Windows terminal checklist PASS.

## Evidence FS-020

- Activation/SPEC/ADR commit: `855be2a`.
- Targeted unit/property/integration/component/live E2E suite: 12 tests PASS.
- Full terminal repository suite: 524 tests PASS.
- Ruff, strict mypy и project-overlay validator: PASS.
- Визуальная проверка grayscale/centered log magnitude/phase diagnostic: PASS.
- Independent review findings по type separation/convention/resource/IFFT/path/backend/bidi
  исправлены; final re-review `GO`.

## Limits / deferred

- Graph foreground `≤250,000`, node+edge records `≤500,000`, canonical JSON `≤32 MiB`.
- Canonical IDs/serialization и `LOOP_ANCHOR` не являются traversal order.
- Spectrum analysis отложен до FS-019; 2D raster Fourier — до FS-020.
- Windows Graphics Capture remains unavailable with `SetIsBorderRequired failed (0x80004002)` after
  reset/retry. This limits automated screenshot evidence but no longer blocks FS-021 because the user
  confirmed the visible GUI/DPI/resize and physical-touch checklist manually.
- Lexical local-path guard не доказывает physical locality mapped/reparse targets; это остаётся
  documented residual risk после FS-023.

## Следующее разумное действие

Создать атомарный FS-027 commit и выполнить разрешённый МДП. После публикации отдельно выбрать
FS-028; не смешивать FS-030 или mobile/basis scope с текущим slice.

## Синхронизация документации

- Для FS-027 обновлены README, Fourier/image SPEC, architecture/decisions/design/mathematics/testing,
  traceability и AI plan/status/roadmap/stage registry. Fourier math, dependency set, security,
  export schema и desktop/mobile UI не изменены.
- `docs/LEARNING_LOG.md` проверен без изменений: замкнутый cyclic-anchor regression и constant-
  reference property semantics закреплены executable tests без отдельного operational runbook.
