# Архитектура Fourier Sketch

## Статус документа

Stages `FS-000`–`FS-010` создали immutable domain/numerical core, application timeline, bounded
freehand capture, cohesive control surface, resource locale boundary и diagnostic Matplotlib/CLI
adapter. Остальные product modules являются целевой архитектурой и появляются строго в
соответствующих stages.

FS-011 расширил Pillow-neutral immutable raster contract типизированным edge result. FS-012 добавил
typed external-contour extraction, отдельный project-owned routing policy и application composition
до принятого `EpicycleTimeline`. OpenCV не выбирает dominant contour и не задаёт его порядок:
selection, normalization и raster-to-domain transform принадлежат проекту.

FS-013 добавил reusable `ImageMvpController`: immutable snapshots имеют generation и явные
`initial|processing|ready|empty|error|cancelled` states. Долгий local decode/CV path выполняется в
одном bounded worker, а публикация результата проверяет generation/cancel token; partial или stale
result никогда не становится ready. `ImageMvpSurface` и headless CLI только dispatch-ят controller
commands и переиспользуют `build_dominant_contour_timeline`, `EpicycleTimeline` и `draw_frame`.

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

Planned Android `FS-031` follows the same direction: mobile touch/presentation adapter → portable
application/domain/math contract. Technology selection remains open until capability evidence;
mobile UI or bridge cannot become a second Fourier implementation.

`domain`/`math` не импортируют PySide6, matplotlib, Pillow, OpenCV или scikit-image. Renderer не
вычисляет coefficients. UI handlers не выполняют Fourier/CV logic.

## Текущее дерево и planned modules

