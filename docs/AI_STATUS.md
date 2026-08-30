# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-020`; validated and committed locally at `5895315`.
- Active Stage ID: `FS-021`, lifecycle `partial`.
- Branch: `main`; renderer-control delta integrated locally by fast-forward.
- Integration: implementation `0faf8fc` and evidence update `2c552a7` are present in `main`;
  PR/release/deployment were not performed.
- Blockers: нет.

## FS-021 progress

- PySide6 source-run shell, freehand/image dispatch, background worker, canvas controls and
  offscreen component checks are implemented, committed and merged locally; push is not performed.
- Targeted desktop component tests, Ruff, mypy, frozen sync and overlay validator pass.
- Full repository regression: `526 passed in 98.80s`; Ruff, strict mypy, frozen sync and overlay PASS.
- Renderer profile (offscreen, Windows-10-10.0.19045-SP0, 8 vCPU): fast core remains `≈0.31 ms/frame`; full
  QPainter paint now measures `≈1.55 ms/frame` default (K=25, N=1024, 300 frames, 1200×760) and
  `≈4.55 ms/frame` stress (K=256, N=4096, 1001 frames, 1200×760), with p99 `6.63` и `11.81 ms/frame`.
  Endpoint parity and deterministic replay were verified by double-run equality check.
- Authorized renderer-control delta removes persistent trace from desktop bounds/paint/toggle while
  retaining the application ledger; desktop speed maps exactly to `0.10..2.00×` in `0.05×` steps.
- Comparable K=25/600-frame offscreen paint improved `≈3.66→2.00 ms/frame`; retained ledger ended
  at 601 points. Targeted component/Ruff/mypy/overlay PASS.
- FS-021 static scene cache is now implemented: original/reconstruction geometry and scene bounds are
  cached until curve/reconstruction/selection changes; dynamic vectors are painted each frame.
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
- PySide6 shell exists as a partial FS-021 source-run slice; live GUI/shutdown/persistence and
  measured renderer optimization remain before terminal completion.
- Lexical local-path guard не доказывает physical locality mapped/reparse targets; hardening остаётся
  FS-023 residual risk.

## Следующее разумное действие

После отдельной команды продолжить FS-021: если новые профили на целевом железе ухудшат
показатели, перейти к bounded QML/QT scene-graph spike и затем выполнить финальные docs/tests gates.
FS-022 и planned Android FS-031 не начинать заодно.

## Синхронизация документации

- Обновлены README, SPEC/ADR, architecture/design/security/testing/traceability/dependencies/
  fallbacks и AI plan/status/roadmap/stage registry.
- Математический/API/export contract проверен: FS-018 добавляет discontinuous application API,
  но не меняет persistence/export contracts FS-022.
- `docs/LEARNING_LOG.md` проверен без изменений: stage не добавил новую повторно полезную
  диагностику сверх принятых graph contracts и regression evidence.
