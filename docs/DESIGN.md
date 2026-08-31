# UI/UX contract Fourier Sketch

## Статус

FS-006 реализовал временную diagnostic Matplotlib surface и headless PNG, а FS-007 — фактический
freehand canvas на том же renderer path. FS-021 добавляет source-run PySide6 shell: SOURCE page,
disabled future workflow pages, mouse freehand/image selection, central resizable Epicycles canvas,
keyboard-focusable controls, visibility checkboxes and `en`/pseudo resources. Desktop показывает
готовый contour и moving endpoint без дублирующего persistent trace-шлейфа. Speed ограничен
`0.01..1.00×` с шагом `0.01×`. Image work runs in a single worker; cancel publishes a stable state
and no partial frame. Image picker defaults to a dark drawing on a light background (with an explicit
reverse-polarity opt-out), so a light image background cannot become the selected outer contour.
The canvas has presentation-only near-unrestricted `0.01..100.00×` zoom and resets every newly
accepted curve to `1.00×` with zero pan. For freehand input this baseline preserves the curve's
relative position and size inside the original drawing field instead of stretching its bounds to fill
the epicycle viewport. Wheel, slider and pinch keep the same scene-coordinate under the geometric
viewport center by scaling pan proportionally; left-button drag and one-finger touch remain the
explicit pan actions. Freehand screen coordinates
are converted to Cartesian Y before building a timeline,
so the contour has the same vertical orientation as the input stroke. The freehand field visual center
is Cartesian origin `O`, the head-to-tail chain start (including the stationary DC vector). Wheel zoom
and the slider stay synchronized. On touchscreen laptops, one-finger touch pans the epicycle viewport
and a two-finger pinch zooms around the fixed viewport center; pinch uses the same bounded zoom value as wheel
and slider. Each vector and its circle receives the same deterministic rainbow color by selection order,
and an existing selection position keeps its color when K grows; this is presentation-only. Reset clears
mouse/touch pan and returns every zoom input to `1.00×`. `Original` is disabled/unchecked without a
ready curve and thereafter exactly mirrors whether the original curve layer is visible. Cancel is
disabled until a background conversion job exists. FS-023 makes Cancel non-blocking and cooperative:
the UI suppresses late publication without `QThread.terminate()`, retains the worker until `finished`,
and defers final window close while that owned bounded worker remains alive.
FS-022 enables an EXPORT page after a timeline is ready. It offers current Curve JSON/CSV, current
ordered coefficient-selection JSON/CSV, reconstruction/spectrum PNG and bounded GIF. Frame count and
duration are explicit; progress/cancel use the existing worker lifecycle. MP4 remains visible but
unavailable with an explanation until a reviewed codec backend exists. Existing destinations require
an explicit overwrite decision and no failed/cancelled export is shown as completed.
The freehand field is vertically aligned with the epicycle viewport in the normal desktop layout; at
smaller window heights it remains usable instead of overlapping the source controls.

## Harmonic Inspector FS-024

- Ready desktop view показывает отдельную read-only inspector panel: keyboard-focusable ordered list
  и textual details выбранной гармоники.
- Row label содержит selection position и signed frequency `k`; detail labels показывают amplitude,
  phase, angular velocity и current complex local contribution. Color не является единственным
  носителем selection.
- Click рядом с видимым vector/circle выбирает ту же frequency; click вне harmonic geometry очищает
  selection. Pointer movement выше click threshold остаётся canvas pan и не меняет inspector.
- Arrow-key navigation списка использует стандартное Qt focus behavior. Empty/stale state показывает
  локализованное объяснение вместо старых значений.
- Animation обновляет только current contribution выбранного `k`; selection не ставит timeline на
  паузу и не меняет trace. Harmonic-count growth сохраняет доступный `k`, shrink очищает исчезнувший;
  новый source/timeline всегда начинает с empty inspector.
- Панель допускает text expansion и использует `en` resources с существующей pseudo-locale. Editing,
  Solo и Build-Up controls отсутствуют до FS-025/FS-026.

## Frequency Solo FS-025

- Inspector получает отдельные доступные mode label и кнопку `Solo` / `Exit Solo`. Вход разрешён
  только для выбранного signed `k`; FS-025 поддерживает ровно одну гармонику, multi-select отложен.
