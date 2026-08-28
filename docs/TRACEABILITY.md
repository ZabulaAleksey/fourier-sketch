# Traceability Fourier Sketch

## Правила чтения

`Implemented`/`verified` появляются только после repository/test evidence. Paths и tests с меткой
`planned` являются target trace, а не существующей функциональностью.

## Behavior matrix

| Behavior | Requirements | Stage(s) | Planned implementation boundary | Planned evidence | Текущий статус |
|---|---|---|---|---|---|
| `BH-DRAW-001` | FR-DRAW-001 | FS-007, FS-008 | application freehand use case | component + live E2E | verified cohesive MVP |
| `BH-IMPORT-001` | FR-IMPORT-001, SEC-INPUT-001 | FS-010..FS-013 | imaging adapters + application | unit + integration + E2E | planned |
| `BH-FOURIER-001` | FR-FOURIER-001, FC-FR-003 | FS-002 | `math` transforms | analytical + property | verified |
| `BH-HARMONICS-001` | FR-HARMONICS-001, FC-FR-005 | FS-003, FS-004 | spectrum selection/metrics | unit + property | verified |
| `BH-EPICYCLE-001` | FR-EPICYCLE-001, EP-FR-001..003 | FS-005 | `math/epicycles` | unit + property | verified |
| `BH-EPICYCLE-TRACE-001` | FR-EPICYCLE-TRACE-001, EP-FR-004 | FS-005..FS-008 | chain state → trace adapter | property + integration + E2E | verified for diagnostic and cohesive freehand MVP |
| `BH-ANIMATION-001` | EP-FR-006, UI-FR-002 | FS-006, FS-008, FS-021 | renderer timeline/view state | component + E2E | verified in Matplotlib MVP; product UI deferred FS-021 |
| `BH-DISCONTINUITY-001` | FR-DISCONTINUITY-001, IM-FR-007 | FS-016, FS-018 | piecewise domain + render policy | property + integration | planned |
| `BH-EXPORT-001` | FR-EXPORT-001, EX-FR-001..003 | FS-022 | export adapters consume timeline | integration + E2E | planned |

## Critical epicycle chain

```text
FR-EPICYCLE-001
→ BH-EPICYCLE-001
→ src/fourier_sketch/math/epicycles.py
→ tests/unit/math/test_epicycles.py + tests/property/test_epicycle_properties.py
```

