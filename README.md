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
PNG/JPEG input, grayscale и threshold intermediate. Stage `FS-011` добавляет два явно разных edge
mode без contour interpretation: project-owned binary boundary и OpenCV Canny.

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
result; contour/curve появятся только в FS-012.

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
- `src/fourier_sketch/` — domain/math, imaging contracts/Pillow/OpenCV adapters, application use cases,
  presentation resources, renderer/CLI;
- `tests/` — smoke, unit, property, integration, component и live E2E executable contracts.

## Ограничения

Diagnostic Matplotlib surface является временным рабочим UI, а не финальным PySide6 shell.
Freehand input, единый Matplotlib MVP, arc-length resampling, безопасный image preprocessing и два
edge intermediate реализованы как проверяемые vertical slices. Contour interpretation, product GUI
и animation export остаются planned.
Reference DFT ограничен correctness-сценариями и не включается как silent fallback. Проект не
обещает идеальную векторизацию произвольных фотографий или оптимальный single-stroke route.
