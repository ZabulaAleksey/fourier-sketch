# Fourier Sketch

Fourier Sketch — поэтапно создаваемое desktop-приложение и математическое ядро для представления
плоской кривой комплексным сигналом `z(t) = x(t) + i y(t)`, анализа Fourier spectrum и анимации
цепочки вращающихся векторов. Конец последнего вектора является единственной drawing point для
анимационного trace.

## Текущее состояние

Реализованы каркас `FS-000`, domain model `FS-001`, transform slice `FS-002`, spectrum analysis
`FS-003`, partial reconstruction/metrics `FS-004`, epicycle mathematics `FS-005`, diagnostic
renderer `FS-006`, bounded freehand input `FS-007`, cohesive freehand-to-trace MVP `FS-008` и
arc-length parameterization `FS-009`.
Публичный пакет
`fourier_sketch.domain` предоставляет immutable `Point2D`, `Curve`, `PiecewiseCurve`,
Fourier coefficient/spectrum values, epicycle geometry и typed validation errors. Публичный
`fourier_sketch.math` выполняет complex conversion, canonical signed-frequency mapping, bounded
reference DFT, explicit NumPy FFT, IDFT, total spectrum energy и deterministic complete-spectrum
views: signed, absolute-frequency, amplitude, interleaved и explicit. Отдельный immutable
`CoefficientSelection` поддерживает first-K и explicit subset, continuous/sample-grid
reconstruction, retained energy и typed error metrics. `build_epicycle_chain` превращает selection
в renderer-ready head-to-tail state, чей endpoint равен reconstruction с учётом origin.
`fourier_sketch.application` управляет timeline/trace и bounded pointer capture. Matplotlib adapter
принимает реальные pointer events, строит `Curve` через uniform-by-index resampling и передаёт её в
тот же Fourier/timeline/renderer path.

Этап `FS-009` завершён: selectable arc-length resampling и измеримое сравнение с текущим
uniform-by-index baseline доступны в одном MVP. Этап `FS-010` завершил безопасный локальный
PNG/JPEG input, grayscale и threshold intermediate. Stage `FS-011` завершён и добавил два явно
разных edge mode: project-owned binary boundary и OpenCV Canny. `FS-012` завершает следующий
самостоятельный slice: детерминированно выбирает один внешний dominant contour, нормализует его в
closed `Curve`, применяет arc-length resampling и передаёт в существующий Fourier/timeline/renderer.
`FS-013` завершил cohesive image-to-Fourier MVP, `FS-014` добавил отдельный диагностический
binary-to-skeleton path через explicit scikit-image Lee backend, а `FS-015` преобразует этот
skeleton в детерминированный graph topology без преждевременного routing.
Обязательный hardening `FS-023` реализован и локально проверен: inverse reconstruction использует
parity-tested bounded NumPy IFFT, Qt cancellation не вызывает forced thread termination, Unicode/
space Windows exports проходят actual codecs, а source wheel устанавливается в isolated environment.
`FS-024` добавляет read-only Harmonic Inspector: signed frequency выбирается кликом по видимому
vector/circle либо keyboard-навигацией списка, а панель показывает selection position, amplitude,
phase, angular velocity и current local contribution из того же immutable frame. Выбор не меняет
Fourier coefficients, chain, endpoint, timeline, trace или animation state.
`FS-025` добавляет явный single-frequency Solo: выбранный signed `k` становится фактическим
одночастотным analysis active set для canvas, reconstruction и отдельного Solo trace, а baseline
timeline/selection/K остаётся неизменным и точно раскрывается при выходе. Во время Solo harmonic
count и export блокируются. `FS-026` добавляет отдельный Harmonic Build-Up: пользователь выбирает
deterministic ordering, target `N` и bounded dwell, после чего canvas/inspector показывают actual
first-K sequence `1..N` с retained energy/RMSE. Play/Pause/Restart управляют только этой sequence,
а baseline timeline не меняется и точно раскрывается при Exit; Solo/export/manual K временно gated.
`FS-027` добавляет opt-in curve simplification diagnostic: bounded project-owned Douglas–Peucker
уменьшает ordered contour до arc-length resampling, сохраняет original/retained-index provenance и
сравнивает original/simplified equal-N/equal-K Fourier paths без universal quality claim.
`FS-028` добавляет отдельный opt-in adaptive sampling diagnostic: discrete turning-angle density
перераспределяет exact N samples, а uniform/adaptive equal-K paths сравниваются без изменения
canonical Fourier math и без утверждения универсального преимущества.
`FS-029` добавляет selectable bounded single-stroke heuristic и measured comparison с прежним
baseline без silent fallback. `FS-030` добавляет один actual-state Educational Mode: кнопка
`Load circle lesson` создаёт canonical 32-sample circle через обычный Fourier timeline, после чего
шаги `samples → coefficient → circle/vector → chain → endpoint → trace` доступны кнопками и
`Alt+Left`/`Alt+Right`/`Alt+Home`. Lesson начинает paused; Play/Pause анимируют и фиксируют те же
actual frame values. Solo, Build-Up, K и export временно locked, а zoom/pan/visibility остаются
presentation controls.
`FS-032` добавляет explicit basis selector для нового freehand stroke: `Fourier epicycles` остаётся
default и использует прежний endpoint/trace path, а `Haar wavelet` строит project-owned
orthonormal 128-sample reconstruction с actual root/coarse-to-fine terms. В Haar view нет
fabricated circles/frequencies/endpoint trace; Play/Pause/Restart, speed, Terms, zoom/pan и
Original/Reconstruction работают отдельно, а Fourier-only inspector/Solo/Build-Up/Educational/
export и image input явно unavailable. Clear удаляет displayed result и снова открывает selector.
`FS-033` расширяет selector двумя честными indexed-базисами: orthonormal complex `DCT-II` и
natural-order `Walsh-Hadamard`. Они собирают reconstruction по индексам `0..N-1`, показывают вклад
последнего выбранного term и не изображают несуществующие circles/vectors/endpoint trace. Отдельная
страница `HARMONIC PLAYGROUND` позволяет вручную собрать до 16 Fourier-компонент по signed `k`,
amplitude и phase, увидеть реальную цепочку эпициклов и анимировать её. Режим начинается с круга
`k=1, A=1, phi=0`; выход восстанавливает предыдущий результат и его состояние.

