# Fourier Sketch

Fourier Sketch — поэтапно создаваемое desktop-приложение и математическое ядро для представления
плоской кривой комплексным сигналом `z(t) = x(t) + i y(t)`, анализа Fourier spectrum и анимации
цепочки вращающихся векторов. Конец последнего вектора является единственной drawing point для
анимационного trace.

## Текущее состояние

Реализованы каркас `FS-000`, domain model `FS-001`, transform slice `FS-002`, spectrum analysis
`FS-003`, partial reconstruction/metrics `FS-004`, epicycle mathematics `FS-005`, diagnostic
renderer `FS-006` и bounded freehand input `FS-007`.
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

Текущий stage — `FS-008`: он превращает уже работающий freehand slice в единый управляемый
workflow с live E2E evidence. Arc-length resampling и image input остаются отдельными stages.

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

Доступны `--samples`, `--harmonics`, `--speed`, `--closed` и `--locale`. Левая кнопка рисует stroke,
`R` сбрасывает его, `Esc` отменяет capture. Input ограничен 10 000 pointer samples, а результат —
4096 samples; превышение budget завершается явным controlled state.

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
- `src/fourier_sketch/` — domain/math, application timeline/freehand, presentation resources,
  renderer/CLI;
- `tests/` — smoke, unit, property, integration, component и live E2E executable contracts.

## Ограничения

Diagnostic Matplotlib surface является временным рабочим UI, а не финальным PySide6 shell.
Freehand input реализован как проверяемый slice; единый MVP workflow относится к FS-008.
Arc-length parameterization, image input, product GUI и animation export остаются planned.
Reference DFT ограничен correctness-сценариями и не включается как silent fallback. Проект не
обещает идеальную векторизацию произвольных фотографий или оптимальный single-stroke route.
