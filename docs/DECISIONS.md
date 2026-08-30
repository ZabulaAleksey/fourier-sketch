# Журнал архитектурных решений

## 2026-08-28 — ADR-001: Полный staged overlay без ранней product implementation

**Контекст:** Пользовательский brief описывает большой pipeline и прямо запрещает реализовывать
все функции одновременно.

**Решение:** Создать GREENFIELD repository как полный ДЕВ / КАРКАС overlay. Stage `FS-000`
содержит package/tooling/docs/smoke scaffold; первый product stage — `FS-001` и требует отдельного
запуска. `prompts/STAGES.md` — единственный detailed stage source.

**Рассмотренные альтернативы:** Сразу реализовать MVP; создать только README; копировать каждый
prompt отдельным файлом.

**Последствия:** Контекст больше минимального скрипта, но требования, DAG и completion evidence
разделены. Empty product directories и speculative code не создаются.

**Миграция / откат:** Удаление overlay не требуется; отдельный stage может быть пересмотрен через
SPEC/ADR до начала реализации.

## 2026-08-28 — ADR-002: Единая complex DFT convention

**Контекст:** Несогласованные signs/normalization ломают reconstruction и epicycle equivalence.

**Решение:** Использовать forward factor `1/N` и negative exponential, inverse positive
exponential без дополнительного factor; even-N Nyquist label — `-N/2`. Полный контракт хранится в
`docs/MATHEMATICS.md`.

**Рассмотренные альтернативы:** NumPy raw index convention без signed domain labels; symmetric
normalization; positive exponent forward transform.

**Последствия:** Все adapters сериализуют signed frequency явно. Любое изменение — breaking
mathematical contract с migration тестов/exports.

**Миграция / откат:** До product data нет миграции. После появления exports потребуется versioned
format и explicit converter.

## 2026-08-28 — ADR-003: Trace только из фактического chain endpoint

**Контекст:** Независимое вычисление decorative reconstruction может визуально расходиться с
показанной vector chain.

**Решение:** Math layer создаёт `EpicycleChainState`; interactive и exported trace append только
`state.endpoint`. Renderer не вычисляет coefficients/reconstruction.

**Рассмотренные альтернативы:** Отдельный fast reconstruction path в renderer; заранее
вычисленная polyline поверх декоративных circles.

**Последствия:** `BH-EPICYCLE-TRACE-001` становится property/integration/E2E contract. Performance
оптимизация обязана сохранять тот же state provenance.

**Миграция / откат:** Alternative renderer допустим только как adapter к тому же chain state.

## 2026-08-28 — ADR-004: `uv` и just-in-time dependencies

**Контекст:** Проект выбирает Python 3.12+ и требует воспроизводимого окружения, но поздние CV/UI
libraries не нужны bootstrap.

**Решение:** `uv` + `pyproject.toml` + `uv.lock` — единственный dependency contract. На FS-000
добавляются только build/test/lint/type tools. NumPy, Hypothesis, matplotlib, Pillow/OpenCV и
PySide6 добавляются в stage фактического использования после capability/license review.

**Рассмотренные альтернативы:** pip/requirements; добавить весь предполагаемый stack сразу;
Poetry.

**Последствия:** Lockfile изменяется по stages, dependency surface остаётся минимальной.

**Миграция / откат:** При несовместимости сохраняется текущий lockfile; silent switch manager
запрещён.

## 2026-08-28 — ADR-005: Initial product locale `en`

**Контекст:** Project context ведётся на русском, но user-facing desktop surface должна иметь
явный language/locale contract до первой строки UI.

**Решение:** Начальная production locale и fallback — `en`; strings живут в resources,
pseudo-locale проверяет expansion/missing keys. Дополнительные production locales не обещаны.

**Рассмотренные альтернативы:** Hardcoded English; использовать язык project docs как locale;
сразу поддержать `ru`/`uk` без утверждённых переводов.

**Последствия:** Stage `FS-006` включает минимальную рабочую locale boundary; Stage `FS-021`
расширяет её, но не создаёт впервые.

**Миграция / откат:** Новая locale добавляется ресурсами и tests без изменения math/application.

## 2026-08-28 — ADR-006: Явные Fourier backends и bounded reference oracle

**Контекст:** FS-002 требует одновременно прозрачную O(N²) формулу для доказательства корректности
и NumPy FFT для рабочего numerical path. Автоматический fallback способен скрыть backend failure
или случайно запустить квадратичную работу на большом input.

