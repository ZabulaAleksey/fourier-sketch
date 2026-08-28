# Состояние проекта для ИИ

## Текущий этап

- Последний завершённый Stage ID: `FS-012`.
- Lifecycle: `completed`.
- Рабочая ветка: `feature/fs-012-dominant-contour`.
- Следующий этап: `FS-013` (`planned`, не начат).
- Локальный `main`: `8a15a9e`; текущая ветка ещё не слита и не отправлена в remote.

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
- Пустой либо непригодный contour возвращает явный no-contour result без выдуманного outline или
  скрытого fallback.

## Evidence FS-012

- Implementation commits: `418192a`, `a1c211c`; activation commit: `cee63d0`.
- Targeted unit/integration/component/E2E/property suite: 59 tests PASS.
- Full repository suite: 358 tests PASS.
- `uv sync --all-groups --frozen`, Ruff, strict mypy, project-overlay validator и diff check: PASS.
- Визуальная проверка диагностического PNG с выбранным ellipse contour и endpoint trace: PASS.
- Независимые correctness и security re-review: GO; новых P0/P1/P2 замечаний нет.

## Известные блокеры

- Нет.

## Ограничения / deferred

- Выбирается один внешний контур; multi-component semantics отложена до `FS-016`.
- Open/dangling edge fragments не преобразуются в замкнутую кривую.
- Product-level image workflow и polish относятся к `FS-013`.
- Skeleton, graph и forced routing не входят в `FS-012`.
- Диагностическая поверхность остаётся Matplotlib/CLI, а не финальным PySide6 shell.
- OpenCV работает как in-process native dependency: Python-код ограничивает размер входа и
  число кандидатов, но native crash нельзя преобразовать в typed Python error.

## Следующее разумное действие

После явного разрешения слить `feature/fs-012-dominant-contour` в `main`, выполнить post-merge
documentation gate и только затем отдельно активировать `FS-013`.

## Синхронизация документации

- `README.md`, `docs/AI_PLAN.md`, `docs/AI_STATUS.md`, `docs/ROADMAP.md`, `prompts/STAGES.md`,
  архитектурные, design, security, testing, traceability, dependency, fallback и learning
  документы синхронизированы с проверенным состоянием `FS-012`.
- Стабильные system/image-to-curve SPEC и математический контракт проверены: требования не
  изменились, поэтому обновление не потребовалось.
- `prompts/STAGES.md` остаётся каноническим stage registry вне `docs/`.
