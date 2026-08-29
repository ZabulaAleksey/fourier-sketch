# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-020`; validated and committed locally at `5895315`.
- Active Stage ID: `FS-021`, lifecycle `in_progress`.
- Branch: `feature/fs-021-pyside6-desktop-gui` from local `main@eee5334`.
- Base/integration target: local `main@eee5334`; `origin/main@aba291d` remains unpushed.
- Blockers: нет.

## FS-021 progress

- PySide6 source-run shell, freehand/image dispatch, background worker, canvas controls and
  offscreen component checks are implemented locally; merge/push are not performed.
- Targeted desktop component tests, Ruff, mypy, frozen sync and overlay validator pass.
- Full regression needs a repeatable final summary: the current host ended the run without it after
  initial progress, so it is not recorded as PASS evidence.

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
- Matplotlib/CLI остаются diagnostic surface; PySide6 shell относится к FS-021.
- Lexical local-path guard не доказывает physical locality mapped/reparse targets; hardening остаётся
  FS-023 residual risk.

## Следующее разумное действие

Выполнить FS-021 source-run PySide6 vertical slice; push и merge не авторизованы.

## Синхронизация документации

- Обновлены README, SPEC/ADR, architecture/design/security/testing/traceability/dependencies/
  fallbacks и AI plan/status/roadmap/stage registry.
- Математический/API/export contract проверен: FS-018 добавляет discontinuous application API,
  но не меняет persistence/export contracts FS-022.
- `docs/LEARNING_LOG.md` проверен без изменений: stage не добавил новую повторно полезную
  диагностику сверх принятых graph contracts и regression evidence.
