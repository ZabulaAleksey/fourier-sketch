# Traceability Fourier Sketch

## Правила чтения

`Implemented`/`verified` появляются только после repository/test evidence. Paths и tests с меткой
`planned` являются target trace, а не существующей функциональностью.

## Behavior matrix

| Behavior | Requirements | Stage(s) | Planned implementation boundary | Planned evidence | Текущий статус |
|---|---|---|---|---|---|
| `BH-DRAW-001` | FR-DRAW-001 | FS-007, FS-008 | application freehand use case | component + live E2E | verified cohesive MVP |
| `BH-IMPORT-001` | FR-IMPORT-001, SEC-INPUT-001 | FS-010..FS-015 | imaging adapters + application | unit + integration + E2E | verified image MVP and graph diagnostic |
| `BH-SKELETON-001` | IM-FR-002, IM-AC-002 | FS-014 | typed Lee adapter + application/preview/export | unit + integration + component + E2E | verified locally |
| `BH-SKELETON-GRAPH-001` | IM-FR-005, IM-AC-007 | FS-015 | immutable graph + compression/JSON/overlay | unit + property + integration + component + E2E | verified locally |
| `BH-FOURIER-001` | FR-FOURIER-001, FC-FR-003 | FS-002 | `math` transforms | analytical + property | verified |
| `BH-HARMONICS-001` | FR-HARMONICS-001, FC-FR-005 | FS-003, FS-004 | spectrum selection/metrics | unit + property | verified |
| `BH-EPICYCLE-001` | FR-EPICYCLE-001, EP-FR-001..003 | FS-005 | `math/epicycles` | unit + property | verified |
| `BH-EPICYCLE-TRACE-001` | FR-EPICYCLE-TRACE-001, EP-FR-004 | FS-005..FS-013 | chain state → trace adapter | property + integration + E2E | verified for freehand and image MVPs |
| `BH-ANIMATION-001` | EP-FR-006, UI-FR-002, UI-FR-007, UI-FR-008 | FS-006, FS-008, FS-013, FS-021 | renderer timeline/view state | component + E2E + frame profile | verified through integrated PySide6 workflow, measured renderer, stable rainbow pairing, fixed-center zoom/source-relative 100% baseline, synchronized Original visibility, desktop touch navigation and user-confirmed manual Windows GUI/DPI/resize + physical-touch checklist |
| `BH-DISCONTINUITY-001` | FR-DISCONTINUITY-001, IM-FR-007 | FS-016, FS-018 | piecewise conversion + discontinuous Fourier/render policy | unit + property + integration + component + E2E | verified locally through FS-018 |
| `BH-EXPORT-001` | FR-EXPORT-001, EX-FR-001..003 | FS-022 | export adapters consume timeline | integration + E2E | verified locally: versioned JSON/CSV, PNG, bounded endpoint-metadata GIF, atomic/cancel/no-overwrite and explicit MP4 unavailable; independent review GO |
| `BH-HARDENING-001` | NFR-NUM-001, NFR-UI-001, NFR-REPRO-001, NFR-PORT-001, NFR-HARD-001 | FS-023 | inverse-grid adapter + owned Qt worker lifecycle + evidence harness | parity + hardening benchmark + coverage + Unicode export + isolated wheel smoke | verified, integrated in `main` and published to `origin/main`; independent re-review GO |
| `BH-INSPECTOR-001` | UI-FR-011, UI-AC-008 | FS-024 | pure presentation projection + frequency-keyed desktop list/canvas selection | unit + component + actual Qt offscreen E2E + full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent review GO |
| `BH-SOLO-001` | UI-FR-012, UI-AC-009, EP-FR-008, EP-AC-007 | FS-025 | one-frequency analysis session over immutable baseline frame | unit + property + component + actual Qt offscreen E2E + full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent re-review GO |
| `BH-BUILDUP-001` | UI-FR-013, UI-AC-010, EP-FR-009, EP-AC-008 | FS-026 | bounded deterministic first-K analysis state machine over immutable baseline | unit + property + integration + component + actual Qt offscreen E2E + full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent review GO |
| `BH-SIMPLIFY-001` | FC-FR-008, FC-AC-006, IM-FR-009, IM-AC-009 | FS-027 | bounded Douglas–Peucker before equal-N resampling and existing timelines | unit + property + integration + component + live CLI E2E + benchmark/full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent review GO |
| `BH-ADAPTIVE-001` | FC-FR-009, FC-AC-007, IM-FR-010, IM-AC-010 | FS-028 | weighted arc-length density with exact N and uniform comparison | unit + property + integration + component + live CLI E2E + performance/full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent review GO |
| `BH-ROUTE-OPT-001` | IM-FR-011, IM-AC-011 | FS-029 | selectable bounded shortest-odd-pairing vs FS-017 baseline | unit + property + integration + component + live CLI E2E + corpus/performance/full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent review GO |
| `BH-EDUCATION-001` | UI-FR-014, UI-AC-011 | FS-030 | canonical actual-state six-step circle lesson over existing timeline/inspector/canvas | unit + integration + component + actual Qt offscreen E2E + content/math/full/static/overlay | verified, integrated in `main` and published to `origin/main`; independent review GO |
| `BH-MOBILE-001` | FR-MOBILE-001, AND-FR-001..006 | FS-031 | Android touch/presentation adapter over parity-proven core | parity + component + device E2E | planned |

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

