# Учебный журнал Fourier Sketch

Здесь появляются только evidence-backed повторно полезные записи с полями Problem, Symptom,
Root cause, Failed attempts, Fix, Verification, Prevention и Links. Git history и обычный progress
сюда не копируются.

## 2026-08-28 — Fast-path не должен обходить численную валидацию

### Problem

- Full retained-energy ratio математически равен `1`, но исходная energy может не помещаться в
  finite `float` даже для coefficients с finite components.

### Symptom

- Full-selection fast-path возвращал `1.0`, тогда как тот же spectrum через `spectrum_energy`
  корректно давал typed overflow error.

### Root cause

- Algebraic shortcut выполнялся до проверки численной представимости denominator.

### Failed attempts

- N/A — дефект найден независимым read-only review до commit этапа.

### Fix

- Total energy валидируется до full/zero fast-path; добавлен regression test с `1e308` coefficient.

### Verification

```text
command / check: uv run pytest -q; uv run ruff check .; uv run mypy
result: PASS
scope: FS-004 unit/property/integration и full regression
caveat: limits остаются явной частью Python float/resource contract
```

### Prevention

- Любой shortcut для degenerate case выполняется только после тех validation checks, которые
  определяют допустимость общего результата.

### Links

- `src/fourier_sketch/math/metrics.py`
- `tests/unit/math/test_metrics.py`

## 2026-08-28 — Pseudo-locale должна быть безопасна для legacy console encoding

### Problem

- Expanded locale использовала Unicode brackets, которые Windows console с `cp1251` не могла
  вывести в live CLI E2E.

### Symptom

- PNG успешно создавался, но success message завершал process через `UnicodeEncodeError`.

### Root cause

- Diagnostic marker был визуально удобен, но не входил в гарантированный charset текущего
  console boundary.

### Failed attempts

- Первый live pseudo-locale E2E создал корректный artifact, но process вернул code `1` на print.

### Fix

- Pseudo/missing markers заменены на заметные ASCII `[!! … !!]` / `[missing:key]`; literals и
  placeholders продолжают проходить expansion/format tests.

### Verification

```text
command / check: uv run pytest -m e2e; uv run pytest tests/unit/presentation/test_i18n.py
result: PASS
scope: Windows live subprocess + resource formatting
caveat: additional production locales still require their own encoding/font/layout evidence
```

### Prevention

- Первый CLI surface проверяет не только resource lookup, но и фактическую запись localized output
  через platform-default subprocess console.

### Links

- `src/fourier_sketch/presentation/i18n.py`
- `tests/e2e/test_diagnostic_cli.py`

## 2026-08-28 — Численная и presentation boundaries требуют точных edge assertions

### Problem

- Формально правильный resampling и рабочий callback path теряли исходные coordinate invariants
  на крайних численных и presentation-сценариях.

### Symptom

- Subnormal open endpoint после interpolation становился `0`, а autoscale после первого press
  менял drawing transform так, что последующие реальные motion events оказывались вне axes.

### Root cause

- Последний open sample проходил через floating-point interpolation вместо точного source
  assignment; drawing axes не имели стабильной data-coordinate system на время capture.

### Failed attempts

- Первоначальный implementation прошёл обычные examples, но targeted Hypothesis и actual callback
  tests воспроизвели обе ошибки.

### Fix

- Open endpoints назначаются точно; drawing axes получают фиксированные limits до регистрации
  событий. Добавлены property и actual Matplotlib callback regression tests.

### Verification

```text
command / check: targeted FS-007 tests; uv run pytest; uv run ruff check .; uv run mypy
result: PASS
scope: resampling, capture, application pipeline, Matplotlib component/live E2E и CLI
caveat: uniform_index остаётся baseline; arc-length method относится к FS-009
```

### Prevention

- Для coordinate pipeline проверять не только приближённое значение, но exact endpoint/topology
  contracts и actual presentation callbacks со стабильным transform.

### Links

