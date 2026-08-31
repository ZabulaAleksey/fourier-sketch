# Detailed stage contracts — Fourier Sketch

Этот файл — единственный подробный источник stages. SPEC определяет требуемое поведение,
`docs/ROADMAP.md` — порядок, `docs/AI_PLAN.md` — один current/next slice. Перед stage implementation
прочитай только выбранный record по exact `Stage ID`.

Для planned stage listed prerequisite является обязательным entry gate: при фактическом старте он
должен иметь lifecycle `completed` и required evidence в `docs/AI_STATUS.md`. Пока это не так,
stage остаётся `planned` и не выдаёт forward dependency за completed prerequisite.

Общий terminal gate каждого stage: accepted tests не изменены без отдельного contract change;
unit/integration/component и live E2E выполнены по применимости; Ruff/mypy/regression/overlay
checks PASS; diff reviewed; README, AI_PLAN, AI_STATUS, ROADMAP, STAGES, TRACEABILITY и затронутые
SPEC/architecture/design/security/testing/dependencies проверены и синхронизированы; commit
evidence получен. Primary/E2E blocker оставляет non-terminal status. После handoff остановиться.

## FS-000 — Project Bootstrap

- Lifecycle: `completed`.
- Evidence: implementation commit `878f724`; frozen restore, smoke, Ruff, mypy, overlay, selector,
  portability and diff checks PASS on Windows / Python 3.12.5.
- Goal: создать clone-restorable repository overlay и minimal importable Python scaffold без
  Fourier/product implementation.
- Context: approved system/feature SPECs, architecture/mathematics contracts и future stages
  должны быть доступны без исходного attachment/chat.

### Dependency DAG & entry preconditions

- DAG: `∅ → FS-000`; prerequisite stages отсутствуют.
- Entry evidence: target directory отсутствовал; GREENFIELD classification; independent Git root;
  Python/uv availability проверяется validation phase.
- Self-reference/cycle/forward dependency: none.

### Scope / non-goals / invariants

- Scope: Git branch, `pyproject.toml`, package scaffold, smoke test, lockfile, full project context,
  behavior matrix and stage catalog.
- Non-goals: domain model, DFT, renderer, image/UI/export implementation; speculative empty modules.
- Invariants: canonical docs paths; `uv` only; no local generic agents/hooks/MCP/Skills; planned
  claims clearly separated from implemented evidence.

### Runnable vertical slice & concrete E2E

- Entry: clean checkout on Python 3.12+ with `uv`.
- Path: frozen dependency restore → import installed/local package → smoke pytest → overlay validator.
- Observable result: versioned package imports and validator reports structurally valid full overlay.
- This internal/developer E2E is complete without future product stage.

### PASS evidence

```powershell
uv sync --all-groups --frozen
uv run pytest
uv run ruff check .
uv run mypy
py -3 ~/.codex/tools/validate_project_overlay.py .
git diff --check
```

PASS: all exit zero, generated lockfile tracked, Git diff contains no product behavior or stale
completion claim. Evidence records environment/branch and caveats.

### Temporary / deferred / failure

- Allowed temporary implementation: version-only package; fully serves import smoke.
- Deferred: all `FS-001`–`FS-030` functionality.
- Failure/rollback: restore manifest/docs from feature commit; dependency resolution failure keeps
  `implemented_unverified`, without switching manager or hand-editing lockfile.
- Documentation impact: all initial canonical files; ERROR_LOG/DEV_LOG intentionally absent.
- Handoff: mark FS-000 completed only after evidence, select FS-001 as planned, stop.

## FS-001 — Domain Model

- Lifecycle: `completed`.
- Goal: implement only typed domain values and invariants required by later math/rendering.
- Context: Fourier Core SPEC FC-FR-001 and domain boundaries in architecture.

### Dependency DAG & entry preconditions

- DAG: `FS-000 → FS-001`; at actual start FS-000 must be completed with frozen restore/smoke.
- Entry evidence: accepted SPEC, clean Git baseline, test inventory, no conflicting domain API.
- Current gate: satisfied — FS-000 is completed/committed; clean baseline passed on
  `feature/fs-001-domain-model` before implementation.

### Scope / non-goals / invariants

- Scope: `Point2D`, `Curve`, `PiecewiseCurve`, `FourierCoefficient`, `FourierSpectrum`,
  `EpicycleVector`, `EpicycleChainState`, typed validation and public imports.
- Non-goals: complex conversion, DFT, rotation, renderer, serialization, NumPy/UI/CV dependencies.
- Invariants: finite coordinates; non-empty ordered curve/segments; explicit open/closed; no hidden
  piecewise bridge; endpoint/last-vector structural consistency when chain state is constructed.

### Runnable vertical slice & concrete E2E

- Entry: Python consumer imports `fourier_sketch.domain`.
- Path: construct valid values → inspect properties → invalid values produce typed errors.
- Observable result: deterministic domain objects fully usable without FS-002.

### PASS evidence

- Add accepted unit tests for every value/invariant and public import path.
- Run `uv run pytest -m unit`, full pytest, Ruff, mypy, overlay validator and diff check.
- PASS: valid/invalid cases and dependency-boundary review succeed; no future module scaffold.
- Current evidence: frozen restore, 30 unit, 1 integration, 1 component, full 33-test suite, Ruff,
  mypy, overlay, public consumer path and dependency-boundary audit PASS; implementation commit
  `63d7c10`.

### Temporary / deferred / failure

- Allowed: stdlib typed dataclasses/value objects; fully working for FS-001 consumer.
- Deferred: conversion/DFT FS-002; behavior methods beyond value invariants.
- Security/performance: reject non-finite values; avoid accidental unbounded copies where possible.
- Failure: SPEC/API ambiguity stops implementation; do not encode guessed convention.
- Docs: traceability/status/plan and architecture only if actual API changes target boundary.
- Handoff: commit FS-001 evidence and stop before FS-002.

## FS-002 — Complex Curve + DFT / IDFT

- Lifecycle: `completed`.
- Goal: deliver reference and NumPy Fourier transforms with one signed-frequency convention.
- Context: FC-FR-002/003 and `docs/MATHEMATICS.md`.

### Dependency DAG & entry preconditions

- DAG: `FS-001 → FS-002`; FS-001 must be completed before start.
- Entry evidence: domain API/unit suite, Python/NumPy capability review, accepted fixture convention.
- Current gate: satisfied — FS-001 completed; clean baseline and dependency capability review PASS;
  user authorized sequential implementation through FS-006.

### Scope / non-goals / invariants

- Scope: Point2D↔complex, O(N²) reference DFT, NumPy FFT adapter, IDFT, signed bins; add NumPy and
  Hypothesis only now with lockfile update.
- Non-goals: spectrum sorting, partial K UX, epicycles, renderer.
- Invariants: exact formulas/Nyquist label; finite non-empty samples; reference/FFT parity;
  round-trip within explicit tolerance.

### Runnable vertical slice & concrete E2E

- Entry: public math API receives a constant/circle `Curve`.
- Path: curve → complex samples → reference/FFT coefficients → IDFT → Point2D samples.
- Observable result: analytical coefficients and reconstructed samples; no later stage required.

### PASS evidence

- Analytical DC/circle/impulse unit tests; Hypothesis round-trip/translation/scaling; real
  reference-vs-NumPy integration.
- `uv sync --all-groups --frozen`, targeted unit/property/integration, full pytest, Ruff, mypy,
  dependency diff and overlay validator.
- PASS includes explicit `atol/rtol` rationale and no NaN/Inf masking.
- Current evidence: analytical unit, Hypothesis property, real reference/NumPy integration, frozen
  restore, Ruff and mypy PASS; reviewer sample-budget/non-finite findings fixed; implementation
  commit `cc65b5a`.

### Temporary / deferred / failure

- Allowed: clear O(N²) reference implementation as correctness oracle; it remains usable for small N.
- Deferred: optimized selection/metrics and UI.
- Fallback: FFT adapter failure is explicit; reference path is used only by deliberate API/test
  selection within bounded N, never silent fallback for large input.
- Docs: dependency contract, math/traceability/status updated.
- Handoff: commit and stop before FS-003.

## FS-003 — Fourier Spectrum

- Lifecycle: `completed`; implementation commit `f004f68`.
- Goal: expose deterministic spectrum metadata, coefficient properties, energy and orderings.

### Dependency DAG & entry preconditions

- DAG: `FS-002 → FS-003`; FS-002 transform parity must be completed.
- Entry evidence: signed coefficient set and accepted Fourier Core tests.
- Current gate: satisfied — FS-002 completed with commit `cc65b5a`; user authorized continuation.

### Scope / non-goals / invariants

- Scope: amplitude, zero-phase convention, energy, signed/absolute/amplitude/interleaved/explicit
  orderings and source metadata.
- Non-goals: partial reconstruction metrics, vector rotation or charts.
- Invariants: exactly N unique bins; deterministic ties; ordering is a view/permutation and never
  changes coefficient values.

### Runnable vertical slice & concrete E2E

- Entry: consumer transforms a circle fixture.
- Path: coefficients → `FourierSpectrum` → requested ordering/energy summary.
- Observable result: dominant `k=+1` for canonical circle and stable ordered list.