- Solo является analysis-проекцией текущего immutable baseline frame. Canvas показывает настоящий
  explicit active set `(k,)`: один vector/circle, его endpoint и reconstruction; отдельный Solo
  endpoint trace остаётся application ledger и по UI-FR-002 не рисуется. Это не visibility-only
  фильтр и не `K=1` prefix selection.
- Baseline timeline продолжает владеть полным spectrum/ordered selection, временем, speed,
  play/pause state и trace. Кнопка выхода раскрывает тот же baseline state, поэтому отдельный restore
  cache с риском потери состояния не нужен.
- При animation tick Solo projection пересчитывается для baseline time и накапливает только actual
  isolated endpoint. Restart начинает новый Solo trace с `t=0`; pause/speed работают как раньше.
- Пока Solo активен, harmonic slider и export navigation/action disabled с локализованным
  объяснением. Inspector остаётся привязанным к baseline list и выбранному `k`; новый timeline или
  stale/empty selection завершает/отклоняет Solo без публикации partial state.
- Явный текст `SOLO — k=…` и состояние кнопки являются non-color cues. Zoom/pan и visibility
  продолжают быть presentation controls и не входят в Solo state.

## Harmonic Build-Up FS-026

- Inspector panel получает Build-Up mode label, ordering combo, target N, dwell milliseconds и
  доступную кнопку `Start Build-Up` / `Exit Build-Up`. Start показывает `K=1` и state `running`.
- Existing Play/Pause context-sensitive resume/pause sequence; Restart возвращает `K=1`, очищает
  dwell/trace и оставляет sequence paused. Baseline timeline time/state/trace не изменяются.
- Canvas и inspector показывают exact first-K set выбранного ordering. Label отображает `K/N`,
  latest signed `k`, retained energy и measured RMSE; UI не обещает monotone RMSE.
- Каждый K имеет singleton mode-local trace, не рисуемый desktop canvas. За один QTimer tick
  выполняется максимум один K-step; smooth interpolation отсутствует.
- Build-Up и Solo mutually exclusive; harmonic slider, mode configuration и export disabled до Exit.
  Exit раскрывает exact latest baseline object, новый timeline очищает analysis session.

## Educational Mode FS-030

- Inspector получает отдельную Educational group с `Load circle lesson`, `Start/Exit`,
  `Previous`, `Next` и `Restart lesson`. Без ready canonical fixture Start/step controls disabled и
  показывают локализованное объяснение.
- Canonical fixture — actual closed 32-sample counter-clockwise unit circle и обычный Fourier
  timeline с одной dominant `k=1`; educational layer не хранит подменные coefficients/geometry.
- Шесть textual steps синхронно используют original sample, locked inspector row `k=1`, canvas
  vector/circle highlight, full head-to-tail chain, red endpoint и equality actual trace endpoint.
  Persistent trace path по UI-FR-002 не добавляется обратно на canvas.
- Lesson начинает existing timeline paused; Play/Pause обновляют actual frame без смены шага.
  `Alt+Left`/`Alt+Right`/`Alt+Home` не конфликтуют со sliders/list navigation. Harmonics, inspector
  retarget, Solo, Build-Up и export locked до Exit; zoom/pan/visibility остаются доступны. Новый
  timeline очищает lesson с explanation; Android/basis controls отсутствуют.

## Basis selector and Haar view FS-032

- Basis combo находится рядом с decomposition controls и default-ит в `Fourier epicycles`.
  Пользователь выбирает `Fourier epicycles` или `Haar wavelet` до завершения нового stroke;
  selection сохраняется при restart/error и никогда не меняется автоматически. С первого pointer
  sample до explicit Clear combo locked; Clear удаляет displayed result и снова открывает выбор, так
  что label никогда не расходится с basis уже отображаемого frame.
- Fourier path и labels остаются прежними. Haar path подписан `Haar wavelet reconstruction`, count
  control подписан `Terms`, а status показывает selected/total terms и active
  `scaling`/`detail level/location`; terms не называются harmonics/frequencies.
- Canvas в Haar mode рисует source curve, partial reconstruction и отличимый contribution active
  term. Circles/vectors/endpoint/trace и frequency inspector/Solo/Build-Up/Educational/export
  недоступны с локализованным explanation; zoom/pan и source/reconstruction visibility остаются.
