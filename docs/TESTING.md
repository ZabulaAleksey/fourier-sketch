# Test strategy Fourier Sketch

## Source of contract

SPEC/ADR задают требования; accepted tests/fixtures/goldens являются executable contract и
evidence. Обычная implementation не изменяет их ради green. Новые tests добавляются до первой
приёмки соответствующего behavior и после этого считаются принятыми.

## Канонические команды

```powershell
uv sync --all-groups --frozen
uv run pytest
uv run ruff check .
uv run mypy
py -3 ~/.codex/tools/validate_project_overlay.py .
uv run coverage erase
uv run coverage run -m pytest
uv run coverage report
uv run python tools/fs023_hardening.py
uv build --wheel
```

FS-023 дополнительно выполняет measured coverage, hardening benchmark и clean wheel smoke командами,
зафиксированными в README после появления соответствующего harness. Installer smoke не заявляется:
выбран только recoverable source wheel, а desktop installer остаётся без утверждённого target.

## Уровни

### Smoke

Stage `FS-000`: clean environment, package import/version, overlay structure.

### Unit

Value invariants, conversions, reference formulas, ordering, metrics, validators, individual image
transforms, threshold-boundary/Canny adapters, graph/routing primitives и export serializers.

### Property

Hypothesis добавлен в FS-002. Реализованы:

- DFT/IDFT round-trip finite arrays;
- translation/DC и complex scaling;
- reference DFT/FFT parity;
- deterministic complete-spectrum ordering/permutation, включая even-N Nyquist;
- full/partial reconstruction, retained-energy bounds и explicit normalized-error states;
- epicycle connectivity, permutation-invariant endpoint и endpoint/reconstruction parity;
- index-resampling order, exact open endpoints, closed seam и bounded output;
- arc-length order/exact open endpoints/closed seam, zero-length failure и uniform straight-line
  spacing;

Planned для соответствующих stages:

- adaptive/curvature-aware sampling (`FS-028`).

### Integration

Real boundaries: Curve → spectrum → chain, image decoder → transform, contour → application use
case, renderer consumes chain state, exporter consumes the same timeline, locale resource loader.

FS-006 реализовал integration boundary `EpicycleFrame → Matplotlib artists/Agg PNG`: circle
center/radius и arrow geometry сравниваются с chain state, visibility не мутирует math, existing
destination сохраняется.

FS-007 реализовал boundary `pointer capture → cleaned/index-resampled Curve → FFT → timeline →
Matplotlib frame`; tests проверяют source/sample provenance, one-point DC и open/closed topology.

FS-010 реализовал boundary `bounded local bytes → allowlisted Pillow verify/decode → typed
grayscale/binary → PNG publication`: реальные PNG/JPEG/TIFF/APNG/corrupt/oversized fixtures
проверяют actual format, EXIF orientation, оба budgets, transform provenance и overwrite safety.

FS-011 реализовал boundary `FS-010 grayscale/binary → explicit threshold boundary или OpenCV
Canny → typed same-sized binary edge raster → PNG`: synthetic shape fixtures проверяют 4/8
connectivity, Canny parameters, distinct algorithm output, backend provenance и source immutability.

FS-012 реализовал boundary `edge result → external candidates → dominant closed Curve →
arc-length samples → FFT/timeline → Agg PNG`: unit/property tests проверяют exact selection key,
backend-order/cyclic/reversal invariance, coordinate/orientation/start policies, malformed output и
budgets; real threshold/Canny integration проверяет endpoint equality.

FS-014 реализовал boundary `FS-010 binary → scikit-image Lee → typed same-sized skeleton →
binary/preview PNG`: synthetic line/T/cross/loop/noise и real JPEG fixtures проверяют thinning,
source immutability, output subset, explicit provenance, empty result и отсутствие solid 2×2 block
как robust property вместо brittle full-image golden.

FS-015 реализовал boundary `typed Lee skeleton → corner-suppressed adjacency → compressed graph →
canonical JSON/overlay`: analytical line/T/cross/loop/multi-component fixtures проверяют degree
roles, junction regions, self-loop и отсутствие bridge; property test проверяет exact disjoint
pixel ownership и byte-stable serialization на generated accepted skeletons. Real integration
проходит FS-010/FS-014 backend до topology. Regression fixtures дополнительно фиксируют raw cycle
внутри junction region, public 250k budget, non-quadratic many-component scan и cancellation
внутри длинной compressed chain.

FS-016 добавляет analytical path/loop/isolated/branched/empty/cancelled fixtures, generative exact
path coverage, real two-ring integration, separate-artist component assertions и live subprocess
`PNG → Lee → graph → PiecewiseCurve → pen-up PNG`. Общий raster transform повторно используется
FS-012 без изменения accepted contour normalization tests.

