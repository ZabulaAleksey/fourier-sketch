# План работы ИИ

## Текущая цель

Реализовать Stage `FS-004`: явный coefficient selection, continuous/discrete partial
reconstruction и определённые error/energy metrics. Lifecycle: `in_progress`.

## Связанные требования

- SPEC: `specs/features/fourier-core.spec.md`.
- IDs: FC-FR-005, FC-FR-006, FC-AC-003, FC-AC-004, FR-HARMONICS-001, AC-SYS-010.
- Stage contract: `prompts/STAGES.md`, heading `FS-004`.

## Stage identity и dependency DAG

- Stage ID: `FS-004`.
- Completed prerequisite: FS-003 implementation `f004f68`, 75 tests and all quality gates PASS.
- DAG: `FS-003 → FS-004`; no cycle/forward dependency.
- Entry gate: satisfied; user authorized the FS-002–FS-006 sequence.

## Runnable vertical slice и consumer scenario

- Entry: consumer transforms a canonical circle or square and chooses K/order or an explicit set.
- Path: complete spectrum → `CoefficientSelection` → reconstruction grid → metrics.
- Observable result: full selection matches FS-002 IDFT; partial selection returns finite points,
  retained energy and defined error diagnostics without FS-005.

## Scope / non-goals / invariants

- Scope: immutable 1..N selection; first-K deterministic ordering; explicit unique subset;
  continuous/discrete reconstruction; MSE/RMSE/max/normalized error; retained energy.
- Non-goals: epicycle geometry, timeline, renderer and monotonic-error claims for arbitrary order.
- Invariants: selection is not a partial `FourierSpectrum`; caller's explicit order is preserved;
  selected bins belong to one complete spectrum; aligned inputs only; no silent NaN/Inf.
- Zero-reference rule: normalized error is `0` only for exact reconstruction; otherwise a typed
  undefined state. Zero-energy retained ratio is `1` for full selection and `0` for partial.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Verify FS-003 terminal evidence and FS-004 entry | completed |
| 2 | Implement selection and reconstruction contracts | in_progress |
| 3 | Implement metrics and degenerate-state semantics | pending |
| 4 | Add unit/property/integration contracts | pending |
| 5 | Run full/static/overlay/reviewer/SPEC gates | pending |
| 6 | Synchronize docs and commit FS-004 | pending |

## Acceptance / PASS

- [ ] Every valid selection contains exactly the requested 1..N unique spectrum bins.
- [ ] Full selection reconstruction matches FS-002 IDFT on the canonical sample grid.
- [ ] Partial continuous/discrete reconstruction follows the documented Fourier formula.
- [ ] Metrics are finite and zero-denominator behavior is explicit and typed.
- [ ] Retained energy follows the documented zero-energy convention.
- [ ] Full quality/reviewer/documentation gates pass.

## Deferred

- Epicycle chain (`FS-005`), diagnostic timeline/renderer (`FS-006`) and performance claims.

## Условие перехода

FS-005 начинается только после FS-004 terminal evidence и commit.