### PASS evidence

- Unit/property tests for amplitudes/phases/unique bins/all orderings and analytical fixture.
- Full pytest/Ruff/mypy/overlay/diff checks.
- PASS: every ordering contains same set; metadata records convention/N.
- Evidence: 75 tests PASS; Ruff/mypy/overlay/diff PASS; independent review PASS after
  overflow-safe magnitude and even-N Nyquist coverage fixes.

### Temporary / deferred / failure

- Allowed: pure Python sorting over NumPy-created coefficients; fully usable at current N.
- Deferred: selection/reconstruction FS-004 and visual spectrum FS-006/FS-019.
- Performance: benchmark claims forbidden; deterministic correctness first.
- Docs: traceability/status/plan, mathematics only if convention defect discovered.
- Handoff: terminal evidence committed; FS-004 entry is satisfied.

## FS-004 — Partial Reconstruction and Metrics

- Lifecycle: `completed`; implementation commit `743a859`.
- Goal: reconstruct from explicit harmonic selections and report defined errors.

### Dependency DAG & entry preconditions

- DAG: `FS-003 → FS-004`; FS-003 orderings/energy must be completed.
- Entry evidence: spectrum public contract and analytical fixtures.
- Current gate: satisfied — FS-003 completed with commit `f004f68`; user authorized continuation.

### Scope / non-goals / invariants

- Scope: K/explicit selection, continuous/discrete reconstruction, MSE/RMSE/max/normalized error,
  retained energy.
- Non-goals: epicycle geometry or renderer.
- Invariants: selection size `1..N`, exact selected set, metric alignment, defined zero-norm behavior,
  no silent NaN.

### Runnable vertical slice & concrete E2E

- Entry: consumer chooses K/order for a square/circle spectrum.
- Path: spectrum → selected set → reconstructed sample grid → metrics.
- Observable result: points and diagnostic metrics without FS-005.

### PASS evidence

- Unit/property tests for full/partial, explicit bins, errors, degenerates and retained energy.
- Integration compares full reconstruction with FS-002 IDFT; full suite/static/overlay checks PASS.
- Evidence: 110 tests PASS; Ruff/mypy/overlay/diff PASS; independent reviewer and re-review PASS.

### Temporary / deferred / failure

- Allowed: vectorized NumPy reconstruction and straightforward metric implementation.
- Deferred: epicycle chain FS-005 and charts/controls.
- Failure: invalid K/set rejected; no automatic ordering substitution.
- Docs: math/traceability/status/plan updated with actual metric semantics.
- Handoff: terminal evidence committed; FS-005 entry is satisfied.

## FS-005 — Epicycle Mathematics

- Lifecycle: `completed`; critical milestone; implementation commit `419b60c`.
- Goal: prove head-to-tail rotating vector model and endpoint/reconstruction equivalence.

### Dependency DAG & entry preconditions

- DAG: `FS-004 → FS-005`; FS-004 selected reconstruction must be completed.
- Entry evidence: accepted coefficient selection and reconstruction API.
- Current gate: satisfied — FS-004 completed with commit `743a859`; user authorized continuation.

### Scope / non-goals / invariants

- Scope: `v_k(t)`, ordered chain start/end/centers/radius/endpoint, origin, orderings; behaviors
  BH-EPICYCLE-001 and BH-EPICYCLE-TRACE-001 at math layer.
- Non-goals: matplotlib/PySide, animation loop, mouse/image input.
- Invariants: DC stationary; sign/phase/amplitude exact; next.start=previous.end;
  endpoint=last.end=origin+sum vectors≈reconstruction for same set.

### Runnable vertical slice & concrete E2E

- Entry: public API receives selected coefficients, normalized time and origin.
- Path: coefficient set → `EpicycleChainState` → endpoint compared to FS-004 reconstruction.
- Observable result: complete geometry state for any renderer; no future component needed.

### PASS evidence

- Analytical unit: DC, ±k, amplitude, phase; property: connectivity, permutation endpoint,
  endpoint/reconstruction over generated finite sets/times; integration consumes real spectrum.
- Full pytest/Ruff/mypy/overlay/diff checks; explicit tolerances and accumulation caveat.
- Evidence: 124 tests PASS; Ruff/mypy/overlay/diff PASS; independent reviewer and re-review PASS.

### Temporary / deferred / failure

- Allowed: straightforward sequential complex accumulation; fully correct baseline.
- Deferred: visualization/trace history FS-006.
- Performance: no premature vectorized state that obscures provenance.
- Docs: math relation and critical traceability verified/updated; status milestone evidence.
- Handoff: terminal endpoint evidence committed; FS-006 entry is satisfied.

## FS-006 — Diagnostic Epicycle Renderer

- Lifecycle: `completed`; implementation commit `1abc0be`.
- Goal: render actual chain states with circles/vectors/endpoint/persistent endpoint trace.

### Dependency DAG & entry preconditions

- DAG: `FS-005 → FS-006`; FS-005 endpoint property must be completed.
- Entry evidence: immutable/explicit chain state API and renderer dependency review.
- Current gate: satisfied — FS-005 completed with commit `419b60c`; user authorized continuation.

### Scope / non-goals / invariants

- Scope: matplotlib adapter, animation timeline, pause/restart/speed/harmonics/visibility, original
  overlay, headless diagnostic output; first real resource-key locale boundary (`en`+pseudo).
- Non-goals: mouse drawing, PySide6 shell, image input, export codecs.
- Invariants: renderer consumes state; `new_trace_point=state.endpoint`; toggles do not mutate math;
  circle center/radius and arrow geometry come from vector state.

### Runnable vertical slice & concrete E2E

- Entry: diagnostic command/module with canonical circle/letter fixture.
- Path: fixture → existing Fourier/selection/chain API → animation states → rendered PNG/manual window.
- Observable result: nested chain, moving endpoint and trace derived from sampled endpoints.

### PASS evidence

- Integration verifies renderer adapter receives/records endpoint states; component smoke covers
  controls/toggles/restart and locale fallback; headless artifact sanity + documented manual check.
- Unit/integration/component/full pytest, Ruff, mypy, frozen sync and overlay PASS.
- Evidence: unit 110, property 9, integration 11, component 18, E2E 4 and full 153 tests PASS;
  Ruff/mypy/overlay/diff/build PASS; built wheel resource loaded from installed `site-packages`;
  independent reviewer GO after transactional-state, immutable-frame, localized-error and
  fail-closed renderer-boundary fixes.

### Temporary / deferred / failure

- Allowed: matplotlib diagnostic UI; it is fully working and later PySide6 replaces presentation,
  not chain math.
- Deferred: freehand FS-007 and full GUI FS-021.
- Failure: headless limitation reported separately; screenshot is not math evidence.
- Docs: DESIGN/i18n/test/trace/status/README commands updated.
- Handoff: implementation committed as `1abc0be`; stop before FS-007.

## FS-007 — Freehand Input

- Lifecycle: `completed`.
- Goal: capture mouse path and feed a valid curve through the existing Fourier/renderer path.

### Dependency DAG & entry preconditions

- DAG: `FS-006 → FS-007`; diagnostic renderer must be completed.
- Entry evidence: working renderer controls and curve/Fourier application contracts.
- Current gate: satisfied by FS-006 commit `1abc0be`; implementation committed as `2eae8bc`.

### Scope / non-goals / invariants

- Scope: mouse capture state, cleanup of consecutive duplicates, minimum validation, explicit
  open/closed selection, current uniform-by-index resampling, invocation of existing chain renderer.
- Non-goals: arc-length quality FS-009, image input, PySide6.
- Invariants: empty input no curve; one-point DC path; short/duplicate/zero-length states explicit;
  event handler dispatches use case rather than implementing math.

### Runnable vertical slice & concrete E2E

- Entry: user opens diagnostic freehand surface and draws a stroke.
- Path: pointer events → raw points → Curve/cleanup/resampling → existing Fourier/chain renderer.
- Observable result: animation starts or typed validation state appears; no FS-008 wrapper needed.

### PASS evidence

- Unit input-state cases; component pointer simulation; integration real Curve→chain; manual live
  drawing diagnostic. Full tests/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: matplotlib event capture and deterministic simple resampling adequate for this slice.
- Deferred: consolidated MVP polish FS-008 and arc-length FS-009.
- Security/resource: bounded point capture/downsampling policy and cancellation/reset.
- Docs: user command, design states, traceability/status/plan.
- Evidence: unit 130, property 10, integration 12, component 26, E2E 7 and full 186 PASS;
  Ruff/mypy/overlay/diff PASS; actual callback E2E and manual visual QA PASS; reviewer GO.
- Handoff: implementation committed as `2eae8bc`; FS-008 activated by existing user authorization.

## FS-008 — First Freehand-to-Trace MVP

- Lifecycle: `completed`; first live product milestone; implementation commit `0c4bfb2`.
- Goal: prove complete user drawing → actual endpoint trace behavior.

### Dependency DAG & entry preconditions

