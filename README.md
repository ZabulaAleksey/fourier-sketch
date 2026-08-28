# Fourier Sketch

Fourier Sketch — поэтапно создаваемое desktop-приложение и математическое ядро для представления
плоской кривой комплексным сигналом `z(t) = x(t) + i y(t)`, анализа Fourier spectrum и анимации
цепочки вращающихся векторов. Конец последнего вектора является единственной drawing point для
анимационного trace.

## Текущее состояние

Реализованы каркас Stage `FS-000` и domain model Stage `FS-001`. Публичный пакет
`fourier_sketch.domain` предоставляет immutable `Point2D`, `Curve`, `PiecewiseCurve`,
Fourier coefficient/spectrum values, epicycle geometry и typed validation errors. Domain model
локально проверен unit, integration и component contracts.

Следующий запланированный этап — `FS-002` (Complex Curve + DFT / IDFT). Он не начинается
автоматически.

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
- `src/fourier_sketch/` — production package и независимый domain layer;
- `tests/` — smoke, unit, integration и component executable contracts.

## Ограничения

Проект пока не имеет пользовательского entry point и не вычисляет Fourier coefficients: domain
values не являются DFT/FFT implementation. Rendering, mouse/image input, GUI и export остаются
planned. Проект не обещает идеальную векторизацию произвольных фотографий или оптимальный
single-stroke route для любого изображения.
