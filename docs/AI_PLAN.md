# План работы ИИ

## Текущая цель

Реализовать Stage `FS-001`: только domain values, invariants, typed validation и public imports,
не начиная DFT, renderer или image pipeline. Lifecycle: `implemented_unverified`; реализация и
review завершены, финальный rerun/documentation/commit gate ещё выполняется.

## Связанные требования

- SPEC: `specs/features/fourier-core.spec.md`.
- IDs: FC-FR-001, AC-SYS-010.
- Stage contract: `prompts/STAGES.md`, heading `FS-001`.

## Stage identity и dependency DAG

- Stage ID: FS-001
- Completed / verified prerequisites: `FS-000` (`878f724`, validated locally and committed).
- DAG: `FS-000 → FS-001`.
- Self-reference/cycle/forward dependency: none.
- Entry gate: satisfied; user command received, clean FS-000 baseline passed, dedicated feature
  branch created.

## Входные предпосылки

| Предпосылка | Evidence доступности до старта |
|---|---|
| Frozen Python environment | `uv sync --all-groups --frozen` PASS, Python 3.12.5 |
| Package scaffold | `uv run pytest` PASS, 1 smoke test, commit `878f724` |
| Stable domain requirement | accepted Fourier Core SPEC |
| No existing accepted domain tests | repository test inventory before FS-001 |

## Самостоятельный runnable vertical slice

- Точка входа: public Python imports from `fourier_sketch.domain`.
- Path: construct domain values → validate invariants → convert/inspect plain values.
- Наблюдаемый результат: deterministic domain objects и typed validation errors.
- Infrastructure в stage: только domain package и его tests; no NumPy/GUI/CV.

## Concrete end-to-end scenario

1. Consumer imports `Point2D`, `Curve`, `PiecewiseCurve`, coefficient/spectrum и epicycle state
   value types.
2. Consumer создаёт valid objects и получает явные values/properties.
3. Invalid non-finite/empty/chain-inconsistent input получает typed error; unit consumer test PASS.

## Scope

### Входит

- domain dataclasses/value objects and validation;
- explicit open/closed and piecewise semantics;
- immutable/controlled collections;
- unit tests of invariants and API imports.

### Не входит

- complex conversion, DFT/FFT, vector rotation;
- renderer, mouse/image input, persistence/export;
- speculative adapters or empty modules for later stages.

## Рабочие задачи

| № | Задача | Depends | Статус |
|---|---|---|---|
| 1 | Re-read exact `FS-001` record and inspect Git/test baseline | FS-000 | completed |
| 2 | Add domain values with typed validation | 1 | completed |
| 3 | Add accepted unit contracts and public imports | 2 | completed |
| 4 | Run unit/full/lint/type/overlay gates | 3 | completed |
| 5 | Synchronize traceability/status/docs and commit | 4 | in_progress |

## Acceptance / PASS criteria

- [x] Public domain API represents every FS-001 value without future implementation.
- [x] Valid and invalid invariants have accepted unit evidence.
- [x] Domain layer has no UI/render/CV dependency.
- [ ] Full canonical checks pass; diff reviewed; documentation gate complete.

## Проверка

```powershell
uv run pytest -m unit
uv run pytest
uv run ruff check .
uv run mypy
py -3 ~/.codex/tools/validate_project_overlay.py .
```

## Допустимая временная реализация

- Plain typed Python value objects without serialization/framework integration.
- Она полностью обслуживает FS-001 consumer path; future DFT only consumes it.

## Deferred to future stages

- complex conversion/DFT (`FS-002`), spectrum operations (`FS-003`), rotating vector math
  (`FS-005`) и all user-facing paths.

## Риски и откат

- Не зафиксировать accidental convention в value types; math decisions остаются в MATHEMATICS.
- Contract conflict → stop, update SPEC/ADR after user decision; do not rewrite accepted tests.

## Definition of Done

- [x] `FS-000` terminal prerequisite подтверждён до старта.
- [x] Runnable consumer scenario and PASS evidence exist without future stage.
- [x] Unit + regression + lint + type + overlay checks PASS.
- [ ] Completion Documentation Synchronization Gate and Git diff review complete.

## Условие остановки

После завершения `FS-001` остановиться; не начинать `FS-002` автоматически.
