# План работы ИИ

## Текущая цель

Stage `FS-006` завершён: первый user-facing diagnostic Matplotlib renderer использует реальный
timeline/controller, endpoint-only trace, headless CLI и resource-key locale boundary.
Lifecycle: `completed`; implementation commit `1abc0be`.

## Связанные требования

- SPEC: `specs/features/epicycle-animation.spec.md`, `specs/system.spec.md`.
- IDs: EP-FR-004..006, EP-AC-004..005, BH-EPICYCLE-TRACE-001, BH-ANIMATION-001,
  FR-I18N-001, AC-SYS-004, AC-SYS-010, AC-SYS-011, SEC-RESOURCE-001, SEC-PATH-001.
- Stage contract: `prompts/STAGES.md`, heading `FS-006`.

## Stage identity и dependency DAG

- Stage ID: `FS-006`.
- Completed prerequisite: FS-005 implementation `419b60c`, 124 tests and re-review PASS.
- DAG: `FS-005 → FS-006`; no cycle/forward dependency.
- Entry gate: satisfied; immutable chain state and endpoint property are accepted and committed.

## Runnable vertical slice и live product scenario

- Entry: `python -m fourier_sketch.cli.diagnostic --headless --output <path>` with canonical curve.
- Path: fixture → FFT → selection → chain timeline → endpoint history → Matplotlib Agg PNG.
- Observable result: non-empty PNG with circles/vectors/endpoint/trace generated through actual
  application/math/renderer code, plus the same controller in a manual interactive window.

## Scope / non-goals / invariants

- Scope: Matplotlib dependency/adapter; timeline play/pause/restart/speed/harmonics; six visibility
  toggles; original/reconstruction overlays; headless CLI; `en` resources and pseudo/fallback.
- Non-goals: freehand capture, PySide6 shell, image input, GIF/video/export codec framework.
- Invariant: renderer receives `EpicycleFrame`; it never computes coefficients, vector geometry or
  trace point. Each appended trace point is exactly `frame.chain.endpoint`.
- Interactive harmonic count is `1..min(N, 4096)`; speed is finite `0 < speed ≤ 100`.
- Restart semantics: pause, set time `0`, discard old trace and retain exactly the new time-zero
  endpoint. Harmonic changes also discard stale trace and retain one current endpoint.
- Existing output path fails closed; no overwrite is performed by the diagnostic CLI.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Verify FS-005 terminal evidence and renderer dependency/license review | completed |
| 2 | Add Matplotlib through uv and implement locale resources | completed |
| 3 | Implement frame/timeline/controller contracts | completed |
| 4 | Implement Matplotlib headless/manual adapters and CLI | completed |
| 5 | Add unit/integration/component/live E2E contracts | completed |
| 6 | Run full/static/overlay/reviewer/security/i18n gates | completed |
| 7 | Synchronize docs and commit FS-006 | completed |

## Acceptance / PASS

- [x] Trace is derived exclusively from chain endpoints across advance/restart/count changes.
- [x] Controls and visibility have explicit validated state transitions without math mutation.
- [x] Circle/vector/endpoint geometry is consumed directly from `EpicycleChainState`.
- [x] Default/fallback/pseudo-locale resource checks pass with no hardcoded app labels.
- [x] Headless live CLI creates a sane PNG and rejects an existing destination.
- [x] Matplotlib, unit/property/integration/component/E2E/full/static/overlay/review gates pass.

## Deferred

- Freehand (`FS-007`), full PySide6 product shell (`FS-021`) and animation export (`FS-022`).

## Условие завершения

Terminal evidence FS-006 зафиксирован. Активного implementation stage нет; FS-007 остаётся
`planned` до отдельной авторизации. Merge/push/PR не выполнялись.
