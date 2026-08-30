# План работы ИИ

## Текущая цель

Завершить ограниченный FS-021 evidence slice: подтвердить desktop source workflows через реальные
component callbacks и синхронизировать контракты после изменения диапазона скорости.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; renderer-control slice завершён и локально интегрирован в `main`.
- Branch: `main`; desktop E2E and renderer-control deltas integrated and pushed.
- DAG: `FS-013 + FS-018 + FS-020 → FS-021`; prerequisites completed locally.
- Contract: UI dispatches existing use cases; optimization preserves actual endpoint history and
  begins with measured QPainter improvements before any QML/GPU decision.

## Integration state

- `main` содержит renderer-control implementation `0faf8fc` и evidence update `2c552a7`.
- PR/release/deployment не выполнялись; remote synchronization проверяется отдельно как внешнее
  integration evidence.

## План выполнения

1. [completed] Добавить PySide6 source-run shell, worker dispatch, central canvas, freehand/image,
   keyboard/visibility controls и offscreen evidence.
2. [completed] Убрать trace из desktop paint/toggle и ограничить smooth speed slider диапазоном
  `0.10..1.00×`, step `0.01×`; сохранить application endpoint ledger.
3. [completed] Кэшировать static paths и static bounds по изменению curve/reconstruction/selection;
   перейти на повторно используемый scene-viewport pass.
4. [completed] Повторить stress profile и закрепить метрику по default/stress конфигу.
5. [pending] Только при недостигнутом target выполнить bounded Qt Quick/QML scene-graph spike.
6. [partial] Offscreen component path для freehand и image, cancellation/shutdown/persistence
   подтверждён. Остаются ручной visible Windows GUI/DPI/resize diagnostic и final review/docs gates;
   затем остановиться до FS-022.

## Handoff

После MDP остановиться на `main` и ожидать отдельной команды пользователя до следующего FS-021 slice.
