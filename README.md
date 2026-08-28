# Fourier Sketch

Fourier Sketch — поэтапно создаваемое desktop-приложение и математическое ядро для представления
плоской кривой комплексным сигналом `z(t) = x(t) + i y(t)`, анализа Fourier spectrum и анимации
цепочки вращающихся векторов. Конец последнего вектора является единственной drawing point для
анимационного trace.

## Текущее состояние

Реализован только каркас Stage `FS-000`: независимый Git-репозиторий, Python package scaffold,
воспроизводимое dependency-окружение, smoke contract и проектная документация. Domain model,
DFT/FFT, rendering, mouse input, image processing, GUI и export ещё не реализованы.

Следующий запланированный этап — `FS-001` (Domain Model). Он не начинается автоматически.

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

## Проверки Stage FS-000

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
- `src/fourier_sketch/` — production package, пока только scaffold;
- `tests/` — принятые executable contracts, пока smoke level.

## Ограничения

Проект пока не имеет пользовательского entry point и не строит Fourier coefficients. Заявленные
в roadmap возможности являются planned, а не implemented. Проект не обещает идеальную
векторизацию произвольных фотографий или оптимальный single-stroke route для любого изображения.
