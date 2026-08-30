# План работы ИИ

## Текущая цель

Подготовить следующий bounded FS-021 renderer optimization slice: cache static paths/bounds и
повторный stress profile, не начиная работу без отдельной команды пользователя.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; renderer-control slice завершён и локально интегрирован в `main`.
- Branch: `main` после fast-forward integration renderer-control delta.
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
   `0.10..2.00×`, step `0.05×`; сохранить application endpoint ledger.
3. [completed] Кэшировать static paths и static bounds по изменению curve/reconstruction/selection;
   перейти на повторно используемый scene-viewport pass.
4. [completed] Повторить stress profile и закрепить метрику по default/stress конфигу.
5. [pending] Только при недостигнутом target выполнить bounded Qt Quick/QML scene-graph spike.
6. [pending] Закрыть live freehand+image GUI, cancellation/shutdown/persistence, DPI/resize и final
   review/docs gates; затем остановиться до FS-022.

## Handoff

После synchronization commit отправить `main` в `origin` и остановиться. Остальные performance
steps FS-021, FS-022 и FS-031 не начинать без отдельной команды пользователя.