## Целевой pipeline

```text
Mouse drawing / image
        ↓
Curve / PiecewiseCurve
        ↓
parameterization and resampling
        ↓
z(t) = x(t) + i y(t)
        ↓
DFT / FFT → spectrum → selected coefficients
        ↓
head-to-tail epicycle chain
        ↓
last endpoint → persistent reconstructed trace
```

Image processing, discontinuous curves and 2D image FFT входят в поздние независимые stages.

## Требования

- Python 3.12+;
- `uv` как единственный dependency manager.

## Подготовка окружения

```powershell
uv sync --all-groups --frozen
```

`uv` использует общий machine cache, но создаёт изолированную project-local `.venv`.

## Diagnostic renderer

Interactive Matplotlib window с Play/Pause/Restart, speed, harmonic count и visibility controls:

```powershell
uv run python -m fourier_sketch.cli.diagnostic
```

Живой headless путь `fixture → FFT → selection → timeline → renderer → PNG`:

```powershell
uv run python -m fourier_sketch.cli.diagnostic --headless --output epicycles.png --frames 120 --harmonics 15
```

Production/fallback locale — `en`; `--locale pseudo` включает диагностическую expanded locale.
Существующий output не перезаписывается и возвращает controlled failure.

## Freehand input

Интерактивное окно с реальным Matplotlib pointer capture, очисткой consecutive duplicates,
явной open/closed семантикой и uniform-by-index resampling:

```powershell
uv run python -m fourier_sketch.cli.freehand
```

Доступны `--samples`, `--harmonics`, `--speed`, `--closed`, `--resampling` и `--locale`. Левая
кнопка рисует stroke, `R` сбрасывает его, `Esc` отменяет capture. Input ограничен 10 000 pointer
samples, а результат — 4096 samples; превышение budget завершается явным controlled state.

На той же surface доступны Play, Pause, Restart, speed и harmonic sliders. Они управляют timeline,
созданным из текущего stroke; Restart сохраняет source curve и сбрасывает trace к одному
zero-time endpoint.

`--resampling uniform_index` сохраняет исходный deterministic baseline; `--resampling arc_length`
равномерно размещает samples по cumulative polyline length. Radio selector на той же surface
перестраивает текущий stroke без второго Fourier path и показывает measured mean spacing/CV.
Zero-total-length arc input завершается typed error и не переключается молча на index method.