- DAG: `FS-007 → FS-008`; FS-007 live input and FS-006 renderer completed.
- Entry evidence: component/manual input path plus endpoint provenance integration.
- Current gate: satisfied by FS-007 commit `2eae8bc`; implementation committed as `0c4bfb2`.

### Scope / non-goals / invariants

- Scope: cohesive runnable entry point, parameter controls, error/restart flow, live E2E automation
  where framework permits, diagnostic evidence for BH-DRAW/FOURIER/EPICYCLE/TRACE/ANIMATION.
- Non-goals: image processing and arc-length algorithm.
- Invariants: shown trace history is exactly chain endpoint history; no decorative alternate path.

### Runnable vertical slice & concrete E2E

- Entry: user launches one documented command and draws a non-degenerate curve.
- Path: UI input → application Curve → Fourier → selection → chain states → endpoint trace.
- Observable result: persistent trace reproduces periodic approximation and controls work.

### PASS evidence

- Live E2E exercises real client/component→application→math→renderer path; trace data asserted
  against recorded states. Unit/integration/component/full/static/overlay gates PASS; manual visual
  check records fixture/action/result.

### Temporary / deferred / failure

- Allowed: matplotlib as fully working MVP shell.
- Deferred: better parameterization FS-009, images FS-010+, PySide6 FS-021.
- Failure: if live event automation unavailable, stage remains `implemented_unverified` until real
  E2E/manual+data evidence meets approved gate; do not mark DONE from mocks.
- Docs: README first runnable workflow, DESIGN, testing, traceability, status/plan.
- Evidence: unit 130, property 10, integration 12, component 31, E2E 8 and full 192 PASS;
  Ruff/mypy/overlay/diff PASS; manual visual QA PASS; reviewer GO after speed/DC widget fixes.
- Handoff: implementation committed as `0c4bfb2`; FS-009 activated by existing user authorization.

## FS-009 — Arc-Length Parameterization

- Lifecycle: `completed`; implementation commit `74f1008`.
- Goal: introduce uniform arc-length resampling and measurable comparison with prior sampling.

### Dependency DAG & entry preconditions

- DAG: `FS-008 → FS-009`; freehand MVP must be completed.
- Entry evidence: current resampling baseline and representative fixtures/metrics.
- Current gate: satisfied by FS-008 commit `0c4bfb2` and reviewer GO.

### Scope / non-goals / invariants

- Scope: cumulative length, normalized parameter, open/closed interpolation, spacing diagnostics,
  user-selectable comparison in existing MVP.
- Non-goals: adaptive sampling FS-028 or simplification FS-027.
- Invariants: order and open endpoints preserved; closed seam explicit; zero length typed failure;
  quality claims based on measured metrics, not assumed universal improvement.

### Runnable vertical slice & concrete E2E

- Entry: freehand/synthetic non-uniform curve with sample count.
- Path: raw Curve → arc-length resample → existing Fourier/chain/trace → metric comparison.
- Observable result: uniform spacing report and runnable reconstructed trace.

### PASS evidence

- Unit/property resampling invariants; integration through real MVP; component selection; E2E
  compares same input. Full/static/overlay gates PASS with measured diagnostics.

### Temporary / deferred / failure

- Allowed: linear interpolation along polyline; fully working for current slice.
- Deferred: curvature-adaptive and simplification algorithms.
- Performance: bound N; no unbounded dense intermediates.
- Docs: MATHEMATICS, SPEC only if behavior changed, trace/status/plan.
- Evidence: full suite 215 PASS; targeted unit/property/integration/component/live E2E, Ruff,
  mypy, overlay, diff and manual visual QA PASS; measured index CV `0.917196816392` versus
  arc-length CV `0.0` on the same fixture; reviewer and compatibility re-review GO.
- Handoff: implementation committed as `74f1008`; FS-010 activated by existing user authorization.

## FS-010 — Validated Image Input, Grayscale and Threshold

- Lifecycle: `completed`; implementation commit `d63b1b0`.
- Goal: safely decode local PNG/JPEG and expose grayscale/denoise/contrast/threshold intermediates.

### Dependency DAG & entry preconditions

- DAG: `FS-009 → FS-010`; core application baseline must be completed before image branch begins.
- Entry evidence: security limits accepted; Pillow/backend capability/license review; clean lockfile.
- Current gate: satisfied by FS-009 commit `74f1008`, existing 25 MiB/40 MP security policy,
  official Pillow 12.3.0 capability/security/API/license review and clean current lockfile.

### Scope / non-goals / invariants

- Scope: safe local decode, EXIF orientation policy, grayscale, optional bounded denoise/contrast,
  threshold/invert, typed intermediate result and diagnostic CLI/view; add minimal image dependency.
- Non-goals: edge detection/contours, remote URLs, skeleton/routing.
- Invariants: 25 MiB/40 MP limits before unsafe work; actual decode allowlist; each transform
  independent; no payload logging; cancellation/invalid input explicit.

### Runnable vertical slice & concrete E2E

- Entry: user/synthetic test supplies local PNG/JPEG.
- Path: file bytes → validation/decode → grayscale → threshold → preview/exported diagnostic image.
- Observable result: valid intermediate artifact with provenance, or controlled rejection.

### PASS evidence

- Unit transforms/limits; integration real decoder with valid/corrupt/spoofed/oversized fixtures;
  component/CLI state; live local-file E2E. Frozen sync/dependency review/full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: Pillow-based deterministic transforms; fully serves preprocessing slice.
- Deferred: Canny FS-011 and contours FS-012.
- Fallback: no silent decoder/algorithm switch; missing optional operation is unavailable with
  provenance; validation failures never retry.
- Docs: dependencies/security/README/architecture/trace/status/plan.
- Evidence: FS-010 targeted 39 and full 254 tests PASS; Ruff, mypy, lock/frozen sync, overlay,
  diff, live CLI, visual QA and security review PASS. Real fixtures cover PNG/JPEG/TIFF spoof,
  APNG, corrupt/truncated, 25 MiB/40 MP, EXIF, transforms, overwrite and privacy-safe failure.
- Handoff: implementation committed as `d63b1b0`; FS-011 activated by existing user authorization.

## FS-011 — Edge Detection

- Lifecycle: `completed`.
- Evidence: implementation commit `b0c3334`; full 299 tests, independent targeted 45 tests,
  Ruff/mypy/frozen-lock/overlay/diff/manual visual gates PASS; security re-review GO.
- Goal: produce diagnostic threshold-boundary and Canny edge maps from validated preprocessing.

### Dependency DAG & entry preconditions

- DAG: `FS-010 → FS-011`; FS-010 safe decode/transforms must be completed.
- Entry evidence: typed grayscale/binary contract and reviewed Canny backend/dependency choice.
- Current gate: satisfied by FS-010 commit `d63b1b0`, typed grayscale/binary contracts and official
  OpenCV 5.0 Canny plus `opencv-python-headless` 5.0.0.93 capability/platform/license review.

### Scope / non-goals / invariants

- Scope: threshold boundary, Canny parameters, edge result/provenance, synthetic fixtures and
  intermediate preview/export; reviewed `opencv-python-headless` added as direct dependency.
- Non-goals: contour ordering, skeletonization or routing.
- Invariants: validated dimensions/types; deterministic parameters; backend named in result;
  algorithm errors are explicit and do not mutate source intermediate.

### Runnable vertical slice & concrete E2E

- Entry: valid preprocessed synthetic line/shape or local image.
- Path: decode/grayscale → selected edge algorithm → edge map preview/export.
- Observable result: binary edge map and parameter/provenance summary.

### PASS evidence

- Unit synthetic line/rectangle/noise cases; integration real FS-010 output through both modes;
  component/CLI selection; full/static/frozen-sync/overlay gates.
- PASS includes negative thresholds/empty-edge state and no contour claim.
- Actual evidence: same-sized binary outputs, 4/8-connectivity, Canny L1/L2/aperture/thresholds,
  no-fallback/unavailable/malformed backend, privacy-safe import failures, bounded provenance,
  overwrite and live subprocess PNG paths all PASS.

### Temporary / deferred / failure

- Allowed: reviewed stable library Canny + project-owned threshold-boundary transform.
- Deferred: contour interpretation FS-012.
- Fallback: backend unavailable → Canny unavailable; threshold boundary may remain separately
  supported, visibly selected, never presented as equivalent Canny.
- Docs: dependency/security/architecture/trace/status/plan.
- Handoff: implementation committed as `b0c3334`; stopped before FS-012 as authorized.

## FS-012 — Dominant Contour to Curve

- Lifecycle: `completed`.
- Goal: extract one deterministic dominant contour and feed it to the proven Fourier/epicycle path.

### Dependency DAG & entry preconditions

- DAG: `FS-011 + FS-009 + FS-008 → FS-012`; all three must be completed at start.
- Entry evidence: edge map contract, arc-length resampling and freehand endpoint-trace application.
- Completion gate: satisfied on `feature/fs-012-dominant-contour`; implementation commits
  `418192a` and `a1c211c` contain the verified vertical slice.

### Scope / non-goals / invariants

- Scope: contour candidates, documented dominant selection/tie-break, orientation/start-point
  normalization, Curve conversion/resampling and synthetic image-to-trace integration.
