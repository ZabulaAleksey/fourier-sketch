# Traceability Fourier Sketch

## Правила чтения

`Implemented`/`verified` появляются только после repository/test evidence. Paths и tests с меткой
`planned` являются target trace, а не существующей функциональностью.

## Behavior matrix

| Behavior | Requirements | Stage(s) | Planned implementation boundary | Planned evidence | Текущий статус |
|---|---|---|---|---|---|
| `BH-DRAW-001` | FR-DRAW-001 | FS-007, FS-008 | application freehand use case | component + live E2E | planned |
| `BH-IMPORT-001` | FR-IMPORT-001, SEC-INPUT-001 | FS-010..FS-013 | imaging adapters + application | unit + integration + E2E | planned |
| `BH-FOURIER-001` | FR-FOURIER-001, FC-FR-003 | FS-002 | `math/dft`, reconstruction | analytical + property | planned |
| `BH-HARMONICS-001` | FR-HARMONICS-001, FC-FR-005 | FS-003, FS-004 | spectrum selection/metrics | unit + property | planned |
| `BH-EPICYCLE-001` | FR-EPICYCLE-001, EP-FR-001..003 | FS-005 | `math/epicycles` | unit + property | planned |
| `BH-EPICYCLE-TRACE-001` | FR-EPICYCLE-TRACE-001, EP-FR-004 | FS-005, FS-006, FS-008 | chain state → trace adapter | property + integration + E2E | planned |
| `BH-ANIMATION-001` | EP-FR-006, UI-FR-002 | FS-006, FS-008, FS-021 | renderer timeline/view state | component + E2E | planned |
| `BH-DISCONTINUITY-001` | FR-DISCONTINUITY-001, IM-FR-007 | FS-016, FS-018 | piecewise domain + render policy | property + integration | planned |
| `BH-EXPORT-001` | FR-EXPORT-001, EX-FR-001..003 | FS-022 | export adapters consume timeline | integration + E2E | planned |

## Critical epicycle chain

```text
FR-EPICYCLE-001
→ BH-EPICYCLE-001
→ planned src/fourier_sketch/math/epicycles.py
→ planned tests/unit + tests/property/test_epicycle_chain.py
```

```text
FR-EPICYCLE-TRACE-001
→ BH-EPICYCLE-TRACE-001
→ planned math/epicycles.py → render/trace.py
→ planned property endpoint/trace tests
→ planned tests/e2e/test_draw_to_trace.py
```

Required equality:

```text
trace(t) = chain.endpoint(t) = Σ selected vectors(t) ≈ reconstruction(t)
```

## Stage FS-000 evidence

| Contract | Artifact | Check | Status before final validation |
|---|---|---|---|
| package scaffold imports | `src/fourier_sketch/__init__.py` | `uv run pytest` | PASS — 1 smoke test |
| dependency contract | `pyproject.toml`, `uv.lock` | frozen sync + lock check | PASS — 14 packages |
| staged overlay | specs/docs/prompts | global overlay validator | PASS |
| stage context selector | `AI_PLAN` → `STAGES` | unique-ID audit | PASS — 31 IDs, FS-001 unique |
| portable context | repository source/docs | machine-path audit | PASS |
| commit evidence | bootstrap implementation | Git commit | PASS — `878f724` |

## Acceptance coverage targets

| Acceptance | Required level | First proving stage |
|---|---|---|
| AC-SYS-001/002 | analytical + property | FS-002 |
| AC-SYS-003/005 | unit + property | FS-005 |
| AC-SYS-004 | integration + E2E | FS-006 + FS-008 |
| AC-SYS-006/007 | integration + E2E | FS-013 + FS-016 |
| AC-SYS-008 | architecture + integration | FS-020 |
| AC-SYS-009 | integration + E2E | FS-022 |
| AC-SYS-010 | stage/evidence review | every stage |
| AC-SYS-011 | component + E2E | FS-006, FS-021 |
| AC-SYS-012 | negative integration/E2E | FS-010, FS-022, FS-023 |
