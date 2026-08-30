# UI/UX contract Fourier Sketch

## Статус

FS-006 реализовал временную diagnostic Matplotlib surface и headless PNG, а FS-007 — фактический
freehand canvas на том же renderer path. FS-021 добавляет source-run PySide6 shell: SOURCE page,
disabled future workflow pages, mouse freehand/image selection, central resizable Epicycles canvas,
keyboard-focusable controls, visibility checkboxes and `en`/pseudo resources. Desktop показывает
готовый contour и moving endpoint без дублирующего persistent trace-шлейфа. Speed ограничен
`0.10..1.00×` с шагом `0.01×`. Image work runs in a single worker; cancel publishes a stable state
and no partial frame. Image picker defaults to a dark drawing on a light background (with an explicit
reverse-polarity opt-out), so a light image background cannot become the selected outer contour.
The canvas has presentation-only `0.50..2.50×` zoom, persisted with desktop preferences, and a reset
to its `1.00×` fitted view. The mouse wheel zooms the canvas and left-button drag pans it; reset also
clears the pan. Freehand screen coordinates are converted to Cartesian Y before building a timeline,
so the contour has the same vertical orientation as the input stroke. Export remains deferred.

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
- canvas сохраняет aspect ratio curve, имеет fit/reset view и bounded `0.50..2.50×` user zoom,
  который не меняет curve/chain/timeline state; wheel zoom и LMB drag pan меняют только viewport,
  а reset возвращает zoom/pan fit baseline;
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

## Planned Android touch surface (FS-031)

- primary canvas accepts a bounded finger/stylus stroke and exposes an explicit cancel state;
- completed stroke transitions to the same circles/vectors/endpoint/trace semantics as desktop;
- Play/Pause/Restart and harmonic/speed controls remain reachable in portrait and landscape;
- touch targets/content descriptions and interruption/background recovery are acceptance surfaces;
- image import, account/cloud sync and store-release UX are outside the MVP.

## Responsive/performance behavior

Window resize не пересчитывает Fourier state. Rendering может downsample только display geometry
с явным provenance, не source result. Long work не блокирует interaction; frame-rate optimization
не меняет endpoint history semantics.