## Stage FS-010 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| encoded/decoded budgets | Pillow adapter | sparse file + real oversized PNG | PASS |
| actual PNG/JPEG allowlist | verify/decode passes | PNG/JPEG/TIFF spoof/APNG/corrupt fixtures | PASS |
| EXIF and typed intermediates | raster/provenance values | integration + integrity regressions | PASS |
| independent transforms | median/autocontrast/threshold/invert | unit + application integration | PASS |
| diagnostic publication | image CLI + temporary/hard-link/replace | component + live E2E | PASS |
| privacy/fallback boundary | stable codes, no full path/payload, no retry | negative E2E + review | PASS |
| dependency/reproducibility | Pillow 12.3.0 direct | official review + lock/frozen sync | PASS |
| regression and static gates | repository | 254 tests + Ruff + mypy + overlay + diff | PASS |
| independent security review | FS-010 diff and typed-integrity fix | reviewer + re-review | GO |
| commit evidence | FS-010 implementation | Git commit | PASS — `d63b1b0` |

## Stage FS-011 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| explicit non-equivalent algorithms | `imaging/edge_detection.py` | synthetic unit + real integration | PASS |
| typed parameters and same-sized binary result | `imaging/edge_model.py` | invariants/negative unit | PASS |
| 4/8 boundary semantics | project NumPy transform | diagonal/border/empty fixtures | PASS |
| OpenCV Canny boundary | lazy headless adapter | real shape + malformed/unavailable backend | PASS |
| no fallback and privacy | typed failures + localized edge CLI | unit/component/live E2E + review | PASS |
| backend provenance integrity | algorithm coherence + bounded ASCII version | spoof/control regression | PASS |
| dependency/reproducibility | OpenCV headless 5.0.0.93 direct | official review + lock/frozen sync | PASS |
| regression and static gates | repository | 299 tests + Ruff + mypy + overlay + diff | PASS |
| manual visual evidence | same shape through both modes | diagnostic PNG inspection | PASS |
| independent security review | import privacy/provenance fixes | reviewer + re-review | GO |
| commit evidence | FS-011 implementation | Git commit | PASS — `b0c3334` |

