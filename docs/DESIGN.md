# UI/UX contract Fourier Sketch

## Статус

FS-006 реализовал временную diagnostic Matplotlib surface и headless PNG, а FS-007 — фактический
freehand canvas на том же renderer path. Разделы ниже фиксируют реализованный UI; остальная
information architecture остаётся approved target для полного PySide6 shell `FS-021`.

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
- canvas сохраняет aspect ratio curve и имеет fit/reset view;
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

## Responsive/performance behavior

Window resize не пересчитывает Fourier state. Rendering может downsample только display geometry
с явным provenance, не source result. Long work не блокирует interaction; frame-rate optimization
не меняет endpoint history semantics.
