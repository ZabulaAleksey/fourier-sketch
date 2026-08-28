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
```

После появления packaging/GUI/export project manifest и CI расширят command surface; команды не
считаются каноническими до фиксации в `pyproject.toml`, README и этом документе.

## Уровни

### Smoke

Stage `FS-000`: clean environment, package import/version, overlay structure.

### Unit

Value invariants, conversions, reference formulas, ordering, metrics, validators, individual image
transforms, graph/routing primitives и export serializers.

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
`image → contour → Fourier` E2E остаётся `BLOCKED_BY_BACKEND` до FS-013.

### E2E

Критические live paths:

1. canonical fixture → Fourier → timeline/endpoints → Agg PNG (`FS-006`, реализован);
2. freehand input → Curve → Fourier → chain → endpoint trace (`FS-007`, input slice реализован;
   `FS-008` подтверждает cohesive controls и exact endpoint-history ledger);
3. image file → decode/contour → same Fourier/chain → trace (`FS-013`);
4. desktop interaction → export → readable artifact with matching endpoint history (`FS-022`).

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

## Manual diagnostics

Visual stages сохраняют command, fixture/inputs, expected geometry/state и observed result. Manual
check дополняет, но не заменяет assertions. Screenshots/golden вводятся только после стабильной
rendering contract и отдельной acceptance.

## Coverage

FS-000 не задаёт искусственный percentage target. До hardening pure math/domain critical branches
должны иметь behavior/property coverage; Stage `FS-023` фиксирует measured baseline и разумный
regression threshold до заявления о target.