```text
FR-EPICYCLE-TRACE-001
→ BH-EPICYCLE-TRACE-001
→ math/epicycles.py → application/freehand.py → render/matplotlib_freehand.py
→ property endpoint + actual callback component/live freehand E2E
→ tests/e2e/test_freehand_surface_e2e.py
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

## Stage FS-001 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| FC-FR-001 finite/non-empty curve values | `src/fourier_sketch/domain/point.py`, `curve.py`, `piecewise_curve.py` | unit tests | PASS |
| FC-FR-004 coefficient/spectrum values | `src/fourier_sketch/domain/fourier.py` | unit tests, canonical signed-bin negative case | PASS |
| epicycle structural state | `src/fourier_sketch/domain/epicycle.py` | unit tests | PASS |
| public consumer boundary | `fourier_sketch.domain` | integration + component tests | PASS |
| typed malformed-input failures | domain constructors | negative unit tests | PASS |
| dependency boundary | domain imports | Ruff/mypy + import audit | PASS — stdlib/internal only |
| independent review | FS-001 diff | reviewer gate | PASS after canonical-bin and typed-error fixes |
| commit evidence | FS-001 implementation | Git commit | PASS — `63d7c10` |

## Stage FS-002 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| FC-FR-002 conversion | `math/conversion.py` | unit + Curve integration | PASS |
| FC-FR-003 formulas/signed bins | `math/frequencies.py`, `math/transforms.py` | analytical + property | PASS |
| FC-AC-001 constant/circle/impulse | transform unit fixtures | analytical assertions | PASS |
| FC-AC-002 parity/round-trip | Hypothesis + real NumPy adapter | property + integration | PASS |
| resource/non-finite failure | transform boundaries | negative unit tests | PASS |
| no silent fallback | explicit `reference_dft` / `fft_dft` API | backend-failure unit test | PASS |
| independent review | FS-002 diff | reviewer gate | PASS after sample-budget/IDFT fixes |
| commit evidence | FS-002 implementation | Git commit | PASS — `cc65b5a` |

## Stage FS-003 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| deterministic complete views | `math/spectrum.py` | unit + property permutations/ties | PASS |
| even-N signed/interleaved convention | spectrum ordering | explicit Nyquist unit cases | PASS |
| total finite energy | `spectrum_energy` | analytical + overflow-negative unit cases | PASS |
| canonical circle summary | real FFT → spectrum analysis | integration | PASS |
| independent review | FS-003 diff | reviewer gate | PASS after magnitude/Nyquist fixes |
| commit evidence | FS-003 implementation | Git commit | PASS — `f004f68` |

## Stage FS-004 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| first-K/explicit selection | `domain/selection.py`, `math/selection.py` | unit + property | PASS |
| full/partial reconstruction | `math/reconstruction.py` | analytical + property + integration | PASS |
| error/degenerate metrics | `math/metrics.py` | formula/zero-norm/overflow unit tests | PASS |
| retained energy/value provenance | `retained_energy_ratio` | zero/full/partial/provenance tests | PASS |
| resource boundaries | reconstruction API | pre-allocation/work negative tests | PASS |
| independent review | FS-004 diff and fixes | reviewer + re-review | PASS |
| commit evidence | FS-004 implementation | Git commit | PASS — `743a859` |

## Stage FS-005 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| rotating vector/DC/±k | `math/epicycles.py` | analytical unit | PASS |
| chain connectivity/geometry | `build_epicycle_chain` | unit + property | PASS |
| endpoint/reconstruction | FS-005 chain vs FS-004 API | property + integration | PASS |
| ordering/permutation endpoint | generated complete selections | property | PASS |
| finite/angular overflow | epicycle public API | negative unit | PASS |
| independent review | FS-005 diff and fixes | reviewer + re-review | PASS |
| commit evidence | FS-005 implementation | Git commit | PASS — `419b60c` |

## Stage FS-006 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| endpoint-only transactional trace | `application/diagnostic_epicycles.py` | component state/failure tests | PASS |
| immutable fail-closed render input | `EpicycleFrame`, Matplotlib boundary | component + integration negatives | PASS |
| actual chain geometry | `render/matplotlib_epicycles.py` | circle/vector/endpoint integration | PASS |
| explicit headless output safety | diagnostic CLI + Agg PNG | live E2E, existing-file negative | PASS |
| locale default/fallback/pseudo | packaged JSON + `Translator` | unit + negative/live E2E | PASS |
| packaged resource | built and installed wheel | `site-packages` resource load | PASS |
| independent review | FS-006 diff and fixes | reviewer + re-reviews | GO |
| commit evidence | FS-006 implementation | Git commit | PASS — `1abc0be` |

## Stage FS-007 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| bounded pointer lifecycle | `application/freehand.py` | unit + component callbacks | PASS |
| index resampling topology | `math/resampling.py` | unit + Hypothesis property | PASS |
| actual freehand vertical slice | `render/matplotlib_freehand.py` | integration + live E2E + visual QA | PASS |
| localized CLI failure boundary | `cli/freehand.py`, resources | component + subprocess E2E | PASS |
| regression and static gates | repository | 186 tests + Ruff + mypy + overlay + diff | PASS |
| independent review | FS-007 diff and fixes | reviewer + re-review | GO |
| commit evidence | FS-007 implementation | Git commit | PASS — `2eae8bc` |

## Stage FS-008 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| one cohesive control surface | `render/matplotlib_freehand.py` | actual widget component | PASS |
| exact endpoint-history ledger | same captured timeline | live event/control E2E | PASS |
| restart and pre-input safety | Play/Pause/Restart/sliders | component + negative states | PASS |
| release and widget truthfulness | event adapter/control sync | component regressions | PASS |
| regression and static gates | repository | 192 tests + Ruff + mypy + overlay + diff | PASS |
| manual visual evidence | actual stroke and controls | Agg visual QA | PASS |
| independent review | FS-008 diff and fixes | reviewer + re-review | GO |
| commit evidence | FS-008 implementation | Git commit | PASS — `0c4bfb2` |

## Stage FS-009 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| open endpoints and closed seam | `math/resampling.py` | unit + property | PASS |
| explicit index/arc-length choice | freehand application and Matplotlib selector | integration + component | PASS |
| same-source spacing diagnostics | immutable metrics + CLI fixture | measured comparison | PASS |
| actual trace vertical slice | selected method → FFT/timeline/endpoint trace | live E2E | PASS |
| degenerate/subnormal compatibility | typed math boundary + optional diagnostics | unit + integration | PASS |
| regression and static gates | repository | 215 tests + Ruff + mypy + overlay + diff | PASS |
| manual visual evidence | actual stroke, selector, metrics and controls | Agg visual QA | PASS |
| independent review | FS-009 diff and compatibility fix | reviewer + re-review | GO |
| commit evidence | FS-009 implementation | Git commit | PASS — `74f1008` |

## Acceptance coverage targets

| Acceptance | Required level | First proving stage |
|---|---|---|
| AC-SYS-001/002 | analytical + property | FS-002 |
| AC-SYS-003/005 | unit + property | FS-005 |
| AC-SYS-004 | integration + E2E | FS-006 diagnostic + FS-008 freehand |
| AC-SYS-006/007 | integration + E2E | FS-013 + FS-016 |
| AC-SYS-008 | architecture + integration | FS-020 |
| AC-SYS-009 | integration + E2E | FS-022 |
| AC-SYS-010 | stage/evidence review | every stage |
| AC-SYS-011 | component + E2E | FS-006, FS-021 |
| AC-SYS-012 | negative integration/E2E | FS-010, FS-022, FS-023 |