## Image preprocessing

FS-010 diagnostic принимает локальный PNG/JPEG, проверяет 25 MiB encoded и 40 MP decoded budgets,
реальный decoder format и single-frame policy, затем применяет EXIF orientation и строит отдельные
grayscale/binary intermediates:

```powershell
uv run python -m fourier_sketch.cli.image input.jpg --output threshold.png --threshold 128 --denoise median_3 --autocontrast
```

`--stage grayscale|binary` выбирает экспортируемый intermediate, `--invert` инвертирует только
threshold result. Существующий destination сохраняется без `--overwrite`. Corrupt, truncated,
oversized, multiframe и content с неподдерживаемым фактическим format завершаются controlled exit
`2`; full path и image payload не выводятся.

## Edge detection

FS-011 diagnostic продолжает тот же безопасный image path и экспортирует выбранный binary edge
intermediate:

```powershell
uv run python -m fourier_sketch.cli.edges input.jpg --output edges.png --algorithm threshold_boundary --connectivity 8
uv run python -m fourier_sketch.cli.edges input.jpg --output canny.png --algorithm canny --canny-low 100 --canny-high 200 --canny-aperture 3 --canny-gradient l2
```

`threshold_boundary` использует thresholded binary mask и выбранную 4/8-connectivity; `canny`
использует grayscale и headless OpenCV. Summary показывает output basename, algorithm/backend,
dimensions и число edge pixels. Режимы не считаются эквивалентными и не подменяют друг друга:
недоступный Canny завершается controlled exit `2`. Empty edge map остаётся валидным diagnostic
result и не объявляется contour/curve.

## Dominant contour to endpoint trace

FS-012 использует OpenCV `RETR_EXTERNAL` + `CHAIN_APPROX_NONE` только для bounded extraction.
Порядок OpenCV не является семантикой: project-owned policy выбирает максимальную exact shoelace
area, затем bounding-box area, point count и canonical signature. Выбранная последовательность
нормализуется counter-clockwise, начинается с topmost/leftmost raster pixel и преобразуется из
pixel centers в центрированные aspect-preserving domain coordinates.

Живой диагностический путь до реального endpoint trace:

```powershell
uv run python -m fourier_sketch.cli.contours input.png --output contour-trace.png --algorithm threshold_boundary --samples 256 --harmonics 25 --frames 60
uv run python -m fourier_sketch.cli.contours input.jpg --output canny-trace.png --algorithm canny --canny-low 50 --canny-high 150
uv run python -m fourier_sketch.cli.contours input.png --output simplification.png --simplify-tolerance 0.02 --samples 256 --harmonics 25
uv run python -m fourier_sketch.cli.contours input.png --output adaptive.png --adaptive-curvature-weight 20 --samples 256 --harmonics 25
```

Summary показывает только output basename, выбранный algorithm, bounded backend identifier,
aggregate candidate/point/sample/trace counts. Пустая edge map или только degenerate fragments
возвращают явный успешный no-contour state без Curve, timeline и PNG. Backend failure и resource
limit дают controlled exit `2`; другой contour algorithm не подставляется. Stage выбирает ровно
один внешний contour: holes, disconnected components, skeleton и forced routing остаются deferred.

При `--simplify-tolerance` тот же normalized contour сначала проходит bounded iterative
Douglas–Peucker, затем original и simplified geometry независимо resample-ятся к одному N и
передаются в существующие timelines. Comparison PNG показывает обе geometry и оба actual
Fourier/trace frames; summary фиксирует tolerance, point reduction, discrete retained-segment
deviation, sampled RMSE и reconstruction RMSE против одной baseline reference. Значение `0`
удаляет только exact collinear/duplicate interior points. `--simplification-budget` ограничивает
distance evaluations; invalid/resource failure не создаёт partial output и не включает silent
fallback на original. Curvature-aware simplification и adaptive sampling остаются отдельными stages.

При `--adaptive-curvature-weight 0..100` normalized contour отдельно проходит weighted arc-length
sampling: discrete turning angle увеличивает positive segment density, но output всегда содержит
ровно N ordered samples, сохраняет open endpoints или closed start/closure. Значение `0` и all-zero
curvature используют explicit `uniform_arc_length_zero_adaptive_signal` provenance. Comparison PNG
показывает uniform/adaptive samples и actual timelines при одинаковых N/K/speed. Adaptive и
simplification options в одном invocation запрещены; default contour path не изменён.

