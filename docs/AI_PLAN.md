# План работы ИИ

## Текущая цель

Продолжить bounded FS-021 renderer control slice: не рисовать дублирующий trace-шлейф и сделать
desktop speed control плавным и безопасно ограниченным, не начиная FS-022.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; пользователь явно авторизовал bounded UI change 2026-08-29.
- Branch: `feature/fs-021-render-controls` from synchronized `main@cb36885`.
- DAG: `FS-013 + FS-018 + FS-020 → FS-021`; prerequisites completed locally.
- Contract: UI dispatches existing use cases; optimization preserves actual endpoint history and
  begins with measured QPainter improvements before any QML/GPU decision.

## Integration state

- Existing partial FS-021 and revised future stages are in `main@cb36885` and `origin/main@cb36885`.
- Renderer-control delta is committed locally at `0faf8fc`; it is not merged/pushed and no
  PR/release/deployment was performed.

## План выполнения

1. [completed] Добавить PySide6 source-run shell, worker dispatch, central canvas, freehand/image,
   keyboard/visibility controls и offscreen evidence.
2. [completed] Убрать trace из desktop paint/toggle и ограничить smooth speed slider диапазоном
   `0.10..2.00×`, step `0.05×`; сохранить application endpoint ledger.
3. [pending] Cache static paths/bounds и повторить stress profile; continuous paused redraw уже
   устранён и timer запускается только для running timeline.
4. [pending] Только при недостигнутом budget выполнить bounded Qt Quick/QML scene-graph spike.
5. [pending] Закрыть live freehand+image GUI, cancellation/shutdown/persistence, DPI/resize и final
   review/docs gates; затем остановиться до FS-022.

## Handoff

Bounded renderer-control delta reviewed and committed locally. Остановиться для отдельного решения
о merge; остальные performance steps FS-021, FS-022 и FS-031 не начинать заодно.
