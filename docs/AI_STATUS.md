# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-015`; validated and committed locally at `da13e4f`.
- Active Stage ID: `FS-016`, lifecycle `in_progress`.
- Branch: `feature/fs-016-piecewise-components`, chained from unmerged FS-015.
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

## Evidence FS-015

- Activation commit: `f56c487`.
- Targeted analytical/property/integration/component/live E2E suite: 23 tests PASS, включая
  raw-cycle/public-budget, non-quadratic component scan и in-chain cancellation regressions.
- Full terminal repository suite после всех review fixes: 450 tests PASS.
- `uv sync --all-groups --frozen --no-cache`, Ruff, strict mypy и project-overlay validator: PASS.
- Визуальная проверка actual cross topology overlay и pseudo-locale layout: PASS.
- Correctness/security review обнаружил raw-cycle, constructor-budget, quadratic scan и
  cancellation-evidence gaps; все исправлены и final re-review завершён с verdict `GO`.

## Limits / deferred

- Graph foreground `≤250,000`, node+edge records `≤500,000`, canonical JSON `≤32 MiB`.
- Canonical IDs/serialization и `LOOP_ANCHOR` не являются traversal order.
- Multi-component `PiecewiseCurve` conversion отложена до FS-016, forced route — до FS-017.
- Matplotlib/CLI остаются diagnostic surface; PySide6 shell относится к FS-021.
- Lexical local-path guard не доказывает physical locality mapped/reparse targets; hardening остаётся
  FS-023 residual risk.

## Следующее разумное действие

Реализовать и проверить FS-016; merge/push не выполнять. После terminal commit активировать FS-017
в следующей chained feature branch по текущему пользовательскому разрешению.

## Синхронизация документации

- Обновлены README, SPEC/ADR, architecture/design/security/testing/traceability/dependencies/
  fallbacks и AI plan/status/roadmap/stage registry.
- Математический, API/export и data-model contracts проверены: FS-015 не меняет curve/Fourier,
  public export format FS-022 или persistence, поэтому отдельные изменения не потребовались.
- `docs/LEARNING_LOG.md` проверен без изменений: stage не добавил новую повторно полезную
  диагностику сверх принятых graph contracts и regression evidence.
