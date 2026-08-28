# UI/UX contract Fourier Sketch

## Статус

UI ещё не реализован. Этот документ фиксирует approved target behavior из product SPEC, а не
утверждает наличие screens. Первый diagnostic user-facing surface планируется в `FS-006`, полный
PySide6 shell — в `FS-021`.

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