## Stage FS-012 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| bounded external extraction | `imaging/contour_model.py`, `opencv_contours.py` | unit malformed/budget + real OpenCV | PASS |
| deterministic dominant key | `routing/dominant_contour.py` | unit ties/order + property cyclic/reversal | PASS |
| normalized closed Curve | transform/orientation/start provenance | unit exact geometry + integration | PASS |
| accepted math reuse | arc-length → FFT → existing timeline | integration endpoint-history assertions | PASS |
| live diagnostic path | localized contour CLI → existing Agg renderer | component + subprocess E2E | PASS |
| empty/no-fallback/privacy | typed no-contour/error and safe summary | negative unit/component/live E2E | PASS |
| regression and static gates | repository | 358 tests + Ruff + mypy + frozen sync + overlay + diff | PASS |
| manual visual evidence | selected ellipse contour, K=12, endpoint trace | rendered PNG inspection | PASS |
| independent review | correctness + security | read-only reviewers | GO — no remaining/new P0/P1/P2 |
| commit evidence | FS-012 implementation and hardening | Git commits | PASS — `418192a`, `a1c211c` |
| integration evidence | local `main` contains FS-012 feature tip | fast-forward `ad93921` + post-merge gates | PASS |

## Stage FS-013 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| typed generation/view state | `application/image_mvp.py` | unit state/config/stale/cancel/error | PASS |
| cohesive image workflow | `render/matplotlib_image_mvp.py` | actual controls + four-panel component | PASS |
| accepted math reuse | dominant contour → existing timeline/draw_frame | both-edge integration endpoint assertions | PASS |
| live client path | `cli/image_mvp.py` interactive/headless entry | subprocess E2E + readable PNG | PASS |
| empty/error/cancel/privacy | resource state + transactional publication | negative unit/component/E2E | PASS |
| regression and static gates | repository | full tests + Ruff + mypy + frozen sync + overlay + diff | PASS |
| manual visual evidence | ellipse intermediates/contour/K=12 endpoint trace | rendered PNG inspection | PASS |
| independent security review | untrusted input/path/cancel/publication boundary | read-only re-review | GO |
| integration evidence | local `main` contains FS-013 through chained fast-forward | `e918761` is ancestor of local `main` | PASS |

## Stage FS-014 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| explicit typed Lee transform | `imaging/skeleton_model.py`, `skimage_skeleton.py` | unit + real integration | PASS |
| line/T/cross/loop/noise properties | synthetic PNG fixtures | same size/subset/thinned/no solid 2×2 | PASS |
| complete/empty/cancel states | `application/skeletonization.py` | unit late/stale/error coverage | PASS |
| actual preview/export | Agg renderer + atomic PNG boundary | component + readable PNG | PASS |
| live client path | `cli/skeleton.py` | subprocess skeleton/preview E2E | PASS |
| no-fallback/privacy/resource safety | typed failures + bounded provenance | negative unit/component/E2E | PASS |
| dependency reproducibility | direct scikit-image 0.26.0 | lock + frozen sync | PASS |
| regression/static/overlay gates | repository | 427 pytest + Ruff + mypy + overlay + diff | PASS |
| independent review | correctness + security | read-only re-reviews | GO — no actionable findings |
| integration evidence | local `main` contains FS-014 feature tip | `eb71ec6` is ancestor of local `main` | PASS |

## Stage FS-015 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| fixed adjacency and compressed topology | `imaging/skeleton_graph*.py` | analytical line/T/cross/loop | PASS |
| exact pixel partition and determinism | generated accepted skeletons | property + repeated JSON | PASS |
| explicit disconnected components | multi-component synthetic/real fixtures | no cross-component edge | PASS |
| real pipeline | FS-010 preprocessing + FS-014 Lee | integration cross/multi-component | PASS |
| canonical JSON and actual overlay | application/Agg adapters | component readable artifacts | PASS |
| live client path | `cli/skeleton_graph.py` | subprocess JSON/overlay E2E | PASS |
| no-fallback/privacy/resource safety | typed limits + atomic local export | negative unit/component/E2E | PASS |
| regression/static/overlay gates | repository | 450 tests + Ruff + mypy + overlay + diff | PASS |
| independent review | correctness + security/resource | findings fixed; final re-review GO | PASS |
| integration evidence | feature branch, not merged | atomic feature commit; merge pending | PASS |

