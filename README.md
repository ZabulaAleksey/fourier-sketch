# Fourier Sketch

Fourier Sketch — поэтапно создаваемое desktop-приложение и математическое ядро для представления
плоской кривой комплексным сигналом `z(t) = x(t) + i y(t)`, анализа Fourier spectrum и анимации
цепочки вращающихся векторов. Конец последнего вектора является единственной drawing point для
анимационного trace.

## Текущее состояние

Реализованы каркас `FS-000`, domain model `FS-001`, transform slice `FS-002`, spectrum analysis
`FS-003`, partial reconstruction/metrics `FS-004` и epicycle mathematics `FS-005`.
Публичный пакет
`fourier_sketch.domain` предоставляет immutable `Point2D`, `Curve`, `PiecewiseCurve`,
Fourier coefficient/spectrum values, epicycle geometry и typed validation errors. Публичный
`fourier_sketch.math` выполняет complex conversion, canonical signed-frequency mapping, bounded
reference DFT, explicit NumPy FFT, IDFT, total spectrum energy и deterministic complete-spectrum
views: signed, absolute-frequency, amplitude, interleaved и explicit. Отдельный immutable
`CoefficientSelection` поддерживает first-K и explicit subset, continuous/sample-grid
reconstruction, retained energy и typed error metrics. `build_epicycle_chain` превращает selection
в renderer-ready head-to-tail state, чей endpoint равен reconstruction с учётом origin.

Следующий этап одобренной последовательности — `FS-006` (diagnostic Matplotlib renderer); он
начинается только после terminal evidence FS-005.

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
- `src/fourier_sketch/` — independent domain и numerical math layers;
- `tests/` — smoke, unit, property, integration и component executable contracts.

## Ограничения

Проект пока не имеет пользовательского entry point. Diagnostic rendering, mouse/image input, GUI
и export остаются planned.
Reference DFT ограничен correctness-сценариями и не включается как silent fallback. Проект не
обещает идеальную векторизацию произвольных фотографий или оптимальный single-stroke route.
