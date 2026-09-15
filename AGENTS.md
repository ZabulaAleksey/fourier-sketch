# Project instructions — Fourier Sketch

## Назначение

`fourier-sketch` — поэтапный Python-проект для преобразования плоских кривых и
контуров изображений в комплексное Fourier-представление и для визуализации
head-to-tail epicycle chain. Глобальный Codex router действует как user layer
этой сессии; formal project DEV bridge отсутствует. Этот файл содержит
project-specific instructions без заявления полного overlay activation.

## Канонический контекст

- стабильные требования: `specs/system.spec.md` и `specs/features/*.spec.md`;
- архитектура и математика: `docs/ARCHITECTURE.md`, `docs/MATHEMATICS.md`;
- UI/UX и безопасность: `docs/DESIGN.md`, `docs/SECURITY.md`;
- тестовый контракт: `docs/TESTING.md`, трассировка — `docs/TRACEABILITY.md`;
- выбранный этап, текущий slice и подтверждённый статус: `docs/STAGES.md`;
- прежние детальные stage contracts для reference: `docs/notes/legacy-stage-contracts.md`.

Для stage-bound задачи прочитай только record с `Stage ID` из `docs/STAGES.md`.
Не реализуй возможности будущих stages «заодно».

## Неподвижные инварианты проекта

1. Во всех модулях используется Fourier convention из `docs/MATHEMATICS.md`.
2. Math layer вычисляет coefficients, vectors и chain state; renderer их только отображает.
3. В animation mode новая точка trace равна фактическому `EpicycleChainState.endpoint`.
4. Следующий epicycle начинается в конце предыдущего; vector ordering не меняет сумму выбранных
   coefficients в пределах установленного численного допуска.
5. `PiecewiseCurve` хранит настоящие разрывы; `PEN_UP_RENDERING` является presentation policy,
   а не скрытым bridge в математической модели.
6. 1D complex curve Fourier и будущий 2D image Fourier — разные модели и API.
7. Принятые tests/fixtures/goldens не изменяются в обычной реализации.

## Маршрутизация задач

- domain/Fourier/epicycle logic: затронутая feature-SPEC, `MATHEMATICS.md`, architecture и stage;
- image/contour/routing: image feature-SPEC, security limits, architecture и stage;
- renderer/UI/export: epicycle или desktop feature-SPEC, `DESIGN.md`, i18n/security и stage;
- изменение dependency: `docs/DEPENDENCIES.md`, architecture decision и lockfile evidence.

## Канонические команды

```powershell
uv sync --all-groups --frozen
uv run pytest
uv run ruff check .
uv run mypy
py -3 ~/.codex/tools/validate_project_overlay.py .
```

Добавляй dependency только в stage, где она реально нужна, и обновляй `uv.lock` только через
`uv`. Загружаемые файлы, export paths и metadata считаются недоверенными.

## Completion delta

Stage может получить terminal status только после PASS evidence своего runnable slice,
релевантных unit/integration/component checks, живого E2E где применимо, проверки diff и
Completion Documentation Synchronization Gate. Если primary path зависит от будущей стадии,
используй нетерминальный статус.
