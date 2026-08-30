# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-022`; versioned data/PNG/GIF export, bounded cancellation and explicit
  MP4 unavailability passed automated gates and independent read-only review.
- Active Stage ID: `FS-022`, lifecycle `completed`; this record intentionally stops before selecting
  or implementing FS-023.
- Integration: touch/rainbow commit `cb323e2` and post-merge status sync are in local `main`.
  No push, PR, release or deployment was performed.
- Scope: FS-023, FS-031 and FS-032 remain inactive and were not started as part of FS-022.
- Blockers: FS-021 terminal blockers отсутствуют. Windows Graphics Capture still returns
  `SetIsBorderRequired failed (0x80004002)`, but the user independently confirmed the manual visible
  DPI/resize and physical-touch checklist; automated capture was not represented as that evidence.

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

- Vector/circle colors now use a stable deterministic rainbow palette by selection position: existing
  colors remain unchanged when K grows and each pair uses the same color. `EpicycleCanvas` accepts
  one-finger touch pan and two-finger anchored pinch through the same `0.01..100.00×` zoom synchronized
  with wheel/slider; reset clears zoom/pan/active gesture state. Component logic verifies presentation-only
  isolation from frame/timeline/trace/animation. Targeted desktop suite: `19 passed`; full repository:
  `543 passed in 130.51s`; Ruff, strict mypy, frozen sync and overlay validator PASS locally. Native
  physical-touch delivery and visible Windows GUI/DPI/resize remain outside automated evidence and
  were confirmed manually by the user.
- Independent read-only re-review: `GO`; the fractional pinch-anchor correction has no remaining
  P0/P1/P2 finding and no scope creep into FS-022, FS-023, FS-031 or FS-032 was found.
- In normal `1200×760` desktop geometry the freehand field is vertically centered with the epicycle
  canvas. The instruction now wraps rather than forcing the source column wider than the renderer.
  Presentation zoom is numerically bounded at `0.01..100.00×`, which is practically unrestricted for
  mouse-wheel navigation while keeping finite QPainter transforms. Component evidence is `16 passed`;
  full repository regression, Ruff and strict mypy PASS locally. This delta is integrated in `main`.
- Freehand source now converts screen Y to Cartesian Y before timeline construction, while its source
  canvas maps it back for display; this preserves the vertical orientation of the user stroke in the
  epicycle canvas. The canvas supports pointer-centered wheel zoom and LMB-drag pan; reset restores
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
- Review P2 исправлены: Cancel всегда публикует `cancelled` после остановки job; `run_desktop()` больше
  не перезаписывает восстановленный размер окна. Неостанавливаемый после bounded terminate job остаётся
  во владении окна до фактического завершения, поэтому `QThread` не уничтожается while running.
  Component regressions покрывают все три случая.
- Current full repository regression: `543 passed in 130.51s`; Ruff, strict mypy, frozen sync and overlay PASS.
- Renderer profile (offscreen, Windows-10-10.0.19045-SP0, 8 vCPU): fast core remains `≈0.31 ms/frame`; full
  QPainter paint now measures `≈1.55 ms/frame` default (K=25, N=1024, 300 frames, 1200×760) and
  `≈4.55 ms/frame` stress (K=256, N=4096, 1001 frames, 1200×760), with p99 `6.63` и `11.81 ms/frame`.
  Endpoint parity and deterministic replay were verified by double-run equality check.
- Authorized renderer-control delta removes persistent trace from desktop bounds/paint/toggle while
  retaining the application ledger; desktop speed is capped for smoother interaction at
  `0.10..1.00×`, currently mapped with `0.01×` resolution.
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
- Lexical local-path guard не доказывает physical locality mapped/reparse targets; hardening остаётся
  FS-023 residual risk.

## Следующее разумное действие

Создать атомарный FS-022 commit и остановиться. FS-023, FS-031 и FS-032 не начинать заодно.

## Синхронизация документации

- Обновлены README, SPEC/ADR, architecture/design/security/testing/traceability/dependencies/
  fallbacks и AI plan/status/roadmap/stage registry.
- Математический/API/export contract проверен: FS-018 добавляет discontinuous application API,
  но не меняет persistence/export contracts FS-022.
- `docs/LEARNING_LOG.md` проверен без изменений: stage не добавил новую повторно полезную
  диагностику сверх принятых graph contracts и regression evidence.