**Решение:** `reference_dft` и `fft_dft` являются отдельными public operations. Complete spectrum
хранит coefficients в FFT storage order с canonical signed labels. Public API возвращает built-in
complex/tuple/domain values. Reference path ограничен 2048 samples, NumPy path — 262144 samples;
оба fail closed на non-finite result. IDFT остаётся прозрачной reference reconstruction.

**Рассмотренные альтернативы:** Один auto-select API; silent NumPy→reference fallback; NumPy arrays
как public contract; неограниченный reference transform.

**Последствия:** Backend/provenance наблюдаемы, analytical oracle остаётся доступным и bounded.
Caller выбирает operation явно; future performance policy может добавить отдельный batch contract,
но не ослабляет текущий limit молча.

**Миграция / откат:** До persisted Fourier data миграции нет. Dependency rollback удаляет только
FS-002 implementation и generated lockfile delta после восстановления FS-001 checks.

## 2026-08-28 — ADR-007: Partial selection как value object и typed metric degeneracy

**Контекст:** FS-004 не может представлять partial set через `FourierSpectrum`, потому что complete
spectrum гарантирует ровно N canonical bins. Normalized error имеет zero centered-reference norm,
а retained energy — zero-total-energy случай.

**Решение:** Введён отдельный immutable `CoefficientSelection`. При связи со spectrum provenance
проверяется по immutable values (`sample_count`, frequency, coefficient value), не object identity.
Normalized error хранит status `defined`, `zero_reference_exact` или
`undefined_zero_reference`; silent `NaN` запрещён. Full zero-energy ratio равен `1`, partial — `0`,
но finite total energy валидируется до fast-path. Sample reconstruction bounded до 262144 points и
16777216 evaluated terms.

**Рассмотренные альтернативы:** Ослабить invariant `FourierSpectrum`; хранить reference identity;
возвращать `NaN`/`Inf`; считать любой zero-denominator error нулём; не ограничивать O(N×K) work.

**Последствия:** Selection безопасно переупорядочивается и передаётся в FS-005; equivalent immutable
data interoperable. Caller обязан обработать typed undefined normalized state и budget failure.

**Миграция / откат:** Persisted selection пока отсутствует. Изменение value provenance или limits
требует SPEC/ADR/test migration до появления session/export formats.

## 2026-08-28 — ADR-008: Immutable render frame и временный Matplotlib diagnostic UI

**Контекст:** FS-006 нужен runnable visual slice до PySide6, но renderer не должен стать вторым
источником Fourier/reconstruction/trace logic. Первая user-facing surface также требует locale и
safe output boundary.

**Решение:** Mutable `EpicycleTimeline` живёт в application и emit-ит immutable `EpicycleFrame`.
Trace append получает только `chain.endpoint`; visibility находится в frame. Matplotlib рисует
готовую geometry, interactive widgets вызывают controller, Agg headless использует тот же путь.
Strings загружаются из English JSON с algorithmic pseudo/fallback. PNG публикуется через temporary
sibling без implicit overwrite.

**Рассмотренные альтернативы:** Вычислять reconstruction в paint callback; хранить trace в
renderer; сразу добавить PySide6; hardcoded labels; использовать screenshot-only acceptance.

**Последствия:** Diagnostic UI полностью runnable и заменяем как adapter; FS-021 может сменить
presentation framework без изменения math/application contracts. Live CLI E2E является
acceptance evidence, screenshot — только visual QA.

**Миграция / откат:** Удаление Matplotlib adapter не меняет domain/math. Новый renderer обязан
потреблять `EpicycleFrame` и пройти те же endpoint/visibility/locale contracts.

## 2026-08-28 — ADR-009: Bounded freehand boundary и явный index-resampling baseline

**Контекст:** FS-007 должен принять реальные pointer events и построить runnable Fourier slice,
не смешивая mutable UI state с math и не выдавая index spacing за arc-length parameterization.

**Решение:** `FreehandCapture` живёт в application и хранит bounded state/provenance. Matplotlib
adapter только переводит actual callbacks в capture, а завершённый result передаёт в существующие
FFT, selection, timeline и renderer. Consecutive duplicates удаляются; baseline
`uniform_index` явно сохраняет open endpoints/closed seam, one-point input остаётся DC. Drawing
axes фиксируют data-coordinate limits на время capture. Limits: 10 000 input и 4096 output points.