- Non-goals: multiple components, skeleton graph, forced routing.
- Invariants: no-contour explicit; one selected contour only; no hidden connections; image/domain
  coordinate transform documented and deterministic.

### Runnable vertical slice & concrete E2E

- Entry: synthetic/local simple shape image.
- Path: validated decode → preprocessing/edges → dominant contour → Curve/resample → existing
  Fourier/chain → endpoint trace.
- Observable result: diagnostic contour and actual endpoint trace for the selected shape.

### PASS evidence

- 59 targeted unit/integration/component/E2E/property tests and 358 full-suite tests PASS.
- Frozen sync, Ruff, strict mypy, project-overlay validator and diff check PASS.
- Live/synthetic E2E verifies contour provenance and endpoint trace history; rendered diagnostic
  PNG visual QA PASS.
- Independent correctness and security re-review: GO, with no remaining/new P0/P1/P2 findings.
- No accepted pre-FS-012 test, fixture, golden or scenario was modified.

### Temporary / deferred / failure

- Allowed: library contour extraction with project-owned deterministic selection.
- Deferred: multi-component FS-016, skeleton FS-014 and product polish FS-013.
- Failure: no contour remains a valid empty result, not fabricated outline.
- Docs: README diagnostic command, architecture/trace/testing/status/plan.
- Handoff: commit and stop before FS-013.

## FS-013 — Image-to-Fourier MVP

- Lifecycle: `completed`; second live product milestone.
- Evidence: generation-safe application state, four-panel Matplotlib UI/headless CLI, 29 targeted
  tests after review hardening, terminal regression, static/frozen/overlay/diff gates, visual QA
  and independent security review PASS/GO.
- Goal: deliver cohesive user-selected image → dominant contour → rotating endpoint trace workflow.

### Dependency DAG & entry preconditions

- DAG: `FS-012 → FS-013`; FS-012 synthetic/live pipeline must be completed.
- Entry evidence: safe input, contour integration and diagnostic renderer E2E data.
- Current gate: satisfied; implementation commit `e918761` is an ancestor of local `main` through
  the chained FS-014 fast-forward merge. Remote push has not been performed.

### Scope / non-goals / invariants

- Scope: one documented launch/action flow, controls for preprocessing/sample/harmonic parameters,
  intermediate views, empty/error/cancel states and live BH-IMPORT→FOURIER→EPICYCLE→TRACE E2E.
- Non-goals: skeleton/multiple contours/ideal arbitrary-photo conversion.
- Invariants: same application/chain state as freehand; actual endpoint trace; selected contour and
  limitations visible; untrusted file limits enforced.

### Runnable vertical slice & concrete E2E

- Entry: user launches MVP and selects supported simple-shape PNG/JPEG.
- Path: UI/diagnostic client → safe decode → edges → dominant contour → Curve → Fourier → chain
  renderer.
- Observable result: intermediate diagnostics plus rotating trace approximating selected contour.

### PASS evidence

- Live user/file E2E through real components; negative corrupt/no-contour/cancel scenarios;
  unit/integration/component/full/static/security/overlay gates and documented visual check.

### Temporary / deferred / failure

- Allowed: matplotlib multi-panel MVP; fully usable until PySide6.
- Deferred: arbitrary/multiple shapes and skeleton routing.
- Failure: unsupported/no-contour returns recovery UI; no silent alternate route.
- Docs: README capabilities/limitations, DESIGN, SECURITY, TRACEABILITY, status/plan.
- Handoff: commit milestone and stop before FS-014.

## FS-014 — Skeletonization

- Lifecycle: `completed`; validated, committed and merged into local `main` 2026-08-29; not pushed.
- Goal: convert validated line art/binary images to a diagnosable one-pixel skeleton.

### Dependency DAG & entry preconditions

- DAG: `FS-013 → FS-014`; image MVP and safe preprocessing must be completed.
- Entry evidence: binary image contract and reviewed skeleton algorithm/dependency.
- Current gate: completed; feature tip `eb71ec6` is an ancestor of local `main`; prerequisite, implementation,
  runnable slice, documentation, verification and local integration gates satisfied 2026-08-29.

### Scope / non-goals / invariants

- Scope: skeletonization adapter, provenance, line/T/cross/loop/noise fixtures, preview/export.
- Non-goals: graph topology extraction or route ordering.
- Invariants: binary shape/dimensions preserved; source not mutated; algorithm/backend explicit;
  empty skeleton and cancellation are valid states.

### Runnable vertical slice & concrete E2E

- Entry: binary line-art fixture/local image.
- Path: FS-010 preprocessing → skeleton transform → preview/export and pixel diagnostics.
- Observable result: one-pixel-wide representation for supported fixture without FS-015.

### PASS evidence

- Fixture unit/golden properties (not brittle full-image snapshot alone), real integration,
  component preview/cancel and full/static/dependency/overlay gates.
- Evidence: 40 targeted and 427 repository tests PASS; frozen sync, Ruff, strict mypy, overlay and
  diff checks PASS; correctness/security re-reviews GO after path/import/one-pixel hardening.

### Temporary / deferred / failure

- Implemented: reviewed scikit-image 0.26.x explicit Lee adapter; fully serves skeleton output.
- Deferred: graph FS-015.
- Fallback: no silent algorithm substitution; capability/provenance explicit.
- Docs: dependencies/architecture/security/trace/status/plan.
- Handoff: atomic commit and local fast-forward merge completed; stopped before FS-015.
  Push/PR remain separate external actions.

## FS-015 — Skeleton Graph

- Lifecycle: `completed`; validated locally on `feature/fs-015-skeleton-graph`.
- Goal: transform skeleton pixels into explicit graph topology with endpoints/junctions/loops/components.

### Dependency DAG & entry preconditions

- DAG: `FS-014 → FS-015`; skeleton contract/fixtures completed.
- Entry evidence: binary skeleton output and graph domain decision.
- Completion evidence: analytical/property/real integration, component JSON/overlay and live CLI
  E2E PASS; full/static/overlay gates PASS; independent review findings resolved.

### Scope / non-goals / invariants

- Scope: pixel adjacency policy, graph node/edge representation, chain compression, topology
  detection and deterministic traversal-neutral serialization for diagnostics.
- Non-goals: optimal route or component joining.
- Invariants: every foreground pixel is represented/traceable once according to policy; loops with
  no endpoint still represented; components explicit; diagonal connectivity convention fixed.

### Runnable vertical slice & concrete E2E

- Entry: T/cross/loop/multi-component skeleton fixture.
- Path: skeleton → graph builder → topology summary/diagnostic overlay.
- Observable result: expected degrees/endpoints/junctions/components without route stage.

### PASS evidence

- Analytical graph fixture unit/property tests; integration with real skeletonizer; diagnostic
  component overlay; full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: project-owned adjacency graph with simple deterministic compression.
- Deferred: PiecewiseCurve FS-016 and forced route FS-017.
- Performance: bounds from image limits; avoid quadratic all-pairs adjacency.
- Docs: architecture/data contracts within architecture, trace/status/plan; ADR if graph model major.
- Handoff: atomic feature commit and stop before merge/FS-016.

## FS-016 — Multiple Components and PiecewiseCurve

- Lifecycle: `completed`; verified 2026-08-29 on `feature/fs-016-piecewise-components`.
- Goal: preserve multiple disconnected components as explicit `PiecewiseCurve` without bridge.

### Dependency DAG & entry preconditions

- DAG: `FS-015 + FS-001 → FS-016`; graph and piecewise domain must be completed.
- Entry evidence: component graph IDs, PiecewiseCurve invariants and contour pipeline.
- Current gate: FS-015 graph and FS-001 `PiecewiseCurve` prerequisites are completed; bounded
  simple-component conversion contract fixed in ADR-017 and implementation authorized.

### Scope / non-goals / invariants

- Scope: graph/component→Curve segments, deterministic component/segment ordering, discontinuity
  metadata, all-components diagnostic rendering with pen-up.
- Non-goals: forced continuous connection and discontinuous Fourier coefficients.
- Invariants: segment boundaries explicit; no artificial bridge; per-segment order/source retained.

### Runnable vertical slice & concrete E2E

- Entry: two disconnected circles fixture/image.
- Path: image/skeleton graph → components → PiecewiseCurve → pen-up diagnostic curve display.
- Observable result: two segments and no drawn connector, independent of FS-018 Fourier mode.

### PASS evidence

- Unit segment/component mappings; property no hidden bridge; integration real image graph;
  component pen-up rendering and live diagnostic E2E; full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: deterministic component ordering by documented spatial key; fully represents data.
- Deferred: forced routing FS-017 and piecewise Fourier FS-018.
- Failure: ambiguous/empty component becomes diagnostic result, not fabricated segment.
- Docs: math discontinuity references, design/trace/status/plan.
- Evidence: 476 repository tests, Ruff, strict mypy, overlay validation and visual pen-up review PASS.
- Handoff: atomic feature commit; continue only through a separate FS-017 activation.

## FS-017 — Forced Continuous Routing

