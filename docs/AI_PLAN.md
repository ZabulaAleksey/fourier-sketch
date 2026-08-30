# План работы ИИ

## Текущая цель

Проверить и интегрировать FS-021 canvas-navigation исправление: freehand contour не отражается
вертикально; колесо масштабирует, а LMB drag перемещает viewport. Сохранить manual Windows
GUI/DPI/resize evidence gate.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; renderer-control slice интегрирован в `main`, image/zoom parent fix и
  canvas-navigation fix локально проверяются в отдельных ветках.
- Branch: `fix/fs-021-canvas-navigation`; merge/push не выполнялись.
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
5. [completed] Для desktop image source включить default dark-ink/light-background preprocessing,
   добавить explicit reverse-polarity opt-out, bounded canvas zoom/reset и component regressions.
6. [completed] Перевести freehand screen Y в Cartesian input, добавить wheel zoom/LMB pan и reset
   viewport с component regressions.
7. [pending] Только при недостигнутом target выполнить bounded Qt Quick/QML scene-graph spike.
8. [blocked] Offscreen component path для freehand и image, cancellation/shutdown/persistence
   подтверждён; review P2 для `cancelled` status и CLI persistence исправлены. Accessibility-only
   fallback подтвердил actual window hierarchy/keyboard controls; lingering job после bounded terminate
   безопасно retained до finish. Manual mouse/image/DPI/resize diagnostic не получен: screenshot capture
   повторно завершился `SetIsBorderRequired failed (0x80004002)`. После его получения выполнить final
   review/docs gates; затем остановиться до FS-022.

## Handoff

После MDP остановиться на `main` и ожидать отдельной команды пользователя до следующего FS-021 slice.
