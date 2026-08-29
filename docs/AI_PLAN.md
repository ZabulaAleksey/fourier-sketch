# План работы ИИ

## Текущая цель

Реализовать FS-021: source-run PySide6 desktop workflow с центральным Epicycles view.

## Активный stage

- Stage ID: `FS-021`
- Lifecycle: `in_progress`; пользователь авторизовал продолжение 2026-08-29.
- Branch: `feature/fs-021-pyside6-desktop-gui`, основана на local `main@eee5334`.
- DAG: `FS-013 + FS-018 + FS-020 → FS-021`; prerequisites completed locally.
- Contract: UI dispatches existing use cases; long work stays outside the GUI thread; the visible trace
  is the actual chain endpoint history.

## Integration state

- FS-015..FS-020 fast-forward merged into local `main@5895315`; merge-status documentation is
  `main@eee5334`.
- Push/PR/release/deployment не выполнялись; `origin/main@aba291d` remains unchanged.

## План выполнения

1. [in_progress] Проверить PySide6 platform/license contract, зафиксировать UI architecture и
   добавить source-run dependency through `uv`.
2. [pending] Реализовать immutable desktop state, bounded background jobs и central Epicycles view.
3. [pending] Подключить freehand и supported image к existing application paths и локализованным
   pages/states.
4. [pending] Закрыть offscreen component, live desktop, cancellation/shutdown, full/static/docs gates.

## Handoff

Работа идёт только в feature branch. После terminal evidence требуется отдельное разрешение на merge;
push не выполняется без отдельного запроса.