- Lifecycle: `completed`; verified 2026-08-29 on `feature/fs-017-forced-routing`.
- Goal: offer an explicit `STRICT_SINGLE_CURVE` route with measurable duplicated/bridge cost.

### Dependency DAG & entry preconditions

- DAG: `FS-016 → FS-017`; disconnected component representation completed.
- Entry evidence: graph/components and cost metric definition accepted.
- Current gate: FS-016 completed and committed locally at `721694d`; implementation authorized.

### Scope / non-goals / invariants

- Scope: deterministic baseline nearest-endpoint/component linking, Euler traversal where valid,
  documented Chinese-Postman-like heuristic only if justified, route provenance and added cost.
- Non-goals: globally optimal TSP/postman guarantee or advanced optimization FS-029.
- Invariants: original graph coverage retained; inserted/duplicated path labeled; result continuous;
  deterministic ties; no perfect-route claim.

### Runnable vertical slice & concrete E2E

- Entry: disconnected/branched accepted graph fixture and selected strict mode.
- Path: graph/components → route policy → continuous Curve → existing Fourier/chain diagnostic.
- Observable result: one continuous route, trace and reported added cost.

### PASS evidence

- Unit known Euler/non-Euler/disconnected routes; coverage/property tests; integration through
  Fourier trace; component policy/cost display; full/static/performance sanity/overlay PASS.

### Temporary / deferred / failure

- Allowed: documented nearest-endpoint + edge-duplication heuristic; fully working, non-optimal.
- Deferred: improved optimization FS-029.
- Failure: impossible/budget-exceeded route remains explicit; no silent switch to piecewise.
- Docs: algorithm limitations, architecture/trace/status/plan and ADR for chosen heuristic.
- Evidence: 487 repository tests, Ruff, strict mypy, overlay validation and visual route review PASS.
- Handoff: atomic feature commit; continue only through a separate FS-018 activation.

## FS-018 — Discontinuous Fourier Mode

- Lifecycle: `completed`; verified 2026-08-29 on `feature/fs-018-discontinuous-fourier`.
- Goal: analyze/render a true piecewise/discontinuous complex periodic signal with endpoint trace.

### Dependency DAG & entry preconditions

- DAG: `FS-016 + FS-005 + FS-006 → FS-018`; piecewise model, chain math and renderer completed.
- Entry evidence: explicit segment metadata and endpoint provenance property.
- Current gate: FS-016, FS-005 and FS-006 completed; implementation authorized.

### Scope / non-goals / invariants

- Scope: deterministic piecewise parameter allocation, explicit jumps, Fourier sampling, strict
  trajectory vs `PEN_UP_RENDERING`, comparison with forced route.
- Non-goals: asymptotic spectrum claims/analysis charts FS-019.
- Invariants: jumps preserved in source; Fourier trajectory not modified by pen-up; last endpoint
  draws approximation including rapid jump transitions in strict mode.

### Runnable vertical slice & concrete E2E

- Entry: explicit-jump/two-circles PiecewiseCurve.
- Path: piecewise sampler → existing Fourier/selection/chain → strict or pen-up renderer.
- Observable result: coefficients/endpoint history shared by both render policies; stroke differs only
  at semantic boundaries.

### PASS evidence

- Unit parameter allocation/jump metadata; property endpoint parity; integration policy comparison;
  component toggle and live diagnostic E2E; full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: documented proportional/equal segment allocation selected explicitly; fully usable.
- Deferred: spectrum analysis FS-019.
- Failure: allocation with insufficient samples rejected; no implicit segment merge.
- Docs: MATHEMATICS, DESIGN, trace/status/plan.
- Evidence: 502 repository tests, Ruff, strict mypy, overlay validation, visual inspection and
  independent final review GO.
- Handoff: atomic feature commit; continue only through a separate FS-019 activation.

## FS-019 — Discontinuity Spectrum Analysis

- Lifecycle: `completed`; verified 2026-08-29 on `feature/fs-019-discontinuity-spectrum`.
- Goal: measure amplitude/log amplitude, retained energy and reconstruction error vs K for jumps.

### Dependency DAG & entry preconditions

- DAG: `FS-018 + FS-004 → FS-019`; discontinuous pipeline and metrics completed.
- Entry evidence: accepted jump fixtures and measured coefficient/error APIs.
- Current gate: FS-018 and FS-004 completed; implementation authorized.

### Scope / non-goals / invariants

- Scope: analysis result, log-zero handling, K sweep with explicit ordering, charts/diagnostic export,
  continuous-vs-discontinuous comparison.
- Non-goals: unproved Gibbs/decay theorem claims or FFT2.
- Invariants: every point derives from recorded parameters/set; log zeros controlled; plot is a view
  over numeric result, not source of truth.

### Runnable vertical slice & concrete E2E

- Entry: explicit-jump accepted fixture and K range.
- Path: piecewise spectrum → K selections/reconstructions → metrics → analysis table/plot.
- Observable result: reproducible data and visualization with provenance.

### PASS evidence

- Unit log/energy/K sweep edge cases; integration with real FS-018; component chart state/export;
  numerical review/full/static/overlay PASS. Claims limited to measured fixtures.

### Temporary / deferred / failure

- Allowed: deterministic batch K loop; adequate for bounded N.
- Deferred: advanced research/benchmark conclusions.
- Failure: invalid range/budget returns typed error; partial sweep marked partial.
- Docs: math/test/trace/status/plan and learning only for real reusable finding.
- Evidence: 512 repository tests, Ruff, strict mypy, overlay validation, comparison visual review
  and independent final review GO.
- Handoff: atomic feature commit; continue only through a separate FS-020 activation.

## FS-020 — Separate 2D Fourier Image Mode

- Lifecycle: `completed`; verified 2026-08-29 on `feature/fs-020-fft2-image-mode`.
- Goal: implement raster `f(x,y) ↔ F(kx,ky)` without reusing 1D epicycle types.

### Dependency DAG & entry preconditions

- DAG: `FS-010 + FS-002 → FS-020`; safe raster input and established transform discipline completed.
- Entry evidence: dedicated 2D data/API design accepted via architecture/ADR; image limits active.
- Current gate: FS-010 and FS-002 completed; implementation authorized.

### Scope / non-goals / invariants

- Scope: FFT2/IFFT2 adapter, magnitude/log magnitude/phase, low/high-pass and explicit selected-
  frequency reconstruction, diagnostic view and round-trip fixtures.
- Non-goals: epicycle visualization of 2D bins, optimal image filters or GPU acceleration.
- Invariants: axes/shift/normalization recorded; real-image reconstruction tolerance defined;
  2D spectrum types separate from `FourierSpectrum` curve.

### Runnable vertical slice & concrete E2E

- Entry: validated grayscale synthetic/local image.
- Path: raster → FFT2 → selected visualization/filter → IFFT2 → output preview/export.
- Observable result: round-trip/filtered image and spectrum diagnostics without GUI FS-021.

### PASS evidence

- Analytical impulse/constant/sinusoid and round-trip tests; integration safe image input;
  component diagnostic controls; full/static/resource/performance sanity/overlay PASS.

### Temporary / deferred / failure

- Allowed: NumPy CPU FFT2 baseline; fully serves bounded image mode.
- Deferred: acceleration and advanced filters.
- Fallback: no GPU/alternate backend; NumPy failure explicit. Oversized input fail closed.
- Docs: dedicated math section/ADR, architecture/security/trace/status/plan.
- Evidence: 524 repository tests, Ruff, strict mypy, overlay validation, visual diagnostic review
  and independent final review GO.
- Handoff: atomic feature commit; stop before FS-021 and await user direction.

## FS-021 — PySide6 Desktop GUI

- Lifecycle: `completed`; source-run shell, renderer optimization, automated/component checks,
  independent review and user-confirmed manual Windows GUI/DPI/resize + physical-touch gates PASS.
- Goal: replace diagnostic shell with a responsive desktop workflow centered on Epicycles view.

### Dependency DAG & entry preconditions

- DAG: `FS-013 + FS-018 + FS-020 → FS-021`; both MVPs, discontinuity and FFT2 modes completed.
- Entry evidence: stable application use cases/view states, i18n resources, PySide6 platform/license
  review and offscreen component-test feasibility.
- Current evidence: PySide6 dependency and source-run shell committed; current full repository suite
  `543 passed`, Ruff/mypy/frozen sync/overlay PASS. Stable vector/circle rainbow pairing and isolated
  desktop touch pan/pinch component logic pass locally; physical-touch delivery and manual visible
  GUI/DPI/resize were confirmed by the user. Measured baseline on the recorded Windows host:
  core timeline ≈`0.31 ms/frame`, QPainter canvas ≈`3.66 ms/frame` at K=25, stress K=256 grows
  from ≈`10.4` to `13.5 ms/frame` as trace reaches 1001 points. Terminal gates PASS.
- Current no-trail/speed delta evidence: desktop paint no longer scans/renders trace or exposes its
  toggle; application ledger remains intact. Comparable K=25/600-frame paint improved
  ≈`3.66→2.00 ms/frame`. Reviewer P1 fixed: timer is inactive while paused and runs only after
  Play; final full suite `527 passed`; independent re-review `GO`. Terminal gates are closed.
