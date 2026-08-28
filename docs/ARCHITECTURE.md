# Архитектура Fourier Sketch

## Статус документа

Stages `FS-000`–`FS-007` создали immutable domain/numerical core, application timeline, bounded
freehand capture, resource locale boundary и diagnostic Matplotlib/CLI adapter. Текущий FS-008
расширяет тот же adapter cohesive control surface. Остальные product modules являются целевой
архитектурой и появляются строго в соответствующих stages.

## Архитектурные цели

- один численный контракт для 1D complex Fourier;
- math/domain независимо от renderer, UI и computer-vision backends;
- один `EpicycleChainState` как источник circle/vector/endpoint rendering;
- отдельные policies для mathematical discontinuity и pen-up drawing;
- диагностируемые небольшие transforms вместо opaque image mega-pipeline;
- application use cases, переиспользуемые diagnostic renderer, GUI и export.

## Слои и направление зависимостей

```text
PySide6 UI / matplotlib renderer / CLI or examples / exporters
                         ↓
                 application use cases
                         ↓
       domain models + mathematical contracts
                         ↑
 imaging / routing / codec adapters (через явные inputs/outputs)
```

Allowed dependency direction:

```text
ui, render, cli, export → application → domain, math
imaging, routing       → domain contracts; application composes them
domain, math           → Python stdlib + NumPy only when introduced
```

`domain`/`math` не импортируют PySide6, matplotlib, Pillow, OpenCV или scikit-image. Renderer не
вычисляет coefficients. UI handlers не выполняют Fourier/CV logic.

## Текущее дерево и planned modules

```text
src/fourier_sketch/
├── __init__.py                 # существует: Stage FS-000 scaffold
├── domain/                     # существует: Stage FS-001 values и invariants
├── math/                       # существует: FS-002..FS-005 core + FS-007 index resampling
├── application/                # существует: FS-006 timeline + FS-007 freehand use case
├── presentation/ + resources/ # существует: en fallback и algorithmic pseudo locale
├── render/                     # существует: Matplotlib frame/PNG/freehand adapters
├── cli/                        # существует: diagnostic и freehand live entry points
├── imaging/                    # planned FS-010..FS-014, FS-020
├── routing/                    # planned FS-012, FS-015..FS-017
└── ui/                         # planned FS-021
```

Empty directories и placeholder interfaces заранее не создаются.

## Основные контракты

### Domain

- `Point2D`: finite Cartesian coordinate.
- `Curve`: ordered non-empty points + explicit open/closed semantics.
- `PiecewiseCurve`: non-empty independent segments + discontinuity metadata.
- `FourierCoefficient` / `FourierSpectrum`: convention-bearing numerical values.
- `EpicycleVector` / `EpicycleChainState`: готовая head-to-tail geometry at time `t`.

Transport/export DTO не должны становиться domain types. Raster data и 2D FFT data не должны
переиспользовать `Curve` spectrum types.

### Application

Use cases принимают typed inputs/config и возвращают typed results/diagnostics. Реальный первый
flow и planned continuations:

```text
canonical Curve → FFT → `EpicycleTimeline` → immutable `EpicycleFrame` → Matplotlib/PNG
Matplotlib pointer events → bounded capture → cleanup/index resample → Curve → тот же timeline
image → decode/transforms → contour/route → curve → same Fourier use case
chain timeline → future animation exporter
raster → separate FFT2 use case
```

### Rendering

`EpicycleChainState` содержит всё нужное:

```text
circle_center = vector.start
circle_radius = vector.amplitude
arrow = vector.start → vector.end
drawing_point = chain.endpoint
```

Visibility flags живут в view state и не меняют chain state.

FS-005 `build_epicycle_chain` является единственной factory геометрии: она сохраняет selection
order, вычисляет rotating local value и последовательно переиспользует предыдущий `end` как
следующий `start`. Renderer FS-006 получает готовый state и не повторяет reconstruction.

FS-006 `EpicycleTimeline` — единственная mutable boundary текущего slice. Каждый emitted
`EpicycleFrame` immutable; trace append получает только `chain.endpoint`. Matplotlib adapter рисует
circle/vector/endpoint/overlays из frame, не импортируется domain/math слоями и не вычисляет
Fourier state. CLI создаёт canonical Curve и проходит тот же application boundary.

FS-007 добавляет `FreehandCapture` как отдельную bounded application boundary: она принимает
только finite `Point2D`, игнорирует соседние дубликаты, fail-closed завершает capture после 10 000
points и создаёт `FreehandCurveResult` с source/sample provenance. `FreehandSurface` соединяет
реальные Matplotlib press/motion/release/key callbacks с capture и не вычисляет Fourier logic в
event handlers: завершённый stroke проходит через `build_freehand_timeline` и существующий
`draw_frame`. Drawing axes имеют стабильную coordinate system на время capture; events вне них
игнорируются.

FS-008 не добавляет второго application path. Matplotlib `Button`/`Slider` вызывают public
`FreehandSurface` commands, которые делегируют play/pause/restart/speed/harmonic операции ровно
тому `EpicycleTimeline`, который создан после capture. Harmonic change использует transactional
timeline validation и сбрасывает trace к endpoint нового chain state; release coordinate внутри
drawing axes добавляется даже без предшествующего motion event.

## Data flow и provenance

Каждый significant result хранит достаточный provenance: source kind, parameters, sample count,
Fourier convention, selected frequencies и algorithm/backend. Пользовательский image/sample
payload не копируется в logs. Intermediate image results доступны только по явному diagnostic/
export request.

FS-002 сохраняет complete coefficients в FFT storage order с canonical signed labels. Reference
DFT и NumPy FFT выбираются явными public functions; reference path не является автоматическим
fallback. Public boundary возвращает built-in complex/tuple/domain values, а не NumPy arrays.
FS-003 добавляет только immutable views над complete spectrum; partial coefficient set появляется
отдельным `CoefficientSelection` contract в FS-004 и не маскируется под `FourierSpectrum`.
Selection использует value provenance: sample count, signed frequency и exact coefficient value;
это позволяет воспроизводимо сравнивать immutable эквивалентные данные без object identity.

## Concurrency и lifecycle

До PySide6 stages операции могут быть синхронными diagnostic commands. В GUI CPU/I/O operations
выполняются worker-ами с progress/cancellation; view получает immutable snapshots/signals. Window
shutdown отменяет work, дожидается bounded cleanup и не оставляет export ошибочно complete.

## i18n/l10n boundary

Первая user-facing surface использует resource keys и locale resolver. Production locale и
fallback — `en`; pseudo-locale используется в component checks. Domain/application errors
возвращают stable codes + parameters, а presentation формирует локализованный текст.

## Trust boundaries

Недоверенные границы: local image bytes/metadata, mouse samples, user parameters, export path и
optional codec/backend output. Limits и failure semantics определены в system SPEC и
`docs/SECURITY.md`. Сетевой/backend boundary отсутствует (`BDX-L0`).

## Packaging и deployment

На FS-001 поддерживается source package через Python 3.12+ и `uv`. Desktop packaging target и
installer не выбраны; решение откладывается до hardening после platform evidence. Repository не
зависит от machine-local prompt/Downloads path.

## Ключевые ограничения

- NumPy, CV, renderer и GUI dependencies добавляются just-in-time, не на bootstrap.
- Performance acceleration не является источником истины: reference implementation и parity
  tests появляются раньше optimization.
- Future stage не может впервые сделать предыдущий runnable slice проверяемым.
