# Состояние проекта для ИИ

## Текущий этап

- Active Stage ID: `FS-012`.
- Lifecycle: `in_progress`.
- Branch: `feature/fs-012-dominant-contour`.
- Goal: dominant external contour → normalized closed `Curve` → arc-length resampling → existing
  Fourier/epicycle endpoint trace.
- Authorization: пользователь разрешил слияние предыдущей ветки и продолжение 2026-08-28.

## Подтверждённо реализовано

- FS-000/FS-001: scaffold и immutable domain model.
- FS-002–FS-005: Fourier transforms, spectrum/selection/reconstruction/metrics и epicycle math.
- FS-006: timeline, immutable renderer frame, Matplotlib/Agg adapters и locale boundary.
- FS-007–FS-009: bounded freehand path, live controls и arc-length parameterization.
- FS-010: safe local PNG/JPEG preprocessing.
- FS-011: threshold-boundary/Canny diagnostics с typed provenance и fail-closed backend boundary.

## Baseline перед FS-012

- Локальный `main`: `8a15a9e`; FS-007–FS-011 и post-merge status синхронизированы.
- Full suite: 299 tests PASS.
- Ruff, mypy, frozen sync, overlay validator и diff check: PASS.
- FS-011 independent security re-review: GO, новых P0/P1/P2 нет.
- Remote `origin/main` не обновлялся; push/PR/release не выполнялись.

## В процессе

- Typed contour extraction contracts и OpenCV external-contour adapter.
- Project-owned deterministic dominant selection и canonical coordinate/orientation/start policy.
- Application/CLI vertical slice до actual timeline endpoint trace и diagnostic PNG.
- Новые FS-012 tests и terminal documentation/evidence sync.

## Известные блокеры

- Нет.

## Ограничения / deferred

- В FS-012 выбирается только один внешний контур; multi-component semantics отложены до FS-016.
- Open/dangling edge fragments не превращаются скрыто в closed curve.
- Product-level image workflow и polish относятся к FS-013.
- Skeleton, graph и forced routing не входят в этап.
- Surface остаётся диагностическим Matplotlib/CLI, не финальным PySide6 shell.

## Следующая задача

Завершить только `FS-012`, собрать terminal evidence, выполнить независимый review и остановиться до
`FS-013`.

## Синхронизация документации

- `docs/AI_PLAN.md`, `docs/AI_STATUS.md`, `docs/ROADMAP.md` и record `FS-012` активированы.
- Остальные state-bearing документы будут обновлены после подтверждённой реализации и проверок.
- `prompts/STAGES.md` остаётся каноническим stage registry вне `docs/`.