- Current fixed-center/view-alignment maintenance evidence: newly accepted freehand curves reset to
  `1.00×`/zero pan and preserve their source-field-relative geometry; wheel/slider/pinch preserve the
  scene-coordinate under the canvas center through proportional pan correction, `Original` mirrors
  ready-layer visibility, and desktop speed starts at `0.01×`.
  Desktop component suite `24 passed`; full repository suite `558 passed`; frozen sync, Ruff, strict
  mypy, diff and overlay PASS; independent read-only review `GO`.

### Scope / non-goals / invariants

- Scope: SOURCE→EXPORT page shell, application state, background jobs/progress/cancellation,
  central Epicycles canvas/controls, keyboard/accessibility, persisted non-sensitive preferences,
  `en`/fallback/pseudo resources; measured renderer optimization.
- Non-goals: new math/CV algorithms, animation codecs, installer packaging.
- Invariants: UI dispatches existing use cases; no math/CV in handlers/paint; worker lifecycle bounded;
  actual chain endpoint history remains in application state/export evidence; desktop paints the
  existing contour and moving endpoint without a duplicate trace trail; visibility affects view only;
  optimization cannot change chain/trace semantics or weaken accepted tests.

### Ordered performance work

1. Record reproducible default/stress frame-time profiles with K, trace length, DPI, window size,
   OS/GPU/CPU and commit.
2. Stop timer/repaint while paused or unchanged; resume only on state/input/animation changes.
3. Cache source/reconstruction paths and scene bounds until curve/K/visibility/resize invalidates them.
4. Remove persistent trace from the desktop paint path and its toggle while retaining the bounded
   application ledger for parity/export; bounds and paint work must not scan `frame.trace`.
5. Batch dynamic geometry and avoid one Python/Qt object allocation per circle/vector where possible.
6. Map desktop speed slider exactly to `0.01..1.00×` in `0.01×` increments and test endpoints/steps.
7. Re-profile and prove endpoint/frame parity. Only if declared target remains unmet, run a bounded
   Qt Quick/QML scene-graph spike; adopt it only with measured gain, compatibility and rollback.
8. Do not migrate to React Native as a performance shortcut. A mobile technology decision belongs
   to FS-031 and requires Windows/Android renderer, bridge, packaging and dependency evidence.

### Runnable vertical slice & concrete E2E

- Entry: documented desktop launch command.
- Path: user selects freehand or supported image → existing application pipeline in worker →
  Epicycles view/control interactions → moving endpoint over the visible contour and diagnostics;
  the non-painted endpoint ledger remains available for parity/export.
- Observable result: responsive full workflow through real core, including error/cancel/restart.
  Default animation target and stress/degraded budget are documented from measured hardware rather
  than assumed; paused mode has zero continuous frame production.

### PASS evidence

- Unit view-state/reducer; integration worker/application; component pages/states/keyboard/i18n/text
  expansion; offscreen freehand+image callbacks through the actual desktop/application path;
  shutdown/cancel/thread leak checks; full/static/dependency/Windows smoke/overlay PASS and manual
  visible DPI/resize diagnostic. Performance evidence includes
  before/after frame-time buckets, long-trace behavior, parity and paused-redraw assertion.
  Component evidence asserts no desktop trace paint/toggle, exact smooth speed range/step, stable
  vector/circle colors by selection position, and bounded presentation-only mouse/touch viewport logic.

### Temporary / deferred / failure

- Allowed: direct PySide6 desktop launch without installer; fully working source-run product.
- Allowed renderer path: optimized QWidget/QPainter when it meets the recorded budget; otherwise a
  Qt Quick/QML scene-graph adapter to the same immutable frame contract.
- Deferred: export implementation FS-022 and packaging hardening FS-023.
- Failure: background exception becomes localized stable error state; no UI-thread fallback.
- Docs: README run workflow, DESIGN, architecture, security/testing/dependencies, trace/status/plan.
- Handoff: FS-021 integrated in local `main`; proceed only through a separately selected FS-022 slice.

## FS-022 — Export

- Lifecycle: `completed`; implementation, automated gates, documentation synchronization and
  independent read-only review PASS on `feature/fs-022-export`.
- Goal: export versioned data/images and animation generated from the same chain timeline.

### Dependency DAG & entry preconditions

- DAG: `FS-021 → FS-022`; desktop/application timeline must be completed.
- Entry evidence: stable Curve/spectrum/state contracts, safe path policy and codec capability review.
- Current gate: satisfied; FS-021 is completed. FS-022 targeted combined suite is `37 passed`, full
  repository suite is `557 passed`; frozen sync, Ruff, strict mypy, diff and overlay PASS.
  Independent read-only review: `GO`.

### Scope / non-goals / invariants

- Scope: Curve JSON/CSV, coefficients JSON/CSV, spectrum/reconstruction/intermediate PNG, GIF;
  MP4 only with stable reviewed backend; version/provenance, overwrite decision, progress/cancel,
  partial artifact recovery.
- Non-goals: cloud sharing, arbitrary codecs or project/session persistence unless separately approved.
- Invariants: animation frames use actual `EpicycleChainState`; trace point=endpoint; no shell
  interpolation; existing file not silently overwritten; success lists actual artifacts.

### Runnable vertical slice & concrete E2E

- Entry: user completes a freehand/image pipeline, opens EXPORT, selects GIF and destination.
- Path: UI → export use case → same timeline/state renderer → safe temp write → readable final file.
- Observable result: artifact reopens, shows nested vectors/final endpoint/matching trace; cancellation
  or unavailable MP4 gives explicit state.

### PASS evidence

- Unit serializers/path/version; integration real GIF/PNG and optional MP4 capability; component
  overwrite/progress/cancel/error; live E2E reopens artifact and compares endpoint history metadata;
  security/logging/full/static/dependency/overlay PASS.

### Temporary / deferred / failure

- Allowed: GIF as mandatory fully working animation; MP4 may remain visibly unavailable.
- Deferred: additional codecs/session state.
- Fallback: MP4 unavailable → user may explicitly choose GIF; no silent output-format change.
  Partial side effect reconciled before retry.
- Docs: README formats/limits, SECURITY, dependency/fallback delta if actual chain, trace/status/plan.
- Handoff: commit and stop before FS-023.

## FS-023 — Hardening and Packaging Readiness

- Lifecycle: `completed`; required product milestone; automated gates PASS and independent re-review GO.
- Goal: establish measured numerical/performance/reliability/platform evidence for completed product.

### Dependency DAG & entry preconditions

- DAG: `FS-022 → FS-023`; complete desktop/export primary paths required.
- Entry evidence: full accepted regression suite and representative data/operation inventory.
- Current gate: prerequisite FS-022 satisfied; user explicitly selected FS-023. Implementation,
  automated gates and independent re-review are complete; commit `a2d7a2c` is integrated in `main`
  and published to `origin/main`.

### Scope / non-goals / invariants

- Scope: large N/high K profiles, numerical stability, cancellation, invalid/degenerate inputs,
  Unicode/Windows paths, export failures, memory/frame bounds, dependency/security audit, installer/
  packaging decision and smoke if approved.
- Non-goals: optional feature stages FS-024+ or unverifiable performance marketing claims.
- Invariants: optimization parity with reference; no weakened validation/tests; source-run path remains
  recoverable if packaging experiment fails.

### Runnable vertical slice & concrete E2E

- Entry: fresh supported Windows environment/clean checkout.
- Path: frozen restore/build or source launch → freehand E2E → image E2E → export E2E → invalid/
  cancel recovery.
- Observable result: documented PASS/failure matrix, measured budgets and runnable artifact/path.

### PASS evidence

- Baseline→profile→targeted optimization→parity→benchmark; unit/integration/component/all live E2E;
  clean restore/build/package smoke if selected; security/dependency/license/static/overlay/diff review.
  Evidence records hardware/OS/Python/commit and caveats.
- Current evidence: 43 targeted and 566 full tests PASS; branch coverage 76% with floor 75%; frozen
  sync, Ruff, strict mypy, dependency compatibility/audit/SBOM and isolated wheel smoke PASS. Named
  Windows benchmark records `N=65,536`, stress `K=4096`, allocation and offscreen paint evidence;
  offscreen timing is not visible GUI/DPI evidence. Source-run/wheel selected, installer/public
  redistribution unselected pending license/notice/LGPL compliance.
- Independent review: initial two P2 test-harness findings fixed; final re-review `GO`, no P0/P1/P2.

### Temporary / deferred / failure

- Allowed: source-run distribution if installer criteria are not approved; must be fully documented
  and runnable, while packaging status remains non-terminal only if installer is required by SPEC.
- Deferred: optional educational/analysis enhancements.
- Failure/rollback: retain known-good implementation/lockfile; optimization/package experiment
  reverts in a dedicated recovery branch, never deletes user data or disables gates.
- Docs: all completion-gate sources, performance/platform limits and release readiness decision.
- Handoff: product milestone committed, integrated and published; no release/deployment claim; stop.

## FS-024 — Harmonic Inspector (Optional)

- Lifecycle: `completed`, optional; automated gates PASS and independent review GO.
- Goal: inspect one chain vector/coefficient without changing mathematical state.

