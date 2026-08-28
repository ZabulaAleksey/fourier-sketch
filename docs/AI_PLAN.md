# План работы ИИ

## Текущая цель

Реализовать critical milestone Stage `FS-005`: математическую head-to-tail epicycle chain и
доказать equivalence её endpoint с FS-004 reconstruction. Lifecycle: `in_progress`.

## Связанные требования

- SPEC: `specs/features/epicycle-animation.spec.md`.
- IDs: EP-FR-001, EP-FR-002, EP-FR-003, EP-AC-001..003, BH-EPICYCLE-001,
  BH-EPICYCLE-TRACE-001, AC-SYS-003, AC-SYS-005, AC-SYS-010.
- Stage contract: `prompts/STAGES.md`, heading `FS-005`.

## Stage identity и dependency DAG

- Stage ID: `FS-005`.
- Completed prerequisite: FS-004 implementation `743a859`, 110 tests and review PASS.
- DAG: `FS-004 → FS-005`; no cycle/forward dependency.
- Entry gate: satisfied; selected reconstruction API is accepted and committed.

## Runnable vertical slice и consumer scenario

- Entry: public API receives a `CoefficientSelection`, finite normalized time and optional origin.
- Path: coefficients → rotating local values → head-to-tail `EpicycleVector` values →
  `EpicycleChainState`.
- Observable result: every start/end/center/radius is renderer-ready and endpoint equals
  `origin + reconstruct_at(selection, time)` without FS-006.

## Scope / non-goals / invariants

- Scope: `v_k(t)`, DC/±k direction, phase/amplitude/angular velocity, sequential chain, origin,
  centers and endpoint.
- Non-goals: trace history, animation loop, Matplotlib/PySide, controls and mouse/image input.
- Invariants: first start equals origin; every next start equals previous end; every center equals
  vector start; endpoint equals last end; source selection order is preserved.
- Periodic evaluation accepts any finite time and reduces it to one period only for stable phase
  calculation; reported state time remains the caller value.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Verify FS-004 terminal evidence and FS-005 entry | completed |
| 2 | Implement rotating-vector and chain builders | in_progress |
| 3 | Add analytical/property/integration parity contracts | pending |
| 4 | Run full/static/overlay/reviewer/SPEC gates | pending |
| 5 | Synchronize milestone docs and commit FS-005 | pending |

## Acceptance / PASS

- [ ] DC is stationary; positive/negative frequency direction, phase and amplitude are analytical.
- [ ] Chain connectivity and domain structural invariants hold for every generated case.
- [ ] Coefficient permutation changes intermediate centers but not endpoint within tolerance.
- [ ] Endpoint equals origin plus FS-004 reconstruction for generated selections/times.
- [ ] Real FFT spectrum/selection flows into a public chain state.
- [ ] Full quality/reviewer/documentation gates pass.

## Deferred

- Persistent trace/timeline/renderer and controls (`FS-006`).

## Условие перехода

FS-006 начинается только после FS-005 endpoint-equivalence terminal evidence и commit.
