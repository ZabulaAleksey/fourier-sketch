# Состояние проекта для ИИ

## Текущий этап

- Stage ID: `FS-006`.
- Lifecycle: `in_progress`.
- Evidence level: FS-005 committed and verified; FS-006 not yet implemented.
- Branch: `feature/fs-002-fs-006-core-renderer`.

## Подтверждённо реализовано

- FS-000/FS-001 project scaffold and immutable domain model.
- FS-002–FS-004 Fourier transforms, spectrum views, selection, reconstruction and metrics.
- FS-005 renderer-independent epicycle chain mathematics and endpoint equivalence.
- FS-005 implementation commit: `419b60c`.

## FS-005 evidence

- Frozen restore: PASS, 17 packages.
- Unit/property/integration/component/full: PASS; full suite 124 tests.
- Ruff/mypy/overlay/diff: PASS.
- Reviewer/re-review: PASS after typed angular-overflow and direct geometry evidence fixes.

## В процессе

- FS-006 Matplotlib dependency, application timeline, renderer, CLI and locale resources.

## Известные блокеры

- None.

## Ограничения / deferred

- First surface is diagnostic Matplotlib, not the final PySide6 shell.
- No freehand/image input or animation codec/export framework yet.

## Следующая задача

Finish FS-006 live headless/user-control evidence and stop before FS-007.

## Интеграция

- Current branch only; merge/push/release NOT PERFORMED.

## Синхронизация документации

- FS-005 endpoint milestone synchronized; FS-006 exact selector activated.
- Dependency/design/i18n/security docs require factual update during FS-006.