- `src/fourier_sketch/math/resampling.py`
- `src/fourier_sketch/render/matplotlib_freehand.py`
- `tests/property/test_resampling_properties.py`
- `tests/e2e/test_freehand_surface_e2e.py`

## 2026-08-28 — Pointer release является самостоятельным input event

### Problem

- Реальный drag может завершиться release coordinate, для которого framework не прислал отдельный
  последний motion event.

### Symptom

- В visual QA последний видимый release point отсутствовал в source stroke, хотя весь последующий
  Fourier/trace path работал корректно.

### Root cause

- Adapter завершал `pointer_up()` без попытки принять finite release coordinate из drawing axes.

### Failed attempts

- FS-007 tests всегда отправляли release в координате последнего motion, поэтому duplicate cleanup
  маскировал отсутствие самостоятельного release contract.

### Fix

- При release активный capture сначала принимает coordinate через тот же bounded `pointer_move`,
  затем переходит в READY. Outside-axes release по-прежнему только завершает текущий stroke.

### Verification

```text
command / check: FS-008 component actual-event test; full pytest; visual QA
result: PASS
scope: press → release без motion, ordinary drag, point budget и source provenance
caveat: platform pointer coalescing остаётся ответственностью Matplotlib backend
```

### Prevention

- Event-driven input tests должны отдельно покрывать press-only, press→release и
  press→motion→release sequences, а не считать motion обязательным перед release.

### Links

- `src/fourier_sketch/render/matplotlib_freehand.py`
- `tests/component/test_freehand_mvp_controls_component.py`

## 2026-08-28 — Равномерность sampling требует измеримого определения

### Problem

- «Более равномерная кривая» неоднозначна: equal source indices и equal traveled distance дают
  разные результаты, а визуальное впечатление не является quality contract.

### Symptom

- На source `x=(0,0.1,1,4)` index output имел spacing от `0.02` до `0.6`, хотя sample count был
  фиксирован и порядок сохранялся.

### Root cause

- `uniform_index` равномерно параметризует source vertex indices, а не cumulative segment length.

### Failed attempts

- N/A — stage contract заранее запретил считать arc-length универсально лучшим без метрики.

### Fix

- Добавлен explicit `arc_length` method и typed spacing metrics. На зафиксированном fixture при
  `N=16` index CV равен `0.917196816392`, arc-length CV — `0`.

### Verification

```text
command / check: unit/property comparison; actual selector integration/E2E; measured CLI snippet
result: PASS
scope: open/closed topology, zero length, same source/method comparison and endpoint trace
caveat: spacing CV не измеряет perceptual или Fourier reconstruction quality
```

### Prevention

- Любой future sampling quality claim должен называть metric, fixture, topology и baseline; новые
  algorithms не заменяют default молча.

### Links

- `src/fourier_sketch/math/resampling.py`
- `tests/integration/test_arc_length_freehand_pipeline.py`
- `tests/property/test_arc_length_resampling_properties.py`

## 2026-08-28 — Pillow verification и decode должны использовать независимые открытия bytes

### Problem

- PNG metadata/frame inspection может продвинуть или закрыть internal file pointer, после чего
  `verify()` уже не является корректным immediate operation.

### Symptom

- Первый FS-010 targeted run дал `RuntimeError: verify must be called directly after open` на
  обычном валидном PNG; binary exporter также ошибочно требовал grayscale stage.

### Root cause

- Один Pillow object одновременно использовался для metadata inspection, multiframe check и
  integrity verification; generic PNG export переиспользовал transform-only grayscale guard.

### Failed attempts

- Перенос multiframe check после verify не помог: `getexif()` на PNG тоже мог materialize state.

### Fix

- Immutable bounded payload открывается отдельно для immediate header `verify()` и отдельно для
  metadata/frame/full decode. Transform guard и generic raster-to-PNG conversion разделены.

### Verification