**Рассмотренные альтернативы:** Вычислять FFT в event handler; хранить nullable/частичный timeline
в renderer; использовать autoscale во время stroke; молча downsample-ить input; назвать index
interpolation arc-length resampling.

**Последствия:** FS-008 расширяет тот же workflow, а FS-009 добавляет selectable arc-length method,
не меняя смысл существующего baseline. Capture/result можно тестировать без Matplotlib, тогда как
component/E2E evidence проходит через фактические callbacks.

**Миграция / откат:** Adapter можно заменить без изменения `FreehandCapture` и math contracts.
Изменение limits или значения `uniform_index` требует SPEC/ADR/test migration.

## 2026-08-28 — ADR-010: Arc-length как явный method с измеряемой, а не абсолютной quality

**Контекст:** FS-009 должен улучшить равномерность spatial samples, не меняя принятый FS-007
index baseline молча и не утверждая универсальное улучшение Fourier approximation.

**Решение:** `ResamplingMethod` содержит отдельные `uniform_index` и `arc_length`. Arc method
использует cumulative polyline length, explicit open/closed targets и тот же limit 4096. Typed
`CurveSpacingMetrics` сообщает mean/min/max/standard deviation/CV. UI method switch rebuild-ит
ready capture transactionally; zero-length arc failure сохраняет предыдущий согласованный result.

**Рассмотренные альтернативы:** Молча заменить index algorithm; автоматически fallback-нуться на
index при zero length; объявить меньший spacing CV доказательством лучшего Fourier result; добавить
adaptive/curvature sampling раньше FS-028.

**Последствия:** Оба method воспроизводимы и сравниваются на одном source. Arc-length гарантирует
uniform cumulative targets, но quality claims ограничены измеренными fixtures. One-point DC
остаётся доступным через index method; `N=1` non-zero arc result имеет typed unavailable spacing.

**Миграция / откат:** Default остаётся `uniform_index`, поэтому существующие callers не меняют
поведение. Удаление selector не меняет FFT/timeline contracts; изменение method semantics требует
SPEC/ADR/test migration.

## 2026-08-28 — ADR-011: Pillow-neutral raster contract и fail-closed PNG/JPEG adapter

**Контекст:** FS-010 должен декодировать недоверенные local images и публиковать диагностируемые
intermediates, но Pillow object не должен стать application/domain API, а широкий decoder registry
не должен автоматически активировать TIFF/EPS/WebP и другие parsers.

**Решение:** Pillow 12.3.0 становится direct dependency только внутри `imaging` adapter. Public
contract — immutable one-byte `RasterImage`, actual-format/dimension/EXIF provenance и stable
`ImageFailureCode`. Adapter проверяет 25 MiB до decoder, открывает immutable bytes только с
PNG/JPEG allowlist, проверяет 40 MP до `load()`, выполняет отдельный `verify()` pass, отвергает
multiframe и применяет EXIF transpose. Grayscale, fixed median 3x3, autocontrast и threshold/invert
остаются отдельными transforms. Retry и silent decoder fallback отсутствуют.

**Рассмотренные альтернативы:** Передавать Pillow objects через application; доверять extension;
использовать весь Pillow registry; добавить OpenCV до FS-011; хранить только final binary без
intermediate/provenance; молча брать первый animation frame.

**Последствия:** FS-011 получает backend-neutral grayscale/binary contract. Image bytes, full path
и EXIF payload не попадают в result/error. Двойное открытие одного memory payload стоит немного
CPU, но исключает file TOCTOU между verification и decode; budgets ограничивают память/работу.

**Миграция / откат:** Удаление direct Pillow и `imaging`/image CLI возвращает проект к FS-009 без
изменения curve/Fourier APIs. Изменение форматов, limits, first-frame или threshold semantics
требует SPEC/security/accepted-test migration.

## 2026-08-28 — ADR-012: Разные edge semantics и headless OpenCV Canny без fallback

**Контекст:** FS-011 должен дать диагностический edge intermediate для thresholded binary mask и
grayscale image. Эти алгоритмы имеют разные входы и результаты; единый auto-select API скрыл бы
semantics и сделал backend failure неоднозначным.