- Play активирует terms в canonical root-scaling/coarse-to-fine order с base rate 4 terms/second,
  умноженным на существующий bounded speed `0.01..1.00×`; completion останавливает timer на `K=N`.
  Pause фиксирует текущий K, Restart возвращает K=1, count slider задаёт current `1..N`. Новый
  freehand stroke строится только выбранным basis adapter. Image input disabled при выбранном Haar
  с explanation; этот slice не делает silent Fourier image fallback и не расширяет raster pipeline.

## Indexed bases and Harmonic Playground FS-033

- Basis combo добавляет `DCT-II` и `Walsh-Hadamard` после Fourier/Haar. Оба режима используют тот же
  source lock/Clear lifecycle и отдельный reconstruction view: grey source, teal selected-term
  reconstruction и violet active indexed-term contribution. Terms/Play/Pause/Restart/speed/zoom/pan
  работают; circles/vectors/endpoint, inspector, Solo, Build-Up, Educational, image input и export
  disabled с basis-specific explanation.
- Sidebar получает отдельную страницу `Harmonic Playground`. В ней keyboard-focusable list хранит
  explicit row order, а поля `k`, amplitude и phase degrees позволяют Apply/update; Remove/Clear и
  Start/Exit являются явными действиями. Entry загружает один term `k=1, A=1, phase=0`.
- Каждая успешная edit операция перестраивает actual paused Fourier frame при `t=0`; central canvas и
  read-only inspector показывают exact authored coefficients/vectors. Harmonic-count, source/basis,
  Solo/Build-Up/canonical lesson/export locked. Generated `Original` скрыт и disabled, поскольку это
  synthesis, а не captured input. Exit возвращает exact prior normal result либо empty canvas.
- Zoom/pan не сбрасываются входом, edit или выходом. Color не является единственным cue: строки
  содержат signed `k`, amplitude и phase; status сообщает active term count/budget и mode. Invalid
  edit сохраняет предыдущий список и frame.

## Curve Simplification diagnostic FS-027

- Existing contour CLI получает opt-in `--simplify-tolerance`; без option UI/output остаются
  прежними. Отдельная PySide page и adaptive sampling не добавляются.
- Comparison PNG содержит original и simplified ordered geometry, а также baseline и simplified
  Fourier/trace panels. Цвет/линия и textual titles различают варианты без color-only semantics.
- Summary показывает algorithm/tolerance, points before/after, measured maximum/RMS deviation,
  length delta, sampled RMSE и обе reconstruction RMSE против baseline. Это diagnostics, не quality
  ranking.
- Invalid tolerance/resource/cancel/output state локализован, existing destination сохраняется;
  пользователь может повторить command без option и получить unchanged original path.

## Adaptive Sampling diagnostic FS-028

- Existing contour CLI получает отдельный opt-in `--adaptive-curvature-weight`; без option
  UI/output остаются прежними, совместное использование с `--simplify-tolerance` отклоняется.
- Comparison PNG показывает uniform/adaptive sampled geometry и два current Fourier frames при
  одинаковых N/K/speed. Summary называет algorithm, weight, policy, curvature/density range,
  spacing CV и reconstruction RMSE; universal improvement claim отсутствует.

## Route Optimization diagnostic FS-029

- Forced-route CLI сохраняет baseline default и получает explicit improved algorithm selector плюс
  bounded optimization budget. Improved selection создаёт comparison artifact/summary с названиями
  обеих policies, duplicated/bridge/added lengths, delta и measured routing time.
- Цвета original/duplicated/bridge и Fourier panel сохраняют FS-017 semantics. Baseline и separate
  piecewise command остаются доступны; timeout/resource/cancel не переключают algorithm молча.

## Diagnostic FS-006 — фактический baseline

- resizable Matplotlib canvas; manual layout `10×8`, controls под canvas, headless output `8×8`;
- Play, Pause, Restart; speed slider `0.1..100.0`; harmonic slider `1..min(N,4096)`;
- CheckButtons для circles, vectors, endpoint, trace, original и reconstruction;
- restart ставит `paused`, time `0` и оставляет ровно один новый endpoint в trace;
- status показывает state, time, K и speed; legend различает original/reconstruction/trace/endpoint;
- цвета: circles `#457b9d`, vectors `#1d3557`, endpoint `#d00000`, trace `#e76f51`,
  original `#8b95a5`, reconstruction `#2a9d8f`; линии/markers дополнительно различаются формой;
