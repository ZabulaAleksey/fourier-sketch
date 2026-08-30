# План работы ИИ

## Текущая цель

Получить недостающее manual visible Windows GUI/DPI/resize evidence для FS-021, не подменяя его
offscreen/component проверками. Интегрированный desktop navigation/color slice сохраняет стабильный
rainbow color по selection order и presentation-only bounded viewport.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; renderer-control, предыдущие UI fixes и touch/rainbow slice интегрированы
  в `main`; manual visible evidence gate остаётся открытым.
- Integration: `cb323e2` находится в локальном `main`; push не выполнялся.
- DAG: `FS-013 + FS-018 + FS-020 → FS-021`; prerequisites completed locally.
- Contract: UI dispatches existing use cases; optimization preserves actual endpoint history and
  begins with measured QPainter improvements before any QML/GPU decision.

## Integration state

- `main` содержит renderer-control implementation `0faf8fc`, последующие UI commits
  `644fd82`/`7d53100`/`66ec1ef`/`7cf355d`, touch/rainbow `cb323e2` и планирование
  routing/basis `29b23ca`.
- PR/release/deployment не выполнялись; публикация `main` в `origin` — отдельное Git evidence,
  не доказательство ручной visual/DPI проверки.

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
8. [completed] Сделать center freehand field chain origin, связать wheel/slider zoom, раскрасить
   vector/circle по rainbow order и disabled-state Cancel без background job.
9. [completed] Стабилизировать rainbow color по selection position при росте K, выровнять color
   vector/circle pair и добавить one-finger touch pan/two-finger anchored pinch с component regressions.
10. [pending] Только при недостигнутом target выполнить bounded Qt Quick/QML scene-graph spike.
11. [blocked] Offscreen component path для freehand и image, cancellation/shutdown/persistence
   подтверждён; review P2 для `cancelled` status и CLI persistence исправлены. Accessibility-only
   fallback подтвердил actual window hierarchy/keyboard controls; lingering job после bounded terminate
   безопасно retained до finish. Manual mouse/image/DPI/resize diagnostic не получен: screenshot capture
   повторно завершился `SetIsBorderRequired failed (0x80004002)`. После его получения выполнить final
   review/docs gates; затем остановиться до FS-022.

## Handoff

Продолжить только FS-021 manual visible Windows GUI/DPI/resize evidence. Не начинать FS-022,
FS-023, FS-031 или FS-032, пока lifecycle FS-021 остаётся `partial`.
