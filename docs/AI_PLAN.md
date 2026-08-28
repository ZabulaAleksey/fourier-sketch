# План работы ИИ

## Текущая цель

Реализовать Stage `FS-007`: bounded freehand capture с actual Matplotlib pointer events,
детерминированным cleanup/index resampling и передачей валидной Curve в существующий
Fourier/epicycle renderer. Lifecycle: `in_progress`.

## Связанные требования

- SPEC: `specs/system.spec.md`, `specs/features/epicycle-animation.spec.md`,
  `specs/features/desktop-export.spec.md`.
- IDs: FR-DRAW-001, FR-CURVE-001, FR-EPICYCLE-TRACE-001, EP-AC-006, UI-AC-001,
  SEC-RESOURCE-001, AC-SYS-004, AC-SYS-010, AC-SYS-011.
- Stage contract: `prompts/STAGES.md`, heading `FS-007`.

## Stage identity и dependency DAG

- Stage ID: `FS-007`.
- Completed prerequisite: FS-006 implementation `1abc0be`, 153 tests and reviewer GO.
- DAG: `FS-006 → FS-007`; no cycle/forward dependency.
- Entry gate: satisfied; renderer/controller/locale boundaries are accepted and committed.

## Runnable vertical slice и live product scenario

- Entry: documented Matplotlib freehand diagnostic command.
- Path: actual press/motion/release events → bounded capture → duplicate cleanup → explicit
  open/closed Curve → index resampling → FFT → `EpicycleTimeline` → endpoint trace/renderer.
- Observable result: a valid stroke starts real epicycle animation; empty/invalid/limit states are
  typed and user-visible without creating a nullable or fabricated timeline.

## Scope / non-goals / invariants

- Scope: capture lifecycle/reset/cap; duplicate cleanup; deterministic index resampling; one-point
  DC path; explicit open/closed semantics; Matplotlib event adapter; live diagnostic evidence.
- Non-goals: consolidated FS-008 workflow polish, arc-length FS-009, image input and PySide6.
- `MAX_CAPTURE_POINTS` is enforced before append; limit rejection is explicit, not silent sampling.
- Events outside the drawing axes never become `Point2D` values.
- Renderer and callbacks dispatch application commands; Fourier/chain/trace math remains in the
  existing application/math boundaries.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Confirm FS-006 prerequisite, baseline and exact FS-007 contract | completed |
| 2 | Implement pure cleanup/index resampling and bounded capture state | in_progress |
| 3 | Compose Curve → FFT → timeline and Matplotlib pointer adapter | pending |
| 4 | Add unit/property/integration/component/live diagnostic evidence | pending |
| 5 | Run full/static/overlay/reviewer gates | pending |
| 6 | Synchronize docs and commit FS-007 | pending |

## Acceptance / PASS

- [ ] Empty, one-point, duplicate, cap, reset and open/closed cases are explicit and tested.
- [ ] Index resampling preserves order and required endpoint/closed semantics.
- [ ] Actual Matplotlib callbacks produce the same typed capture/application path as manual input.
- [ ] Valid input reaches real FFT/timeline/chain/endpoint trace; no decorative trace path exists.
- [ ] Component/live diagnostic, full suite, Ruff, mypy, overlay and reviewer gates pass.

## Deferred

- Cohesive milestone controls/evidence (`FS-008`), arc-length (`FS-009`), images (`FS-010+`) and
  final PySide6 shell (`FS-021`).

## Условие завершения

После terminal evidence FS-007 активировать только FS-008 и не начинать FS-009 до отдельного
completion gate. Merge/push/PR выполняются только по отдельному разрешению пользователя.