- axes сохраняют equal aspect и fit с margin; renderer не меняет curve/chain state при resize;
- labels берутся из `resources/en.json`; pseudo locale расширяет literals ASCII-markers
  `[!! … !!]`.

Ограничения diagnostic UI: нет workflow navigation, labels toggle, keyboard/accessibility layer,
reduced-motion integration, saved locale и production-grade inline errors. Они не объявляются
готовыми до FS-021; controlled CLI failures доступны уже сейчас.

## Freehand FS-007 — фактический baseline

- layout из двух panels: слева drawing axes со стабильными limits, справа существующая epicycle
  visualization;
- drag левой кнопкой начинает, продолжает и завершает один stroke; events вне drawing axes и
  другие кнопки не меняют capture;
- consecutive duplicate samples не накапливаются; one-point stroke остаётся валидной DC curve;
- open/closed semantics задаются явно до capture, output samples задаются в диапазоне `1..4096`;
- успешный pointer release сразу показывает фактический Fourier timeline frame и endpoint trace;
- `R` очищает source/result/trace для повторного ввода, `Esc` переводит незавершённый capture в
  controlled cancelled state;
- status/error/help strings берутся из locale resources; production/fallback locale — `en`.

FS-008 расширяет этот же workflow controls и live evidence, не создавая второй input/Fourier path.

## Freehand MVP FS-008 — фактический baseline

- Play/Pause/Restart расположены под drawing panel; speed и harmonic sliders — под render panel;
- controls до первого stroke безопасны и не создают timeline или placeholder result;
- speed/harmonic values, заданные до drawing, применяются при создании timeline;
- Pause сохраняет time/trace, Play продолжает тот же timeline, Restart сохраняет source stroke,
  ставит timeline на паузу при `t=0` и оставляет один actual endpoint в trace;
- harmonic change перестраивает selection/reconstruction/chain внутри существующего timeline и
  начинает trace с endpoint нового state;
- release coordinate внутри drawing axes принимается как последний point даже без отдельного
  motion callback.

## Arc-length selector FS-009 — фактический baseline

- RadioButtons `Index`/`Arc length` расположены под Play/Pause/Restart и принадлежат той же
  freehand surface;
- выбор до drawing задаёт method следующего result; выбор после valid stroke transactionally
  перестраивает его через существующий timeline;
- drawing status показывает selected method, mean spacing и CV, а не обещание «лучшего» результата;
- zero-length arc selection показывает controlled invalid state и возвращает selector к method,
  который соответствует сохранённому timeline; silent fallback отсутствует.

## Image preprocessing FS-010 — фактический diagnostic baseline

- локальный CLI принимает source, output, `grayscale|binary`, threshold `0..255`, fixed
  `none|median_3`, autocontrast, invert, overwrite и locale;
- success summary показывает только output basename, actual format, oriented dimensions и stage;
- invalid/corrupt/oversized/multiframe input получает localized controlled failure без full path,
  raw exception, metadata или pixel payload;
- grayscale и binary доступны как разные intermediates; invert не меняет grayscale;
- existing output требует явного `--overwrite`; contour controls не смешиваются с этим CLI и
  доступны в отдельном FS-012 diagnostic entry point.

## Edge detection FS-011 — фактический diagnostic baseline

- отдельный CLI выбирает `threshold_boundary|canny`; active algorithm и backend видимы в success
  summary и не маскируются общим названием «vectorization»;
- threshold-boundary показывает 4/8-connectivity, Canny — low/high, Sobel aperture и L1/L2 norm;
- параметры неактивного algorithm не валидируются как условие запуска выбранного режима;
- output — same-sized binary PNG и edge pixel count, но не contour/curve preview;
- empty edge map является успешным диагностическим состоянием; unavailable Canny показывает
  localized controlled failure без автоматического переключения на threshold boundary;
- existing output требует explicit `--overwrite`; full path, pixels и backend exception не
  выводятся.

## Dominant contour FS-012 — фактический diagnostic baseline

- отдельный localized CLI принимает safe image/edge options плюс `samples`, `harmonics`, `speed`,
  `frames` и `frame-delta`, затем рисует существующий epicycle frame в PNG;
- success summary показывает output basename, selected edge algorithm, bounded contour backend,
  aggregate candidate/contour/sample/trace counts, но не path или pixels;