```text
src/fourier_sketch/
├── __init__.py                 # существует: Stage FS-000 scaffold
├── domain/                     # существует: Stage FS-001 values и invariants
├── math/                       # существует: FS-002..FS-005 core + FS-007/FS-009 resampling
├── application/                # существует: timeline, freehand, image/edge/contour use cases
├── presentation/ + resources/ # существует: en fallback и algorithmic pseudo locale
├── render/                     # существует: Matplotlib frame/PNG/freehand/image-MVP adapters
├── cli/                        # diagnostic, freehand, image/CV, skeleton и skeleton_graph
├── imaging/                    # существует: raster, Pillow, edge и external-contour adapters
├── routing/                    # dominant, piecewise и explicit forced-route policies
└── ui/                         # существует: PySide6 desktop adapter FS-021
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
image → decode/transforms → explicit edge mode → dominant contour → closed Curve → same Fourier use case
      → generation-safe MVP snapshot → four-panel Matplotlib surface/headless PNG
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

FS-009 `ResamplingMethod` различает `uniform_index` и `arc_length`. Arc-length implementation
строит bounded cumulative segment array, включает seam только для closed Curve и fail-closed
отклоняет non-positive/non-finite total length. Method switch публикует result/timeline только
после полного успешного rebuild; при failure предыдущий method/result остаётся согласованным с UI.

FS-027 добавляет `math.curve_simplification` как bounded geometry transform перед resampling.
Application comparison сохраняет source/simplified curves, независимо resample-ит их к одному N и
создаёт два existing `EpicycleTimeline` с одинаковым K/speed. Core не импортирует OpenCV/UI/render;
contour DTO/default builder не меняются. Existing contour CLI включает comparison только через
explicit tolerance и передаёт typed result read-only renderer-у. Work-budget/cancel failure не
публикует partial result и не включает silent original fallback. Curvature/adaptive allocation не
принадлежат этой boundary.

FS-028 добавляет отдельный pure `math.adaptive_sampling` рядом с FS-009 resampling, не изменяя
существующие `resample_curve_by_arc_length` или Fourier APIs. Application comparison строит uniform
и adaptive curves с одинаковыми N/K/speed; contour CLI/render подключают это только opt-in и
запрещают смешанный simplification+adaptive invocation.

FS-010 `imaging.model` хранит one-byte `RasterImage` как grayscale или binary, decode provenance,
transform sequence и stable privacy-safe failure code без Pillow/NumPy values в public result.
`pillow_backend` сначала проверяет file size, читает не более 25 MiB + 1, дважды открывает один
immutable byte payload: первый pass ограничивает format/dimensions и выполняет `verify()`, второй
проверяет single-frame, читает EXIF, полностью декодирует, применяет orientation и grayscale.
Application затем независимо применяет fixed median 3x3, autocontrast и inclusive threshold/
invert. Diagnostic export выбирает ровно один named intermediate, кодирует PNG до публикации и
использует temporary sibling + exclusive hard-link publication либо explicit atomic replace.

FS-011 `EdgeDetectionResult` связывает same-sized binary edge raster с explicit algorithm,
backend version, typed parameters и source stage/dimensions. `threshold_boundary` считает
foreground-side boundary по 4/8-neighborhood с outside-as-background semantics. Canny adapter
лениво загружает `cv2`, валидирует low/high/aperture/L2 и backend output, но не пропускает OpenCV
objects через application API. Application выбирает binary source только для boundary и grayscale
только для Canny; unavailable/failing Canny не запускает другой algorithm.

FS-012 разделяет library extraction и продуктовую семантику. `imaging.opencv_contours` вызывает
`findContours` с `RETR_EXTERNAL`/`CHAIN_APPROX_NONE`, проверяет native output, source-foreground
membership, simple-cycle uniqueness, adjacency и budgets, очищает adjacent/terminal duplicates и
отбрасывает zero-area/open-backtracking candidates. `routing.dominant_contour`
выбирает ровно один candidate по ключу `-area2, -bbox_area, -point_count, canonical_signature`,
независимому от backend order. Он разворачивает raster sequence в counter-clockwise domain order,
вращает closed sequence к topmost/leftmost pixel и применяет transform:

```text
scale = 2 / max(width - 1, height - 1)
x = (column - (width - 1)/2) * scale
y = ((height - 1)/2 - row) * scale
```

`application.dominant_contour` сохраняет preprocessing/edge/extraction provenance, применяет только
существующий `resample_curve_by_arc_length`, `build_freehand_timeline` и renderer. Empty/degenerate
extraction возвращает `ImageNoContourResult`: Curve, Fourier state и PNG при этом не создаются.

## Data flow и provenance

Каждый significant result хранит достаточный provenance: source kind, parameters, sample count,
Fourier convention, selected frequencies и algorithm/backend. Пользовательский image/sample
payload не копируется в logs. Intermediate image results доступны только по явному diagnostic/
export request.

FS-010 provenance содержит actual `PNG`/`JPEG`, encoded byte count, source/oriented dimensions,
валидированный EXIF orientation и ordered transform names. Source path, EXIF payload и pixels в
provenance/CLI failure не входят.

FS-011 provenance содержит точные `threshold_boundary|canny`, backend (`fourier-sketch/numpy` или
`opencv/<version>` с bounded ASCII identifier), algorithm-specific parameters, source
stage/dimensions и edge pixel count. Binary edge payload доступен как diagnostic artifact, но не
называется contour/curve.

FS-012 provenance добавляет extraction backend, exact external/none modes, candidate count,
selected area/bounds/point count, selection policy, source dimensions, coordinate transform, scale,
orientation и start-point policy. Source path, raster payload и raw native error в него не входят.

FS-014 provenance содержит explicit `lee`, bounded `scikit-image/<version>`, source dimensions и
source/skeleton foreground counts. Adapter принимает только binary raster, сохраняет dimensions,
не мутирует source и fail closed отклоняет wrong dtype/shape, output foreground вне source либо
solid `2×2` block, несовместимый с one-pixel skeleton contract.

FS-002 сохраняет complete coefficients в FFT storage order с canonical signed labels. Reference
DFT и NumPy FFT выбираются явными public functions; reference path не является автоматическим
fallback. Public boundary возвращает built-in complex/tuple/domain values, а не NumPy arrays.
FS-003 добавляет только immutable views над complete spectrum; partial coefficient set появляется
отдельным `CoefficientSelection` contract в FS-004 и не маскируется под `FourierSpectrum`.
Selection использует value provenance: sample count, signed frequency и exact coefficient value;
это позволяет воспроизводимо сравнивать immutable эквивалентные данные без object identity.

## Concurrency и lifecycle

FS-013 interactive Matplotlib surface уже выполняет image/CV operation в одном worker; immutable
generation snapshots и cooperative cancellation предотвращают stale publication. Headless CLI
остаётся синхронным. Полный progress contract, guaranteed join и Qt worker lifecycle относятся к
PySide6 stages; window shutdown отменяет current generation и не помечает partial result complete.

FS-014 использует тот же generation-safe application pattern в `SkeletonController`. Cooperative
token проверяется до dependency import, до и после native Lee call; cancelled/stale operation не
публикует `LocalSkeletonResult`. CLI остаётся синхронным и публикует ровно один atomic artifact.

## Skeletonization boundary (FS-014)

`imaging.skeleton_model` владеет immutable result/error/algorithm contracts и
same-dimension/subset/count invariants. `imaging.skimage_skeleton` lazy-imports pinned
`scikit-image 0.26.x`, вызывает только `skeletonize(binary_bool, method="lee")` и ограничивает
foreground 4 000 000 pixels.

`application.skeletonization` связывает существующий FS-010 preprocessing с adapter и PNG export.
`render.matplotlib_skeleton` строит actual source/result preview, а `cli.skeleton` явно выбирает
`skeleton` либо `preview`.

## Skeleton graph boundary (FS-015)

`imaging.skeleton_graph_model` владеет immutable undirected pseudomultigraph schema, typed failure,
component/node/edge contracts и exact foreground partition validation. `imaging.skeleton_graph`
применяет `corner-suppressed-8-v1`, вычисляет raw pixel degree, объединяет смежные junction pixels,
сжимает maximal degree-2 chains и представляет pure degree-2 component через deterministic
`LOOP_ANCHOR` + self-loop. Components, nodes и undirected edges canonical sorted; их IDs и JSON
order являются storage semantics, но не traversal.

`application.skeleton_graph` связывает real FS-010/FS-014 path с graph builder и atomic canonical
JSON. `render.matplotlib_skeleton_graph` рисует component-colored adjacency overlay, а отдельный
`cli.skeleton_graph` выбирает ровно один `json|overlay` artifact. Raster `PixelPoint`, compressed
node incidence и будущий route остаются разными types/semantics.

## Piecewise component boundary (FS-016)

`routing.piecewise_components` выполняет all-or-nothing conversion: simple path, pure self-loop и
isolated component дают ровно один segment каждый; branched/complex component не превращается в
скрытый traversal. `RasterCoordinateTransform` является общим владельцем
`pixel-center-centered-aspect-v1` для dominant contour и piecewise pipelines. Application хранит
source graph provenance, renderer рисует segments раздельно, а boundary metadata существует между
соседними segments. Forced traversal/edge duplication/bridge принадлежат FS-017.

## Forced route boundary (FS-017)

Shared `imaging.skeleton_adjacency` гарантирует одинаковый `corner-suppressed-8-v1` raw graph для
FS-015 и routing. `routing.forced_route` применяет exact Hierholzer для 0/2 odd vertices и linear
spanning-tree T-join для остальных, затем объединяет components explicit cyclic bridges. Каждый
step aligned с closed `Curve` и имеет original/duplicated/bridge provenance; metrics пересчитывают
added cost. Application resamples именно этот route в существующий Fourier timeline. Policy opt-in,
не меняет FS-016 PiecewiseCurve и не обещает optimal Postman/TSP.

FS-029 расширяет только internal odd-vertex duplication policy: default FS-017 tree T-join остаётся
неизменным, improved policy использует bounded weighted shortest-path pairing и тот же Hierholzer,
component ordering, explicit bridges и Fourier consumer. Application comparison владеет двумя
route results и routing-time measurements; piecewise pipeline не импортирует optimization layer.

## Discontinuous Fourier boundary (FS-018)

`math.piecewise_sampling` владеет bounded exact-budget allocation и immutable boundary ledger.
`application.discontinuous_fourier` единожды превращает sampled `PiecewiseCurve` в concatenated
complex periodic sequence и переиспользует существующие FFT/epicycle APIs. Render mode не входит в
математическое состояние: strict mode рисует один periodic path, pen-up mode — independent artists.
Отдельный comparison adapter resamples explicit closed forced route к тому же N, не конвертируя
PiecewiseCurve в route и не смешивая provenance двух policies.

## Spectrum analysis boundary (FS-019)

FS-019 keeps `SpectrumAnalysis` as immutable numeric source of truth. Application builds a
same-parameter discontinuous/forced comparison; Matplotlib and CLI only render/export that result.
Predictable reconstruction budget exhaustion returns explicit partial analysis with retained points.

## Separate FFT2 boundary (FS-020)

`math.fft2_image` owns dedicated `FFT2Raster`, `FFT2Spectrum` and composite diagnostic result;
1D `FourierSpectrum`/epicycle modules не импортируются. Application rejects raster budget before
float conversion, renderer consumes readonly shifted views, CLI enters through FS-010 safe decode.

## Export boundary (FS-022)

`application.exporting` owns schema-versioned Curve/current-selection JSON/CSV, bounded animation
plans and atomic byte publication. Animation frames call the accepted `build_epicycle_chain` for the
same selection and accumulate only actual endpoints; they do not mutate the interactive timeline.
`render.exporting` owns Matplotlib spectrum PNG and fixed-size Pillow GIF encoding. Desktop widgets
only select parameters/destination and dispatch the existing worker. MP4 has an explicit unavailable
capability result; no subprocess, alternate codec or silent format substitution exists.

## Harmonic inspector boundary (FS-024)

`presentation.harmonic_inspector` создаёт immutable read-only projection одной гармоники из
согласованных по selection order `EpicycleFrame.selection` и `EpicycleFrame.chain`. Signed frequency
`k` является stable presentation identity; projection не владеет coefficient, chain или timeline и
не выполняет повторный Fourier calculation. `DesktopWindow` владеет выбранным `k`, списком и
локализованным форматированием, а `EpicycleCanvas` выполняет только device-space hit-test уже
подготовленных vector/circle geometry. Click selection отделён от drag-pan movement threshold.
Новый timeline и отсутствующий в текущем frame `k` очищают selection; обычный animation frame только
обновляет projection. Solo/visibility filtering и build-up ordering остаются FS-025/FS-026.

## Frequency Solo boundary (FS-025)

`application.frequency_solo` владеет bounded analysis session поверх immutable baseline
`EpicycleFrame`. Session находит coefficient по stable signed frequency, создаёт explicit
`CoefficientSelection` из одного элемента и через канонические `reconstruct_samples` и
`build_epicycle_chain` формирует display frame с фактической isolated geometry/endpoint. Отдельный
Solo trace обновляется только при новом baseline time и всегда заканчивается display endpoint.

`EpicycleTimeline` и его complete `FourierSpectrum`, ordered selection, time/state/speed/visibility и
trace ledger не мутируются Solo session. Desktop продолжает отправлять play/pause/restart/advance в
baseline timeline и только затем применяет analysis projection к canvas. Inspector list/details
читают baseline frame, mode label — session state, а export во время Solo блокируется; поэтому
существующий FS-022 exporter не получает скрытую active-set подмену. Новый timeline завершает
session; явный owner token не позволяет продолжить session на другом timeline даже при совпадающих
Curve/coefficient values. Multi-select и ordered build-up принадлежат отдельному FS-026 contract.

## Harmonic Build-Up boundary (FS-026)

`application.harmonic_build_up` владеет bounded state machine и analysis projection над immutable
baseline `EpicycleFrame` и complete immutable `FourierSpectrum`. Session переиспользует canonical
`select_first`, `reconstruct_samples`, `build_epicycle_chain`, `retained_energy_ratio` и
`reconstruction_metrics`; `EpicycleTimeline` предоставляет только read-only spectrum provenance.
Required source-owner identity запрещает продолжить mode на другом timeline.

Desktop reuse existing QTimer: при активном mode tick продвигает только один bounded dwell step и
не меняет baseline timeline. Play/Pause/Restart context-sensitive к Build-Up; Exit раскрывает exact
latest baseline object и возобновляет обычные timeline ticks без catch-up. K transition сбрасывает
только mode-local trace. Solo, manual K, configuration и export gated как взаимоисключающие policies.
No second timer, coefficient mutation, smooth interpolation or FS-030 lesson orchestration.

## Educational Mode boundary (FS-030)

`application.educational_mode` владеет canonical circle fixture и bounded guided-step session над
actual `EpicycleFrame`; snapshot содержит выровненные sample/coefficient/vector/chain/endpoint/trace
references, source identity и lesson id, но не renderer strings. `presentation.educational_mode`
форматирует canonical equation/resources. Desktop adapter синхронизирует locked inspector/canvas
highlight и scoped keyboard, используя existing timeline/QTimer; отдельного lesson timer,
coefficient math или trace ledger нет. Solo/Build-Up/export locks остаются UI boundary, а
mobile/basis layers не импортируют lesson.

## Basis selection and Haar boundary (FS-032)

`domain.basis` owns only immutable basis/term/decomposition/selection values. `math.haar` owns the
project Haar analysis/synthesis and validates the power-of-two/budget contract. Application
`basis_decomposition` explicitly dispatches `FOURIER_EPICYCLE` to the unchanged
`EpicycleTimeline` or adapts an immutable source Curve to a recorded Haar analysis grid and
`HaarTimeline`; it never catches a Haar failure by switching to Fourier.

`HaarFrame` is intentionally not an `EpicycleFrame`: it contains source/analysis/reconstruction and
active term-contribution curves but no `FourierSpectrum`, vector chain, endpoint or trace ledger.
Desktop owns the explicit basis selector and sends either frame type to mutually exclusive canvas
paths. Existing Play/Pause/Restart, speed and one bounded count slider are presentation controls;
Fourier inspector/Solo/Build-Up/Educational/export surfaces are disabled in Haar mode rather than
receiving fabricated frequency state. Android remains outside this adapter.

## Indexed basis and harmonic authoring boundary (FS-033)

`domain.indexed_basis` хранит immutable indexed terms/decomposition/selection только для DCT-II и
Walsh-Hadamard; exact ownership и canonical prefix проверяются отдельно от Haar types.
`math.indexed_basis` владеет ортонормированными analysis/synthesis/contribution algorithms и
resource bounds. `application.basis_decomposition` dispatches их в отдельный
`IndexedBasisTimeline`/`IndexedBasisFrame`; Fourier/Haar frames не расширяются union-полями.

`application.harmonic_playground` валидирует ordered user-authored polar terms и строит complete
zero-filled canonical `FourierSpectrum` плюс explicit-frequency `EpicycleTimeline`. Generated Curve
является точной sample-grid суммой authored terms, а не placeholder. Desktop владеет reversible mode
lock/previous-timeline reference; math, source capture и canonical Educational session не знают о UI
режиме. Один existing QTimer обслуживает normal, indexed-basis и playground animation.

## i18n/l10n boundary

Первая user-facing surface использует resource keys и locale resolver. Production locale и
fallback — `en`; pseudo-locale используется в component checks. Domain/application errors
возвращают stable codes + parameters, а presentation формирует локализованный текст.

## Trust boundaries

Недоверенные границы: local image bytes/metadata, mouse samples, user parameters, export path и
optional codec/backend output. Limits и failure semantics определены в system SPEC и
`docs/SECURITY.md`. Сетевой/service backend отсутствует (`BDX-L0`); OpenCV является локальным
library adapter с валидируемым output contract.

## Packaging и deployment

FS-023 подтвердил source package через Python 3.12+ и frozen `uv`: wheel строится Hatchling,
устанавливается с locked dependencies в isolated environment, импортирует packaged resources и
запускает desktop CLI help вне checkout. Bundled desktop installer не выбран: project license,
third-party notices и PySide6 LGPL redistribution obligations требуют отдельного решения до public
redistribution. Repository не зависит от machine-local prompt/Downloads path.

## Ключевые ограничения

- NumPy, CV, renderer и GUI dependencies добавляются just-in-time, не на bootstrap.
- Performance acceleration не является источником истины: reference implementation и parity
  tests появляются раньше optimization.
- Desktop renderer optimization follows ADR-022: measured QPainter work first, optional QML scene
  graph only after parity; Android framework selection is isolated to FS-031.
- Future stage не может впервые сделать предыдущий runnable slice проверяемым.