FS-017 проверяет shared adjacency parity, Euler loop/open trail, non-Euler tree T-join,
disconnected cyclic bridges, exact original-link coverage, deterministic generated paths и live
`image → Lee → graph → route → resampling → Fourier timeline → PNG`.

FS-029 добавляет accepted corpus loop/branch/asymmetric comb/disconnected, baseline/improved
coverage/continuity parity, deterministic algorithm selection, bounded shortest-path expansion and
cancel/resource failure. Integration/component/live CLI показывают method, duplicate/bridge/added
delta и routing time; full/performance evidence не объявляет heuristic exact/global optimum.

### Component

Matplotlib/PySide controls and state transitions: empty/loading/error/disabled/cancelled, visibility
toggles, keyboard navigation, default/fallback/pseudo-locale, text expansion. Headless/offscreen
mode допустим только если он выполняет actual component code.

FS-006 component evidence покрывает play/pause/restart, speed/K, six visibility toggles, trace
budget и locale fallback/pseudo. Полный PySide state/accessibility matrix остаётся FS-021.

FS-007 component evidence вызывает фактические Matplotlib callbacks для press/motion/release/key,
проверяет stable drawing coordinates, ignore-outside behavior, reset/cancel и controlled limits.

FS-008 component evidence вызывает фактические Button press/release events и Slider callbacks на
той же surface: pre-input safety, play/pause/restart, speed/K, release coordinate и trace reset.

FS-009 component/live evidence вызывает RadioButtons method selection на ready actual-event
capture, сравнивает measured CV и проверяет transactional restore для one-point arc failure.

FS-010 component evidence запускает localized image CLI in-process и проверяет success,
invalid-options и existing-output states; live subprocess E2E проходит local JPEG → transforms →
binary PNG и privacy-safe corrupt failure. Это самостоятельный preprocessing slice, а полный
cohesive product `image → controls → contour → Fourier` E2E остаётся scope FS-013.

FS-011 component/live evidence запускает localized edge CLI для обоих selected algorithms,
проверяет algorithm-specific parameters, same-sized binary PNG, existing-output preservation и
privacy-safe corrupt failure. Unavailable/malformed Canny подтверждён negative unit path без
fallback.

FS-012 component/live evidence запускает localized contour CLI, проходит реальный local
PNG → decode/preprocess → выбранные edges → OpenCV external extraction → dominant/resampled Curve →
тот же timeline/renderer → PNG. Assertions проверяют provenance/sample/trace counts, existing-output
preservation, pseudo locale и explicit empty result без Curve/timeline/artifact. Это runnable
diagnostic slice; FS-013 переиспользует его без изменения accepted FS-012 контрактов.

FS-013 component evidence вызывает реальные Matplotlib Button/Slider/CheckButtons/key callbacks,
проверяет initial/processing/ready/empty/error/cancelled, control enablement, pseudo expansion и
cancelled late-result suppression. Integration проходит обе explicit edge ветки до общего
timeline endpoint; live subprocess E2E создаёт четырёхпанельный PNG, recovery PNG для no-contour,
privacy-safe corrupt failure и existing-output preservation.

FS-014 component evidence рисует actual two-panel Agg preview с source/result/provenance, проверяет
pseudo expansion и no-overwrite race. Application tests подтверждают complete/empty/error states,
cooperative cancellation и stale-generation suppression; live subprocess E2E повторно открывает
binary skeleton/preview PNG и проверяет corrupt/existing-output/privacy paths.

FS-015 component evidence рисует actual skeleton/topology overlay с component-colored edges и
endpoint/junction/loop/isolated markers, повторно открывает PNG/JSON и проверяет atomic
no-overwrite. Live subprocess E2E проходит local PNG → Lee → graph → canonical JSON/overlay и
privacy-safe corrupt failure.

FS-016 component evidence проверяет отдельный Matplotlib artist на каждый curve segment, explicit
boundary count, pseudo-locale и повторно открываемый atomic PNG. Live subprocess E2E подтверждает
два segments и одну pen-up boundary для двух disconnected strokes.

### E2E

Критические live paths:

1. canonical fixture → Fourier → timeline/endpoints → Agg PNG (`FS-006`, реализован);
2. freehand input → Curve → Fourier → chain → endpoint trace (`FS-007`, input slice реализован;
   `FS-008` подтверждает cohesive controls и exact endpoint-history ledger);
3. image file → controls/decode/edges → dominant contour/Curve → same Fourier/chain → trace
   (`FS-013`, cohesive Matplotlib/headless product flow реализован);
4. image file → binary preprocessing → explicit Lee skeleton → readable skeleton/preview PNG
   (`FS-014`, самостоятельный local diagnostic реализован);
5. image file → Lee skeleton → explicit components/nodes/edges → readable JSON/topology overlay
   (`FS-015`, traversal-neutral diagnostic реализован);