- `no contour` является самостоятельным empty state: summary объясняет причину, output не создаётся;
- rendered frame переиспользует фактические original/reconstruction/chain/trace слои FS-006 и не
  вводит отдельную декоративную contour preview математику;
- existing output сохраняется без `--overwrite`; backend/resource/parameter failure локализован и
  не показывает raw native detail;
- этот отдельный diagnostic остаётся доступным; cohesive surface реализована в FS-013.

## Image-to-Fourier FS-013 — фактический cohesive MVP

- один launch/action flow принимает выбранный локальный image path и начинает operation через
  `Process`/Enter; Esc отменяет, Space переключает play/pause;
- layout `2×2`: grayscale, binary, edge map + orange dominant contour, затем actual
  epicycle/endpoint trace; нижняя строка постоянно показывает форматы, budgets и deferred scope;
- controls включают threshold, median/autocontrast/invert, explicit edge selector, samples,
  harmonics, speed и Play/Pause/Restart; algorithm-specific Canny/connectivity options также
  доступны в documented CLI invocation;
- `processing` отключает конфликтующие controls и включает Cancel; ready включает timeline
  controls; empty/error/cancelled показывают resource-based recovery message и снова разрешают
  explicit Process;
- background generation не публикует stale/partial result после Cancel; headless mode отображает
  ту же причинную цепочку в atomic four-panel PNG;
- `en` является production/fallback locale, algorithmic pseudo-locale проверяет expansion. Полный
  PySide6 navigation/accessibility/DPI shell остаётся FS-021.

## Skeletonization FS-014 — фактический diagnostic baseline

- CLI принимает локальный PNG/JPEG и явно выбирает один output mode: same-sized `skeleton` PNG
  либо two-panel `preview` PNG;
- preview показывает исходный binary raster и фактический Lee result рядом, а title/summary —
  algorithm, bounded backend provenance и source/result foreground counts;
- состояния `READY`, `EMPTY`, `ERROR`, `CANCELLED` различаются: empty не маскирует backend failure,
  cancelled не показывает partial result;
- сообщения локализованы через `en`/fallback/pseudo resources, success summary показывает только
  безопасный basename;
- graph endpoints/junctions и components добавлены отдельной FS-015 surface; route намеренно
  отсутствует до следующих stages.

## Skeleton graph FS-015 — фактический diagnostic baseline

- отдельный CLI выбирает ровно один `json|overlay` output, не меняя FS-014 skeleton command;
- overlay показывает Lee skeleton рядом с component-colored compressed topology; endpoint,
  junction region, loop anchor и isolated pixel имеют разные markers;
- canonical порядок component/node/edge и loop anchor являются диагностикой/storage, а не выбранным
  single-stroke traversal;
- summary показывает только aggregate counts и policy, а не source path/pixels;
- empty graph остаётся честным empty state; PiecewiseCurve и forced bridges не имитируются.

## Piecewise diagnostic FS-016

- слева показывается actual Lee skeleton, справа — domain-space segments;
- каждый segment имеет собственный color/artist, поэтому renderer не может нарисовать скрытый
  connector между components;
- footer показывает terminal status, segment count и число explicit pen-up boundaries;
- unsupported/empty/cancelled states объясняются на curve panel без fabricated partial curve.

## Принцип продукта

Главный визуальный объект — причинная цепочка:

```text
coefficient → rotating vector → next center → final endpoint → persistent trace
```

Пользователь должен одновременно понимать вклад harmonics и видеть reconstructed curve. Circles,
vectors и trace не являются независимыми декоративными слоями с разной математикой.

## Information architecture

Planned workflow pages:

1. `SOURCE` — freehand или локальный image input;
2. `MONOCHROME` — grayscale/contrast/threshold diagnostics;
3. `EDGES` — threshold boundaries/Canny;
4. `CONTOURS` — contour/components/routing policy;
5. `CURVE` — samples, open/closed/piecewise semantics и resampling;
6. `FOURIER SPECTRUM` — coefficients, ordering, retained energy, error;
7. `EPICYCLES` — central animation and inspection;
8. `EXPORT` — formats, destination, progress и failure provenance.

Page доступна только если её prerequisites существуют; disabled state объясняет требуемый input.