**Решение:** Project-owned NumPy transform возвращает foreground-side boundary бинарной маски с
explicit 4/8-connectivity и outside-as-background. Canny реализован отдельным лениво загружаемым
adapter к `opencv-python-headless` 5.0.0.93 с validated low/high, Sobel aperture и L1/L2 choice.
Оба возвращают immutable `EdgeDetectionResult`: same-sized binary raster, exact algorithm/backend,
typed parameters и source stage/dimensions. OpenCV unavailable/failure не переключает algorithm.

**Рассмотренные альтернативы:** Реализовать Canny самостоятельно; использовать full GUI OpenCV;
автоматически выбирать algorithm или fallback на threshold boundary; считать edge map contour;
возвращать raw NumPy/OpenCV arrays через application boundary.

**Последствия:** Диагностические результаты воспроизводимы и честно сравнимы, но не объявляются
эквивалентными или «лучшими». Headless wheel увеличивает runtime graph; его platform/license/
third-party notices проверяются в dependency contract. Empty edge map остаётся валидным output.

**Миграция / откат:** Удаление direct OpenCV отключает только Canny; project threshold boundary и
FS-010 остаются работоспособными без автоматического route change. Любое изменение edge semantics
или fallback требует SPEC/ADR/accepted-test migration.

## 2026-08-28 — ADR-013: Project-owned dominant contour и нормализованные pixel centers

**Контекст:** `findContours` возвращает backend-ordered raster sequences; их порядок, ориентация,
start point и pixel units не являются стабильным domain contract. FS-012 должен выбрать ровно один
contour и воспроизводимо передать его в уже проверенный Fourier path без скрытого bridge.

**Решение:** OpenCV используется только с `RETR_EXTERNAL` и `CHAIN_APPROX_NONE`. Adapter проверяет
typed binary input, native shape/dtype/bounds/adjacency/source-foreground binding, simple-cycle
uniqueness, edge density, candidate count и aggregate point budget. Project-owned routing выбирает minimum key
`(-abs(area2), -bbox_area, -point_count, canonical_signature)`. Closed sequence приводится к
counter-clockwise domain orientation и topmost/leftmost raster start. Pixel centers центрируются,
Y инвертируется, обе оси масштабируются одним `2/max(width-1,height-1)`. Затем применяется только
существующий arc-length resampling и timeline.

**Рассмотренные альтернативы:** `max(cv.contourArea)` с backend-order tie; `CHAIN_APPROX_SIMPLE`;
растянуть X/Y независимо; оставить pixel units; автоматически соединить компоненты; подменить
contour skeleton/convex hull; добавить второй CV backend.

**Последствия:** Результат инвариантен к backend candidate order, cyclic shift и reversal; Fourier
amplitudes выражены в нормализованной, а не pixel шкале. Holes и остальные disconnected external
components намеренно не входят в Curve. Empty/degenerate input возвращает typed no-contour result;
budget/backend failure остаётся ошибкой без alternate algorithm.

**Миграция / откат:** Удаление FS-012 contour/routing/application/CLI modules возвращает проект к
FS-011 и не меняет edge/Fourier contracts. Изменение selection key, transform ID, orientation,
start-point или budgets требует SPEC/ADR/accepted-test migration.

## 2026-08-28 — ADR-014: Generation-safe image MVP поверх существующего timeline

**Контекст:** FS-013 должен объединить decode/CV/Fourier path в отзывчивую Matplotlib surface, но
не переносить CV/math в callbacks и не публиковать поздний результат после Cancel или повторного
Process. Полный PySide6 worker framework относится к FS-021.

**Решение:** `ImageMvpController` владеет monotonic generation, отдельным cancel token и immutable
snapshot со states `initial|processing|ready|empty|error|cancelled`. Pipeline выполняется одним
`ThreadPoolExecutor` worker; publish разрешён только current generation с неустановленным token.
Renderer/CLI dispatch-ят application commands и используют тот же `ImageContourTimelineResult`,
`EpicycleTimeline` и `draw_frame`. Headless four-panel PNG остаётся explicit mode и публикуется
атомарно; no-contour получает recovery view, а не fabricated trace.

**Рассмотренные альтернативы:** Синхронно блокировать Matplotlib event loop; вычислять CV/Fourier в
widget callbacks; полагаться только на `Future.cancel()`; позволить late worker overwrite; создать
второй UI timeline; автоматически переключать Canny/threshold mode.

