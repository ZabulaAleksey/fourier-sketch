# Состояние проекта для ИИ

## Текущий этап

- Last completed Stage ID: `FS-014`.
- Active Stage ID: `FS-015`, lifecycle `in_progress`.
- Branch: `feature/fs-015-skeleton-graph`, создана от `main@aba291d`.
- Integration state: `main` и `origin/main` синхронизированы на `aba291d` до активации stage.
- Scope: raster skeleton topology graph; FS-016 PiecewiseCurve и FS-017 routing не активированы.
- Push/PR/release/deployment не выполнялись.

## Подтверждённо реализовано

- `FS-000`–`FS-006`: scaffold, immutable domain model, Fourier pipeline, metrics, epicycle math,
  timeline и диагностический Matplotlib/Agg renderer.
- `FS-007`–`FS-009`: bounded freehand input, live freehand-to-trace MVP и arc-length
  parameterization.
- `FS-010`–`FS-011`: безопасный локальный PNG/JPEG preprocessing и typed threshold/Canny edge
  diagnostics.
- `FS-012`: bounded external-contour extraction, project-owned deterministic dominant selection,
  canonical orientation/start point, normalized `Curve`, resampling и реальный
  image → contour → Fourier → epicycle endpoint-trace CLI/E2E путь.
- `FS-013`: generation-safe `ImageMvpController`, background Matplotlib surface, четыре панели
  intermediates/contour/epicycles, preprocessing/edge/sample/harmonic/speed controls, явные
  initial/processing/ready/empty/error/cancelled states и единый interactive/headless live path.
- `FS-014`: explicit scikit-image 0.26.x Lee adapter, immutable skeleton/provenance contracts,
  4 000 000 foreground budget, generation-safe controller, atomic skeleton/preview PNG и local CLI.
- Пустой либо непригодный contour возвращает явный no-contour result без выдуманного outline или
  скрытого fallback.

## Evidence FS-013

- Activation commit: `92660de`.
- Targeted unit/integration/component/live E2E suite: 29 tests PASS после security/correctness fixes.
- Full terminal repository suite: 387 tests PASS.
- `uv sync --all-groups --frozen`, Ruff, strict mypy, project-overlay validator и diff check: PASS.
- Визуальная проверка четырёхпанельного PNG с ellipse, выбранным contour и endpoint trace: PASS.
- Независимые correctness/security reviews: GO после atomic no-overwrite, unsafe-path и Unicode
  hardening; обязательных P0/P1/P2 findings не осталось.

## Известные блокеры

- Нет.

## Evidence FS-014

- Activation commit: `b4c8c27`.
- Targeted unit/integration/component/live E2E suite: 40 tests PASS.
- Full terminal repository suite: 427 tests PASS.
- `uv sync --all-groups --frozen`, Ruff, strict mypy, project-overlay validator и diff check: PASS.
- Synthetic line/T/cross/loop/noise, real PNG/JPEG, empty/cancel/stale, corrupt/private-path,
  no-overwrite и malformed backend scenarios: PASS.
- Независимые correctness/security re-reviews: GO после local-path/import-time/solid-`2×2`
  hardening; обязательных findings не осталось.

## Ограничения / deferred

- Выбирается один внешний контур; multi-component semantics отложена до `FS-016`.
- Open/dangling edge fragments не преобразуются в замкнутую кривую.
- Skeleton graph, component semantics и forced routing остаются FS-015–FS-017.
- Диагностическая поверхность остаётся Matplotlib/CLI, а не финальным PySide6 shell.
- OpenCV работает как in-process native dependency: Python-код ограничивает размер входа и
  число кандидатов, но native crash нельзя преобразовать в typed Python error.

## Текущее действие

Реализовать и проверить FS-015 по active plan; merge/push не выполнять без отдельного разрешения.

## Синхронизация документации

- README, AI plan/status/roadmap/stage registry, architecture/decisions/design, security/testing,
  traceability/dependencies/fallbacks синхронизированы с validated FS-014.
- Post-merge Completion Documentation Synchronization Gate выполнен для локального `main`;
  integration evidence отражает fast-forward merge FS-013/FS-014 и отсутствие push.
- Стабильные system/image-to-curve/desktop-export SPEC и математический контракт проверены: требования не
  изменились, поэтому обновление не потребовалось.
- `prompts/STAGES.md` остаётся каноническим stage registry вне `docs/`.
