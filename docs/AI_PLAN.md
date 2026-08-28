# План работы ИИ

## Текущая цель

Реализовать Stage `FS-002`: conversion `Point2D ↔ complex`, canonical signed frequencies,
reference DFT, явный NumPy FFT adapter и reference IDFT. Lifecycle: `implemented_unverified`;
final regression/documentation/commit gate выполняется.

Пользователь одобрил последовательную реализацию `FS-002`–`FS-006`, но текущий исполнимый slice
ограничен FS-002; следующий stage начнётся только после terminal evidence и commit текущего.

## Связанные требования

- SPEC: `specs/features/fourier-core.spec.md`.
- IDs: FC-FR-002, FC-FR-003, FC-AC-001, FC-AC-002, AC-SYS-001, AC-SYS-002, AC-SYS-010.
- Математический контракт: `docs/MATHEMATICS.md`.
- Stage contract: `prompts/STAGES.md`, heading `FS-002`.

## Stage identity и dependency DAG

- Stage ID: `FS-002`.
- Completed prerequisite: `FS-001` (`63d7c10`, validated and committed).
- DAG: `FS-001 → FS-002`.
- Self-reference/cycle/forward dependency: none.
- Entry gate: satisfied; пользователь разрешил продолжение, clean FS-001 baseline PASS.

## Входные предпосылки

| Предпосылка | Evidence |
|---|---|
| Domain values and invariants | FS-001 committed, public domain tests PASS |
| Frozen environment | `uv sync --all-groups --frozen` PASS |
| Stable formula and signed bins | accepted SPEC + `docs/MATHEMATICS.md` + ADR-002 |
| Dependency capability | NumPy/Hypothesis support Python 3.12; license/platform review complete |

## Runnable vertical slice и concrete consumer scenario

- Entry: public `fourier_sketch.math` API receives a finite non-empty `Curve`.
- Path: curve → Python complex samples → reference/NumPy coefficients → `FourierSpectrum` →
  IDFT → reconstructed complex samples/points.
- Observable result: constant/circle/impulse analytical fixtures and round-trip pass without
  FS-003 or later modules.

## Scope

### Входит

- explicit point/curve complex conversion;
- FFT-storage-to-signed-frequency mapping including even-N negative Nyquist;
- bounded O(N²) reference DFT as correctness oracle;
- explicit NumPy FFT adapter without silent fallback;
- reference IDFT and public imports;
- NumPy runtime, Hypothesis dev dependency and generated lockfile.

### Не входит

- spectrum ordering/energy, selection/metrics, epicycles, renderer;
- automatic backend fallback;
- leaking `numpy.ndarray`/NumPy scalars through public boundaries.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Baseline, architecture and dependency capability review | completed |
| 2 | Add dependencies through `uv` and verify graph | completed |
| 3 | Implement conversion/frequencies/transforms public API | completed |
| 4 | Add analytical/property/integration contracts | completed |
| 5 | Run frozen/full/static/overlay/SPEC/reviewer gates | completed |
| 6 | Synchronize docs and commit FS-002 evidence | in_progress |

## Acceptance / PASS

- [x] FC-FR-002 conversion preserves value and order.
- [x] FC-FR-003 exact formulas, normalization and signed bins match the mathematical contract.
- [x] Reference/NumPy parity and IDFT round-trip pass with explicit tolerances.
- [x] Empty/non-finite/oversized inputs/results fail with typed errors.
- [ ] Full regression/static/overlay/reviewer/documentation gates pass.

## Fallback и resource contract

- Primary optimized path is the explicitly called NumPy adapter.
- Reference DFT is a separately called bounded correctness oracle, not an automatic fallback.
- Invalid input, dependency/backend error or reference size overflow fails explicitly; no retry and
  no silent backend substitution.

## Deferred

- Spectrum views/energy (`FS-003`), selection/reconstruction metrics (`FS-004`), epicycles
  (`FS-005`) and visualization (`FS-006`).

## Проверки

```powershell
uv sync --all-groups --frozen
uv run pytest -m unit
uv run pytest -m property
uv run pytest -m integration
uv run pytest
uv run ruff check .
uv run mypy
py -3 ~/.codex/tools/validate_project_overlay.py .
```

## Условие перехода

FS-003 начинается только после FS-002 `completed` и commit evidence.
