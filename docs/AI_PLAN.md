# План работы ИИ

## Текущая цель

После восстановления пользовательского лимита продолжить FS-021 с measured renderer optimization;
до этого сохранить проверенный source-run PySide6 slice в `main` без запуска FS-022.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `partial`; пользователь явно остановил дальнейшее выполнение 2026-08-29.
- Branch: `feature/fs-021-pyside6-desktop-gui`, основана на local `main@eee5334`.
- DAG: `FS-013 + FS-018 + FS-020 → FS-021`; prerequisites completed locally.
- Contract: UI dispatches existing use cases; optimization preserves actual endpoint history and
  begins with measured QPainter improvements before any QML/GPU decision.

## Integration state

- FS-015..FS-020 fast-forward merged into local `main@5895315`; merge-status documentation is
  `main@eee5334`.
- Push/PR/release/deployment не выполнялись; `origin/main@aba291d` remains unchanged.

## План выполнения

1. [completed] Добавить PySide6 source-run shell, worker dispatch, central canvas, freehand/image,
   keyboard/visibility controls и offscreen evidence.
2. [pending] Убрать paused/unchanged redraw, cache static paths/bounds и сделать trace incremental/
   bounded; повторить default/stress frame profiles и parity.
3. [pending] Только при недостигнутом budget выполнить bounded Qt Quick/QML scene-graph spike.
4. [pending] Закрыть live freehand+image GUI, cancellation/shutdown/persistence, DPI/resize и final
   review/docs gates; затем остановиться до FS-022.

## Handoff

Пользователь разрешил локальный merge текущего partial slice в `main` и остановил дальнейшее
выполнение до восстановления лимита. После resume первым остаётся performance step FS-021;
FS-022 и FS-031 не начинать без новой явной команды.