6. image file → graph components → explicit PiecewiseCurve → pen-up overlay (`FS-016`, реализован);
7. image file → explicit forced cyclic route → Fourier trace (`FS-017`, реализован);
8. desktop interaction → export → readable artifact with matching endpoint history (`FS-022`).
9. Android finger/stylus stroke → parity-proven Fourier chain → animated endpoint trace on a named
   emulator/device (`FS-031`, planned).

До появления live product path сценарий имеет `BLOCKED_BY_BACKEND`/non-terminal status и не
заменяется mock-only success. Для local desktop equivalent backend — application/core path.

## Numerical fixtures

Planned accepted fixtures: constant, circle, ellipse, square, triangle, line, spiral,
figure-eight, letter-like curve, two disconnected circles, explicit jump и noisy contour.
Fixture generation фиксирует N, orientation, parameterization и expected property, а не только
картинку.

Circle convention example при `z[n] = exp(i2πn/N)`: dominant coefficient `C_(+1)=1` с прочими
coefficients около zero. Если screen Y-axis inversion применяется, она остаётся presentation
transform и не меняет domain fixture silently.

## Tolerances and evidence

Каждый numerical test задаёт `atol/rtol` рядом с rationale (N, scale, algorithm). Сравнение с
renderer pixels не заменяет numerical assertion. NaN/Inf и degenerate metrics проверяются
отдельно.

Evidence report для gate:

```text
command/check
result: PASS | FAIL | BLOCKED | NOT RUN
scope and environment/commit
caveat
```

## Stage gates

- functional change: релевантные unit + integration + component;
- mathematical invariant: unit + property + analytical fixture;
- user-facing stage: component + live E2E;
- security boundary: negative/integration tests;
- performance claim: recorded baseline/benchmark + correctness parity;
- dependency change: lockfile + frozen clean restore.

Full `uv run pytest` остаётся regression suite. Test count не фиксируется в docs, чтобы не создавать
stale claims.

FS-018 acceptance дополнительно проверяет exact equal/proportional allocation, materialized closed
segment seam, flattened boundary indices и periodic last→first boundary; property determinism,
одинаковые spectra/endpoint history двух render policies, same-budget forced-route comparison,
разное число source artists и live two-circle PNG в обоих modes.

FS-019 acceptance проверяет zero-safe finite logarithm, invalid/duplicate/unordered K, monotonic
retained energy и full-K reconstruction, real FS-018 comparison с одинаковыми parameters,
chart series/atomic no-overwrite и live measured explicit-jump PNG.

FS-020 acceptance проверяет constant/impulse/sinusoid bins, generated real round-trip, readonly
types/convention metadata, low/high/selected masks, asymmetric complex rejection, pre-allocation
resource failure, safe local-image integration, atomic component PNG и live/bidi-safe CLI.

FS-021 desktop component evidence asserts no trace paint/toggle, exact `0.01..1.00×` speed mapping
with `0.01×` steps and preserved application endpoint ledger. Remaining performance evidence records
default/stress K, trace length, DPI/window and hardware; asserts no continuous paused redraw,
before/after frame buckets and exact endpoint parity.
Desktop image regression uses a dark contour on a light PNG and goes through the actual picker/worker
path. Canvas zoom regressions cover its numerically bounded near-unrestricted `0.01..100.00×`
presentation scale, reset button and
persisted preference without changing timeline state.
Freehand component regressions assert the screen-to-Cartesian Y conversion used by the renderer;
viewport interaction regressions drive an actual `QWheelEvent` and left-button drag, require all zoom
inputs to preserve the scene-coordinate under the canvas center by proportional pan correction, and
require reset/newly accepted curve to restore `1.00×` and zero pan. A
freehand baseline regression verifies that the source-field and epicycle-field coordinate extents map
proportionally instead of fitting the curve's own bounds. `Original` control regressions require
disabled/unchecked empty state and exact checked-to-layer visibility synchronization for a ready frame.
The source center maps to `(0, 0)` and round-trips through its screen transform. Wheel zoom updates the
slider to the same scale. Rainbow regressions use several harmonics, require stable colors by selection
position as K grows, and require each vector/circle pair to share its color. Touch regressions exercise
the isolated viewport-gesture calculation for one-finger pan and bounded fixed-center pinch zoom,
reset and presentation-state isolation; the offscreen Qt runtime is not evidence that a physical touch
device delivered native `QTouchEvent` sequences. The user-confirmed manual Windows checklist supplies
the physical-touch, visible DPI and resize evidence separately. Cancel is disabled without a job then
enabled only for a running conversion.
Source-layout regression opens the normal `1200×760` desktop shell and requires the freehand field's
vertical center to match the epicycle canvas center.
The offscreen component suite drives actual `FreehandCanvas` mouse callbacks and the desktop file-picker
callback for a local PNG through their existing worker/application paths; test-local in-memory settings
keep this evidence from writing user preferences. It does not replace manual visible Windows/DPI evidence.
That manual evidence was confirmed separately by the user at the FS-021 terminal gate.
Component regressions also require that Cancel publishes the localized cancelled state and that the CLI
launch path preserves the size restored by `DesktopWindow`; a job that survives bounded termination
remains owned until it actually stops.

