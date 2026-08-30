# План работы ИИ

## Текущая цель

Проверить и интегрировать FS-021 source-layout/zoom-range улучшение: freehand field центрируется с
epicycle canvas, а wheel zoom остаётся практически неограниченным. Сохранить manual Windows
GUI/DPI/resize evidence gate.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; renderer-control slice интегрирован в `main`, а UI fixes локально проверены
  в последовательности отдельных веток.
- Branch: `feat/fs-021-source-layout-and-zoom-range`; merge/push не выполнялись.
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
7. [completed] Центрировать freehand field с epicycle canvas в normal desktop layout и расширить
   presentation zoom до `0.01..100.00×` с component regression.
8. [pending] Только при недостигнутом target выполнить bounded Qt Quick/QML scene-graph spike.
9. [blocked] Offscreen component path для freehand и image, cancellation/shutdown/persistence
   подтверждён; review P2 для `cancelled` status и CLI persistence исправлены. Accessibility-only
   fallback подтвердил actual window hierarchy/keyboard controls; lingering job после bounded terminate
   безопасно retained до finish. Manual mouse/image/DPI/resize diagnostic не получен: screenshot capture
   повторно завершился `SetIsBorderRequired failed (0x80004002)`. После его получения выполнить final
   review/docs gates; затем остановиться до FS-022.

## Handoff

После MDP остановиться на `main` и ожидать отдельной команды пользователя до следующего FS-021 slice.