### Dependency DAG & entry preconditions

- DAG: `FS-023 + FS-021 + FS-005 → FS-024`; hardened GUI and chain metadata completed.
- Entry evidence: stable selection/hit-test mapping and accessible inspector design.
- Current gate: implementation and terminal evidence complete in `feature/fs-024-harmonic-inspector`;
  authorized MDP remains the integration action. Stable frequency identity, click/drag hit-test
  separation and accessible list/panel are recorded in SPEC/architecture/design/testing.

### Scope / non-goals / invariants

- Scope: select vector/circle/list row; show k, amplitude, phase, angular velocity and current local
  contribution with resource strings/keyboard path.
- Non-goals: editing coefficients or frequency solo.
- Invariants: inspection read-only; value derives from same coefficient/state; selection identity
  stable across view ordering/timeline updates.

### Runnable vertical slice & concrete E2E

- Entry: user opens Epicycles and selects a visible harmonic.
- Path: hit/list selection → stable coefficient ID → inspector view model → localized panel.
- Observable result: values match actual chain state while animation continues/pauses.

### PASS evidence

- Unit mapping/format; integration chain state; component pointer/keyboard/empty/text expansion;
  live GUI E2E; full/static/overlay PASS.
- Current evidence: targeted `32 passed`, focused post-self-review `7 passed`, full repository
  `573 passed in 146.79s`; frozen sync, Ruff, strict mypy, diff and overlay PASS. Independent review
  `GO`, no P0/P1/P2. Actual Qt offscreen E2E is functional evidence, not manual visible DPI evidence.

### Temporary / deferred / failure

- Allowed: side panel with textual numeric values; fully serves inspection.
- Deferred: solo FS-025 and build-up FS-026.
- Failure: off-canvas/stale selection clears explicitly, never shows wrong harmonic.
- Docs: DESIGN/trace/status/plan.
- Handoff: commit and perform the authorized MDP; stop FS-024 before selecting FS-025.

## FS-025 — Frequency Solo (Optional)

- Lifecycle: `planned`, optional.
- Goal: let user visually isolate selected harmonics with explicit analysis semantics.

### Dependency DAG & entry preconditions

- DAG: `FS-024 + FS-003 → FS-025`; inspector and deterministic selection completed.
- Entry evidence: selected coefficient IDs and separation of render selection vs Fourier selection.
- Current gate: DAG prerequisites are completed after FS-024; optional stage remains unselected.

### Scope / non-goals / invariants

- Scope: solo/multi-select UI, explicit mode label, original selection restore and isolated contribution
  trace/geometry according to documented semantics.
- Non-goals: mutating/exporting source spectrum by default.
- Invariants: original spectrum immutable; user sees whether solo changes chain coefficient set or
  visibility only; endpoint/trace equivalence uses actual active set.

### Runnable vertical slice & concrete E2E

- Entry: user selects coefficient in inspector and activates Solo.
- Path: UI command → explicit active selection/view policy → chain states → visible isolated trace;
  exit restores prior set.
- Observable result: chosen frequency contribution and correct labels/provenance.

### PASS evidence

- Unit state transitions/restore; property active-set endpoint; component accessibility; live E2E;
  full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: one harmonic solo first, if SPEC scope explicitly says one and multi-select deferred; it
  must fully work for declared slice.
- Deferred: build-up sequence FS-026.
- Failure: empty selection rejected; no hidden state loss.
- Docs: SPEC if one-vs-multi contract changes, DESIGN/trace/status/plan.
- Handoff: commit and stop.

## FS-026 — Harmonic Build-Up Animation (Optional)

- Lifecycle: `planned`, optional.
- Goal: animate reconstruction sets `1 → 2 → … → N` using deterministic ordering.

### Dependency DAG & entry preconditions

- DAG: `FS-024 + FS-004 + FS-021 → FS-026`; inspector, selection/reconstruction and GUI completed.
- Entry evidence: deterministic ordering and timeline/state-machine decision.
- Current gate: DAG prerequisites are completed after FS-024; optional stage remains unselected.

### Scope / non-goals / invariants

- Scope: build-up timeline, ordering/count controls, pause/restart, current K/metrics and endpoint
  trace reset/transition semantics.
- Non-goals: changing coefficients or claiming error monotonicity for arbitrary ordering.
- Invariants: each step uses exact first-K set of displayed ordering; trace derives from that step's
  actual chain; transitions cannot mix histories ambiguously.

### Runnable vertical slice & concrete E2E

- Entry: user selects ordering and starts Build-Up.
- Path: timeline increments K → existing selection/chain → actual endpoint trace + inspector update.
- Observable result: visibly increasing harmonic set with reproducible state/metrics.

### PASS evidence

- Unit state machine; property set/endpoint; integration timeline; component controls; live E2E;
  performance sanity/full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: discrete step animation with configurable dwell; fully serves behavior.
- Deferred: smooth interpolation between coefficient sets unless separately specified.
- Failure: K budget/cancel restores stable state; no unbounded trace accumulation.
- Docs: DESIGN/math semantics/trace/status/plan.
- Handoff: commit and stop.

## FS-027 — Curve Simplification (Optional)

- Lifecycle: `planned`, optional.
- Goal: simplify contours with measured shape/error impact before resampling.

### Dependency DAG & entry preconditions

- DAG: `FS-023 + FS-009 + FS-013 → FS-027`; hardened metrics/parameterization/image MVP completed.
- Entry evidence: baseline sample/error/performance measurements and algorithm decision.
- Current gate: DAG prerequisites are completed; optional stage remains unselected and its algorithm
  entry evidence has not been accepted.

### Scope / non-goals / invariants

- Scope: Douglas–Peucker baseline and optional curvature-aware policy only if justified, tolerance
  config, open/closed handling, diagnostics and comparison metrics.
- Non-goals: adaptive resampling FS-028 or route optimization.
- Invariants: order/closure preserved; source curve immutable; simplification provenance and point
  reduction/error visible; no universal quality claim.

### Runnable vertical slice & concrete E2E

- Entry: image/freehand curve with tolerance.
- Path: source Curve → simplifier → existing resampling/Fourier/chain → side-by-side metrics/trace.
- Observable result: reduced point curve and measured reconstruction/shape effects.

### PASS evidence

- Unit known polylines/closure/degenerate; property subsequence/order/tolerance where valid;
  integration/E2E existing pipeline; benchmarks/full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: deterministic Douglas–Peucker only; fully working baseline.
- Deferred: curvature-aware algorithm and FS-028 allocation.
- Failure: invalid tolerance rejected; original path remains selectable/recoverable.
- Docs: algorithm/metrics decision, trace/status/plan.
- Handoff: commit and stop.

## FS-028 — Adaptive Sampling (Optional)

- Lifecycle: `planned`, optional.
- Goal: allocate more samples near measured curvature while preserving curve semantics and budget.

### Dependency DAG & entry preconditions

- DAG: `FS-027 + FS-009 → FS-028`; simplification/baseline arc-length sampling completed.
- Entry evidence: curvature definition, sample budget and comparison fixtures accepted.
- Current gate: unsatisfied while prerequisites are planned.

### Scope / non-goals / invariants

- Scope: curvature estimate, bounded allocation, open/closed boundaries, deterministic comparison
  with uniform arc-length sampling.
- Non-goals: changing Fourier convention or claiming superiority for all curves.
- Invariants: exact total budget, preserved order/endpoints/closure, finite spacing and explicit
  degenerate behavior.

### Runnable vertical slice & concrete E2E

- Entry: high-curvature accepted fixture and fixed sample count.
- Path: Curve → adaptive samples → existing Fourier/chain → metrics/trace comparison.
- Observable result: reproducible allocation visualization and measured result.

### PASS evidence

- Unit/property allocation budget/order/degenerates; integration/E2E comparison; performance/full/
  static/overlay PASS with no unsupported quality claim.

### Temporary / deferred / failure

- Allowed: documented discrete curvature weighting with minimum per segment; fully serves slice.
- Deferred: learning/optimization-based sampling.
- Failure: unstable/zero weights use explicit uniform policy only if pre-approved and provenance marks
  it; otherwise typed failure.
- Docs: MATHEMATICS/decision/trace/status/plan.
- Handoff: commit and stop.

## FS-029 — Better Single-Stroke Optimization (Optional)

- Lifecycle: `planned`, optional.
- Goal: improve added route cost over FS-017 baseline without weakening coverage/correctness.

### Dependency DAG & entry preconditions

- DAG: `FS-023 + FS-017 → FS-029`; hardened product and baseline route/cost completed.
- Entry evidence: representative benchmark corpus, baseline costs/time and optimization goal.
- Current gate: DAG prerequisites are completed; optional stage remains unselected and its benchmark
  entry evidence has not been accepted.

### Scope / non-goals / invariants

- Scope: one justified improved graph heuristic, deterministic budget, baseline comparison and
  selectable algorithm/provenance. Corpus includes representative complex multi-stroke line art with
  disconnected components, loops and branches; the user sees added length, bridge count and duplicate
  length before accepting an improved route.