```text
command / check: FS-010 unit/integration/component/live E2E targeted suite
result: PASS — 39 tests after typed provenance/integrity review regressions
scope: PNG/JPEG, TIFF spoof, APNG, corrupt/truncated, 25 MiB/40 MP, EXIF, transforms, overwrite
caveat: contour/edge behavior не входит в FS-010
```

### Prevention

- Decoder integration tests должны использовать real format plugins и вызывать integrity API в
  документированном lifecycle; adapter types не должны сужать generic export semantics.

### Links

- `src/fourier_sketch/imaging/pillow_backend.py`
- `tests/integration/test_image_preprocessing_pipeline.py`
- `tests/e2e/test_image_preprocessing_e2e.py`

## 2026-08-28 — Параметры неактивного algorithm не должны блокировать выбранный path

### Problem

- Один CLI предлагает два edge algorithm с разными input stages и наборами параметров.

### Symptom

- Первая композиция CLI создавала оба parameter object до dispatch; невалидный Canny threshold
  мог бы остановить явно выбранный `threshold_boundary`, хотя Canny не запускался.

### Root cause

- Presentation boundary валидировал общий namespace аргументов вместо active capability contract.

### Failed attempts

- Общий eager construction выглядел компактно, но делал независимые algorithms неявно связанными.

### Fix

- CLI сначала разрешает selected algorithm и конструирует только его typed parameters;
  application dispatch сохраняет отдельные binary/grayscale paths без fallback.

### Verification

```text
command / check: FS-011 unit/application/component/live E2E targeted suite
result: PASS — explicit algorithms, invalid Canny parameters and no-fallback failures
scope: threshold boundary, OpenCV Canny, localized CLI and diagnostic PNG
caveat: edge map не является contour до FS-012
```

### Prevention

- Multi-backend CLI валидирует shared input отдельно, а backend-specific options — только после
  explicit selection; inactive backend не становится скрытой prerequisite.

### Links

- `src/fourier_sketch/cli/edges.py`
- `src/fourier_sketch/application/edge_detection.py`
- `tests/component/test_edge_cli_component.py`

## 2026-08-28 — Ненулевая contour area не доказывает замкнутую topology

### Problem

- `findContours(CHAIN_APPROX_NONE)` может представить тонкий открытый L/T fragment как
  backtracking sequence с повторными pixels и маленькой ненулевой shoelace area.

### Symptom

- Первичная FS-012 реализация принимала такой candidate, неявно закрывала seam через `Curve` и
  создавала timeline, хотя forced routing и hidden connections отложены.

### Root cause

- Проверялись только adjacent/terminal duplicates, area и seam adjacency; non-terminal repeats,
  принадлежность points исходному foreground и content-independent timeline options отсутствовали
  в полном typed boundary.

### Failed attempts

- Synthetic square/zero-area line fixtures прошли, но не воспроизвели фактический OpenCV output
  для branched/open one-pixel fragments.

### Fix

- Usable candidate теперь является simple adjacent cycle с уникальными pixels; каждый point
  обязан ссылаться на `255` в source edge map. Реальные OpenCV L/T fragments дают `NoContourResult`.
- Timeline speed валидируется до CV-path даже для blank input. Retained geometry ограничена
  250k edge pixels / 25k candidates / 100k aggregate points до Python-object expansion.
- Path-derived success basename экранирует control/format/surrogate и bidi characters.

### Verification

```text
command / check: targeted FS-012 review regressions; full pytest; Ruff; mypy; frozen sync; overlay
result: PASS — 59 targeted, 358 full
scope: topology, source binding, resource budget, option consistency, terminal safety, live trace
caveat: multi-component/open-route semantics остаются deferred до FS-016/FS-017
```

### Prevention

- Для CV adapter тестировать не только идеальные shapes, но и actual backend representation
  открытых branches; topology contract должен быть сильнее одной area metric.

### Links

- `src/fourier_sketch/imaging/contour_model.py`
- `src/fourier_sketch/imaging/opencv_contours.py`
- `tests/unit/imaging/test_opencv_contours.py`
- `tests/integration/test_dominant_contour_pipeline.py`