## Stage FS-016 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| one simple component → one segment | routing conversion | path/loop/isolated analytical unit | PASS |
| no fabricated partial route | typed terminal results | branched/empty/cancelled unit | PASS |
| exact deterministic coverage | raster provenance | generated path property | PASS |
| real multi-component pipeline | two-ring PNG | integration + live subprocess | PASS |
| explicit pen-up display | separate Matplotlib artists | component + visual inspection | PASS |
| regression/static/overlay gates | repository | 476 tests + Ruff + mypy + overlay | PASS |

## Stage FS-017 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| shared raw adjacency | FS-015 builder + routing helper | graph regression/parity | PASS |
| Euler/tree T-join coverage | forced route core | analytical + property | PASS |
| explicit cyclic seam/cost | step provenance + metrics | disconnected fixtures | PASS |
| Fourier consumer path | resampled closed route | integration + live subprocess | PASS |
| visible provenance | LineCollection overlay | component + visual inspection | PASS |
| regression/static/overlay gates | repository | 487 tests + Ruff + mypy + overlay | PASS |

## Stage FS-018 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| exact allocation and closed seams | piecewise sampler | analytical unit + property | PASS |
| indexed explicit/cyclic jumps | immutable boundary ledger | unit + integration | PASS |
| shared math, distinct stroke policy | discontinuous application/renderer | integration + component | PASS |
| forced-route comparison | same-budget comparison adapter | integration | PASS |
| live two-circle path | discontinuous CLI/Agg PNG | subprocess E2E + visual inspection | PASS |
| regression/static/overlay gates | repository | full pytest + Ruff + mypy + overlay | PASS |

## Stage FS-019 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| finite amplitude/log view | spectrum analysis | unit + property | PASS |
| explicit measured K sweep | retained energy/RMSE result | unit + property | PASS |
| same-parameter comparison | FS-018 vs closed forced route | integration | PASS |
| numeric chart view | Matplotlib adapter | component + visual inspection | PASS |
| live explicit-jump export | spectrum-analysis CLI | subprocess E2E | PASS |
| regression/static/overlay gates | repository | full pytest + Ruff + mypy + overlay | PASS |

## Stage FS-020 evidence

| Contract | Artifact | Check | Status |
|---|---|---|---|
| dedicated 2D convention/types | FFT2 raster/spectrum | analytical unit + review | PASS |
| FFT2/IFFT2 and filters | NumPy adapter | unit + generated round-trip | PASS |
| safe local image path | FS-010 grayscale → FFT2 | integration + resource negative | PASS |
| shifted diagnostic views | Matplotlib adapter | component + visual inspection | PASS |
| live local client | FFT2 CLI | subprocess E2E + bidi/path safety | PASS |
| regression/static/overlay gates | repository | full pytest + Ruff + mypy + overlay | PASS |

## Acceptance coverage targets

| Acceptance | Required level | First proving stage |
|---|---|---|
| AC-SYS-001/002 | analytical + property | FS-002 |
| AC-SYS-003/005 | unit + property | FS-005 |
| AC-SYS-004 | integration + E2E | FS-006 diagnostic + FS-008 freehand |
| AC-SYS-006/007 | integration + E2E | FS-013 dominant trace; FS-014 skeleton; FS-015 graph; Piecewise FS-016 |
| AC-SYS-008 | architecture + integration | FS-020 |
| AC-SYS-009 | integration + E2E | FS-022 |
| AC-SYS-010 | stage/evidence review | every stage |
| AC-SYS-011 | component + E2E | FS-006, FS-021 |
| AC-SYS-012 | negative integration/E2E | FS-010, FS-011, FS-012, FS-022, FS-023 |
| AC-SYS-013..015 | parity + component + hardening/package smoke | FS-023 |
