# Состояние проекта для ИИ

## Текущий этап

- Stage ID: `FS-004`.
- Lifecycle: `in_progress`.
- Evidence level: FS-003 committed and verified; FS-004 not yet implemented.
- Branch: `feature/fs-002-fs-006-core-renderer`.

## Подтверждённо реализовано

- FS-000/FS-001 project scaffold and immutable domain model.
- FS-002 conversion, canonical signed bins, bounded reference DFT, explicit NumPy FFT and IDFT.
- FS-003 spectrum energy and deterministic complete-spectrum ordering views.
- FS-003 implementation commit: `f004f68`.

## FS-003 evidence

- Frozen restore: PASS, 17 packages.
- Unit/property/integration/component/full: PASS; full suite 75 tests.
- Ruff/mypy/overlay/diff: PASS.
- Reviewer: no P0/P1; overflow-safe magnitude and even-N Nyquist test fixes verified.

## В процессе

- FS-004 coefficient selection, reconstruction and metrics.

## Известные блокеры

- None.

## Ограничения / deferred

- No epicycle chain or user-facing renderer yet.
- Reference and NumPy backends remain explicit; no automatic fallback.

## Следующая задача

Finish FS-004 and commit its evidence before FS-005.

## Интеграция

- Current branch only; merge/push/release NOT PERFORMED.

## Синхронизация документации

- FS-003 implementation and terminal evidence synchronized; FS-004 exact selector activated.
- `DESIGN.md`, `SECURITY.md`, `DEPENDENCIES.md` and `FALLBACKS.md` checked without changes.
