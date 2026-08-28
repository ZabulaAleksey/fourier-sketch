# Состояние проекта для ИИ

## Текущий этап

- Stage ID: `FS-000`
- Lifecycle: `implemented_unverified`
- Evidence level: `validated locally`
- Branch: `feature/project-bootstrap`

## Prerequisites и runnable path

- Prerequisites: none (GREENFIELD bootstrap).
- Primary vertical slice: clean checkout → frozen dependency restore → package import smoke →
  overlay validator.
- Concrete end-to-end PASS evidence: frozen restore, package smoke and overlay validator PASS on
  Windows / Python 3.12.5; commit gate remains pending.
- Future-stage dependency: none.

## Реализовано локально

- independent Git repository and protected-target workflow;
- Python 3.12 package/tooling scaffold;
- stable SPEC, architecture, mathematics, design, security, testing and dependency contracts;
- planned stage catalog/roadmap and context routing.

## Не реализовано

Product code Stage `FS-001+`: domain model, Fourier engine, epicycles, renderer, inputs, GUI,
image processing, routing, FFT2 и exports.

## Известные блокеры

- Terminal `FS-000` status ожидает local commit и повторный documentation/diff gate.

## Scaffold / temporary / deferred

- Scaffold: importable package with version only.
- Temporary implementation: none presented as product behavior.
- Deferred: all product stages `FS-001`–`FS-030`.

## Следующая рекомендуемая задача

Выполнить local commit Stage `FS-000`, повторить documentation/diff gate, затем только по явной
команде начать `FS-001`.

## Последние проверенные команды

```text
uv lock --check
result: PASS; 14-package lock graph current

uv sync --all-groups --frozen
result: PASS; Python 3.12.5, project-local .venv

uv run pytest
result: PASS; 1 smoke test

uv run ruff check .
result: PASS

uv run mypy
result: PASS; 2 source files

py -3 ~/.codex/tools/validate_project_overlay.py .
result: PASS; Project overlay OK

stage selector audit
result: PASS; 31 unique IDs, selector FS-001 unique

portability audit
result: PASS; no machine-specific paths in project source/context
```

## Последняя проверенная интеграция

- Initial empty main commit: `a2bda62`.
- Bootstrap content: validated but uncommitted at this snapshot.

## Синхронизация документации

- Updated: all initial canonical project sources.
- Checked without changes: none (new GREENFIELD overlay).
- Not created by design: ERROR_LOG/DEV_LOG and local agents/hooks/MCP/Skills.

## Заметки для следующей сессии Codex

Не доверять planned paths как implementation evidence. `docs/AI_PLAN.md` выбирает exact record
`FS-001`, но Stage не запускался.
