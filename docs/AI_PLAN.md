# План работы ИИ

## Текущая цель

Реализовать Stage `FS-008`: превратить подтверждённый freehand input slice в один cohesive
freehand-to-trace MVP с controls, restart/error flow и live E2E evidence. Lifecycle: `in_progress`.

## Связанные требования

- SPEC: `specs/system.spec.md`, `specs/features/epicycle-animation.spec.md`,
  `specs/features/desktop-export.spec.md`.
- IDs: FR-DRAW-001, FR-FOURIER-001, FR-EPICYCLE-001, FR-EPICYCLE-TRACE-001, EP-FR-006,
  EP-AC-006, UI-AC-001, AC-SYS-004, AC-SYS-010, AC-SYS-011.
- Stage contract: `prompts/STAGES.md`, heading `FS-008`.

## Stage identity и dependency DAG

- Stage ID: `FS-008`.
- Completed prerequisite: FS-007 implementation `2eae8bc`, 186 tests and reviewer GO.
- DAG: `FS-007 → FS-008`; no cycle/forward dependency.
- Entry gate: satisfied; actual pointer capture, provenance and endpoint renderer path committed.

## Runnable vertical slice и live product scenario

- Entry: user launches one documented freehand command and draws a non-degenerate curve.
- Path: actual UI events → `FreehandCapture` → Curve → FFT → selection → chain timeline →
  endpoint trace, with parameter controls and restart/error handling on the same surface.
- Observable result: trace history equals recorded chain endpoint history; controls change the same
  timeline, and reset/error states never expose a fabricated or stale result.

## Scope / non-goals / invariants

- Scope: cohesive runnable entry point; harmonic/speed/play/pause/restart controls; explicit
  validation/recovery; automated actual-event E2E plus diagnostic artifact/data evidence.
- Non-goals: arc-length algorithm FS-009, image processing FS-010+, final PySide6 shell FS-021.
- Existing `FreehandCapture`, FFT, `EpicycleTimeline` and `draw_frame` stay the only computation
  path; FS-008 does not introduce a parallel MVP pipeline.
- Persistent trace contains only `EpicycleChainState.endpoint` values.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Confirm FS-007 prerequisite and exact FS-008 contract | completed |
| 2 | Add cohesive controls and restart/error lifecycle to the same surface | in_progress |
| 3 | Add documented diagnostic execution/artifact path without duplicating math | pending |
| 4 | Add unit/integration/component/live E2E endpoint-history evidence | pending |
| 5 | Run full/static/overlay/reviewer and manual visual gates | pending |
| 6 | Synchronize docs and commit FS-008 | pending |

## Acceptance / PASS

- [ ] One documented command exposes actual drawing, controls and recovery.
- [ ] Play/pause/speed/harmonic/restart operate on the timeline built from the captured stroke.
- [ ] Actual event E2E asserts trace values against recorded chain endpoints.
- [ ] Invalid/reset flows leave no stale or decorative trace.
- [ ] Component/live E2E, full suite, Ruff, mypy, overlay, visual and reviewer gates pass.

## Deferred

- Arc-length (`FS-009`), images (`FS-010+`) and final PySide6 shell (`FS-021`).

## Условие завершения

После terminal evidence FS-008 активировать только FS-009 и не начинать FS-010 до отдельного
completion gate. Merge/push/PR выполняются только по отдельному разрешению пользователя.
