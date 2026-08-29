# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-016`; validated and committed locally at `721694d`.
- Active Stage ID: `FS-017`, lifecycle `in_progress`.
- Branch: `feature/fs-017-forced-routing`, chained from unmerged FS-016.
- Base/integration target: `main` и `origin/main@aba291d`; branch chain не merged/pushed.
- Blockers: нет.

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

## Evidence FS-016

- Activation commit: `1af0de4`.
- Targeted unit/property/integration/component/live E2E suite: 26 tests PASS.
- Full terminal repository suite: 476 tests PASS.
- Ruff, strict mypy и project-overlay validator: PASS.
- Визуальная проверка two-ring pen-up overlay: PASS; два отдельных artists, connector отсутствует.
- Bounded cancellation, atomic no-overwrite и privacy-safe corrupt-input regressions: PASS.
- Correctness review P2 по non-finite/overflow scale, untyped result/provenance, forged exact
  coverage и non-canonical traversal order исправлены; final re-review: `GO`.

## Limits / deferred

- Graph foreground `≤250,000`, node+edge records `≤500,000`, canonical JSON `≤32 MiB`.
- Canonical IDs/serialization и `LOOP_ANCHOR` не являются traversal order.
- Forced continuous route отложен до FS-017, Piecewise Fourier — до FS-018.
- Matplotlib/CLI остаются diagnostic surface; PySide6 shell относится к FS-021.
- Lexical local-path guard не доказывает physical locality mapped/reparse targets; hardening остаётся
  FS-023 residual risk.

## Следующее разумное действие

Реализовать и проверить FS-017; merge/push не выполнять. После terminal commit активировать FS-018.

## Синхронизация документации

- Обновлены README, SPEC/ADR, architecture/design/security/testing/traceability/dependencies/
  fallbacks и AI plan/status/roadmap/stage registry.
- Математический/API/export contract проверен: FS-016 публикует PiecewiseCurve, но не меняет
  Fourier/public export/persistence contracts; они остаются FS-018/FS-022.
- `docs/LEARNING_LOG.md` проверен без изменений: stage не добавил новую повторно полезную
  диагностику сверх принятых graph contracts и regression evidence.