## Image-to-Fourier MVP

FS-013 объединяет безопасный импорт, промежуточные изображения, dominant contour и фактический
endpoint trace на одной четырёхпанельной Matplotlib surface. Интерактивный запуск принимает явно
выбранный локальный PNG/JPEG; обработка начинается кнопкой `Process` или клавишей Enter:

```powershell
uv run python -m fourier_sketch.cli.image_mvp input.png
```

Surface показывает grayscale, binary threshold, edge map с выбранным dominant contour и тот же
`EpicycleTimeline`, который рисует circles/vectors/endpoint/trace. Доступны threshold,
median/autocontrast/invert, explicit threshold-boundary/Canny selector, sample/harmonic/speed,
Play/Pause/Restart; Esc отменяет обработку, Space переключает play/pause. Canny thresholds,
aperture/gradient и boundary connectivity задаются CLI options при запуске.

Для автоматизации живой путь работает headless через тот же application controller:

```powershell
uv run python -m fourier_sketch.cli.image_mvp input.jpg --headless --output image-mvp.png --algorithm canny --canny-low 50 --canny-high 150 --samples 256 --harmonics 25 --frames 60
```

`no contour` сохраняет явный recovery PNG без Curve/timeline; corrupt/unsupported input завершает
команду с кодом `2` и не публикует partial artifact. Существующий output сохраняется без
`--overwrite`. Limits остаются прежними: PNG/JPEG, 25 MiB encoded, 40 MP decoded, 250 000 edge
pixels, 25 000 candidates и 100 000 aggregate contour points. MVP выбирает только крупнейший
внешний contour; skeleton, multiple components и arbitrary-photo cleanup отложены.

## Skeletonization diagnostic

FS-014 принимает тот же безопасно декодированный локальный PNG/JPEG, строит FS-010 binary raster
и применяет только explicit `scikit-image 0.26.x` Lee skeletonization:

```powershell
uv run python -m fourier_sketch.cli.skeleton input.png --output skeleton.png
uv run python -m fourier_sketch.cli.skeleton input.png --mode preview --output skeleton-preview.png
```

Первый режим атомарно экспортирует same-sized binary skeleton, второй — actual two-panel
source/skeleton preview. Summary содержит basename, algorithm/backend provenance, dimensions и
source/skeleton pixel counts; full path и pixel payload не выводятся. Empty foreground является
успешным пустым skeleton. Существующий destination не перезаписывается без `--overwrite`.

Сохраняются лимиты FS-010: 25 MiB encoded и 40 MP decoded. Дополнительно skeletonization допускает
не более 4 000 000 foreground pixels. Недоступный, несовместимый или malformed backend завершает
команду с кодом `2`; Zhang/OpenCV или другой algorithm не подставляется.

## Skeleton graph diagnostic

FS-015 строит explicit components, endpoints, compressed junction regions, degree-2 chain edges и
pure-loop anchors по fixed `corner-suppressed-8-v1` adjacency. Canonical JSON является storage и
diagnostic format, но не задаёт traversal order:

```powershell
uv run python -m fourier_sketch.cli.skeleton_graph input.png --output skeleton-graph.json
uv run python -m fourier_sketch.cli.skeleton_graph input.png --mode overlay --output skeleton-graph.png
```

JSON содержит именованные raster coordinates `column`/`row`, FS-014 algorithm/backend provenance,
explicit component membership и exact node/edge pixel ownership. Overlay показывает compressed
edges по компонентам и отдельные markers endpoint/junction/loop/isolated; линии не являются
single-stroke route. Empty skeleton даёт валидный empty graph. Ограничения FS-015: не более
250 000 skeleton foreground pixels, 500 000 node+edge records и 32 MiB canonical JSON. Existing
output не перезаписывается без `--overwrite`; fallback adjacency/backend или implicit component
bridge отсутствуют.

## Piecewise component diagnostic

FS-016 преобразует каждый однозначно представимый graph component в отдельный `Curve`: simple
path, pure loop или isolated pixel. Компоненты не соединяются, а pen-up boundary хранится явно:

```powershell
uv run python -m fourier_sketch.cli.piecewise input.png --output piecewise.png
```

Diagnostic PNG рисует каждый segment отдельным artist. Branched/complex topology возвращает
`unsupported`, empty input — `empty`, cancellation — `cancelled`; partial `PiecewiseCurve` ни в
одном из этих состояний не публикуется. Forced routing реализован отдельно в FS-017, а Piecewise
Fourier реализован отдельно в FS-018.

## Forced cyclic route diagnostic

FS-017 предоставляет только явный `STRICT_SINGLE_CURVE` mode. Eulerian links проходят один раз,
non-Euler graph получает bounded tree T-join duplicates, а disconnected components и periodic seam
соединяются красными bridges с измеренной added length:

```powershell
uv run python -m fourier_sketch.cli.forced_route input.png --output forced-route.png
```

Overlay различает original/duplicated/bridge steps и показывает Fourier diagnostic того же closed
route. Baseline deterministic и bounded, но не заявляет global Postman/TSP optimality.

FS-029 добавляет selectable bounded heuristic, которая жадно соединяет odd vertices кратчайшими
путями по исходному graph. При её выборе создаётся один comparison PNG с baseline/improved route,
Fourier frames, duplicated/bridge/added cost, delta и временем routing:

```powershell
uv run python -m fourier_sketch.cli.forced_route input.png `
  --route-algorithm greedy_shortest_odd_pairing_v1 `
  --optimization-budget 100000 `
  --output route-comparison.png