**Последствия:** MVP работает до PySide6 и одновременно формирует reusable view-state boundary.
Отмена cooperative: уже начатый native call может закончиться, но его result не публикуется.
Worker ограничен одним потоком; progress и guaranteed shutdown join остаются FS-021/FS-023.

**Миграция / откат:** Matplotlib image surface и CLI можно удалить без изменения FS-010–FS-012 или
math contracts. Изменение state/publication semantics требует SPEC/ADR/accepted-test migration.

## 2026-08-29 — ADR-015: Explicit scikit-image Lee skeleton без fallback

**Контекст:** FS-014 нужен реальный same-sized one-pixel skeleton из validated binary raster.
Project-owned thinning потребовал бы отдельной algorithm validation, OpenCV не предоставляет
эквивалентный core contract, а default 2D Zhang в scikit-image 0.26.0 имеет открытый upstream
дефект на некоторых dense masks.

**Решение:** добавить direct `scikit-image>=0.26.0,<0.27`, lazy-import backend и всегда вызывать
`skimage.morphology.skeletonize(..., method="lee")`. Adapter принимает только FS-010 binary
`RasterImage`, ограничивает foreground 4 000 000 pixels, сохраняет dimensions/source immutability,
валидирует bool shape и output-subset semantics и записывает `scikit-image/<version>` provenance.
Unavailable, несовместимый, failed или malformed backend возвращает typed failure; automatic
Zhang/OpenCV/project-owned fallback запрещён.

**Последствия:** graph topology не выводится из skeleton pixels до FS-015; cancellation остаётся
cooperative вокруг native call. Empty foreground является complete empty result. Patch-level
upgrade внутри 0.26.x требует frozen-lock regression suite; minor upgrade требует повторного API,
fixture, platform и license review.

**Миграция / откат:** persisted data отсутствует. Откат удаляет FS-014 adapter/controller/CLI,
direct dependency и lock graph; FS-010–FS-013 остаются рабочими. Пользовательские PNG не удаляются.

## 2026-08-29 — ADR-016: Corner-suppressed raster graph и traversal-neutral schema

**Контекст:** FS-015 должен сохранить topology Lee skeleton без ложных diagonal triangles,
неявного routing order и потери pure loops. Generic mutable graph или смешение raw pixels с
compressed nodes сделало бы будущие FS-016/FS-017 неоднозначными.

**Решение:** project-owned builder использует policy `corner-suppressed-8-v1`: orthogonal
foreground смежны всегда, diagonal — только когда оба общих orthogonal bridge pixels background.
Raw degree `0/1/2/>=3` означает isolated/endpoint/continuation/junction. Смежные junction pixels
объединяются в `JUNCTION_REGION`, maximal degree-2 chains становятся edges, pure degree-2 component
получает row-major `LOOP_ANCHOR` и canonical self-loop. Immutable undirected pseudomultigraph
сохраняет parallel/self edges, explicit components и exact disjoint foreground partition между
node-owned pixels и edge interiors. Schema `fourier-sketch/skeleton-graph-v1` сортирует данные
canonical, но serialization order не является route. Builder ограничен 250 000 foreground pixels
и 500 000 node+edge records; cancellation/failure typed, fallback отсутствует.

**Рассмотренные альтернативы:** 4-neighborhood с потерей diagonal strokes; обычная 8-neighborhood
с corner triangles; отдельный node на каждый junction pixel; NetworkX как accidental transitive
dependency; выбор loop start как route; автоматическое соединение components.

**Последствия:** topology и provenance воспроизводимы, все skeleton pixels traceable ровно один раз,
а FS-016/FS-017 получают явную component boundary без преждевременного traversal. Builder остаётся
линейным по raster/foreground adjacency и fail-closed при budget/cancellation/malformed topology.

**Миграция / откат:** persisted graph data до FS-015 отсутствует. Изменение connectivity policy,
compression, schema ID или budgets требует SPEC/ADR/accepted-test migration; откат удаляет только
FS-015 graph/application/diagnostic surface и не меняет FS-014 skeletonization.

## 2026-08-29 — ADR-017: One component — one segment без implicit routing

**Контекст:** `PiecewiseCurve` хранит независимые ordered `Curve`, но branched skeleton component
не имеет единственного порядка без выбора/дублирования graph edges. FS-016 должен показать
disconnected components с pen-up, не реализуя заранее forced routing FS-017.

