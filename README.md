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
```

Summary показывает только output basename, выбранный algorithm, bounded backend identifier,
aggregate candidate/point/sample/trace counts. Пустая edge map или только degenerate fragments
возвращают явный успешный no-contour state без Curve, timeline и PNG. Backend failure и resource
limit дают controlled exit `2`; другой contour algorithm не подставляется. Stage выбирает ровно
один внешний contour: holes, disconnected components, skeleton и forced routing остаются deferred.

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
одном из этих состояний не публикуется. Forced routing и Piecewise Fourier остаются FS-017/FS-018.

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

## Ограничения

Diagnostic Matplotlib surface является временным рабочим UI, а не финальным PySide6 shell.
Freehand input, единый Matplotlib MVP, arc-length resampling, безопасный image preprocessing, два
edge intermediate и single dominant contour-to-trace реализованы как проверяемые vertical slices.
Cohesive image MVP, Lee skeleton diagnostic, traversal-neutral skeleton graph и explicit
PiecewiseCurve conversion реализованы; forced routing, PySide6 product GUI и animation export
остаются planned.
Reference DFT ограничен correctness-сценариями и не включается как silent fallback. Проект не
обещает идеальную векторизацию произвольных фотографий или оптимальный single-stroke route.