FS-022 tests require versioned/order-preserving Curve and selected-coefficient JSON/CSV, atomic
no-overwrite publication, readable reconstruction/spectrum PNG, and a real Pillow GIF reopened from
disk. GIF metadata endpoint history must equal the exported frame chain endpoints. Bounds, progress,
cooperative cancellation, temp cleanup and explicit MP4-unavailable behavior receive negative tests.
Desktop component evidence drives the EXPORT page/file-picker/overwrite decision through the actual
worker/export boundary; it does not substitute a codec or write into user preferences.

FS-023 tests compare optimized inverse reconstruction with the scalar reference evaluation, exercise
representative large N and stress K within existing caps, measure rather than disguise machine-specific
timings, and prove that Cancel never force-terminates an owned Qt worker. Positive Unicode/space paths
pass through real atomic export. Clean wheel installation/import/resource loading is source-package
evidence only and does not substitute an installer or visible GUI/DPI verification.

FS-024 unit tests require frequency-key lookup to return the exact aligned coefficient/vector
projection, preserve selection position and return explicit empty for unknown/stale `k`. Component
tests cover initial empty state, ordered list and keyboard navigation, canvas vector/circle click,
click-versus-drag-pan separation, K grow persistence/K shrink clearing and pseudo-locale expansion.
Before/after snapshots prove selection does not mutate Curve, coefficients, chain, endpoint, timeline,
speed or trace; animation advance updates the inspector's current local contribution. A live desktop
E2E drives actual freehand pointer callbacks through the worker-backed timeline before list/canvas
selection. Offscreen Qt execution is functional E2E evidence, not manual visible Windows DPI evidence.

FS-025 unit/property tests exercise entry/advance/restart/exit over a one-frequency explicit
selection and require display endpoint/reconstruction/Solo-trace parity with the canonical Fourier
coefficient. They also cover empty/unknown frequency rejection and transactional failure without
changing the baseline frame. Component tests drive keyboard inspector selection and the accessible
Solo/Exit Solo control, verify the explicit mode label, disabled harmonic/export controls, continuing
play/pause/time/speed behavior and exact baseline snapshot restoration. Actual Qt offscreen E2E may
prove the live user-to-canvas path, but remains distinct from visible Windows GUI/DPI evidence.

FS-026 unit tests cover bounded dwell transitions, no-skipped K, pause/resume/restart/completed,
invalid target/ordering/source and transactional projection. Property/integration tests require every
selection to equal the deterministic first-K prefix, endpoint/reconstruction/retained-energy/RMSE
parity and per-K singleton trace without baseline mutation. Component/actual-Qt offscreen E2E drive
ordering/target/dwell, context-sensitive Play/Pause/Restart, inspector refresh, explicit metrics and
Solo/harmonic/export gating. Offscreen remains functional evidence, not manual visible GUI/DPI or
screen-reader evidence.

FS-027 unit/property tests cover open/closed known polylines, deterministic anchors/ties, degenerate
and duplicate samples, source subsequence/order/topology, tolerance residual, immutable source and
typed invalid/budget/cancel failure. Integration compares original/simplified equal-N resampling and
same-K actual timelines against one baseline reference. Component/live CLI tests require localized
side-by-side artists/metrics, atomic no-overwrite output and unchanged legacy path without tolerance.
Performance evidence records representative completion and bounded worst-case abort; it does not
claim asymptotic improvement.

FS-028 unit/property tests cover turning-angle fixtures, exact N, deterministic weighted targets,
open endpoints, closed seam/start, duplicates, all-zero curvature provenance, invalid/zero-length
failure and immutable source. Integration compares uniform/adaptive equal-N/equal-K timelines;
component/live CLI verify atomic side-by-side PNG, metrics, option conflict and unchanged legacy path.

FS-031 adds touch/lifecycle unit/component tests, Python-reference coefficient/endpoint parity,
installed Android E2E and manifest/frame-time/memory/package-size evidence.

## Manual diagnostics

Visual stages сохраняют command, fixture/inputs, expected geometry/state и observed result. Manual
check дополняет, но не заменяет assertions. Screenshots/golden вводятся только после стабильной
rendering contract и отдельной acceptance.

## Coverage

FS-000 не задаёт искусственный percentage target. До hardening pure math/domain critical branches
должны иметь behavior/property coverage; Stage `FS-023` фиксирует measured baseline и разумный
regression threshold до заявления о target.