- Non-goals: exact global optimum unless algorithm/proof and feasible bounds explicitly accepted;
  silently turning pen-up input into a continuous route.
- Invariants: graph coverage and continuity preserved; cost never reported without method;
  timeout/cancel returns no false-complete route.

### Runnable vertical slice & concrete E2E

- Entry: accepted routing corpus, including complex multi-stroke line art, and optimization budget.
- Path: graph → user-selected baseline/improved route → cost/time comparison → existing Fourier
  endpoint trace.
- Observable result: valid route plus measured delta; baseline and `PIECEWISE_DISCONNECTED` remain
  available instead of fabricated bridges.

### PASS evidence

- Correctness/golden/property tests; baseline benchmark and parity; integration/E2E selector;
  cancellation/performance/full/static/overlay PASS with environment recorded.

### Temporary / deferred / failure

- Allowed: bounded heuristic that may not improve every input, provided result is valid and metrics
  explicit.
- Deferred: exact solver/research variants.
- Fallback: timeout may offer explicit baseline route after capability check; no silent switch.
- Docs: ADR/algorithm limits/performance/trace/status/plan.
- Handoff: commit and stop.

## FS-032 — Basis Selection and Haar Wavelet Reconstruction (Optional)

- Lifecycle: `planned`, optional.
- Goal: let a user explicitly choose `FOURIER_EPICYCLE` or `HAAR_WAVELET` for a bounded curve
  decomposition, then animate the selected basis' actual partial reconstruction.

### Dependency DAG & entry preconditions

- DAG: `FS-023 + FS-004 + FS-021 → FS-032`; hardened product, partial-reconstruction metrics and
  a completed desktop basis-control surface are required.
- Entry evidence: accepted basis-decomposition SPEC, canonical freehand/closed-curve fixture corpus,
  numerical baseline and UI language distinguishing a rotating epicycle from a wavelet term.
- Current gate: DAG prerequisites are completed; FS-032 remains unselected and may start only through
  a separately approved stage slice.

### Scope / non-goals / invariants

- Scope: explicit basis selector with `FOURIER_EPICYCLE` default and project-owned orthonormal Haar
  baseline; immutable basis-specific result/provenance, bounded coefficient/term selection and one
  actual animated partial-reconstruction view for each basis.
- Non-goals: silently replacing Fourier, presenting Haar terms as rotating circles, arbitrary wavelet
  families, image raster transforms, or a claim that one basis is universally superior.
- Invariants: source `Curve` stays immutable; selected basis and ordering are recorded; invalid or
  unavailable basis fails visibly without fallback; Fourier endpoint/epicycle equality remains exact
  only in Fourier mode, while Haar animation displays scale/location terms and the corresponding
  reconstructed curve.

### Runnable vertical slice & concrete E2E

- Entry: user completes a canonical freehand curve and selects a basis before decomposition.
- Path: Curve → explicit basis adapter → bounded immutable decomposition → basis-specific term
  selection → animation frame → desktop view/provenance.
- Observable result: Fourier mode shows the existing head-to-tail epicycles; Haar mode visibly builds
  the same curve approximation from selected scale/location terms and labels it as wavelet
  reconstruction, without fabricated circles or endpoint-trace equivalence.

### PASS evidence

- Unit Haar analysis/synthesis on constant, impulse, step and small deterministic curves; property
  finite/bounded round trip and coefficient-selection provenance; integration basis adapter and
  reconstruction metrics; component selector/disabled/error/pseudo-locale paths; live desktop E2E for
  both bases; numerical/performance/full/static/overlay PASS with environment and caveats recorded.

### Temporary / deferred / failure

- Allowed: Haar only as the fully working non-Fourier baseline; it must reconstruct and animate its
  declared slice without an external numerical-library fallback.
- Deferred: Daubechies/biorthogonal families, learned bases, cross-basis quality rankings and export
  extensions until separately specified.
- Failure: unsupported basis, over-budget input or numerical failure publishes no partial/stale
  reconstruction; the user may explicitly choose Fourier, but the application never switches modes
  silently.
- Docs: basis SPEC, ARCHITECTURE/ADR, DESIGN/MATHEMATICS/TESTING, traceability/status/plan.
- Handoff: commit optional stage and stop.

## FS-030 — Educational Mode (Optional)

- Lifecycle: `planned`, optional.
- Goal: show the causal mapping samples→coefficient→circle/vector→chain→endpoint→trace.

### Dependency DAG & entry preconditions

- DAG: `FS-023 + FS-024 + FS-026 → FS-030`; hardened GUI, inspector and build-up completed.
- Entry evidence: accessible instructional design, terminology/resources and stable step state.
- Current gate: unsatisfied while prerequisites are planned.

### Scope / non-goals / invariants

- Scope: guided stepper, synchronized sample/spectrum/vector highlights, equations from canonical
  convention, pause/keyboard/locale resources and canonical fixtures.
- Non-goals: new math algorithms, assessment system or unreviewed theorem claims.
- Invariants: displayed values/equations derive from actual state; educational trace remains actual
  endpoint; explanations never contradict MATHEMATICS/SPEC.

### Runnable vertical slice & concrete E2E

- Entry: user selects canonical circle fixture and Educational Mode.
- Path: guided controls → actual samples/spectrum/chain states → synchronized labels/equations/trace.
- Observable result: user can step from coefficient to its current vector contribution and final
  drawing point without hidden mock data.

### PASS evidence

- Unit mapping/equation formatting; integration actual states; component keyboard/fallback/
  pseudo-locale/text expansion; live guided E2E; content/math review; full/static/overlay PASS.

### Temporary / deferred / failure

- Allowed: one canonical circle lesson covering the complete causal chain; fully working slice.
- Deferred: additional lessons/quizzes/locales.
- Failure: unavailable state disables step with explanation; no fabricated values.
- Docs: DESIGN/user guide in README only if launch behavior changes, trace/status/plan.
- Handoff: commit optional stage, synchronize evidence and stop.

## FS-031 — Android Touch-to-Epicycles MVP

- Lifecycle: `planned`, optional mobile expansion.
- Goal: deliver an installable offline Android MVP where a finger/stylus stroke is decomposed into
  the same Fourier vectors and animated as an actual endpoint trace.

### Dependency DAG & entry preconditions

- DAG: `FS-023 + FS-008 + FS-005 → FS-031`; hardened shared contracts, live freehand capture
  semantics and epicycle mathematics must be completed before mobile implementation starts.
- Entry evidence: accepted `specs/features/android-touch.spec.md`, canonical fixture parity corpus,
  Android SDK/emulator or named physical device, and a reviewed technology decision.
- Technology decision gate: compare at least Qt/QML Android with Python deployment and a native
  Android adapter around a portable core; React Native/Skia is eligible only if current Android and
  required desktop/toolchain support are proven. Record build size, offline capability, bridge cost,
  renderer frame time, maintenance/license and packaging implications. No framework is preselected.
- Current gate: DAG prerequisites are completed, but Android capability/SDK/device entry evidence is
  not approved and FS-031 remains unselected.

### Scope / non-goals / invariants

- Scope: debug-installable Android app, single-touch/stylus canvas, bounded sampling/resampling,
  Play/Pause/Restart, harmonic/speed controls, circles/vectors/endpoint/trace, portrait/landscape,
  lifecycle cancellation, content descriptions, local-only state and measured frame/memory budget.
- Non-goals: image import, cloud sync/account, Play Store publication, advertisements, telemetry,
  desktop replacement or new Fourier/CV algorithms.
- Invariants: same DFT convention, selection and endpoint equality as shared reference; mobile UI
  never becomes a second math source; raw touch data remains local; no required network permission.

### Runnable vertical slice & concrete E2E

- Entry: documented build/install command for declared Android emulator/device.
- Path: user draws one stroke with finger/stylus → bounded capture → Curve/resampling → shared or
  parity-proven Fourier use case → epicycle chain → animated circles/vectors/endpoint/trace.
- Observable result: installed app supports play/pause/restart and harmonic change, survives
  cancel/background/foreground/rotation coherently and produces no stale or fabricated trace.

### PASS evidence

- Unit touch lifecycle/coordinate transform/budgets; property/reference coefficient and endpoint
  parity; integration actual mobile adapter; component gestures/controls/accessibility/layout;
  live emulator or physical-device E2E; lifecycle interruption tests; recorded frame-time/memory/
  package-size evidence; manifest/privacy/dependency/license review; reproducible build and full
  unaffected Python core/static/overlay gates.

### Temporary / deferred / failure

- Allowed: debug APK on one declared Android architecture/device profile; it must provide the full
  offline touch-to-animation slice. Release signing/store distribution are not implied.
- Deferred: image import, cross-device sync, iOS, store release and additional mobile locales.
- Failure: unsupported device/backend shows a stable unavailable state; no silent renderer/math
  substitution, upload or partial stale animation. Technology spike failure leaves desktop/core intact.
- Docs: mobile SPEC, architecture/decision/design/security/testing/dependencies, README build/run,
  traceability/roadmap/status/plan and exact toolchain/version evidence.
- Handoff: commit the Android MVP, do not claim store release, and stop for explicit direction.
