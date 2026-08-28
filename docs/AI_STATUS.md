# Состояние проекта для ИИ

## Текущий этап

- Stage ID: `FS-005`.
- Lifecycle: `in_progress`.
- Evidence level: FS-004 committed and verified; FS-005 not yet implemented.
- Branch: `feature/fs-002-fs-006-core-renderer`.

## Подтверждённо реализовано

- FS-000/FS-001 project scaffold and immutable domain model.
- FS-002 conversion, canonical signed bins and explicit reference/NumPy transforms.
- FS-003 spectrum energy and deterministic complete-spectrum ordering views.
- FS-004 immutable selection, reconstruction, retained energy and typed error metrics.
- FS-004 implementation commit: `743a859`.

## FS-004 evidence

- Frozen restore: PASS, 17 packages.
- Unit/property/integration/component/full: PASS; full suite 110 tests.
- Ruff/mypy/overlay/diff: PASS.
- Reviewer/re-review: PASS after full-energy overflow and value-provenance evidence fixes.

## В процессе

- FS-005 epicycle rotation, chain geometry and endpoint equivalence.

## Известные блокеры

- None.

## Ограничения / deferred

- No persistent trace, user-facing renderer or controls yet.
- FS-004 reconstruction limits are 262144 output samples / 16777216 evaluated terms.

## Следующая задача

Finish FS-005 and commit endpoint-equivalence evidence before FS-006.

## Интеграция

- Current branch only; merge/push/release NOT PERFORMED.

## Синхронизация документации

- FS-004 implementation, ADR/security/math/learning evidence synchronized; FS-005 selector active.
- `DESIGN.md`, `DEPENDENCIES.md` and `FALLBACKS.md` checked without changes.