**Решение:** graph component преобразуется в один segment только для simple open path, pure loop
или isolated pixel. Pure loop остаётся closed, path/isolated — open. Все components должны быть
представимы; иначе typed `UNSUPPORTED_TOPOLOGY` сохраняет graph provenance и не публикует partial
`PiecewiseCurve`. Segment ordering следует canonical component storage order, но не является
global route. Explicit boundary metadata хранит соседние component IDs и left/right endpoints;
renderer создаёт отдельный artist на segment без connector. FS-012 и FS-016 переиспользуют один
`pixel-center-centered-aspect-v1` transform; `1×1` raster получает scale `1.0` и origin.

**Рассмотренные альтернативы:** разрезать branch на несколько strokes; DFS/Euler traversal;
дублировать edges; соединять nearest endpoints; возвращать partial curve; использовать raw pixel
coordinates без aspect/y convention.

**Последствия:** two-circle/path input получает честный `PiecewiseCurve`, exact component/pixel
provenance и pen-up display. Branched input остаётся диагностируемым unsupported result до FS-017;
discontinuous Fourier не запускается до FS-018. Новая dependency не требуется.

**Миграция / откат:** persisted piecewise artifacts отсутствуют. Изменение representability,
ordering, coordinate transform или boundary schema требует SPEC/ADR/test migration; откат удаляет
FS-016 conversion/diagnostic surface и shared helper возвращается внутрь contour adapter.

## 2026-08-29 — ADR-018: Raw-pixel Euler route с bounded tree T-join

**Контекст:** compressed FS-015 graph сохраняет component topology, но переход между разными edge
contacts внутри multi-pixel `JUNCTION_REGION` нельзя восстановить непрерывно без raw adjacency.
FS-017 должен дать opt-in cyclic route для Fourier, показать duplication/bridge cost и не обещать
глобально оптимальный Postman/TSP result.

**Решение:** `corner-suppressed-8-v1` adjacency выносится в shared imaging helper и используется
FS-015 builder и FS-017 без расхождения policy. Component с 0 odd vertices проходит exact
Hierholzer circuit, с 2 — exact trail. Для `>2` odd vertices deterministic row-major spanning tree
образует linear T-join: parent edge дублируется тогда и только тогда, когда subtree содержит
нечётное число odd vertices; augmented multigraph затем проходит Hierholzer. Original и duplicate
edge instances имеют разную provenance. Disconnected components выбираются bounded greedy
nearest-entry policy с canonical ties; bridges, включая final seam, являются отдельными operations.
Route всегда `Curve(closed=True)`, а added cost равен сумме duplicated и bridge Euclidean lengths.

**Рассмотренные альтернативы:** traversal только compressed edges скрывает движение внутри
junction region; полный minimum Chinese Postman/TSP сложнее и не нужен baseline; удвоение всех
edges линейно, но создаёт заведомо больший cost даже когда T-join короче; open route оставляет
неизмеренный periodic Fourier seam.

**Последствия:** algorithm deterministic и `O(V+E+C²)` при component cap `1024`, route samples
ограничены FFT budget `262144`, cancellation проверяется bounded batches. Оптимальность не
заявляется; улучшение route относится к FS-029. Empty/cancelled/resource/malformed result не
публикует partial Curve.

**Миграция / откат:** новый route является opt-in и не меняет FS-015 graph или FS-016 Piecewise
semantics. Изменение adjacency, T-join, component tie-break, step provenance/cost или cyclic seam
требует SPEC/ADR/accepted-test migration.

## 2026-08-29 — ADR-019: Один discontinuous signal, две stroke policies

**Контекст:** PiecewiseCurve не содержит bridges, но DFT требует один periodic sample sequence.
Renderer не должен скрытно менять signal при переключении pen-up/strict display.

**Решение:** equal/proportional allocator детерминированно распределяет total samples с минимум
одним на segment и canonical remainder ties. Concatenated samples сохраняют boundary jump metadata,
включая last→first seam, и единожды поступают в существующие FFT/selection/chain APIs.
`STRICT_TRAJECTORY` рисует весь periodic signal, `PEN_UP_RENDERING` рисует segments отдельно;
coefficients, reconstruction и endpoint ledger общие.

**Последствия:** jumps являются математическим input, не artificial bridge. Allocation меньше числа
segments fail closed; spectrum-decay interpretation отложена до FS-019. Dependency не добавляется.

