# План работы ИИ

## Текущая цель

Подготовить отдельный проверяемый slice FS-022 для data/image/animation export поверх завершённого
desktop/application timeline, не включая packaging hardening FS-023 или optional extensions.

## Активный stage

- Stage ID: `FS-022`
- Lifecycle: `planned`; реализация export ещё не начата.
- Prerequisite: FS-021 `completed`; automated/component evidence и user-confirmed manual visible
  Windows GUI/DPI/resize + physical-touch checklist получены.
- Contract: export должен потреблять существующие Curve/coefficient/timeline/endpoint данные без
  отдельного математического или animation-state path.

## Integration state

- `main` содержит завершённый FS-021, включая renderer-control `0faf8fc`, последующие UI commits
  `644fd82`/`7d53100`/`66ec1ef`/`7cf355d` и touch/rainbow `cb323e2`.
- Push/PR/release/deployment не выполнялись; публикация `main` в `origin` остаётся отдельным
  не выполненным Git action.

## План выполнения

1. [pending] Прочитать и проверить FS-022 Stage contract, export SPEC/ADR и существующие serialization
   boundaries; определить минимальный runnable export slice.
2. [pending] Реализовать FS-022 строго через существующие immutable application/timeline данные.
3. [pending] Добавить unit/integration/component/live export evidence, выполнить full quality gates,
   review и Completion Documentation Synchronization Gate.

## Handoff

FS-021 завершён. Следующая работа ограничена FS-022; не начинать FS-023, FS-031 или FS-032 заодно.