```

Default остаётся `baseline_tree_t_join_v1`; budget exhaustion/cancellation не подменяются baseline
молча. Improved heuristic снижает стоимость на принятом asymmetric fixture, но не обещает улучшение
на каждом graph или global optimum. `PIECEWISE_DISCONNECTED` остаётся отдельным mode без bridges.

## Discontinuous Fourier diagnostic

FS-018 распределяет ровно заданный sample budget между independent segments, материализует
замыкание closed segments и хранит индексы/длину каждого межсегментного jump, включая periodic
last→first seam. Обе stroke policies используют один spectrum и timeline:

```powershell
uv run python -m fourier_sketch.cli.discontinuous --mode pen_up_rendering --output discontinuous.png
uv run python -m fourier_sketch.cli.discontinuous --mode strict_trajectory --output strict.png
```

`PEN_UP_RENDERING` рисует segments раздельно; `STRICT_TRAJECTORY` показывает весь periodic signal
с jump transitions. Same-budget comparison с explicit closed forced route доступен через
`compare_discontinuous_with_forced_route`; spectrum decay analysis относится к FS-019.

## Measured discontinuity spectrum

FS-019 публикует numeric amplitude/log-amplitude и measured retained-energy/RMSE sweep по explicit
K без asymptotic/Gibbs claims:

```powershell
uv run python -m fourier_sketch.cli.spectrum_analysis --output spectrum-analysis.png
```

Каждая точка хранит sample count, ordering, K и controlled log floor; PNG является только view над
immutable result. Continuous/forced comparison использует те же параметры и sample budget.

## Separate 2D Fourier image mode

FS-020 выполняет bounded grayscale `FFT2 → view/filter → IFFT2` отдельными raster/spectrum types:

```powershell
uv run python -m fourier_sketch.cli.fft2_image input.png --output fft2.png
```

Canonical coefficients unshifted; magnitude/log/phase views centered. Low/high-pass и selected
frequency policies записываются в result. Этот mode не создаёт 1D coefficients или epicycles.

## Проверки

```powershell
uv run pytest
uv run ruff check .
uv run mypy
py -3 ~/.codex/tools/validate_project_overlay.py .
```

## Структура контекста

- `specs/` — стабильные требования;
- `docs/` — архитектура, математика, дизайн, безопасность, тестирование и состояние;
- `prompts/STAGES.md` — единственный подробный каталог этапов;
- `src/fourier_sketch/` — domain/math, imaging contracts/Pillow/OpenCV adapters, project-owned
  routing policy, application use cases, presentation resources, renderer/CLI;
- `tests/` — smoke, unit, property, integration, component и live E2E executable contracts.

## Desktop GUI (FS-021)

Запуск source-run desktop workflow:

```powershell
uv run python -m fourier_sketch.cli.desktop
```

В окне можно нарисовать freehand stroke либо выбрать локальный PNG/JPEG. Image path использует
существующий validated image-to-contour application flow в background worker; epicycle canvas
показывает готовый contour, rotating vectors и moving endpoint без дублирующего trace-шлейфа.
Desktop speed slider ограничен `0.01..1.00×` и меняется шагом `0.01×`. Application endpoint ledger
сохраняется для parity/export. Wheel, zoom slider и touchscreen pinch используют один bounded
`0.01..100.00×` presentation zoom вокруг фиксированного центра: точка графика под центром canvas
остаётся на месте, а pan корректируется пропорционально; LMB drag и
one-finger touch перемещают только viewport. Новая freehand curve сбрасывает view к `1.00×`/нулевому
pan и сохраняет свой относительный размер и положение внутри исходного drawing field. `Original`
disabled/unchecked без ready curve и затем точно отражает видимость исходного слоя. Vector/circle
каждой harmonic pair имеют стабильный различимый
rainbow color по selection order. Другие workflow pages и installer пока disabled/deferred.

Basis выбирается до рисования stroke. `DCT-II` и `Walsh-Hadamard` используют тот же `Terms`,
Play/Pause/Restart, speed и navigation surface, но Fourier-only Inspector/Solo/Build-Up/
Educational/export для них заблокированы. В `HARMONIC PLAYGROUND` кнопка входа создаёт canonical
circle; поля `k`, `Amplitude`, `Phase (degrees)` и `Add / update k` добавляют или меняют компоненту,
а Remove/Clear/Reset управляют набором. Суммарная amplitude ограничена `8`, поэтому недопустимое
изменение отклоняется без потери предыдущего набора.

После построения timeline страница EXPORT позволяет сохранить current Curve и ordered selected
coefficients как versioned JSON/CSV, reconstruction/spectrum PNG или bounded animated GIF. GIF
использует тот же chain/endpoint path, хранит endpoint-history metadata и ограничен `2..120`
кадрами по `20..1000 ms`. Existing destination заменяется только после явного подтверждения;
cancel/failure не публикуют partial artifact. MP4 отображается как unavailable, потому что reviewed
codec backend пока не выбран; silent fallback в GIF отсутствует.

## Hardening evidence (FS-023)

```powershell
uv run python tools/fs023_hardening.py
uv run coverage erase
uv run coverage run -m pytest
uv run coverage report
uv build --wheel
```

Harness записывает named Windows/Python/NumPy/PySide6 environment, large-N FFT round-trip,
stress-K timeline, Python allocation peak и offscreen QPainter timings. Offscreen measurement не
является manual visible GUI/DPI evidence. Coverage baseline составляет 76% branch-aware при floor 75%.
Поддерживается recoverable source wheel/source-run workflow; bundled desktop installer и public
redistribution не выбраны, пока отсутствуют project-license/third-party-notice и PySide6 LGPL
compliance decisions.

## Ограничения

Matplotlib diagnostics остаются поддерживаемыми diagnostic adapters. FS-021 добавляет source-run
PySide6 shell, FS-022 — local data/PNG/GIF export, FS-023 — measured hardening и проверяемый
source wheel, FS-024 — read-only inspector выбранной гармоники, а FS-025 — single-frequency Solo
analysis с точным baseline restore. FS-032/FS-033 добавляют Haar, DCT-II, Walsh-Hadamard и ручную
Fourier-песочницу без утверждения, что один basis универсально лучше другого. Bundled installer и
MP4 ещё не реализованы.
Freehand input, единый Matplotlib MVP, arc-length resampling, безопасный image preprocessing, два
edge intermediate и single dominant contour-to-trace реализованы как проверяемые vertical slices.
Cohesive image MVP, Lee skeleton diagnostic, traversal-neutral graph, PiecewiseCurve conversion,
explicit forced route, discontinuous Fourier и bounded GIF export реализованы; MP4/additional codecs
остаются planned.
Reference DFT ограничен correctness-сценариями и не включается как silent fallback. Проект не
обещает идеальную векторизацию произвольных фотографий или оптимальный single-stroke route.

После desktop hardening roadmap содержит planned `FS-031`: offline Android MVP, где finger/stylus
stroke проходит тот же Fourier/epicycle contract и анимирует фактический endpoint trace. Mobile
framework пока намеренно не выбран до capability/performance/packaging evidence.