## 2026-08-29 — ADR-020: Recorded K sweep без asymptotic claims

**Контекст:** discontinuities дают измеряемое high-frequency content, но один bounded fixture не
доказывает общий закон decay или Gibbs theorem. Нужен reproducible analysis source of truth.

**Решение:** analysis хранит signed frequency, amplitude и `log10(max(amplitude, floor))`; floor
является recorded parameter. K sweep принимает explicit unique ascending values и одно explicit
ordering, затем переиспользует accepted selection, retained-energy и reconstruction metrics APIs.
Continuous comparison вычисляется тем же algorithm/parameters. Renderer только отображает result.

**Последствия:** zero amplitudes finite, каждая chart point traceable к K/order/floor/sample count.
Complexity bounded числом K и N; advanced asymptotic conclusions остаются deferred.

## 2026-08-29 — ADR-021: Dedicated shifted-view FFT2 model

**Решение:** 2D image mode использует separate immutable raster and spectrum values. NumPy `fft2`
и `ifft2` сохраняют default backward normalization; canonical coefficients unshifted, а centered
shift применяется только к magnitude/log/phase view и filter-mask coordinates. Axes всегда
`(row,column)`. Filters создают новый spectrum with recorded policy; 1D curve/epicycle types не
импортируются.

**Последствия:** CPU baseline bounded active decoded image limits; GPU/alternate backend fallback
отсутствует. Изменение normalization/shift/axis convention требует SPEC/ADR/test migration.

## 2026-08-29 — ADR-022: Optimize measured Qt renderer before framework migration

**Контекст:** FS-021 source-run PySide6 shell proves the desktop path, but animation smoothness is
limited by per-frame Python/QPainter work, complete trace redraw and a fixed 33 ms timer. Local
profile separates the fast numerical timeline from the presentation cost. A React Native rewrite
would also require a Windows/mobile graphics backend and a bridge or port of NumPy/CV/core.

**Решение:** сохранить Python domain/application source of truth. Сначала убрать redraw paused/
unchanged state, cache static paths/bounds, update trace incrementally with a bounded policy and
batch dynamic geometry. После before/after parity profile Qt Quick/QML scene graph допускается как
renderer adapter, если QWidget/QPainter не достигает declared budget. React Native не выбран как
desktop optimization; mobile framework FS-031 выбирается отдельным capability decision.

**Рассмотренные альтернативы:** немедленный полный React Native rewrite; повышение timer rate без
уменьшения frame work; перенос Fourier/CV logic в paint layer; преждевременный native/Rust rewrite.

**Последствия:** существующие math/application tests и source-run rollback сохраняются. Любой GPU/
QML/mobile adapter обязан доказать endpoint/frame parity и measured gain; framework migration не
может маскировать regression или переносить обязательную инфраструктуру в будущий stage.

## 2026-08-30 — ADR-023: Versioned atomic export and Pillow-only GIF baseline

**Контекст:** FS-022 должен экспортировать data/images/animation из уже проверенного desktop timeline,
не вводя второй Fourier/animation path. GIF обязателен, MP4 требует отдельной capability/license
проверки, а existing/partial destinations являются user-data boundary.

**Решение:** Curve и текущая ordered coefficient selection получают явные JSON/CSV schema version 1.
Reconstruction/spectrum PNG потребляют текущие immutable frame/selection. GIF строит bounded sequence
`2..120` из `build_epicycle_chain` для той же selection, накапливает только фактические endpoints и
кодируется already-pinned Pillow в sibling temporary file. Публикация атомарна; no-overwrite default,
overwrite explicit, cancellation проверяется между кадрами. Endpoint history сохраняется bounded GIF
metadata для reopen/parity evidence. MP4 backend отсутствует и объявляется unavailable без fallback.

**Рассмотренные альтернативы:** FFmpeg subprocess, imageio-ffmpeg и silent MP4→GIF fallback отклонены
без отдельного dependency/license/redistribution review; screen capture отклонён как второй renderer
path; unversioned ad-hoc JSON/CSV не обеспечивает migration contract.

**Последствия:** dependency graph не меняется, все exports локальные и воспроизводимые; GIF baseline
ограничен 120 кадрами и fixed renderer size. Выбор MP4 backend, повышение animation budgets или schema
version требует отдельного capability/security/compatibility решения.