FS-018 diagnostic сохраняет это разделение уже в Matplotlib surface: заголовок явно называет
`strict_trajectory` или `pen_up_rendering`, source panel показывает соответственно один periodic
artist либо отдельный artist на segment, а spectrum panel остаётся общим. Переключение display
policy не пересчитывает samples, coefficients или endpoint history.

## Epicycles view

Обязательные controls:

- harmonic count и animation speed;
- ordering;
- show/hide circles, vectors, endpoint, trace, original, reconstruction, labels;
- Play, Pause, Restart;
- Export Animation только после соответствующего stage/capability.

Canvas contract:

- circle center совпадает с vector start;
- vector tip совпадает с vector end;
- следующий circle center следует за предыдущим tip;
- final endpoint заметен независимо от trace color;
- trace добавляет actual endpoint history;
- original/reconstruction overlays визуально отличимы и имеют legend/label.

## States

Для каждой page:

- `empty`: понятный следующий action;
- `ready`: input и parameters валидны;
- `processing`: progress + cancellation, controls не создают conflicting job;
- `paused`: timeline state сохраняется;
- `validation_error`: проблема ввода рядом с control;
- `runtime_error`: stable message code, recovery action и безопасная detail boundary;
- `cancelled`: partial result не выдан как completed;
- `completed`: result/provenance доступны.

## Layout и visual foundation

- desktop-first resizable layout: left workflow/controls, central canvas, optional right inspector;
- canvas сохраняет aspect ratio curve, имеет fit/reset view и numerically bounded near-unrestricted
  `0.01..100.00×` user zoom,
  который не меняет curve/chain/timeline state; wheel zoom, touchscreen pinch и slider используют одно
  синхронизированное значение и сохраняют scene-coordinate под центром canvas через пропорциональную
  коррекцию pan, LMB drag и one-finger touch меняют viewport,
  а reset возвращает zoom/pan к fixed-center `1.00×` baseline;
- typography, color tokens и spacing утверждаются при первом UI implementation на основе
  component evidence, не выдумываются bootstrap-документом;
- color не единственный signal; selected/failure/paused states имеют icon/text/shape;
- text expansion не перекрывает canvas controls; truncation имеет tooltip/accessible name.

## Input and error UX

Image limits показываются до dialog/processing where possible. Corrupt/oversized/no-contour cases
не ведут автоматически к другому algorithm; UI показывает фактический backend и recovery options.
Export overwrite требует явного выбора.

## Accessibility

- keyboard navigation для controls и workflow pages;
- visible focus;
- label/control association и accessible names для canvas toggles;
- pause/restart доступны без pointer;
- animation учитывает reduced-motion preference, когда platform integration доступна;
- screen-reader summary может описать sample/harmonic count и endpoint state, не поток каждого
  animation frame.

## i18n/l10n delta

- initial production locale/fallback: `en`;
- pseudo-locale: test-only, с expansion и marked missing keys;
- locale resolution: explicit session/user choice → saved preference → OS hint if supported → `en`;
- RTL production locale не заявлена; direction-specific acceptance появляется вместе с такой
  locale, а layout остаётся построенным на framework layouts без ручного pixel positioning;
- formatted numbers presentation-aware, domain values остаются canonical floats/integers.

## Android touch surface (FS-031)

Desktop touchscreen navigation в FS-021 ограничена pan/pinch существующего epicycle viewport и не
реализует Android stroke/lifecycle surface ниже.

- primary canvas accepts a bounded finger/stylus stroke and exposes an explicit cancel state;
- completed stroke transitions to the same circles/vectors/endpoint/trace semantics as desktop;
- Play/Pause/Restart and harmonic/speed controls remain reachable in portrait and landscape;
- touch targets/content descriptions and interruption/background recovery are acceptance surfaces;
- image import, account/cloud sync and store-release UX are outside the MVP.

Implemented FS-031 layout uses one large focusable canvas, concise state summary,
Play/Pause/Restart and labeled harmonic/speed sliders. Before a stroke the canvas invites drawing;
after pointer-up it renders circles/vectors/endpoint/trace. Starting a new stroke atomically
replaces the prior result; cancel clears only in-progress input. Portrait stacks controls below the
canvas, while landscape keeps the canvas dominant without hiding primary actions.

## Responsive/performance behavior

Window resize не пересчитывает Fourier state. Rendering может downsample только display geometry
с явным provenance, не source result. Long work не блокирует interaction; frame-rate optimization
не меняет endpoint history semantics.
