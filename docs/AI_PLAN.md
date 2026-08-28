# План работы ИИ

## Текущая цель

Реализовать Stage `FS-009`: добавить uniform arc-length resampling, измеримые spacing diagnostics
и selectable comparison с принятым `uniform_index` в существующем freehand MVP. Lifecycle:
`in_progress`.

## Связанные требования

- SPEC: `specs/system.spec.md`, `specs/features/fourier-core.spec.md`,
  `specs/features/epicycle-animation.spec.md`.
- IDs: FR-CURVE-001, FR-DRAW-001, FC-FR-002, FR-EPICYCLE-TRACE-001, AC-SYS-003,
  AC-SYS-004, AC-SYS-010.
- Stage contract: `prompts/STAGES.md`, heading `FS-009`.

## Stage identity и dependency DAG

- Stage ID: `FS-009`.
- Completed prerequisite: FS-008 implementation `0c4bfb2`, 192 tests and reviewer GO.
- DAG: `FS-008 → FS-009`; no cycle/forward dependency.
- Entry gate: satisfied; representative freehand workflow and index-resampling baseline committed.

## Runnable vertical slice и live product scenario

- Entry: user draws or supplies a non-uniform polyline and selects resampling method/sample count.
- Path: cleaned source Curve → selected index/arc-length method → spacing metrics → existing
  FFT/timeline/controls → endpoint trace.
- Observable result: both methods run through the same MVP; diagnostics report actual segment
  spacing, while zero-total-length arc-length input produces a typed controlled failure.

## Scope / non-goals / invariants

- Scope: cumulative polyline length; open/closed interpolation; explicit method value; spacing
  metrics/comparison; MVP method selector; unit/property/integration/component/live E2E evidence.
- Non-goals: adaptive/curvature sampling FS-028, simplification FS-027, image input FS-010+.
- Open endpoints remain exact; closed seam is included in length and output has no repeated first
  endpoint; order is preserved.
- `uniform_index` semantics remain unchanged and one-point DC remains available through it.
- Arc-length zero-total-length input fails typed; no silent switch to index resampling.
- Output sample budget remains `1..4096`; no unbounded dense intermediate.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Confirm FS-008 prerequisite and exact FS-009 contract | completed |
| 2 | Implement arc-length resampling and spacing metrics | in_progress |
| 3 | Add explicit method through capture and existing MVP selector | pending |
| 4 | Add unit/property/integration/component/live comparison evidence | pending |
| 5 | Run full/static/overlay/reviewer and measured diagnostics | pending |
| 6 | Synchronize docs and commit FS-009 | pending |

## Acceptance / PASS

- [ ] Open order/endpoints and closed seam/topology are preserved for bounded N.
- [ ] Zero total length is a typed failure; index baseline does not change silently.
- [ ] Spacing diagnostics measure both methods on the same representative source.
- [ ] Existing MVP selector runs arc-length Curve through the same timeline/endpoint trace.
- [ ] Unit/property/integration/component/E2E, full/static/overlay and reviewer gates pass.

## Deferred

- Adaptive sampling (`FS-028`), simplification (`FS-027`) and image input (`FS-010+`).

## Условие завершения

После terminal evidence FS-009 активировать только FS-010 и не начинать FS-011 до отдельного
completion gate. Merge/push/PR выполняются только по отдельному разрешению пользователя.
