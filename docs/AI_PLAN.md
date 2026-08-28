# План работы ИИ

## Текущая цель

Реализовать Stage `FS-003`: deterministic spectrum energy и views/orderings без изменения
coefficient values и без partial selection. Lifecycle: `in_progress`.

## Связанные требования

- SPEC: `specs/features/fourier-core.spec.md`.
- IDs: FC-FR-004, FC-FR-005, FC-AC-003, FR-HARMONICS-001, AC-SYS-010.
- Stage contract: `prompts/STAGES.md`, heading `FS-003`.

## Stage identity и dependency DAG

- Stage ID: `FS-003`.
- Completed prerequisite: FS-002 implementation `cc65b5a`, all numerical gates PASS.
- DAG: `FS-002 → FS-003`; no cycle/forward dependency.
- Entry gate: satisfied; user already authorized the FS-002–FS-006 sequence.

## Runnable vertical slice и consumer scenario

- Entry: consumer transforms a canonical circle with `fft_dft`.
- Path: complete spectrum → energy summary → signed/absolute/amplitude/interleaved/explicit full
  ordering views.
- Observable result: `k=+1` is dominant and every view is a deterministic permutation of the same
  complete coefficient set.

## Scope / non-goals

- Scope: `SpectrumOrdering`, deterministic tie-breaks, complete explicit permutation and total
  squared-amplitude energy.
- Non-goals: partial K/explicit subset, reconstruction, metrics, epicycles and charts.
- Invariant: ordering never changes a coefficient or constructs an invalid partial spectrum.

## Tie-break contract

- signed: `frequency`;
- absolute: `(abs(frequency), frequency)`;
- amplitude: `(-amplitude, abs(frequency), frequency)`;
- interleaved: `0,+1,-1,+2,-2,…` over available bins;
- explicit: exactly one occurrence of every complete-spectrum frequency in caller order.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Verify FS-002 terminal evidence and FS-003 entry | completed |
| 2 | Implement ordering enum/views and energy API | in_progress |
| 3 | Add deterministic unit/property/integration contracts | pending |
| 4 | Run full/static/overlay/reviewer/SPEC gates | pending |
| 5 | Synchronize docs and commit FS-003 | pending |

## Acceptance / PASS

- [ ] All orderings are deterministic permutations of the same complete set.
- [ ] Explicit ordering rejects missing/duplicate/unknown frequencies.
- [ ] Energy equals `Σ|C_k|²`; zero spectrum energy is `0.0`.
- [ ] Circle fixture reports dominant `k=+1`.
- [ ] Full quality/reviewer/documentation gates pass.

## Deferred

- Partial selection and retained energy (`FS-004`), epicycles (`FS-005`), visualization (`FS-006`).

## Условие перехода

FS-004 начинается только после FS-003 terminal evidence и commit.
